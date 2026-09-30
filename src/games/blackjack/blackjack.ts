import { freshDeck, shuffle, type Card } from '../shared/cards';
import { errorEvent, type GameEngine, type GameEvent, type Rng } from '../shared/types';

/**
 * Placeholder blackjack (§1/§9): 6-deck shoe, dealer stands on all 17s, blackjack pays 3:2,
 * hit / stand / double. No splits or insurance — just enough for a playable round.
 */
export type BlackjackPhase = 'betting' | 'player' | 'settled';
export type BlackjackOutcome = 'blackjack' | 'win' | 'push' | 'lose' | 'bust';

export interface BlackjackState {
  chips: number;
  phase: BlackjackPhase;
  bet: number;
  player: Card[];
  dealer: Card[];
  /** Dealer's hole card is hidden while the player acts. */
  dealerHidden: boolean;
  outcome: BlackjackOutcome | null;
  payout: number;
}

export type BlackjackCommand =
  | { type: 'deal'; bet: number }
  | { type: 'hit' }
  | { type: 'stand' }
  | { type: 'double' };

export function handValue(cards: Card[]): { total: number; soft: boolean } {
  let total = 0;
  let aces = 0;
  for (const c of cards) {
    if (c.rank === 14) { aces++; total += 11; } else total += Math.min(c.rank, 10);
  }
  while (total > 21 && aces > 0) { total -= 10; aces--; }
  return { total, soft: aces > 0 };
}

const isBlackjack = (cards: Card[]) => cards.length === 2 && handValue(cards).total === 21;

export class BlackjackGame implements GameEngine<BlackjackState, BlackjackCommand> {
  readonly gameType = 'blackjack' as const;
  private shoe: Card[] = [];
  private s: BlackjackState;

  constructor(chips: number, private readonly rng: Rng) {
    this.s = { chips, phase: 'betting', bet: 0, player: [], dealer: [], dealerHidden: true, outcome: null, payout: 0 };
  }

  getState(): BlackjackState {
    return structuredClone(this.s);
  }

  private draw(): Card {
    if (this.shoe.length < 52) this.shoe = shuffle(freshDeck(6), this.rng);
    return this.shoe.pop()!;
  }

  dispatch(cmd: BlackjackCommand): GameEvent[] {
    const s = this.s;
    switch (cmd.type) {
      case 'deal': {
        if (s.phase === 'player') return [errorEvent('finish the current hand first')];
        if (!Number.isInteger(cmd.bet) || cmd.bet <= 0) return [errorEvent('bet must be a positive whole number')];
        if (cmd.bet > s.chips) return [errorEvent('not enough chips')];
        s.chips -= cmd.bet;
        Object.assign(s, { bet: cmd.bet, player: [this.draw(), this.draw()], dealer: [this.draw(), this.draw()], dealerHidden: true, outcome: null, payout: 0, phase: 'player' });
        const events: GameEvent[] = [{ type: 'dealt', player: s.player, dealerUp: s.dealer[0] }];
        if (isBlackjack(s.player) || isBlackjack(s.dealer)) events.push(...this.settle());
        return events;
      }
      case 'hit': {
        if (s.phase !== 'player') return [errorEvent('no hand in play')];
        s.player.push(this.draw());
        const events: GameEvent[] = [{ type: 'card', to: 'player', card: s.player.at(-1) }];
        if (handValue(s.player).total > 21) events.push(...this.settle());
        return events;
      }
      case 'double': {
        if (s.phase !== 'player' || s.player.length !== 2) return [errorEvent('double only on the first two cards')];
        if (s.bet > s.chips) return [errorEvent('not enough chips to double')];
        s.chips -= s.bet;
        s.bet *= 2;
        s.player.push(this.draw());
        return [{ type: 'card', to: 'player', card: s.player.at(-1) }, ...this.dealerPlays(), ...this.settle()];
      }
      case 'stand': {
        if (s.phase !== 'player') return [errorEvent('no hand in play')];
        return [...this.dealerPlays(), ...this.settle()];
      }
      default:
        return [errorEvent('unknown command')];
    }
  }

  private dealerPlays(): GameEvent[] {
    const s = this.s;
    s.dealerHidden = false;
    const events: GameEvent[] = [{ type: 'reveal', card: s.dealer[1] }];
    if (handValue(s.player).total > 21) return events;
    while (handValue(s.dealer).total < 17) {
      s.dealer.push(this.draw());
      events.push({ type: 'card', to: 'dealer', card: s.dealer.at(-1) });
    }
    return events;
  }

  private settle(): GameEvent[] {
    const s = this.s;
    s.dealerHidden = false;
    const p = handValue(s.player).total;
    const d = handValue(s.dealer).total;
    let outcome: BlackjackOutcome;
    let returned = 0; // chips handed back, including the stake
    if (p > 21) outcome = 'bust';
    else if (isBlackjack(s.player) && !isBlackjack(s.dealer)) { outcome = 'blackjack'; returned = s.bet + Math.floor(s.bet * 1.5); }
    else if (isBlackjack(s.dealer) && !isBlackjack(s.player)) outcome = 'lose';
    else if (d > 21 || p > d) { outcome = 'win'; returned = s.bet * 2; }
    else if (p === d) { outcome = 'push'; returned = s.bet; }
    else outcome = 'lose';
    s.chips += returned;
    s.payout = returned - s.bet;
    s.outcome = outcome;
    s.phase = 'settled';
    return [{ type: 'settled', outcome, payout: s.payout, player: p, dealer: d }];
  }
}
