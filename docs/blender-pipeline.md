# Blender → Web pipeline (Layer 1 → Layer 2 → Layer 3)

```
blender/rooms/<zone>/<zone>.blend
  │  blender -b … --python blender/tools/export_zone.py        (validate_zone.py runs first; errors abort)
  ▼
blender/exports/<zone>.glb          raw, unoptimised, gitignored
  │  node scripts/build-assets.mjs
  │    strip library-material textures → prune(keepLeaves, keepAttributes) → dedup → flatten
  │    → instance (EXT_mesh_gpu_instancing) → join static visuals per material → weld
  │    → KTX2: ETC1S baseColor/emissive, UASTC(+zstd, RDO) normal/ORM → Meshopt
  │    → glTF-Validator + contract checks (scripts/validate-assets.mjs) — errors fail the build
  ▼
public/assets/rooms/<zone>/<zone>.glb  +  public/assets/manifest.json (generated)
  │  runtime: src/loading/glbZone.ts (GLTFLoader + KTX2Loader worker + Meshopt WASM)
  ▼
ZoneInstance — identical contract to code-built zones (colliders, lights, bounds, spawn, probe)
```

## Commands

| Command | Does |
|---|---|
| `npm run build:assets` | Export + optimise + validate every zone in `blender/zones.json`, write the manifest |
| `npm run build:assets -- vip` | One zone |
| `npm run build:assets -- --skip-export` | Re-optimise existing `blender/exports/*.glb` without launching Blender |
| `npm run validate:assets -- public/assets/rooms/vip/vip.glb` | Validate an optimised GLB |
| `npm run author:vip` | Re-run the VIP bootstrap script (**overwrites** `vip.blend` — only before hand edits) |

Tools: Blender 5.2 (`blender` on PATH, or `BLENDER=/path`), KTX-Software 4.4.2 unpacked into
`.tools/ktx/` (official signed macOS pkg from github.com/KhronosGroup/KTX-Software, extracted with
`pkgutil --expand-full`; the build puts `.tools/ktx/bin` on PATH), glTF-Transform 4.5, gltf-validator.

## Exporter settings (export_zone.py)

