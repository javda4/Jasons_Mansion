# Architecture Report — Mansion (fork of the Riviera Mansion Casino)

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

## D. Streaming — **implemented (Phase 4 slice; Mansion layout 2026-10-07)**

**Zone graph.** The graph is generated: `blender/zones.json` (the master layout) → `build-assets` →
`public/assets/manifest.json` → `src/world/zoneGraph.ts`. Every zone is a Blender GLB placed by an explicit world
transform. The casino's slot-based layout (`LOBBY_SLOTS` / `HALL_SLOTS`) and the code-built fallback rooms were
removed for the Mansion. The floor plan is in `docs/mansion-plan.md`.

**Zone states and policy.** `ZoneManager` runs `unloaded → loading → loaded(hidden) → active → unloading`. The pure
policy in `streamingPolicy.ts` (unit-tested):
- current zone = priority 1;
- one portal away = priority 2;
- two away = priority 3, loaded only when idle;
- zones beyond two hops unload after 20 s.

**Loading a zone:**
1. fetch and decode the GLB;
2. attach the game presenters for whatever tables it holds (`src/tables/attach.ts`, keyed by the `tableId` prefix);
3. apply the manifest transform;
4. `compileAsync` (off-screen);
5. capture the zone's probe;
6. register its doors and colliders.

**Doors and visibility.** Doors (`world/doors.ts`) hold closed with an "unlatch" nudge until the zone behind them
is ready, and close themselves when the player walks away. Visibility is portal-based: the current zone plus the
zones seen through open doors, two deep.

**Future:** GLB loading in workers; memory ceilings per tier.

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

## Game presentation on the 3D tables (V2, 2026-09-30)

```
engine (src/games, pure) ─▶ GameSession ─▶ GameView (slim HUD: controls + status)
                                   │                 ▲ waits for the promise before revealing results
                                   └─▶ ZoneManager.gameState(tableId, state, events) ─▶ ZoneInstance.onGameState
                                          ├─ card tables  src/tables/cardPresenters.ts (blackjack, baccarat, poker)
                                          ├─ roulette      src/rooms/roulette/runtime.ts (rotor, ball, chips, dolly)
                                          └─ slots         src/rooms/slots/runtime.ts (instanced reels, spin to result)
```

- **Contract:** `ANCHOR_` empties (conventions.ANCHOR_ROLES; validated in Blender and Node). An anchor's
  three.js local −Z is the top of a card laid there (away from the guest); presenters parent their objects
  to anchors, so zone transforms and table rotation apply automatically. Roulette `layout` / `wheel`
  anchors carry the bet-box centres and ball-track geometry in their extras; reels carry radius/width.
- **Runtime art:** `Card_Atlas`, `Chip_Atlas`, `Slot_Reel` in textures.json with their layout in `meta`
  (grid, denominations, reel stop order) — generated by `npm run make-game-textures`, never hard-coded.
- **Pacing:** presenters return promises; the HUD disables controls ("The dealer deals…") and reveals the
  outcome and new chip count only when the cards/ball/reels have landed.
- **Seats:** `seat` + `focus` anchors give the seated camera pose; `SEAT_FOV` (main.ts) narrows the view a
  little per game. Card games look down over the rail (~40–50°) so pips read; roulette is a near
  top-down view of the whole layout and the spinning wheel, and its chips/ball are scaled with the
  (≈2× real) printed layout. Bets are placed by clicking the layout (`src/tables/layoutPick.ts`).
- **Seated light:** `TABLE_LAMP` adds a soft spot (the LightPool's spot slot) only where the room's own
  fittings leave the felt dim (blackjack, roulette); `SEAT_EXPOSURE` eases a linear exposure multiplier
  (`post.exposure`, applied in the grade before AgX) so bright tables don't blow out cards.
  `OVERHEAD_DIM` fades the room's own fittings right over the table (poker pendants 0.8 m above the felt,
  the baccarat chandelier) to 15 % while seated (`LightPool.setDim`, intensities only) — their hot spot
  made white cards and chips glare and bloom, which exposure alone can't fix.
- **Felt:** zone felts (`MAT_<Zone>_Felt*`) are made matte at load (specular 0.1, env 0.35) — glTF's
  default dielectric specular laid a pale tan veil over the baize under chandeliers.

## Lighting stability (V2)
Electric fittings never flicker (only `…Fire…` lights keep `flicker`, with irregular per-light noise).
High tier: bloom reads the TRAA-resolved image (not the jittered raw frame) with threshold 1.0, and a
pre-TRAA HDR clamp (`FIREFLY_CLAMP` = 20) stops sub-pixel candle bulbs from shimmering. Metals feed SSR at
45 %; gilt/brass are rubbed, aged finishes (rough ≈ 0.5, env 1.1–1.2).

## Runtime effects — `FX_` (V2)
Some things can't survive glTF: a living fire is animated, self-lit, volumetric. They are authored as an
`FX_<Zone>_<Name>_NN` empty whose `extras.effect` names a simulator in `src/fx/effects.ts` (validated by
`conventions.FX_EFFECTS` / `validate-assets.mjs`); the empty's origin is the effect's base, its size extras
shape it. The Salon Privé hearth (`blender/tools/vip_fire.py`): bark-scanned logs on a cast-iron grate over
an ash bed are ordinary geometry; `fire` adds ~17 camera-facing flame tongues in one draw call (domain-warped
fractal noise in a tapering envelope, blackbody ramp, additive HDR → bloom), ember-crack and coal glow as
emissive nodes on `MAT_*_LogBark / _LogEnd / _Ashes`, and a few dozen sparks. Firelight stays a flickering
`LIGHT_` in the LightPool, placed in front of the opening (inside the firebox it blew the hearth out).

## Licensed asset pack — Kraffing Casino Pack V1 (V2)
Source GLBs live in `blender/props/kraffing/` (**git-ignored**: a paid pack is never published as source;
only the optimised, KTX2-compressed room GLBs ship). `kit.Zone.import_pack` imports a piece as one
instanced prototype, keeping the pack's floor-centre origin so separately imported parts (a roulette table
and its wheel) stay registered; it bakes a turn (our player-side convention) and `PACK_SCALE` 0.86 (the
pack is ~16 % oversize) and renames materials `MAT_Kraffing_<Name>`. The pack's bar stools, loose coins
and cards are dropped — guests sit on our velvet tub chairs and the runtime deals real cards and chips.

| Pack piece | Where | Notes |
|---|---|---|
| Blackjack_Table_1 | Blackjack room ×4 | `kr_blackjack_table`: anchors on the printed boxes |
| Poker_Table_1 | Poker room ×4 | `kr_poker_table`: guest seat 5, house 9/2/7; `board.spacing` = printed boxes |
| Roulette_Table_1 | Roulette room ×4 | `kr_roulette_table`: the pack wheel is the rotor (unique mesh per table), `wheel.offset` = pocket 0's angle, `order` = its CCW pocket order; `layout` carries the printed box centres + half-sizes (`cell/zero/dozen/out`) for click-to-bet |
| Slot_Machine_1 | Slot hall ×40 | `kr_slot_machine`: its reel drums replaced by our runtime reels at the same centres |
| Lucky_Spin_Machine_1/2 | Slot hall (decor) | not playable |
| Pool_Table_1, Jukebox_1 | Salon Privé (decor) | `blender/tools/vip_pack.py` |
| Poker_Table_2, Roulette_Table_2 | unused | need their own felt calibration |

Calibration = orthographic top renders of each original model (m/px noted in `casino_props.py`) plus
ray-cast felt heights and the wheel's radial profile. Build: pack data maps (`TX_…`) are encoded at 1024².
