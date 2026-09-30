import { BaccaratGame } from './baccarat/baccarat';
import { BlackjackGame } from './blackjack/blackjack';
import { PokerGame } from './poker/poker';
import { RouletteGame } from './roulette/roulette';
import type { GameSessionManager } from './shared/session';
import { SlotsGame } from './slots/slots';

/** Wires every placeholder engine into the session manager. Swap an engine here to replace it. */
export function registerGames(sessions: GameSessionManager): void {
  sessions.register('blackjack', ({ chips, rng }) => new BlackjackGame(chips, rng));
  sessions.register('poker', ({ chips, rng }) => new PokerGame(chips, rng));
  sessions.register('baccarat', ({ chips, rng }) => new BaccaratGame(chips, rng));
  sessions.register('roulette', ({ chips, rng }) => new RouletteGame(chips, rng));
  sessions.register('slots', ({ chips, rng }) => new SlotsGame(chips, rng));
}
