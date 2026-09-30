import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { BaccaratGame, bankerDraws, handTotal } from './baccarat/baccarat';
import { BlackjackGame, handValue } from './blackjack/blackjack';
import { bestHand, CATEGORY, compareScores, PokerGame } from './poker/poker';
import { betReturn, RouletteGame } from './roulette/roulette';
import { registerGames } from './registry';
import type { Card } from './shared/cards';
import { seededRng } from './shared/rng';
import { GameSessionManager, Wallet } from './shared/session';
import { slotReturn, SlotsGame } from './slots/slots';

const c = (s: string): Card => {
  const suit = s.at(-1) as Card['suit'];
  const r = s.slice(0, -1);
  const rank = ({ J: 11, Q: 12, K: 13, A: 14 } as Record<string, number>)[r] ?? Number(r);
  return { rank, suit };
};

describe('architecture: game engines are renderer- and DOM-free (§9)', () => {
  const files: string[] = [];
  const walk = (dir: string) => {
    for (const f of readdirSync(dir)) {
      const p = path.join(dir, f);
      if (statSync(p).isDirectory()) walk(p);
      else if (p.endsWith('.ts') && !p.endsWith('.test.ts')) files.push(p);
    }
  };
  walk(path.join(import.meta.dirname));
  it.each(files)('%s', (file) => {
    const src = readFileSync(file, 'utf8');
    expect(src).not.toMatch(/from ['"](three|three\/.*|\.\.\/\.\.\/(render|ui|world|loading|audio)\/.*)['"]/);
    expect(src).not.toMatch(/\b(document|window|localStorage|requestAnimationFrame)\b/);
  });
});

describe('blackjack', () => {
  it('values soft and hard hands', () => {
    expect(handValue([c('AS'), c('6H')])).toEqual({ total: 17, soft: true });
    expect(handValue([c('AS'), c('6H'), c('9C')]).total).toBe(16);
    expect(handValue([c('AS'), c('AH'), c('9C')]).total).toBe(21);
  });
  it('is deterministic under a seed and conserves chips', () => {
    const run = () => {
      const g = new BlackjackGame(1000, seededRng(42));
      g.dispatch({ type: 'deal', bet: 100 });
      if (g.getState().phase === 'player') g.dispatch({ type: 'stand' });
      return g.getState();
    };
    const a = run(), b = run();
    expect(a).toEqual(b);
    expect(a.phase).toBe('settled');
    expect(a.chips).toBe(1000 + a.payout);
  });
  it('rejects bets beyond the stack without changing state', () => {
    const g = new BlackjackGame(50, seededRng(1));
    const before = g.getState();
    expect(g.dispatch({ type: 'deal', bet: 100 })[0].type).toBe('error');
    expect(g.getState()).toEqual(before);
  });
});

describe('poker hand evaluation', () => {
  const rank = (cards: string[]) => CATEGORY[bestHand(cards.map(c))[0]];
  it('recognises categories from 7 cards', () => {
    expect(rank(['AS', 'KS', 'QS', 'JS', 'TS'.replace('T', '10'), '2H', '3D'])).toBe('Straight flush');
    expect(rank(['9C', '9D', '9H', '9S', '2H', '3D', '5C'])).toBe('Four of a kind');
    expect(rank(['9C', '9D', '9H', '4S', '4H', '3D', '5C'])).toBe('Full house');
    expect(rank(['AS', '2D', '3H', '4S', '5H', 'KD', 'QC'])).toBe('Straight');
    expect(rank(['AS', 'AD', 'KH', 'KS', '5H', '2D', '3C'])).toBe('Two pair');
  });
  it('orders hands by kicker', () => {
    const a = bestHand(['AS', 'AD', 'KH', '9S', '5H', '2D', '3C'].map(c));
    const b = bestHand(['AH', 'AC', 'QH', '9D', '5S', '2C', '3H'].map(c));
    expect(compareScores(a, b)).toBeGreaterThan(0);
  });
  it('plays a full hand to showdown', () => {
    const g = new PokerGame(1000, seededRng(7));
    g.dispatch({ type: 'deal' });
    for (let i = 0; i < 4; i++) g.dispatch({ type: 'check' });
    const s = g.getState();
    expect(s.street).toBe('showdown');
    expect(s.board).toHaveLength(5);
    expect(s.winners.length).toBeGreaterThan(0);
  });
});

describe('baccarat', () => {
  it('scores hands modulo 10 with faces worth zero', () => {
    expect(handTotal([c('KS'), c('7H')])).toBe(7);
    expect(handTotal([c('9S'), c('8H')])).toBe(7);
  });
  it('applies the banker third-card rule', () => {
    expect(bankerDraws(3, 8)).toBe(false);
    expect(bankerDraws(6, 7)).toBe(true);
    expect(bankerDraws(7, 1)).toBe(false);
  });
  it('settles a coup and conserves chips', () => {
    const g = new BaccaratGame(1000, seededRng(3));
    g.dispatch({ type: 'deal', on: 'banker', amount: 100 });
    const s = g.getState();
    expect(s.winner).not.toBeNull();
    expect(s.chips).toBe(1000 + s.payout);
  });
});

describe('roulette', () => {
  it('pays standard odds', () => {
    expect(betReturn({ kind: 'straight', value: 17, amount: 10 }, 17)).toBe(360);
    expect(betReturn({ kind: 'red', amount: 10 }, 1)).toBe(20);
    expect(betReturn({ kind: 'red', amount: 10 }, 0)).toBe(0);
    expect(betReturn({ kind: 'dozen', value: 3, amount: 10 }, 30)).toBe(30);
  });
  it('spins within 0–36 and refunds cleared bets', () => {
    const g = new RouletteGame(500, seededRng(9));
    g.dispatch({ type: 'bet', bet: { kind: 'even', amount: 50 } });
    g.dispatch({ type: 'clear' });
    expect(g.getState().chips).toBe(500);
    g.dispatch({ type: 'bet', bet: { kind: 'black', amount: 50 } });
    g.dispatch({ type: 'spin' });
    const r = g.getState().lastResult!;
    expect(r).toBeGreaterThanOrEqual(0);
    expect(r).toBeLessThanOrEqual(36);
  });
});

describe('slots', () => {
  it('pays three of a kind and cherries', () => {
    expect(slotReturn(['seven', 'seven', 'seven'], 5)).toBe(400);
    expect(slotReturn(['cherry', 'cherry', 'bar'], 5)).toBe(10);
    expect(slotReturn(['bar', 'bell', 'lemon'], 5)).toBe(0);
  });
  it('keeps the chip ledger consistent over many spins', () => {
    const g = new SlotsGame(10_000, seededRng(11));
    let spent = 0, won = 0;
    for (let i = 0; i < 500; i++) { g.dispatch({ type: 'spin', bet: 5 }); spent += 5; won += g.getState().lastWin; }
    expect(g.getState().chips).toBe(10_000 - spent + won);
  });
});

describe('sessions', () => {
  it('opens a table by gameType, syncs the wallet and resumes by tableId', () => {
    const wallet = new Wallet(1000);
    const sessions = new GameSessionManager(wallet, seededRng(5));
    registerGames(sessions);
    const s = sessions.open('slots_01', 'slots');
    s.dispatch({ type: 'spin', bet: 10 });
    expect(wallet.balance).toBe((s.state as { chips: number }).chips);
    expect(sessions.open('slots_01', 'slots')).toBe(s);
    sessions.close('slots_01');
    expect(sessions.open('slots_01', 'slots')).not.toBe(s);
  });
});
