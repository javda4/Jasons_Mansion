import { freshDeck, shuffle, type Card } from '../shared/cards';
import { errorEvent, type GameEngine, type GameEvent, type Rng } from '../shared/types';

/** Placeholder punto banco: standard third-card tableau, banker pays 0.95:1, tie 8:1. */
export type BaccaratSide = 'player' | 'banker' | 'tie';

export interface BaccaratState {
  chips: number;
  phase: 'betting' | 'settled';
  bet: { on: BaccaratSide; amount: number } | null;
  player: Card[];
  banker: Card[];
  winner: BaccaratSide | null;
  payout: number;
}

export type BaccaratCommand = { type: 'deal'; on: BaccaratSide; amount: number };

export const cardPoints = (c: Card) => (c.rank >= 10 && c.rank <= 13 ? 0 : c.rank === 14 ? 1 : c.rank);
export const handTotal = (cards: Card[]) => cards.reduce((t, c) => t + cardPoints(c), 0) % 10;

export class BaccaratGame implements GameEngine<BaccaratState, BaccaratCommand> {
  readonly gameType = 'baccarat' as const;
  private shoe: Card[] = [];
  private s: BaccaratState;

  constructor(chips: number, private readonly rng: Rng) {
    this.s = { chips, phase: 'betting', bet: null, player: [], banker: [], winner: null, payout: 0 };
  }

  getState(): BaccaratState { return structuredClone(this.s); }

  private draw(): Card {
    if (this.shoe.length < 20) this.shoe = shuffle(freshDeck(8), this.rng);
    return this.shoe.pop()!;
  }

  dispatch(cmd: BaccaratCommand): GameEvent[] {
    const s = this.s;
    if (cmd.type !== 'deal') return [errorEvent('unknown command')];
    if (!['player', 'banker', 'tie'].includes(cmd.on)) return [errorEvent('bet on player, banker or tie')];
    if (!Number.isInteger(cmd.amount) || cmd.amount <= 0 || cmd.amount > s.chips) return [errorEvent('invalid bet')];
    s.chips -= cmd.amount;
    const p = [this.draw(), this.draw()];
    const b = [this.draw(), this.draw()];
    // naturals stop the coup
    if (handTotal(p) < 8 && handTotal(b) < 8) {
      let playerThird: Card | null = null;
      if (handTotal(p) <= 5) { playerThird = this.draw(); p.push(playerThird); }
      const bt = handTotal(b);
      const draws = playerThird === null
        ? bt <= 5
        : bankerDraws(bt, cardPoints(playerThird));
      if (draws) b.push(this.draw());
    }
    const pt = handTotal(p), bt = handTotal(b);
    const winner: BaccaratSide = pt > bt ? 'player' : bt > pt ? 'banker' : 'tie';
    let returned = 0;
    if (winner === 'tie') returned = cmd.on === 'tie' ? cmd.amount * 9 : cmd.amount; // side bets push on a tie
    else if (winner === cmd.on) returned = cmd.on === 'banker' ? cmd.amount + Math.floor(cmd.amount * 0.95) : cmd.amount * 2;
    s.chips += returned;
    Object.assign(s, { phase: 'settled', bet: { on: cmd.on, amount: cmd.amount }, player: p, banker: b, winner, payout: returned - cmd.amount });
    return [{ type: 'coup', player: p, banker: b, playerTotal: pt, bankerTotal: bt, winner, payout: s.payout }];
  }
}

/** Banker's third-card rule when the player drew a third card worth `p3`. */
export function bankerDraws(bankerTotal: number, p3: number): boolean {
  switch (bankerTotal) {
    case 0: case 1: case 2: return true;
    case 3: return p3 !== 8;
    case 4: return p3 >= 2 && p3 <= 7;
    case 5: return p3 >= 4 && p3 <= 7;
    case 6: return p3 === 6 || p3 === 7;
    default: return false;
  }
}
