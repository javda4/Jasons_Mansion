# CLAUDE.md — Mansion (Browser 3D World)

This file guides Claude Code in this repository. Read it fully before starting any task.

## 1. What this project is

A browser-based, first-person, explorable 3D casino set in an old-world French Riviera mansion
(1920s–1940s Riviera luxury, Belle Époque / Victorian architecture, classic European casino).
Visual language: dark polished wood, marble floors, brass and gold, chandeliers, velvet, ornate
doors, grand staircases, long hallways, warm cinematic lighting.

The mansion **is** the navigation system. Users walk from the entrance into the Grand Lobby, down
hallways, through doors, and up to tables. Casino games are interactive destinations inside that
world — never separate pages reached through flat menus.

**Primary focus: the world, not the games.** The main job is building the interactive,
photorealistic mansion environment — architecture, materials, lighting, streaming, navigation, and
interaction. Casino gameplay is secondary. Do not spend effort on game statistics, house-edge
tuning, payout tables, odds analysis, or rules completeness. Game logic only needs to be a small,
reasonably plausible **placeholder** (e.g. a basic shuffled deck for blackjack, a uniform 0–36
roulette spin, simple weighted slot reels) whose purpose is to demonstrate the
world → table → game hand-off. Keep placeholders behind the clean game interface (§9) so they can
be replaced later; when choosing where to spend time, always favour the environment.

**Priority order when trade-offs conflict:**
`REALISM → PERFORMANCE → MODULARITY → EXTENSIBILITY → GAME INTEGRATION`
Browser performance still beats raw polygon count: the target is "luxury cinematic environment",
achieved within a realistic real-time budget — not "low-poly browser game", and not an offline render.

**Entertainment / play-money only.** Never implement payments, deposits, withdrawals, or
real-money wagering. Any future real-money capability would require a separate server-side
backend and compliance architecture; it must never live in the client.

---

## 2. The core mental model (most important section)

Blender and the web runtime are **not** interchangeable environments. Never frame work as
"converting the Blender world into a website". The project is four layers with one-way contracts:

```
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│ 1. AUTHORING         │   │ 2. DELIVERY          │   │ 3. RUNTIME           │   │ 4. APPLICATION       │
│ Blender              │──▶│ glTF 2.0 / GLB       │──▶│ Renderer + engine    │──▶│ Interaction & game   │
│ (content pipeline)   │   │ + asset manifest     │   │ (Three.js/WebGPU —   │   │ systems (our code)   │
│                      │   │ (the contract)       │   │  pending decision)   │   │                      │
└──────────────────────┘   └──────────────────────┘   └──────────────────────┘   └──────────────────────┘
 .blend files, source        optimized, compressed,     loading, streaming,        player, interaction,
 textures, bake setups,      validated files that       rendering, culling,        zones, audio, UI,
 Python export tools         ship to the browser        collision queries          game sessions, net
```

What each layer owns, and what it must NOT do:

| Layer | Owns | Must not |
|---|---|---|
| **1. Authoring (Blender)** | Modeling, UVs, PBR materials, light/AO baking, LOD & collider authoring, naming, custom properties, export scripts | Be treated as the runtime. Blender-only features (procedural node trees, Cycles/EEVEE-specific shaders, unapplied modifiers, particles, volumetrics, geometry nodes) do **not** survive export — they must be baked to meshes/textures or re-implemented at runtime. |
| **2. Delivery (GLB + manifest)** | Geometry, PBR materials (glTF metallic-roughness), textures, node hierarchy, `extras` metadata, punctual lights, animations; manifest describes rooms, sizes, dependencies, priorities | Contain game rules or runtime logic. It is data only. |
| **3. Runtime (renderer/engine)** | Loading/decoding, scene graph, rendering, lighting, post, LOD switching, culling, streaming, collision/physics queries, spatial audio playback | Know casino rules. Know Blender. It reads the delivery contract only. |
| **4. Application (our code)** | Player controller, interaction framework, zone manager, game sessions, UI, audio design, debug tools, future networking | Depend on renderer internals where avoidable. Game engines (blackjack, poker, …) must not import the renderer at all. |

**How information crosses the boundaries — this is the contract:**

1. **Names** — Blender object/collection names follow the convention in §6. The runtime parses
   prefixes (`COLLIDER_`, `SPAWN_`, `DOOR_`, …) to decide how each node is treated.
2. **Custom properties → glTF `extras` → runtime `userData`.** Interaction metadata is authored in
   Blender as custom properties, exported via "Include › Custom Properties", and read by the
   interaction system. This is how objects declare themselves interactable without hard-coding.
3. **The asset manifest** — generated by the build pipeline, never hand-maintained for sizes/hashes.
   The runtime loads rooms from the manifest, not from hard-coded URLs.
4. **Events** — the runtime/application boundary to game systems is an event/command interface
   (e.g. `interaction:activated { interactionType, tableId, gameType }`), never direct calls into
   rendering objects.

