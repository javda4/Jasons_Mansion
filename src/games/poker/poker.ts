import { freshDeck, shuffle, type Card } from '../shared/cards';
import { errorEvent, type GameEngine, type GameEvent, type Rng } from '../shared/types';

/**
 * Placeholder Texas Hold'em (§1/§9): the player against three house bots in a fixed-limit hand.
 * Bots simply call (a bot may fold pre-flop with a weak hand) — enough for a playable round that
 * exercises the table → session → engine hand-off. No side pots, no all-ins.
 */
export type PokerStreet = 'idle' | 'preflop' | 'flop' | 'turn' | 'river' | 'showdown';

export interface PokerSeat {
  name: string;
  hole: Card[];      // bots' cards are hidden in `getState()` until showdown
  folded: boolean;
  isPlayer: boolean;
}

export interface PokerState {
  chips: number;
  street: PokerStreet;
  pot: number;
  board: Card[];
  seats: PokerSeat[];
  /** Amount the player must add to continue this street. */
  toCall: number;
  betSize: number;
  winners: string[];
  winningHand: string | null;
  payout: number;
}

export type PokerCommand =
  | { type: 'deal' }
  | { type: 'check' }   // check or call
  | { type: 'raise' }   // one fixed-size raise per street
  | { type: 'fold' };

const BOTS = ['Comtesse', 'Baron', 'Signor'];
const ANTE = 10;

// ------------------------------------------------------------------ hand evaluation

export const CATEGORY = ['High card', 'Pair', 'Two pair', 'Three of a kind', 'Straight', 'Flush', 'Full house', 'Four of a kind', 'Straight flush'] as const;

/** Score of a 5-card hand: higher is better; comparable across hands. */
export function score5(cards: Card[]): number[] {
  const ranks = cards.map((c) => c.rank).sort((a, b) => b - a);
  const flush = cards.every((c) => c.suit === cards[0].suit);
  const uniq = [...new Set(ranks)];
  let straightHigh = 0;
  if (uniq.length === 5 && ranks[0] - ranks[4] === 4) straightHigh = ranks[0];
  if (uniq.length === 5 && ranks[0] === 14 && ranks[1] === 5) straightHigh = 5; // wheel A-2-3-4-5
  const counts = new Map<number, number>();
  for (const r of ranks) counts.set(r, (counts.get(r) ?? 0) + 1);
  // ranks ordered by (count desc, rank desc)
  const groups = [...counts.entries()].sort((a, b) => b[1] - a[1] || b[0] - a[0]);
  const shape = groups.map((g) => g[1]).join('');
  const kick = groups.map((g) => g[0]);
  if (straightHigh && flush) return [8, straightHigh];
  if (shape === '41') return [7, ...kick];
  if (shape === '32') return [6, ...kick];
  if (flush) return [5, ...ranks];
  if (straightHigh) return [4, straightHigh];
  if (shape === '311') return [3, ...kick];
  if (shape === '221') return [2, ...kick];
  if (shape === '2111') return [1, ...kick];
  return [0, ...ranks];
}

export function compareScores(a: number[], b: number[]): number {
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const d = (a[i] ?? 0) - (b[i] ?? 0);
    if (d) return d;
  }
  return 0;
}

/** Best 5-card score from 5–7 cards (checks every 5-card combination). */
export function bestHand(cards: Card[]): number[] {
  let best: number[] = [-1];
  const pick = (start: number, chosen: Card[]) => {
    if (chosen.length === 5) {
      const s = score5(chosen);
      if (compareScores(s, best) > 0) best = s;
      return;
    }
    for (let i = start; i <= cards.length - (5 - chosen.length); i++) pick(i + 1, [...chosen, cards[i]]);
  };
  pick(0, []);
  return best;
}

// ------------------------------------------------------------------ engine

export class PokerGame implements GameEngine<PokerState, PokerCommand> {
  readonly gameType = 'poker' as const;
  private deck: Card[] = [];
  private s: PokerState;
  private raisedThisStreet = false;

  constructor(chips: number, private readonly rng: Rng) {
    this.s = {
      chips, street: 'idle', pot: 0, board: [], toCall: 0, betSize: 20, winners: [], winningHand: null, payout: 0,
      seats: [{ name: 'You', hole: [], folded: false, isPlayer: true }, ...BOTS.map((name) => ({ name, hole: [], folded: false, isPlayer: false }))],
    };
  }

