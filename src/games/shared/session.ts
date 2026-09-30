import type { GameEngine, GameEvent, GameType, Rng } from './types';

/** Play-chip wallet (§1: entertainment only — no payments, deposits or withdrawals). */
export class Wallet {
  constructor(private chips: number) {}
  get balance(): number { return this.chips; }
  set(balance: number): void { this.chips = Math.max(0, Math.floor(balance)); }
}

export interface EngineFactory {
  /** Build an engine for a table. `chips` is the player's current stack. */
  (opts: { tableId: string; chips: number; rng: Rng }): GameEngine<{ chips: number }, unknown>;
}

export type SessionListener = (state: unknown, events: GameEvent[]) => void;

/**
 * One seat at one table. The world only knows `tableId`/`gameType`; it asks the manager to open a
 * session and never touches the engine. UI and 3D presentation subscribe to state + events.
 */
export class GameSession {
  private listeners = new Set<SessionListener>();

  constructor(
    readonly tableId: string,
    readonly gameType: GameType,
    private readonly engine: GameEngine<{ chips: number }, unknown>,
    private readonly wallet: Wallet,
  ) {}

  get state(): unknown { return this.engine.getState(); }

  dispatch(command: unknown): GameEvent[] {
    const events = this.engine.dispatch(command);
    this.wallet.set(this.engine.getState().chips);
    for (const l of this.listeners) l(this.engine.getState(), events);
    return events;
  }

  subscribe(listener: SessionListener): () => void {
    this.listeners.add(listener);
    listener(this.engine.getState(), []);
    return () => this.listeners.delete(listener);
  }
}

export class GameSessionManager {
  private factories = new Map<GameType, EngineFactory>();
  private sessions = new Map<string, GameSession>();

  constructor(readonly wallet: Wallet, private readonly rng: Rng) {}

  register(type: GameType, factory: EngineFactory): void {
    this.factories.set(type, factory);
  }

  /** Re-opening a table resumes its session (state is kept per tableId). */
  open(tableId: string, gameType: GameType): GameSession {
    const existing = this.sessions.get(tableId);
    if (existing) return existing;
    const factory = this.factories.get(gameType);
    if (!factory) throw new Error(`no engine registered for ${gameType}`);
    const engine = factory({ tableId, chips: this.wallet.balance, rng: this.rng });
    const session = new GameSession(tableId, gameType, engine, this.wallet);
    this.sessions.set(tableId, session);
    return session;
  }

  /** Called when the player leaves a table: the next visit starts from the wallet balance. */
  close(tableId: string): void {
    this.sessions.delete(tableId);
  }
}