When a feature request arrives, first decide **which layer it belongs to**. If it spans layers,
define the contract change (name prefix, `extras` key, manifest field, event) before writing code.

---

## 3. Current status & how to work

**Mansion (2026-10-07):** this folder (`~/Desktop/Mansion`) is a fork of CasinoV2 with a new direction: a real
French Riviera villa with casino games woven into fitting rooms, not a casino with mansion styling. Every room is
fully dressed as its real type (library, salon, ballroom, dining room, …). Night mood is kept. The plan, floor plan,
room dressing lists and phases (M0–M5) live in **`docs/mansion-plan.md`**; it overrides the casino-era layout below.
The `casino.png` reference still sets the mood, but not the layout.

**Inherited status (CasinoV2, 2026-09-30):** Phases 1–6 are complete and the **V2 realism pass** is in progress in this folder
(`~/Desktop/CasinoV2`). V1 (`~/Desktop/Casino`) is the frozen baseline that was first published.
The technology is decided and documented in `docs/architecture.md`:
- **Stack:** Three.js r186 `WebGPURenderer` (WebGL2 fallback) · TSL post stack (GTAO, SSR, TRAA, bloom, AgX)
  · TypeScript + Vite · Vitest · Blender 5.2 · glTF-Transform (KTX2 ETC1S/UASTC + Meshopt) · Cycles lightmaps.
- **World:** Lobby (hub, **no games**) → West/East Galleries → Poker, Blackjack, Baccarat, Roulette and Slot
  rooms, plus the Salon Privé. Every zone is Blender-authored, baked and streamed from the manifest.
- **Games:** placeholder engines (`src/games`) played on the 3D tables via `ANCHOR_` presenters (§9).

**Design direction the user has set (keep to it):**
- Photoreal over stylised. Nothing glossy: satin wood and walls (clearcoat ≤ 0.2); only marble stays polished.
- Real sources over procedural: photoscans (Poly Haven), real carpet photos (Met), the licensed pack (§6).
- Electric lights never flicker; only fire does. Gilt and brass are aged and rough, not mirror-bright.
- Card tables must read clearly while seated: no glare on cards (see §8 "Seated table lighting").
- Follow `casino.png` for mood (Persian runners, red velvet tub chairs, marble medallion floor).

### Making a change (the loop for future updates)

1. Decide the layer (§2). For a cross-layer change, update the contract (prefix / extras / manifest)
   *and* its validators in the same change.
2. Author content through the Blender scripts (never by hand in `public/assets/`):
   - game rooms: `blender/tools/author_room.py` + `casino_props.py`;
   - Salon Privé: its `vip_*.py` patch scripts;
   - lobby: `author_lobby.py` (casino era);
  - Mansion rooms: `author_<room>.py` (Stair Hall: `author_stair_hall.py`), with `floors.py` / `flora.py` /
    `mansion.py` as the shared kit. Placement comes from the `transform` in `blender/zones.json`;
    a `tableId` must be `<gameType>_<NN>`.
3. Lit zone changed? Re-bake it: `npm run bake -- <zone>`. Anchor-only changes can patch both
   `<zone>.blend` and `<zone>_baked.blend` and skip the bake.
4. `npm run build:assets -- <zone>`, then `npm run typecheck && npm test && npm run build`.
5. Verify in a browser with a fresh automation browser (see §15), seated at each affected table, and
   check the console.
6. Update `docs/` and this file in the same change.

For a *new* technology decision, the original rule still applies: research current docs first and record an
ADR / architecture section before substantial code.

### Mandatory order of work (implementation rule)

1. Inspect the repository — determine what already exists.
2. Research current technology (use WebSearch/WebFetch against official docs, release notes,
   changelogs, caniuse). Base decisions on documented capabilities, not memory.
3. Write the **architecture report** (`docs/architecture.md`) answering questions A–J in §4, with a
   recommendation and rationale for each, **before** substantial code. Present it to the user.
4. Create the initial project structure.
5. Build the smallest functional prototype for the current phase.
6. Verify it works (build passes, runs in browser, check console, measure FPS/draw calls).
7. Progressively add functionality.

**Do not generate large amounts of code at once. Do not sacrifice architecture for a quick visual demo.**

### Report at every major stage

- What was implemented
- Why it was implemented that way
- What files changed
- How to test it (exact commands + what to look for)
- What remains / known issues

### Development phases

