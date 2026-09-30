import { errorEvent, type GameEngine, type GameEvent, type Rng } from '../shared/types';

/** Placeholder 3-reel slot with weighted symbols and a tiny paytable (§1: simple weighted reels). */
export const SYMBOLS = ['cherry', 'lemon', 'bell', 'bar', 'seven', 'diamond'] as const;
export type SlotSymbol = (typeof SYMBOLS)[number];
const WEIGHTS: Record<SlotSymbol, number> = { cherry: 30, lemon: 25, bell: 18, bar: 14, seven: 8, diamond: 5 };
/** Multiplier for three of a kind; two cherries pay 2×, one cherry 1× (stake back). */
export const PAYTABLE: Record<SlotSymbol, number> = { cherry: 10, lemon: 15, bell: 20, bar: 40, seven: 80, diamond: 150 };

export interface SlotsState {
  chips: number;
  reels: SlotSymbol[];
  lastBet: number;
  lastWin: number;
}

export type SlotsCommand = { type: 'spin'; bet: number };

function pick(rng: Rng): SlotSymbol {
  const total = SYMBOLS.reduce((t, s) => t + WEIGHTS[s], 0);
  let r = rng() * total;
  for (const s of SYMBOLS) {
    r -= WEIGHTS[s];
    if (r < 0) return s;
  }
  return SYMBOLS[0];
}

export function slotReturn(reels: SlotSymbol[], bet: number): number {
  const [a, b, c] = reels;
  if (a === b && b === c) return bet * PAYTABLE[a];
  const cherries = reels.filter((s) => s === 'cherry').length;
  return cherries === 2 ? bet * 2 : cherries === 1 ? bet : 0;
}

export class SlotsGame implements GameEngine<SlotsState, SlotsCommand> {
  readonly gameType = 'slots' as const;
  private s: SlotsState;

  constructor(chips: number, private readonly rng: Rng) {
    this.s = { chips, reels: ['seven', 'seven', 'seven'], lastBet: 0, lastWin: 0 };
  }

  getState(): SlotsState { return structuredClone(this.s); }

  dispatch(cmd: SlotsCommand): GameEvent[] {
    const s = this.s;
    if (cmd.type !== 'spin') return [errorEvent('unknown command')];
    if (!Number.isInteger(cmd.bet) || cmd.bet <= 0 || cmd.bet > s.chips) return [errorEvent('invalid bet')];
    s.chips -= cmd.bet;
    s.reels = [pick(this.rng), pick(this.rng), pick(this.rng)];
    s.lastBet = cmd.bet;
    s.lastWin = slotReturn(s.reels, cmd.bet);
    s.chips += s.lastWin;
    return [{ type: 'spin', reels: s.reels, win: s.lastWin }];
  }
}
