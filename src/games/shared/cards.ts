import { randomInt } from './rng';
import type { Rng } from './types';

export type Suit = 'S' | 'H' | 'D' | 'C';
/** 2–10, J=11, Q=12, K=13, A=14 */
export interface Card { rank: number; suit: Suit }

export const SUITS: readonly Suit[] = ['S', 'H', 'D', 'C'];

export function freshDeck(decks = 1): Card[] {
  const out: Card[] = [];
  for (let d = 0; d < decks; d++) for (const suit of SUITS) for (let rank = 2; rank <= 14; rank++) out.push({ rank, suit });
  return out;
}

/** Fisher–Yates with an injected RNG (deterministic under a seed). */
export function shuffle<T>(items: T[], rng: Rng): T[] {
  for (let i = items.length - 1; i > 0; i--) {
    const j = randomInt(rng, i + 1);
    [items[i], items[j]] = [items[j], items[i]];
  }
  return items;
}

export function cardLabel(c: Card): string {
  const r = c.rank <= 10 ? String(c.rank) : ['J', 'Q', 'K', 'A'][c.rank - 11];
  return r + { S: '♠', H: '♥', D: '♦', C: '♣' }[c.suit];
}
