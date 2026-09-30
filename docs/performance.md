# Performance Budgets

Desktop-first targets (mid-range discrete GPU / Apple M1 at 1440p, "high" tier). Mobile tier later.
The debug overlay (`~` or `?debug`) shows live FPS, frame time, draw calls and triangles.

| Metric | Desktop high | Desktop medium | Mobile (later) |
|---|---|---|---|
| Frame rate | 60 fps (16.6 ms) | 60 fps | 30–60 fps |
| Draw calls per frame | ≤ 400 | ≤ 300 | ≤ 150 |
| Triangles on screen | ≤ 2.5 M | ≤ 1.5 M | ≤ 500 k |
| Shadow-casting lights visible | ≤ 2 | ≤ 1 | 0 |
| Dynamic lights per room | ≤ 12 | ≤ 8 | ≤ 4 |
| GPU texture memory (resident) | ≤ 1.5 GB | ≤ 1 GB | ≤ 350 MB |
| Per-zone download (GLB + KTX2) | ≤ 25 MB | — | ≤ 10 MB |
| Initial download to interactive | ≤ 30 MB | — | ≤ 15 MB |
| Texture size | 2K hero, 1K props, 512 trims | 1K cap | 1K cap |

Phase 1 note: textures are JPG (~19 MB); KTX2 in Phase 2 should cut GPU memory ~4–6× and download
~40 %. Post-processing cost is tier-gated: high = GTAO + bloom + TRAA; medium = bloom + SMAA; low = none.

## Measured (2026-09-29, Chrome, WebGPU, Apple Silicon, 3024×1618 @ 2× DPR, tier high)

| View | FPS | Draw calls (all passes) | Triangles |
|---|---|---|---|
| Lobby (with gallery visible through open door) | 70 | 256 | 266 k |
| Poker Room | 85 | 140 | 267 k |
| Blackjack Room | 90 | 126 | 196 k |
| Baccarat Room | 70 | 114 | 109 k |
| Roulette Room | 77 | 121 | 177 k |
| Slot Room (~40 instanced machines) | 77 | 99 | 140 k |

First-ever zone loads can take several seconds because WebGPU pipelines compile on first use
(e.g. West Gallery 17 s cold, < 1 s warm); this runs off-screen and doors hold closed meanwhile.
Neighbouring zones now stream (and compile) behind the entry curtain; see the Phase 6 section below.

## Phase 3 — Blender-authored Grand Lobby (2026-09-29, same machine/tier)

| Item | Value |
|---|---|
| Lobby GLB (Meshopt, instanced, library textures stripped) | 2.7 MB (16.2 MB raw export) |
| Lobby lightmap (2048², UASTC + zstd, mipmapped) | 1.2 MB |
| Lobby triangles (authored, incl. 1,787 instanced parts in 22 batches) | 312 k |
| In-view from the entrance | 60 fps · 187–193 draw calls (all passes) · ~920 k triangles |
| Door open, gallery visible | 59 fps · 263 draw calls |
| Runtime lights used by the lobby | 2 (chandelier point + shadow key); 21 fixtures are bake-only |
| Time to interactive (dev server, warm cache) | ~6 s |
| Bake (Cycles, M1 Max GPU, 256 spp, indirect + bake-only direct) | ~2.5 min |

## Phase 6 — reflections, 4K lightmap, audio (2026-09-29, lobby entrance view, all zones loaded)

| Configuration | FPS |
|---|---|
| High @ 2× DPR, SSR on | 47 |
| High @ 2× DPR, SSR off | 59 |
| Medium @ 2× DPR | 71 |
| **High @ 1.5× DPR, SSR on (new default)** | **81** |
| High @ 1.25× DPR, SSR on | 112 |

Render resolution is now part of each quality tier (high 1.5×, medium 1.25×, low 1×, capped at the
display's DPR); TRAA reconstructs detail so 1.5× on a Retina display is visually near-identical.
The lobby lightmap is 4096² (4.4 MB UASTC KTX2, ≈ 30 MB of GPU memory with mips; bake ≈ 8.5 min).

## Phase 6 — all zones Blender-authored and baked (2026-09-29)

| Zone | GLB (Meshopt) | Lightmap (UASTC KTX2) | Authored tris |
|---|---|---|---|
| Grand Lobby | 3.8 MB | 4096² · 4.7 MB | 312 k |
| West / East Gallery | 2.7 MB each | 2048² · 1.1 MB each | 178 k / 190 k |
| Poker / Blackjack / Baccarat | 3.0 / 2.9 / 2.2 MB | 2048² · 1.3 MB each | 282 k / 305 k / 165 k |
| Roulette / Slots | 3.7 / 2.1 MB | 2048² · 1.3 / 1.4 MB | 330 k / 306 k |

The Slot Room reel symbols were first authored as extruded, high-resolution text (1.2 M tris for 40
machines); they are now flat, low-resolution curves (306 k for the whole room). Full re-bake of all
eight lit zones ≈ 35 min on an M1 Max (`npm run bake:all`).

**Zone load time is shader compilation, not download.** Debug builds log each zone's split
(`[zones] <id>: fetch+decode+build … ms, compile … ms`). With a warm Chrome shader cache:
fetch + KTX2/Meshopt decode + build is 40–300 ms per zone and `compileAsync` 0–2.4 s (zones that
only reuse already-compiled material variants compile in ~1 ms). On a *cold* shader cache (first
visit ever) the lobby takes ~11 s behind the entry curtain and the first gallery ~30 s off-screen,
because every unique material × lightmap variant compiles a new pipeline. Streaming already starts
the neighbouring galleries behind the curtain, and doors hold closed until a zone is ready, so the
player never sees an uncompiled zone. Further cuts would come from fewer unique zone-local
materials (merge `MAT_<Zone>_*` variants into the shared library).
