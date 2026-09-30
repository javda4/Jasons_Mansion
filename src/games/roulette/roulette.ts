import { randomInt } from '../shared/rng';
import { errorEvent, type GameEngine, type GameEvent, type Rng } from '../shared/types';

/** Placeholder single-zero (European/French) roulette: uniform 0–36, common bets. */
export type RouletteBetKind = 'straight' | 'red' | 'black' | 'odd' | 'even' | 'low' | 'high' | 'dozen';
export interface RouletteBet { kind: RouletteBetKind; value?: number; amount: number }

export interface RouletteState {
  chips: number;
  bets: RouletteBet[];
  lastResult: number | null;
  lastPayout: number;
  history: number[];
}

export type RouletteCommand =
  | { type: 'bet'; bet: RouletteBet }
  | { type: 'clear' }
  | { type: 'spin' };

export const RED = new Set([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]);

/** Total returned (stake included) for one bet on a result; 0 if it loses. */
export function betReturn(bet: RouletteBet, n: number): number {
  const a = bet.amount;
  if (bet.kind === 'straight') return bet.value === n ? a * 36 : 0;
  if (n === 0) return 0; // single zero: all outside bets lose (no la partage in this placeholder)
  switch (bet.kind) {
    case 'red': return RED.has(n) ? a * 2 : 0;
    case 'black': return !RED.has(n) ? a * 2 : 0;
    case 'odd': return n % 2 === 1 ? a * 2 : 0;
    case 'even': return n % 2 === 0 ? a * 2 : 0;
    case 'low': return n <= 18 ? a * 2 : 0;
    case 'high': return n >= 19 ? a * 2 : 0;
    case 'dozen': return bet.value !== undefined && Math.ceil(n / 12) === bet.value ? a * 3 : 0;
  }
}

export class RouletteGame implements GameEngine<RouletteState, RouletteCommand> {
  readonly gameType = 'roulette' as const;
  private s: RouletteState;

  constructor(chips: number, private readonly rng: Rng) {
    this.s = { chips, bets: [], lastResult: null, lastPayout: 0, history: [] };
  }

  getState(): RouletteState { return structuredClone(this.s); }

  dispatch(cmd: RouletteCommand): GameEvent[] {
    const s = this.s;
    switch (cmd.type) {
      case 'bet': {
        const b = cmd.bet;
        if (!Number.isInteger(b.amount) || b.amount <= 0 || b.amount > s.chips) return [errorEvent('invalid bet')];
        if (b.kind === 'straight' && (b.value === undefined || b.value < 0 || b.value > 36)) return [errorEvent('pick a number 0–36')];
        if (b.kind === 'dozen' && ![1, 2, 3].includes(b.value ?? 0)) return [errorEvent('dozen must be 1, 2 or 3')];
        s.chips -= b.amount;
        s.bets.push({ ...b });
        return [{ type: 'betPlaced', bet: b }];
      }
      case 'clear': {
        s.chips += s.bets.reduce((t, b) => t + b.amount, 0);
        s.bets = [];
        return [{ type: 'cleared' }];
      }
      case 'spin': {
        if (!s.bets.length) return [errorEvent('place a bet first')];
        const n = randomInt(this.rng, 37);
        const returned = s.bets.reduce((t, b) => t + betReturn(b, n), 0);
        const staked = s.bets.reduce((t, b) => t + b.amount, 0);
        s.chips += returned;
        s.lastResult = n;
        s.lastPayout = returned - staked;
        s.history = [n, ...s.history].slice(0, 12);
        s.bets = [];
        return [{ type: 'spin', result: n, payout: s.lastPayout }];
      }
      default:
        return [errorEvent('unknown command')];
    }
  }
}