| Phase | Goal | Key deliverables |
|---|---|---|
| **1 — Technical prototype** | Prove runtime fundamentals | App scaffold, renderer, first-person camera, WASD, mouse look, pointer lock, basic collision, lighting, one small primitive room, debug overlay |
| **2 — Blender pipeline** | Prove Blender → GLB → web end-to-end | Blender project structure, naming validation, Python export tooling, gltf-transform optimize step, KTX2, validation, manifest, loader. Demo: Blender model → GLB → walkable in browser |
| **3 — Grand Lobby** | Prove visual fidelity is achievable | Marble, wood, chandeliers, staircase, doors, furniture, baked + dynamic lighting, decorative architecture |
| **4 — Room system** | Prove streaming & transitions | Hallway, doors, zone load/unload, seamless transitions, interaction framework. Route: Lobby → Hallway → Poker Room |
| **5 — Game prototypes** | Prove world → game hand-off | Simple UI + lightweight placeholder logic for Poker, Blackjack, Baccarat, Roulette, Slots. Flow: approach table → prompt → E → game view. Keep it minimal; the hand-off matters, not the game depth |
| **6 — Polish** | Production quality | Materials, advanced lighting, environmental audio, animations, asset optimization, camera feel, loading optimization, responsive UI |

Do not skip ahead. Do not start NPCs, multiplayer, or mobile controls until asked.

---

## 4. Architecture report — questions that must be answered first

Write answers into `docs/architecture.md` (decisions as short ADRs in `docs/adr/` are welcome).
Evaluate honestly — **do not assume Three.js is the answer**; the layer model above is
engine-agnostic by design.

- **A. Runtime:** Three.js vs React Three Fiber vs Babylon.js vs PlayCanvas vs other. Weigh: rendering
  quality ceiling, WebGPU maturity, glTF/KTX2/Meshopt support, bundle size, control over the frame
  loop, ecosystem, maintainability. Consider that a game-style frame loop with imperative systems
  may fit poorly with React reconciliation — if R3F is chosen, justify it; React may still be the
  right choice for the 2D UI layer only.
- **B. Graphics API:** WebGL2 vs WebGPU vs WebGPU-with-WebGL2-fallback. Check current browser
  support (Chrome, Edge, Safari, Firefox; desktop and mobile) and what the chosen engine's
  fallback path actually supports (post-processing, shader authoring, compute).
- **C. Blender → browser pipeline:** exporter settings, optimization tooling (e.g. glTF-Transform),
  validation (Khronos glTF-Validator + our own checks), manifest generation, automation level.
- **D. Streaming:** zone graph, preload radius, priorities, unload policy, memory ceilings,
  how doors/portals hide loading.
- **E. Collision:** is a full physics engine needed? Compare custom capsule vs Rapier (WASM) vs
  three-mesh-bvh-style queries vs Cannon/Ammo. Consider stairs, doors, worker offloading, and
  future server-side reuse.
- **F. Lighting:** baked lightmaps/AO vs dynamic lights vs hybrid; environment maps/reflection
  probes; shadow strategy; tone mapping & color management; restrained post-processing.
- **G. Textures:** KTX2/Basis (ETC1S vs UASTC per map type), resolutions, atlasing, mipmaps.
- **H. Budgets:** realistic polygon / texture-memory / draw-call / download-size budgets (desktop
  first, mobile later). Record them in `docs/performance.md`.
- **I. Game separation:** how game engines stay independent of rendering and UI.
- **J. Multiplayer readiness:** what to do now so WebSockets / WebRTC / Colyseus-style
  authoritative servers remain possible later.

---

## 5. Target repository layout

Adjust if the architecture report finds something better; update this section if it changes.

```
/
├── CLAUDE.md
├── src/                         # LAYERS 3 + 4 (runtime + application)
│   ├── core/                    # app bootstrap, frame loop, event bus, config, service registry
│   ├── render/                  # renderer setup, post-processing, lighting, env maps, quality tiers
│   ├── world/                   # zone graph, zone manager (streaming), room activation
│   ├── loading/                 # manifest reader, asset loader, cache, priorities, retries
│   ├── player/                  # input mapping, character controller, movement tuning
│   ├── camera/                  # first-person camera, FOV, head bob (subtle), transitions
│   ├── physics/                 # collision world, queries (render-agnostic interface)
│   ├── interaction/             # raycast targeting, interactable registry, handlers by type
│   ├── rooms/                   # per-room runtime modules (animations, audio, special logic)
│   ├── games/                   # LAYER 4 game systems — NO renderer imports
│   │   ├── shared/              # GameSession, wallet (play chips), RNG, cards/deck utilities
│   │   ├── poker/  blackjack/  baccarat/  roulette/  slots/
│   ├── audio/                   # ambience zones, positional sources, mixer
│   ├── ui/                      # HUD (prompts, casino name, menu), game UIs, map (later)
│   ├── debug/                   # debug overlay & visualizers (stripped from production)
│   └── utils/
├── public/                      # LAYER 2 output only — generated, optimized, shipped
│   ├── assets/rooms/<zone>/     # <zone>.glb (+ LOD / collider GLBs if split)
│   ├── assets/props/            # shared reusable props (slot machine parts, chairs, chips)
│   ├── assets/env/              # HDR/KTX2 environment maps
│   ├── assets/audio/
│   └── assets/manifest.json     # generated
├── blender/                     # LAYER 1 — source of truth for content (never served)
│   ├── mansion/                 # master layout / blockout
│   ├── rooms/<zone>/            # one .blend per zone
│   ├── props/                   # linked-library reusable assets
│   ├── materials/               # material library .blend
│   ├── textures_src/            # full-res source textures (PNG/EXR/TIFF)
│   ├── exports/                 # raw, unoptimized exporter output (intermediate, gitignored)
│   └── tools/                   # Blender Python: validate, export, bake helpers
├── scripts/                     # Node pipeline (runs outside Blender)
│   ├── optimize-assets          # glTF-Transform: prune, dedup, weld, compress, KTX2
│   ├── validate-assets          # glTF-Validator + naming/extras/budget checks
│   └── build-assets             # orchestrates export → optimize → validate → manifest
└── docs/
    ├── architecture.md  blender-pipeline.md  asset-guidelines.md  performance.md
    ├── adding-a-room.md  adding-a-game.md  adding-a-blender-asset.md  deployment.md
    └── adr/
```