GLB · +Y up (never pre-rotate) · **apply modifiers** (bevels/subdivision become geometry) ·
**custom properties → extras** · **punctual lights, lighting mode SPEC** (physical: candela = W ÷ 4π × 683;
author lights with `watts(candela)` or in Blender's W) · no cameras · no Draco/Meshopt at export
(compression is one decision, made in the optimise step) · objects in `_WIP*` / `_REF*` collections
are never exported.

## Contract details added in Phase 2

- **Library materials by name.** A Blender material named like an entry in
  `src/render/materialNames.ts` (e.g. `MAT_Wood_WalnutPolished`) is a *library material*: its
  textures are stripped from the GLB and the runtime substitutes the shared material (same look as
  code-built rooms, textures downloaded once). Give it textures in Blender for viewport preview
  only. Any other `MAT_<Surface>_<Variant>` (e.g. `MAT_Vip_Fire`) is zone-unique and ships as KTX2.
- **UV0 is in metres** for anything using a tiling library material (1 UV unit = 1 m).
- **SPAWN_** empties face along their **local +Z** (use a Single Arrow empty; rotate it to point into
  the room). **PROBE_** empties mark the reflection-probe capture point. **TRIGGER_<Zone>_Bounds** is
  the zone volume. **COLLIDER_** meshes must be axis-aligned boxes (Z rotations in 90° steps).
- **Light extras:** `castShadow: true` makes a light a candidate for the single shadow slot;
  `flicker: true` adds candle flicker. Range comes from the light's *Custom Distance*.
- **Instancing:** use linked duplicates (Alt+D) for repeated props — they become one GPU-instanced
  draw. Plain static visuals (`ROOM_/PROP_/TABLE_/CHAIR_` without extras) are merged per material.
- **Doors** stay owned by the neighbouring code zone for now; `DOOR_` nodes in GLBs are validated but
  not yet wired at runtime.

## Registering a zone

Add it to `blender/zones.json`, the master layout. Each entry has:
- a title, the blend path and a PascalCase zone segment;
- neighbours;
- an explicit world `transform { x, z, rotY }` (glTF axes; `rotY` a multiple of π/2, because colliders stay
  axis-aligned).

The build:
- refuses zones without a valid transform;
- writes the manifest entry (asset URL, bytes, hash, stats, transform);
- drops zones that are no longer in the registry.

At startup `src/world/zoneGraph.ts` builds the graph from the manifest alone. It makes neighbour links symmetric,
ignores neighbours that aren't built yet, and starts the player in the preloaded zone.

## Measured (Salon Privé demo)

Raw export 9.4 MB → optimised **661 KiB** (library textures stripped, 4 unique textures as KTX2,
Meshopt geometry) · 77 k triangles · 495 linked duplicates → 32 instanced draws · 222 → 70 mesh nodes
after static merge · in-browser: 134 draw calls (all passes), ~70 fps at 2× DPR.

## Baked lighting (Phase 3)

```
lobby.blend ──npm run bake -- lobby──▶ lobby_baked.blend + T_Lobby_Lightmap.png/.json ──build:assets──▶
  lobby.glb (TEXCOORD_1 on lightmapped meshes) + lobby_lightmap.ktx2 (UASTC, sRGB, mipmapped) + manifest.lightmap
```

- **Hybrid split.** The lightmap holds *indirect* light from every light and emitter, plus *direct*
  light from lights marked `bakeOnly` (sconces, lamps, newel lamps, moonlight). Dynamic lights
  (the chandelier and its shadow key) keep their direct light real-time, so specular highlights and
  moving shadows stay live and nothing is counted twice. Bake-only lights never reach the runtime
  LightPool, which frees slots for neighbouring zones.
- **Flagging.** Give architecture the custom property `lightmap` (the kit's `lightmap=True`). The bake
  applies modifiers, joins flagged objects per material, Smart-UV-projects a `Lightmap` UV layer,
  equalises texel density and packs one atlas. Moving things (door leaves), instanced props and
  small furniture are not lightmapped — they are lit by the dynamic lights and the reflection probe.
- **Units.** three.js adds a lightmap texel to *irradiance*; Cycles' diffuse-light pass is
  irradiance/π, and exported light power is W = 4π·cd/683. The bake scales lights ×683, encodes
  `v = clamp(E_π · s)` (s puts the 99.5th percentile at 1.0) as 8-bit sRGB, and records
  `intensity = π / s` for `lightMapIntensity`.
- **Runtime.** `glbZone.ts` gives every mesh with `uv1` a per-zone clone of its (library) material
  with `lightMap` on UV channel 1; clones share the library textures and only dispose the lightmap.
- **Cost.** 2048² at 256 spp on an M1 Max GPU ≈ 7 min. Rebake after changing lit geometry or lights.

## The whole mansion in Blender (Phase 6)

All eight zones are authored in Blender from shared modules in `blender/tools/`:

| Module | Contents |
|---|---|
| `kit.py` | geometry primitives (boxes, lathes, swept mouldings with mitres, curve tubes, 3D text, fluted shafts), lights in physical units, logic empties |
| `mansion.py` | the house's architectural vocabulary: dressed walls, doors (DOOR_ contract), plaques, sconces, windows, paintings (Met Open Access, true aspect), coffered ceilings, chandeliers, furniture, `AUDIO_` emitters |
| `casino_props.py` | game furniture: printed felt as flat Cinzel geometry, a modelled roulette rotor (one node with `extras.rotor`), physical slot reels, `INTERACT_` volumes with `casinoTable` extras |
| `author_lobby.py`, `author_hallway.py -- <hall_west\|hall_east>`, `author_room.py -- <poker\|blackjack\|baccarat\|roulette\|slots>`, `author_vip.py` | per-zone bootstrap scripts (re-running overwrites hand edits) |

`npm run bake:all` re-bakes every lightmapped zone (lobby 4096², others 2048²) and rebuilds all assets.
Zones attach to their parent's slot (`attach: { zone, slot }` → `LOBBY_SLOTS` / `HALL_SLOTS` in
`src/rooms/shared/layout.ts`); moving parts get a per-zone runtime module (`src/rooms/<zone>/runtime.ts`).
The code-built zones remain as fallbacks for any zone missing from the manifest.

Authoring notes learned the hard way:
- **Glass** — `K.material(..., alpha=0.18)` sets the Principled Alpha + Blended render method, which exports as
  glTF `alphaMode: BLEND`. An opaque dark "glass" pane hides everything behind it (the slot reels did).
- **Joined meshes** — `K.join_into` renames the resulting mesh to the object name; glTF-Transform names
  instance nodes after their mesh, so a leftover `…_01.001` mesh name fails the naming validator.
- **Small text on repeated props** — use `K.text(..., extrude=0, resolution=2)`; extruded, high-resolution
  curves multiply by every instance (the reel symbols were 1 M triangles before this).

## V2 realism pass (2026-09-30)

| Source | Script | Lands in | Used as |
|---|---|---|---|
| Poly Haven photoscanned models (CC0): Chesterfield, Louis XV sofa, bergère, carved console, ornate mirror, marble bust, porcelain horse, grandfather + mantel clocks, candelabra, chinoiserie vase, oil lamp, pedestal stand, leafy plant | `npm run fetch-models` (`scripts/fetch-models.mjs`) | `blender/props/polyhaven/<id>/` (glTF, 1k) | `K.import_prop(pid, key, …)` → one instanced prototype per zone; `Mansion.prop()` / `Mansion.place()` |
| The Met Open Access photographs of real antique carpets (CC0) | `npm run make-carpets` (`scripts/make-carpets.mjs`) | `blender/textures_src/carpets/T_<Rug>_*` (whole rugs) + library set `Carpet_Gul` (seamless tile, `textures.json`) | `Mansion.rug()` (gallery runners, lobby area rugs, with modelled fringes); `MAT_Fabric_CarpetCrimson/Forest` |
| Modelled flowers | `blender/tools/flora.py` | generated petal/leaf maps in `textures_src/flora/` | `flora.arrangement()` — ~165 roses + leaves + greenery, all instanced |

Contract notes:
- **`K.import_prop`** rotates a scan to face local +Y, puts its origin on the floor (or on the back plane for
  wall-hung pieces), applies scale to the mesh, renames materials `MAT_<Key>_<Part>`, converts glass
  transmission to alpha blend (no transmission pass at runtime) and can recolour via `tint` (exported as
  `baseColorFactor`). Scans are *zone* materials: their textures ship (KTX2) in the zone GLB.
- **New library material `MAT_Marble_Bardiglio`** (blue-grey marble) — `materialNames.ts`, `materials.ts`,
  `mansion.library_materials` updated together.
- **Carpets** keep the photographed design and colour; the pile (fibre normal, AO, roughness) is synthesised
  because museum photos are lit flat. Runners use the whole rug (borders + ends) at its true aspect.
- **Table chairs** are red velvet tub chairs (`Mansion.tub_chair`, barrel back with channel tufting), after the
  casino.png poker room; `dining_chair` is an alias so every table picked them up.
- **Gloss**: wood/leather/damask runtime finishes are satin (clearcoat 0.1–0.2, rough 0.4+); only marble keeps a
  polished clearcoat.
