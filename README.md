# Le Grand Riviera — browser 3D casino mansion (V2)

A first-person, explorable 1920s French Riviera casino mansion that runs in the browser (Three.js WebGPU with a
WebGL2 fallback). Walk from the Grand Lobby through the galleries into the Poker, Blackjack, Baccarat, Roulette
and Slot rooms and the Salon Privé, and sit down at a table. **Play-money entertainment only.**

## Play it online (GitHub Pages)

**https://javda4.github.io/riviera-casino/**

- Every push to `main` rebuilds and redeploys the site automatically (`.github/workflows/pages.yml`, about
  2–3 minutes). Follow a run in the repository's **Actions** tab, or from a terminal with `gh run watch`.
- The online site is a production build: the debug overlay is compiled out (use the local debug page below).
- Best in a current desktop Chrome, Edge or Safari; browsers without WebGPU fall back to WebGL2 automatically.

## Run it locally (localhost)

Requires Node.js 22+ and Git LFS for the 3D assets (`git lfs install && git lfs pull` after cloning).

```sh
npm install
npm run dev
```

Open **http://localhost:5173/**, click *Enter the Mansion*, then:

| Key | Action |
|---|---|
| W A S D / mouse | walk / look (click the page to capture the mouse) |
| Shift | walk faster |
| E | interact — open doors, sit at a table or a slot machine |
| Esc | pause menu / leave the table |
| M | mute |

To check the production build locally (exactly what GitHub Pages serves):

```sh
npm run build
npm run preview        # http://localhost:4173/
```

## Debug page

The debug overlay exists only on the dev server (`npm run dev`); production builds strip it out.

- **http://localhost:5173/?debug** opens the page with the overlay and collider wireframes.
- Press **`` ` ``** (backtick) to toggle the overlay on any dev-server page.
- The overlay shows FPS and frame time, draw calls, triangles, texture memory, the current zone, each zone's
  load state and the loading queue, player/camera coordinates and the interaction ray.
- The browser console (F12) logs each zone's load time: `[zones] <zone>: fetch+decode+build … ms, compile … ms`.

URL flags (combine with `&`, e.g. `http://localhost:5173/?debug&quality=medium`):

| Flag | Effect |
|---|---|
| `?debug` | debug overlay + collider wireframes (dev server only) |
| `?quality=high\|medium\|low` | force a quality tier (render resolution, shadows, SSR/GTAO, bloom) |
| `?webgl` | force the WebGL2 fallback instead of WebGPU |

`?quality` and `?webgl` also work on the GitHub Pages site.

## Tests and build

```sh
npm run typecheck      # TypeScript
npm test               # Vitest unit tests (collision, game engines)
npm run build          # type-check + production build → dist/
```

## How the project is organised

The world is authored in Blender (`blender/`, Git LFS) and exported through the asset pipeline into
`public/assets/` (`npm run build:assets`); the runtime lives in `src/`. **`CLAUDE.md`** documents the
architecture, conventions and every pipeline command; `docs/` has the details.

## Third-party content

- CC0: textures and photoscanned models from Poly Haven and ambientCG; paintings and carpet photographs from
  The Metropolitan Museum of Art Open Access.
- Licensed: game tables, slot machines and decor from the **Kraffing Casino Pack V1**. The pack's source files
  are not in this repository (`blender/props/kraffing/` is git-ignored); only the optimised room files that
  embed it ship with the site.
