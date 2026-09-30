# Adding a casino game

Games are **placeholders by design** (CLAUDE.md §1): small, plausible rules whose job is to prove
the world → table → game hand-off. Keep them behind the engine interface so they can be replaced.

```
3D world ─▶ INTERACT_ volume (casinoTable extras) ─▶ InteractionSystem ─▶ GameSessionManager ─▶ <Game>Engine
                                                                   │
                                                                   └─▶ GameView (2D sheet) + seated camera
```

1. **Engine** — `src/games/<game>/<game>.ts`, pure TypeScript implementing `GameEngine<State, Command>`
   (`src/games/shared/types.ts`): `dispatch(command)` returns events; `getState()` returns a JSON-safe
   snapshot that includes `chips`. Take randomness only from the injected `Rng`. Invalid commands
   return an `error` event and leave state untouched. **No imports** from three.js, `render/`, `ui/`,
   `world/`, the DOM or storage — `src/games/games.test.ts` fails the build if you do.
2. **Tests** — add cases to `src/games/games.test.ts` (seeded determinism, payouts, chip conservation).
3. **Register** — add the factory in `src/games/registry.ts` and the `GameType` in `src/games/shared/types.ts`
   (the interaction schema re-uses it, so the asset validator accepts the new `gameType`).
4. **UI** — `src/ui/games/<game>.ts`: a renderer that draws state and sends commands; register it in
   `RENDERERS` in `src/ui/gameView.ts`. Never compute outcomes in the UI.
5. **World** — give the table an `INTERACT_` volume with extras
   `{ interactable: true, interactionType: 'casinoTable', gameType, tableId, interactionPrompt }`
   (code rooms: `tableVolume()` in `src/rooms/shared/props.ts`; Blender rooms: custom properties on
   an `INTERACT_<Zone>_<Name>` mesh). `tableId` must be unique and stable.
6. **Play money only.** Chips come from `Wallet`; never add payments, deposits or real stakes.

## Presenting a new game on its table (V2)
1. Author the table in `blender/tools/casino_props.py` with `interact(...)` plus `anchor(...)` empties for
   `seat`, `focus` and whatever the game lays out (add new roles to `conventions.ANCHOR_ROLES` and
   `validate-assets.mjs` together — it's a contract change).
2. Add a presenter: either a card-table subclass in `src/tables/cardPresenters.ts` or a room runtime module
   (`src/rooms/<zone>/runtime.ts`) that sets `inst.onGameState` and returns a promise that resolves when
   the animation is done. Build with `CardTable`, `chipPile`, `movePile` and `Tweens` from `src/tables`.
3. Give the HUD a compact renderer in `src/ui/games/` (info + buttons only; honour `ui.busy`).