Rules:
- `blender/` is **source**, `public/assets/` is **build output**. Never hand-edit files in
  `public/assets/`; regenerate them. Never serve anything from `blender/`.
- Large binaries (.blend, source textures, GLB, audio) belong in Git LFS once the repo is initialized.
- Never commit enormous unoptimized assets to production paths.

---

## 6. Blender authoring conventions (Layer 1 → Layer 2 contract)

Full detail belongs in `docs/blender-pipeline.md` and `docs/asset-guidelines.md`. Core rules:

### Units, transforms, origins
- Metric, 1 unit = 1 m. Real-world scale (door ≈ 2.2–2.6 m tall for this era, table height ≈ 0.75 m).
- Apply scale and rotation before export. Exporter handles Blender Z-up → glTF Y-up; don't pre-rotate.
- Each room's origin sits at a documented anchor (e.g. the room's main entrance threshold, floor
  level) so rooms snap into the mansion's world layout via manifest transforms.
- Props: origin at base center, on the floor contact point. Doors: origin on the hinge axis.

### Naming: `PREFIX_Zone_Name_Index[_Subindex]` (PascalCase segments, 2-digit indices)

| Prefix | Meaning | Runtime treatment |
|---|---|---|
| `ROOM_` | Room root / main visual shell | Zone root node |
| `COLLIDER_` | Simplified collision mesh | Removed from render; fed to collision world |
| `TRIGGER_` | Volume (zone boundary, audio zone, streaming trigger) | Invisible; used for enter/exit events |
| `PORTAL_` | Doorway/opening between zones | Zone graph edge; visibility/streaming hint |
| `DOOR_` | Openable door | Animated; interactable |
| `SPAWN_` | Player spawn / arrival point (facing = the empty's local +Z; use a Single Arrow empty) | Empty; read for position/orientation |
| `INTERACT_` | Interaction anchor/volume | Interactable target |
| `TABLE_` / `CHAIR_` / `SLOT_` / `PROP_` | Furniture / game objects / decor | Visual; may carry `extras` |
| `LIGHT_` | Light (exported as KHR_lights_punctual if dynamic) | Dynamic light or bake-only marker |
| `PROBE_` | Reflection/irradiance probe location | Env-map capture point |
| `NAV_` | Navigation mesh | Hidden; used for pathfinding (NPCs later) |
| `AUDIO_` | Positional sound emitter | Empty with `extras.sound` |
| `FX_` | Runtime-simulated effect (hearth fire, …) — things glTF can't carry | Empty with `extras.effect` (+ size); `src/fx` spawns it |
| `ANCHOR_` | Game-presentation pose (seat, focus, card spots, bet spots, shoe, reels, wheel, layout) | Empty with `extras.anchor` (role) + `tableId` [+ `index`, role data]; src/tables builds on it |
| `LOD1_` / `LOD2_` suffix `_LOD1` | Level-of-detail variants | See LOD rule below |

Examples: `ROOM_Poker_Main`, `DOOR_Poker_Entrance`, `COLLIDER_Poker_Main`, `SPAWN_Poker_Main`,
`TABLE_Poker_01`, `CHAIR_Poker_01_01`, `LIGHT_Poker_Chandelier_01`, `TRIGGER_Poker_Bounds`.

- LOD: name variants `<BaseName>_LOD0`, `_LOD1`, `_LOD2` (LOD0 = full detail).
- Collections mirror structure: `ZONE_Poker` › `VISUAL`, `COLLISION`, `LOGIC` (spawns, triggers,
  portals, interaction points), `LIGHTS`, `PROBES`, `NAV`. Collections whose name starts with `_WIP`
  or `_REF` are never exported.
- Materials: `MAT_<Surface>_<Variant>` (e.g. `MAT_Marble_Calacatta`, `MAT_Marble_Bardiglio`, `MAT_Wood_WalnutPolished`,
  `MAT_Brass_Aged`). Share materials from the material library; no duplicate `.001` copies.
  **Library materials are matched by name** (`src/render/materialNames.ts`): the build strips their
  textures and the runtime substitutes the shared material. UV0 for tiling materials is in metres.
- Lights export as KHR_lights_punctual in **SPEC** mode (candela = W ÷ 4π × 683). Light extras:
  `castShadow`, `flicker`, `bakeOnly` (lives only in the lightmap; skipped at runtime).
- **Doors:** `DOOR_<Zone>_<Id>` empty (local +Z → owning room) carries the door extras plus
  `collider: "COLLIDER_<Zone>_Door<Id>"`; leaves `DOOR_<Zone>_<Id>_L/_R` are single meshes with their
  origin on the hinge axis (join all leaf parts — the pipeline flattens hierarchies).
- **Lightmaps:** objects with custom property `lightmap` are joined per material, unwrapped to UV1 and
  baked by `npm run bake -- <zone>` (Cycles, GPU) into `<zone>_baked.blend` + `T_<Zone>_Lightmap.png/json`;
  that baked file is what gets exported. Details: `docs/blender-pipeline.md`.
- **Photoscanned props** (Poly Haven, CC0) come in through `K.import_prop` as instanced prototypes; **real
  carpets** (Met, CC0) through `scripts/make-carpets.mjs` + `Mansion.rug`. See docs/blender-pipeline.md (V2).
- **Licensed pack (Kraffing Casino Pack V1):** source GLBs live in `blender/props/kraffing/`.
  - **Git-ignored. Never commit or publish the pack's source files.**
  - Import with `K.import_pack` (`casino_props.pack_proto`). It keeps the pack origin, bakes a turn plus
    `PACK_SCALE` 0.86 and names materials `MAT_Kraffing_*`.
  - `kr_*_table`, `kr_slot_machine` and `kr_decor` place pieces and emit anchors calibrated to the printed
    felts (orthographic top renders; m/px noted in code).
  - The pack's stools, coins and cards are dropped.
  - Poker_Table_2 and Roulette_Table_2 are not used yet: each needs its own felt calibration.
  - Details: docs/architecture.md "Licensed asset pack".
- **Salon Privé** (`vip.blend` is the source of truth after its bootstrap). `npm run author:vip`
  re-runs the bootstrap and then these patch scripts:
  - `vip_sofas.py`: the lobby's Louis sofas;
  - `vip_fire.py`: logs, grate, ash bed and the `FX_` fire;
  - `vip_pack.py`: the pool table and jukebox.
- Textures: `T_<Material>_<Map>.<ext>` with map suffixes `BaseColor`, `Normal`, `ORM`
  (occlusion-roughness-metallic packed), `Emissive`, `Lightmap`.

### Custom properties (→ glTF `extras`)
Interaction metadata is authored as custom properties on the object, never hard-coded per object:

```json
{ "interactable": true, "interactionType": "door",
  "interactionPrompt": "Enter Poker Room", "target": "poker" }

{ "interactable": true, "interactionType": "casinoTable",
  "gameType": "blackjack", "tableId": "blackjack_01", "interactionPrompt": "Play Blackjack" }
```

The allowed keys and values per `interactionType` are defined in one schema
(`src/interaction/schema.ts`), and the validator checks exported `extras` against it.

### Materials & textures
- glTF metallic-roughness PBR only (Principled BSDF with image textures). Anything procedural must
  be baked to textures before export.
- UV0 = material UVs. UV1 = non-overlapping lightmap UVs on any mesh that receives baked lighting.
- Power-of-two texture sizes. Pack AO/roughness/metallic into one ORM texture.
- Reuse tiling materials + trim sheets for architecture; unique textures only where they earn it.

### Geometry
- Collision meshes are separate, simple, closed/convex where possible — never the render mesh.
- Repeated props (chairs, slot machines, chips, columns) are **linked-library assets** in Blender
  and must remain shared meshes in the export so the runtime can instance them.
- Slot machines are modular: `SlotMachine_Base`, `_Screen`, `_Lights`, `_ButtonPanel` — instantiated,
  never hundreds of unique machines.

---

## 7. Delivery pipeline (Layer 2)

```
.blend ─▶ Blender Python validate ─▶ glTF export (GLB) ─▶ glTF-Transform optimize
      ─▶ KTX2 textures ─▶ glTF-Validator + custom checks ─▶ manifest.json ─▶ public/assets/
```

- Automate with `blender --background --python blender/tools/export_zone.py -- <zone>` plus
  `scripts/build-assets`. One command should rebuild one zone or all zones.
- **Do not blindly enable every compression method.** Draco and Meshopt are alternatives for
  geometry — pick one per the architecture report (Meshopt is typically favoured for fast decode and
  animation/morph support; Draco for maximum static-mesh size reduction). Measure file size, decode
  time, and visual quality on real assets before deciding.
- Textures: KTX2/Basis — generally ETC1S for base color/emissive where quality allows, UASTC for
  normal maps and anything that shows artifacts. Always generate mipmaps. Verify on real content.
- The manifest is generated, and includes per zone: asset URLs, byte sizes, content hashes,
  dependencies (shared props, env maps), neighbours, world transform, default priority, preload flag.

```json
{ "zones": {
    "lobby": { "asset": "/assets/rooms/lobby/lobby.glb", "bytes": 18874368,
               "hash": "…", "preload": true, "neighbors": ["hall_east", "entrance"],
               "dependencies": ["props/chandelier_grand"] },
    "poker": { "asset": "/assets/rooms/poker/poker.glb", "bytes": 12582912,
               "hash": "…", "preload": false, "neighbors": ["hall_east"] } } }
```

- Validation failures (bad names, missing lightmap UVs, over-budget textures/tris, invalid `extras`)
  **fail the build**. Warnings are printed with the offending object name.

---

## 8. Runtime & application systems (Layers 3–4)

### Zone streaming
- The mansion is a **graph of zones** connected by portals — not one monolithic scene.
- States per zone: `unloaded → loading → loaded (hidden) → active → unloading`.
- Load policy: current zone = priority 1; zones one portal away = 2; two away = 3 (load only if idle
  bandwidth); beyond = not loaded. Approaching a `PORTAL_`/`TRIGGER_` escalates the target zone.
- Unload with hysteresis (distance/graph-hops + time) so walking back and forth doesn't thrash.
- Never block the frame on decode: decoding/transcoding in workers where the engine supports it;
  upload textures incrementally; compile shaders/pipelines before a zone becomes visible.
- If a zone isn't ready when the player reaches the door, hold the door closed briefly / slow the
  opening — preserve continuity. Never a full page reload or a hard cut to a loading screen after
  the initial load.
- Initial load targets: exterior/entrance + lobby shell only, interactive quickly; everything else streams.

### Player & camera
- Desktop: WASD move, mouse look (pointer lock), Shift sprint, Space optional jump, E interact,
  ESC menu. All bindings go through an input-action map so gamepad/touch can be added later.
- Kinematic capsule controller: acceleration/deceleration, configurable FOV, sensitivity, head
  height (~1.65–1.7 m eye height), step-up for stairs, slope limit, ground snapping, no wall clipping
  (camera near plane + capsule radius), no falling through floors.
- Feel: grounded and weighty, not floaty. Movement constants live in one config file.

### Collision
- Collision geometry comes only from `COLLIDER_` meshes, never from render meshes.
- Collision is behind an interface (`physics/`) so the implementation (custom BVH vs Rapier, etc.)
  can change, and so the same world data could be used by an authoritative server later.

### Interaction framework
- One generic system: each frame, a center-screen ray (with a max distance) finds the nearest
  interactable; the HUD shows the prompt (`E  ENTER POKER ROOM`, `E  PLAY BLACKJACK`).
- Handlers are registered per `interactionType` (`door`, `casinoTable`, `slotMachine`, `elevator`,
  …). Adding a new type = adding a handler + schema entry, never editing unrelated code.
- Interactables come from GLB `extras` or can be registered in code for runtime-spawned objects.

### Rendering & lighting (to be finalized by the architecture report)
- Physically based materials, correct color management (sRGB output, linear workflow), filmic
  tone mapping (e.g. ACES/AgX-style), HDR environment lighting for reflections.
- Hybrid lighting is the expected direction: baked lightmaps/AO for static architecture (the
  realism workhorse), a few dynamic shadow-casting lights, emissive chandeliers with restrained bloom,
  local reflection probes/env maps per room for marble and brass.
- Post-processing is restrained: tone mapping, subtle bloom, SSAO/contact shadows where affordable,
  antialiasing. No heavy chromatic aberration, lens dirt, or "game demo" looks.
- Quality tiers (high / medium / low) selectable at runtime; mobile will use a lower tier.
- **Lights are data, not objects.** Zones declare `LightDef`s; the runtime `LightPool` drives a fixed
  set of real lights (10 point + 1 spot + 1 shadow key). Never add three.js lights to zone content —
  a changing light count recompiles every shader (see docs/architecture.md §F).

### Performance techniques (all expected)
Frustum culling, portal/room-based occlusion, LODs, GPU instancing for repeated props, mesh merging
of static per-material geometry, texture atlasing/trim sheets, compressed geometry & textures,
lazy/priority loading, workers for decode, WASM where it pays off (decoders, physics).
Budgets live in `docs/performance.md` and are enforced by validation + the debug overlay.

### Audio
Spatial audio with per-zone ambience beds (lobby hum, distant conversation, card/chip sounds,
roulette wheel, slot machines) crossfaded by zone triggers, plus positional emitters from `AUDIO_`
nodes. Audio assets stream with their zone. Respect browser autoplay rules (start on user gesture).

### Animation & NPCs
Early: doors, subtle chandelier sway, curtains, roulette wheel, slot reels/lights. Keep it sparse.
NPCs (dealers, guests, bartenders, staff, security) are **later**; leave extension points only:
`NPC → animation / navigation (NAV_ meshes) / dialogue / behavior`.

### UI
Minimal and diegetic-first. Casino name top-left, interaction prompt bottom-center, ESC menu.
UI fades when not needed. The optional mansion map is secondary, never the primary navigation.

### Seated table lighting (V2)
While the player is seated (`src/main.ts`), these settings apply:
- `SEAT_FOV`: the view narrows per game.
- `SEAT_EXPOSURE`: a linear exposure eases in (`post.exposure`, applied before AgX). Card games run at
  ×0.7 of the base value.
- `TABLE_LAMP`: a soft feature spot lights the table, only where the room's fittings leave the felt dim.
- `OVERHEAD_DIM`: the fittings right over the table fade to 15 % (`LightPool.setDim`), used for poker
  and baccarat.

Zone felts (`MAT_<Zone>_Felt*`) are made matte at load, and runtime card stock is matte. Tune these
values, never the room lights, when a table reads too bright or dark.

### Runtime effects (`FX_`)
Things glTF can't carry are simulated at runtime from an `FX_` empty (`extras.effect`, see `src/fx`).
Current effect: `fire` (the Salon Privé hearth), made of:
- flame tongues from noise, in one draw call;
- ember and coal glow on `MAT_*_LogBark / _LogEnd / _Ashes`;
- sparks.

Firelight stays a flickering `LIGHT_`.

### Debug mode (dev builds only, compiled out of production)
FPS, frame time, draw calls, triangles, texture memory (where available), current zone, loaded
zones + states, loading queue, player/camera coordinates, collider wireframes, interaction ray.

---

## 9. Game systems (Layer 4) — separated from the world

**Presentation (V2):** games are played *on the 3D table*. Blender tables carry `ANCHOR_` empties; room
runtime modules (`src/rooms/<game>/runtime.ts`, `src/tables/cardPresenters.ts`) reconcile cards, chips,
reels, ball and dolly with each engine snapshot via `ZoneInstance.onGameState` and return a promise the
HUD waits for. The HUD (`src/ui/gameView.ts`) is a slim, non-modal control bar — it never draws cards.

```
3D WORLD ─▶ INTERACTION SYSTEM ─▶ GAME SESSION ─▶ <Game> ENGINE (pure logic)
                                        │
                                        └─▶ GAME UI / GAME VIEW (subscribes to state)
```

- `BlackjackGame`, `PokerGame`, `BaccaratGame`, `RouletteGame`, `SlotsGame` are **pure TypeScript**
  modules: no renderer imports, no DOM, no audio. Input = commands (`hit`, `stand`, `bet`),
  output = state + events. They must be unit-testable in Node.
- Injectable RNG (seedable for tests). Serializable state. This lets the same engine later run on
  an authoritative server with the client as a view.
- The world only knows `tableId` / `gameType` and asks the session layer to open a game.
  A table's 3D presentation (cards, chips, wheel animation) subscribes to game events; it never
  decides outcomes.
- Currency is play chips only (see §1).
- **Placeholder scope (see §1):** implement only enough rules for a playable demo round. No
  statistical validation, RTP/house-edge modelling, or exhaustive rule variants unless the user asks.
  The architecture (interface, separation, serializable state) matters more than the game's depth.

## 10. Multiplayer readiness (do not implement yet)

- Keep simulation state (player transform, zone, game state) separate from render objects; identify
  entities by stable IDs.
- Route player intent through commands/input actions so they can be sent over a network later.
- Networking will be its own module, independent of the renderer (candidates to research later:
  WebSockets, WebRTC, Colyseus, Socket.IO, authoritative server).
- Game engines must be server-runnable (see §9). Never trust the client for outcomes.

---

## 11. Development principles

1. Separate world rendering from game logic.
2. Separate Blender source assets from exported web assets.
3. Never put enormous unoptimized assets into production.
4. Prefer modular rooms.
5. Prefer reusable assets.
6. Prefer instancing over duplicated geometry.
7. Optimize before scaling the environment.
8. Keep game logic independent of rendering.
9. Keep networking independent of the rendering engine.
10. Keep assets replaceable.
11. Every cross-layer change is a contract change — update the schema, validator, and docs together.

## 12. Platform targets

Desktop first (Chrome, Edge, Safari on macOS/Windows). Mobile later (virtual joystick, touch look,
interaction buttons, lower quality tier) — do not compromise desktop for mobile during prototyping,
but don't make choices that rule mobile out.

## 13. Documentation to maintain

`docs/`: architecture & technology decisions (and why the renderer was chosen), Blender → web
pipeline, Blender export requirements, asset optimization, room streaming, player controller,
collision, interaction system, game architecture, performance, deployment, and how-tos for adding a
room, a casino game, and a Blender asset. Update docs in the same change as the code they describe.

## 14. Commands

| Command | What it does |
|---|---|
| `npm run dev` | Vite dev server on http://localhost:5173 (debug page: `/?debug`) |
| `npm run preview` | Serve the production `dist/` build on http://localhost:4173 (what GitHub Pages serves) |
| `npm run build` | Type-check + production build to `dist/` (debug code stripped via `__DEBUG__`) |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | Vitest unit tests (collision, later game engines) |
| `npm run fetch-textures` | Download CC0 PBR sources → `blender/textures_src/` (normalised to power-of-two), publish web copies + `textures.json` → `public/assets/textures/` |
| `npm run build:assets [-- <zone>] [--skip-export]` | Blender validate+export → glTF-Transform optimise (KTX2, Meshopt, instancing, merge) → validate → `public/assets/rooms/` + generated `manifest.json` |
| `npm run validate:assets -- <file.glb>` | glTF-Validator + naming/extras/budget checks on an optimised GLB |
| `npm run author:stair_hall` | Re-generate the Stair Hall + Vestibule `.blend` (Mansion M1; overwrites hand edits) |
| `npm run author:grand_salon` | Re-generate the Grand Salon `.blend` (Mansion M2; uses `furniture.py` for the hearth, piano, bureau and vitrines) |
| `npm run author:library` / `npm run author:ballroom` | Re-generate the Library / Ballroom `.blend` (Mansion M3) |
| `npm run author:vip` / `npm run author:lobby` | Casino-era bootstrap scripts (zones retired in the Mansion; kept for reference) |
| `npm run bake -- <zone> [size] [samples]` | Cycles GPU lightmap bake → `<zone>_baked.blend` + lightmap PNG/JSON (slow; run after editing a lit zone) |
| `npm run bake:all` | Re-bake all eight lit zones and rebuild every asset (≈ 25–30 min on an M1 Max) |
| `blender -b --factory-startup --python blender/tools/author_room.py -- <zone>` | Re-generate a game room's `.blend` (also `author_hallway.py -- hall_west\|hall_east`) |
| `npm run fetch-art` | Public-domain paintings (Met Open Access, CC0) → `blender/textures_src/art/` + `public/assets/art/` |
| `npm run fetch-models` | CC0 photoscanned furniture/decor from Poly Haven → `blender/props/polyhaven/` (imported with `K.import_prop`) |
| `npm run make-game-textures` | Card/chip atlases + reel strip (runtime, with layout `meta` in textures.json), printed felts, wheel ring, slot marquee/pay glass (`blender/textures_src/games/`) |
| `npm run make-carpets` | Real antique carpets (Met Open Access) → rug textures in `blender/textures_src/carpets/` + the seamless `Carpet_Gul` library set |
| `blender -b blender/rooms/<zone>/<zone>.blend --python blender/tools/validate_zone.py -- <Zone>` | Authoring-time validation only |

In-app keys: WASD/mouse, Shift, E (interact), Esc (pause / leave table), M (mute), `` ` `` (debug overlay, dev only).
URL flags: `?debug` (overlay + collider wireframes; `` ` `` toggles), `?quality=high|medium|low`,
`?webgl` (force the WebGL2 fallback). KTX-Software lives in `.tools/ktx/` (see docs/blender-pipeline.md).

