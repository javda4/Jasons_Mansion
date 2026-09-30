# Le Grand Riviera — browser 3D casino mansion

A first-person, explorable 1920s French Riviera casino mansion that runs in the browser (Three.js WebGPU with a
WebGL2 fallback). Walk from the Grand Lobby through the galleries into the Poker, Blackjack, Baccarat, Roulette
and Slot rooms and sit down at a table. **Play-money entertainment only.**

**Live:** https://javda4.github.io/riviera-casino/ (desktop Chrome/Edge/Safari recommended)

Controls: WASD walk · mouse look · Shift faster · E interact · Esc pause / leave table · M mute.
URL flags: `?quality=high|medium|low`, `?webgl`.

## Development

```sh
npm install
npm run dev        # http://localhost:5173 (add ?debug for the overlay)
npm test
npm run build
```

The world is authored in Blender (`blender/`, stored with Git LFS) and exported through the asset pipeline
into `public/assets/`. See `CLAUDE.md` and `docs/` for the architecture, pipeline and conventions.
Pushing to `main` deploys to GitHub Pages via `.github/workflows/pages.yml`.

Third-party content: textures from Poly Haven and ambientCG (CC0); paintings from The Metropolitan Museum of
Art Open Access (CC0).
