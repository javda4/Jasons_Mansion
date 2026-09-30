# Architecture Report — Riviera Mansion Casino

Status: **accepted for Phase 1** (2026-09-29). Revisit each decision at the phase noted.
Priority order: `REALISM → PERFORMANCE → MODULARITY → EXTENSIBILITY → GAME INTEGRATION`.

Versions checked on 2026-09-29 (npm): three 0.186.1, vite 8.3.1, @babylonjs/core 9.28,
playcanvas 2.22, @react-three/fiber 9.8, @dimforge/rapier3d-compat 0.21, three-mesh-bvh 0.9.15,
@gltf-transform/cli 4.5.1, vitest 5.0.

---

## A. Runtime — **Three.js (r186), imperative, no React in the frame loop**

| Option | For | Against |
|---|---|---|
| **Three.js** | Largest ecosystem; first-class glTF/KTX2/Meshopt loaders; `WebGPURenderer` with automatic WebGL2 fallback; node/TSL post stack (GTAO, SSR, TRAA, bloom, SMAA); small core; total control of the frame loop | No built-in editor, streaming or physics — we write those (we want to own them anyway) |
| React Three Fiber | Declarative scene authoring | Reconciliation overhead and indirection for a game-style loop of imperative systems (streaming, controller, interaction). Adds nothing the layer model needs |
| Babylon.js 9 | Batteries-included (physics plugin, inspector, WebGPU) | Heavier bundle; engine opinions overlap with systems we want to own; smaller glTF-authoring community for Blender workflows |
| PlayCanvas 2 | Excellent perf, editor-centric | Best value comes from its hosted editor; weaker fit for a Blender-as-source-of-truth pipeline |

**Decision:** Three.js, imported from `three/webgpu`. Systems are plain TypeScript classes ticked
from one loop (`src/core/loop.ts`). React may be used later for 2D game UI only; the HUD is plain DOM.

## B. Graphics API — **WebGPU with automatic WebGL2 fallback**

WebGPU ships by default in Chrome/Edge (since 113), Safari 26 (macOS/iOS, Sep 2025) and Firefox
(Windows 141, Apple-Silicon macOS 145). `WebGPURenderer` falls back to a WebGL2 backend when WebGPU
is unavailable, and TSL node materials/post-processing compile to both backends — so we author one
shader/post stack. `?webgl` forces the fallback for testing. Compute-only features must stay optional.

## C. Blender → browser pipeline — **implemented (Phase 2)**

`blender/tools/export_zone.py` (headless Blender 5.2, validation first) → `scripts/build-assets.mjs`
(glTF-Transform 4.5: strip library-material textures, dedup, flatten, instance, per-material join,
weld, KTX2 ETC1S/UASTC via KTX-Software 4.4.2, **Meshopt**) → Khronos glTF-Validator + contract checks
(`scripts/validate-assets.mjs`, sharing `schema.ts` and `materialNames.ts` with the runtime) →
generated `public/assets/manifest.json` → `src/loading/glbZone.ts` builds the same `ZoneInstance` as
code zones. Meshopt over Draco: faster decode, works with instancing. Demo: the Salon Privé,
9.4 MB raw → 661 KiB. Full detail: `docs/blender-pipeline.md`.

## D. Streaming — **implemented (Phase 4 slice)**

Zone graph in `src/world/zoneGraph.ts` (stand-in for the generated manifest): lobby → west/east
galleries → poker, blackjack, baccarat, roulette, slots (+ a locked VIP door). Each zone module is
its own code-split chunk. `ZoneManager` runs `unloaded → loading → loaded(hidden) → active →
unloading`; the pure policy in `streamingPolicy.ts` (unit-tested) gives priority 1 = current,
2 = one portal away, 3 = two away only when idle, and unloads zones beyond two hops after 20 s.
Loading = dynamic import → build → apply manifest transform → `compileAsync` (off-screen) →
per-zone probe capture → register doors/colliders. Doors (`world/doors.ts`) hold closed with an
"unlatch" nudge until the zone behind them is ready, and close themselves when the player walks
away. Visibility is portal-based: current zone + zones seen through open doors (two deep).
Future: GLB loading in workers, memory ceilings per tier.