## 15. Repository, publishing & testing

- **GitHub:** Mansion is `javda4/Jasons_Mansion` (public). Pushing `main` runs `.github/workflows/pages.yml`, which
  deploys to **https://javda4.github.io/Jasons_Mansion/** (the workflow derives `BASE_PATH` from the repo name).
  The CasinoV2 lines below describe that older project.
- **CasinoV2 GitHub:** `javda4/riviera-casino` (public). Pushing `main` runs `.github/workflows/pages.yml`, which
  builds with `BASE_PATH=/riviera-casino/` and deploys to **https://javda4.github.io/riviera-casino/**.
  Large binaries (`.blend`, textures, GLB, KTX2, audio) go through Git LFS (`.gitattributes`).
- **Never publish**, and keep all of these in `.gitignore`:
  - `.claude/`, `.mcp.json`, `.env*`, `CLAUDE.local.md` (developer and third-party service config);
  - the reference photos (`PHOTO-*.jpg`, `casino.png`);
  - the licensed pack sources (`blender/props/kraffing/`).
- **Commit identity:** use the GitHub noreply address, never a personal email.
- **Removing something that was already pushed:** rewriting history is not enough. The repository must be
  deleted and recreated. That needs the `delete_repo` token scope, which the user grants with
  `gh auth refresh -h github.com -s delete_repo`.
- **Licence note:** the built room GLBs embed the Kraffing pack's textures (compressed). Confirm the pack's
  licence allows use on a public website before publishing rooms that contain it.
- **Browser testing:** use a fresh automation browser (Playwright MCP), not the user's own Chrome. Kill
  stale automation Chrome processes: they starve the GPU and wedge screenshots. Seat helpers used in
  testing: activate the table's `casinoTable` handler, then drive `gameView.send(...)`.
- **Dev server:** Claude runs it on port 5174 (`npx vite --port 5174 --strictPort`), a background task with
  a 2-hour limit. The user's default is 5173.