  getState(): PokerState {
    const copy = structuredClone(this.s);
    if (copy.street !== 'showdown') {
      for (const seat of copy.seats) if (!seat.isPlayer) seat.hole = seat.hole.map(() => ({ rank: 0, suit: 'S' as const }));
    }
    return copy;
  }

  dispatch(cmd: PokerCommand): GameEvent[] {
    const s = this.s;
    switch (cmd.type) {
      case 'deal': {
        if (s.street !== 'idle' && s.street !== 'showdown') return [errorEvent('hand in progress')];
        if (s.chips < ANTE + s.betSize * 4) return [errorEvent('not enough chips for a hand')];
        this.deck = shuffle(freshDeck(), this.rng);
        s.chips -= ANTE;
        s.pot = ANTE * s.seats.length; // bots ante from the house
        s.board = [];
        s.winners = [];
        s.winningHand = null;
        s.payout = 0;
        for (const seat of s.seats) Object.assign(seat, { hole: [this.deck.pop()!, this.deck.pop()!], folded: false });
        // a bot with an unpaired hand below ten-high sometimes folds pre-flop
        for (const seat of s.seats) {
          if (seat.isPlayer) continue;
          const [a, b] = seat.hole;
          if (a.rank !== b.rank && Math.max(a.rank, b.rank) < 10 && this.rng() < 0.5) seat.folded = true;
        }
        s.street = 'preflop';
        this.raisedThisStreet = false;
        s.toCall = 0;
        return [{ type: 'dealt', hole: s.seats[0].hole, folded: s.seats.filter((x) => x.folded).map((x) => x.name) }];
      }
      case 'check':
      case 'raise': {
        if (!['preflop', 'flop', 'turn', 'river'].includes(s.street)) return [errorEvent('no hand in play')];
        const events: GameEvent[] = [];
        if (cmd.type === 'raise') {
          if (this.raisedThisStreet) return [errorEvent('one raise per street')];
          if (s.chips < s.betSize) return [errorEvent('not enough chips')];
          this.raisedThisStreet = true;
          s.chips -= s.betSize;
          const callers = s.seats.filter((x) => !x.isPlayer && !x.folded).length;
          s.pot += s.betSize * (1 + callers); // bots always call a raise
          events.push({ type: 'raise', amount: s.betSize, callers });
        } else {
          events.push({ type: 'check' });
        }
        return [...events, ...this.nextStreet()];
      }
      case 'fold': {
        if (!['preflop', 'flop', 'turn', 'river'].includes(s.street)) return [errorEvent('no hand in play')];
        s.seats[0].folded = true;
        s.street = 'showdown';
        s.winners = ['House'];
        s.winningHand = null;
        return [{ type: 'fold' }];
      }
      default:
        return [errorEvent('unknown command')];
    }
  }

  private nextStreet(): GameEvent[] {
    const s = this.s;
    this.raisedThisStreet = false;
    const next: Record<string, PokerStreet> = { preflop: 'flop', flop: 'turn', turn: 'river', river: 'showdown' };
    s.street = next[s.street];
    if (s.street === 'flop') s.board.push(this.deck.pop()!, this.deck.pop()!, this.deck.pop()!);
    else if (s.street === 'turn' || s.street === 'river') s.board.push(this.deck.pop()!);
    if (s.street !== 'showdown') return [{ type: 'street', street: s.street, board: s.board }];
    return this.showdown();
  }

  private showdown(): GameEvent[] {
    const s = this.s;
    const live = s.seats.filter((x) => !x.folded);
    const scored = live.map((seat) => ({ seat, score: bestHand([...seat.hole, ...s.board]) }));
    scored.sort((a, b) => compareScores(b.score, a.score));
    const top = scored.filter((x) => compareScores(x.score, scored[0].score) === 0);
    s.winners = top.map((x) => x.seat.name);
    s.winningHand = CATEGORY[scored[0].score[0]];
    if (top.some((x) => x.seat.isPlayer)) {
      const share = Math.floor(s.pot / top.length);
      s.chips += share;
      s.payout = share;
    }
    return [{ type: 'showdown', winners: s.winners, hand: s.winningHand, payout: s.payout }];
  }
}
