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