## E. Collision — **custom kinematic capsule behind an interface**

Walking a mansion needs: wall sliding, step-up for stairs, ground snap, doors. It does not need
rigid-body dynamics. Phase 1: pure-TS capsule vs axis-aligned boxes (`src/physics/`) — zero
dependencies, render-agnostic, runnable on a server. Phase 2+: `COLLIDER_` meshes become arbitrary
triangles, so the same `CollisionWorld` interface gets a **three-mesh-bvh** capsule-sweep backend.
Rapier (WASM, 0.21) stays the upgrade path if we need dynamic props; it would slot in behind the
same interface.

## F. Lighting — **hybrid**

- Static architecture: **baked lightmap on UV1 (implemented, Phase 3)** — Cycles bakes indirect light from all
  lights plus direct light from `bakeOnly` fixtures; the chandelier stays dynamic. See docs/blender-pipeline.md.
- Dynamic: a few warm point/spot lights (chandeliers, sconces) with **1–2 shadow casters per room**;
  everything else unshadowed.
- Reflections: per-zone **reflection probe** captured into a PMREM target when the zone streams in;
  entering a zone GPU-copies its probe into the one shared environment texture (swapping the texture
  object would rebuild every material). Later: baked `PROBE_` captures shipped as KTX2.
- **Light pool** (`render/lightPool.ts`): zones declare lights as data (`LightDef`); a fixed set of
  10 point + 1 spot + 1 shadow-casting spot is assigned each 0.2 s to the most relevant lights of the
  visible zones, with cross-fades. The light count never changes, so shaders never recompile when
  zones stream. Measured: 5 extra spot slots at 2× DPR cost ~50 % of the frame (57 → 27 fps).
- Colour: linear workflow, sRGB output, **AgX** tone mapping (handles saturated warm highlights better
  than ACES), exposure per room.
- Post (quality-tiered): GTAO ambient occlusion, emissive-driven bloom, TRAA/SMAA. No chromatic
  aberration, lens dirt, or heavy vignette.
- **Screen-space reflections (Phase 6, high tier):** SSR at half resolution. three's SSR weights by
  metalness, so the beauty pass writes `reflectivity = max(metalness, clearcoat × 0.35)` and a
  clearcoat-aware roughness into an MRT target; marble, French-polished walnut and brass reflect the
  actual room (the per-zone probe still supplies off-screen reflections).
- **Grade:** a restrained linear-light grade before tone mapping — slight warmth, +6 % saturation, a
  very soft vignette.

## G. Textures

KTX2/Basis: **UASTC** for normal maps and ORM; **ETC1S** for base colour/emissive when artefact-free;
mipmaps always. Sizes: 2K hero surfaces (floors, panelling), 1K props, 512 small trims. Trim sheets and
tiling materials for architecture. Phase 1 uses CC0 Poly Haven JPGs (marble, walnut, jacquard, leather,
wool felt) until `toktx` is added to the pipeline.

## H. Budgets

See `docs/performance.md`.

## I. Game separation — **implemented (Phase 5)**

`src/games/` holds pure engines (blackjack, Texas Hold'em vs three bots, punto banco, single-zero
roulette, 3-reel slots) implementing `GameEngine` — commands in, JSON-safe state + events out,
injected RNG. `GameSessionManager` maps `tableId`/`gameType` → engine and syncs the play-chip
`Wallet`. The world only emits `interaction:activated` from `INTERACT_` volumes; the `casinoTable`
handler opens a session, eases the camera into a seated pose and shows `GameView` (a modal
`<dialog>`: focus trap, Esc leaves, `role="status"` results). A test forbids renderer/DOM imports
under `src/games`. How-to: `docs/adding-a-game.md`.

## J. Multiplayer readiness

Player intent flows through the input-action map (`src/player/input.ts`) → commands; the simulated
state (position, velocity, zone) lives in `PlayerState`, separate from the camera/render objects;
entities have stable string IDs (`tableId`, zone ids). Collision and game engines are renderer-free,
so an authoritative server can reuse them. No networking code until asked.
