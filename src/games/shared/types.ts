/**
 * Game-system contracts (CLAUDE.md §9). Everything under src/games is pure TypeScript:
 * no renderer, DOM, audio or storage imports — engines must run unchanged in Node or on an
 * authoritative server later. Play chips only (§1).
 */
export type GameType = 'poker' | 'blackjack' | 'baccarat' | 'roulette' | 'slots';

/** A fact emitted by an engine; presentation layers (2D UI, 3D table) subscribe to these. */
export interface GameEvent {
  type: string;
  [key: string]: unknown;
}

export interface GameEngine<State, Command> {
  readonly gameType: GameType;
  /** Serialisable snapshot (JSON-safe) — what a server would send to clients. */
  getState(): State;
  /** Apply a player command. Invalid commands produce an `error` event and change nothing. */
  dispatch(command: Command): GameEvent[];
}

/** Uniform random in [0, 1). Injected so tests (and a future server) control randomness. */
export type Rng = () => number;

export function errorEvent(message: string): GameEvent {
  return { type: 'error', message };
}
