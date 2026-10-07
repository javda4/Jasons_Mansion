import { gameOfTable, type GameType } from '../interaction/schema';
import type { ZoneInstance } from '../world/roomBuilder';

type Attach = (inst: ZoneInstance) => void;

/** Per-game 3D presenters, loaded only for games a zone actually holds. */
const PRESENTERS: Record<GameType, () => Promise<Attach>> = {
  roulette: () => import('../rooms/roulette/runtime').then((m) => m.enhanceRoulette),
  slots: () => import('../rooms/slots/runtime').then((m) => m.enhanceSlots),
  blackjack: () => import('./cardPresenters').then((m) => (inst: ZoneInstance) => m.attachCardTables(inst, 'blackjack')),
  baccarat: () => import('./cardPresenters').then((m) => (inst: ZoneInstance) => m.attachCardTables(inst, 'baccarat')),
  poker: () => import('./cardPresenters').then((m) => (inst: ZoneInstance) => m.attachCardTables(inst, 'poker')),
};

/**
 * Attaches the presenters for every game whose `ANCHOR_` tables are in this zone. A mansion room can hold
 * tables of several games, while each presenter claims the zone's single `onGameState` / `onGameEvent` hooks,
 * so each presenter's hooks are captured in turn and the zone's hooks dispatch by the table's game.
 */
export async function attachGameTables(inst: ZoneInstance): Promise<void> {
  const games = new Set<GameType>();
  for (const a of inst.anchors ?? []) {
    const g = gameOfTable(a.tableId);
    if (g) games.add(g);
  }
  if (!games.size) return;
  const attach = await Promise.all([...games].map(async (g) => [g, await PRESENTERS[g]()] as const));
  const state = new Map<GameType, NonNullable<ZoneInstance['onGameState']>>();
  const event = new Map<GameType, NonNullable<ZoneInstance['onGameEvent']>>();
  for (const [g, fn] of attach) {
    inst.onGameState = undefined;
    inst.onGameEvent = undefined;
    fn(inst);
    if (inst.onGameState) state.set(g, inst.onGameState);
    if (inst.onGameEvent) event.set(g, inst.onGameEvent);
  }
  inst.onGameState = (tableId, s, events) => {
    const g = gameOfTable(tableId);
    return g ? state.get(g)?.(tableId, s, events) : undefined;
  };
  inst.onGameEvent = (tableId, e) => {
    const g = gameOfTable(tableId);
    if (g) event.get(g)?.(tableId, e);
  };
}
