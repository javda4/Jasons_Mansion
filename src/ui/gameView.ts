import type { GameSession, Wallet } from '../games/shared/session';
import type { GameEvent, GameType } from '../games/shared/types';
import './gameView.css';
import { renderBaccarat } from './games/baccarat';
import { renderBlackjack } from './games/blackjack';
import { renderPoker } from './games/poker';
import { renderRoulette } from './games/roulette';
import { renderSlots } from './games/slots';

/** Per-game presentation: draws state into `body`, sends commands via `send`. UI only — no rules. */
export type GameRenderer = (body: HTMLElement, state: never, send: (cmd: unknown) => void, ui: GameUi) => void;

export interface GameUi {
  /** Selected stake (shared chip selector). */
  stake: number;
  status(text: string, tone?: 'win' | 'lose' | ''): void;
  chipSelector(): string;
  lastEvents: GameEvent[];
}

const RENDERERS: Record<GameType, GameRenderer> = {
  blackjack: renderBlackjack as GameRenderer,
  poker: renderPoker as GameRenderer,
  baccarat: renderBaccarat as GameRenderer,
  roulette: renderRoulette as GameRenderer,
  slots: renderSlots as GameRenderer,
};

const TITLES: Record<GameType, string> = {
  blackjack: 'Blackjack', poker: "Texas Hold'em", baccarat: 'Baccarat', roulette: 'Roulette', slots: 'Machine à Sous',
};

const STAKES = [10, 25, 100, 500];
const nf = new Intl.NumberFormat('fr-FR');

/**
 * The 2D half of a table: a modal <dialog> (focus trap, Esc to leave) docked over the seated 3D
 * view. It subscribes to a GameSession and never decides outcomes (§9).
 */
export class GameView {
  private dialog: HTMLDialogElement;
  private body: HTMLElement;
  private chips: HTMLElement;
  private statusEl: HTMLElement;
  private unsubscribe: (() => void) | null = null;
  private ui: GameUi;
  onLeave: () => void = () => {};
  /** Presentation hook for engine events (sounds, 3D table reactions). */
  onEvents: (events: GameEvent[]) => void = () => {};

  constructor(private readonly wallet: Wallet) {
    this.dialog = document.createElement('dialog');
    this.dialog.className = 'game';
    this.dialog.setAttribute('aria-labelledby', 'game-title');
    this.dialog.innerHTML = `
      <div class="game__panel">
        <header class="game__head">
          <h2 class="game__title" id="game-title"></h2>
          <span class="game__chips">Chips <b id="game-chips"></b></span>
          <button type="button" class="game__leave" data-leave>Leave table <kbd>Esc</kbd></button>
        </header>
        <div class="game__body" id="game-body"></div>
        <p class="game__status" id="game-status" role="status" aria-live="polite"></p>
      </div>`;
    document.body.append(this.dialog);
    this.body = this.dialog.querySelector('#game-body')!;
    this.chips = this.dialog.querySelector('#game-chips')!;
    this.statusEl = this.dialog.querySelector('#game-status')!;
    this.dialog.querySelector('[data-leave]')!.addEventListener('click', () => this.onLeave());
    // Esc on a modal dialog fires `cancel`; route it through the same leave path
    this.dialog.addEventListener('cancel', (e) => { e.preventDefault(); this.onLeave(); });
    this.dialog.addEventListener('click', (e) => {
      const stake = (e.target as HTMLElement).closest<HTMLElement>('[data-stake]');
      if (stake) { this.ui.stake = Number(stake.dataset.stake); this.body.querySelectorAll('[data-stake]').forEach((b) => b.setAttribute('aria-pressed', String(b === stake))); }
    });
    const self = this;
    this.ui = {
      stake: 25,
      lastEvents: [],
      status: (text, tone = '') => { self.statusEl.textContent = text; self.statusEl.dataset.tone = tone; },
      chipSelector() {
        return `<div class="game__row"><span class="game__label">Stake</span>${STAKES.map((s) =>
          `<button type="button" class="chip-btn" data-stake="${s}" aria-pressed="${s === this.stake}">${s}</button>`).join('')}</div>`;
      },
    };
  }

  get open(): boolean { return this.dialog.open; }

  show(session: GameSession, tableLabel: string): void {
    this.unsubscribe?.();
    this.dialog.querySelector('#game-title')!.textContent = `${TITLES[session.gameType]} · ${tableLabel}`;
    this.ui.status('');
    const render = RENDERERS[session.gameType];
    const send = (cmd: unknown) => {
      const events = session.dispatch(cmd);
      const err = events.find((e) => e.type === 'error');
      if (err) this.ui.status(String(err.message), 'lose');
    };
    this.unsubscribe = session.subscribe((state, events) => {
      this.ui.lastEvents = events;
      if (events.length) this.onEvents(events);
      this.chips.textContent = nf.format(this.wallet.balance);
      render(this.body, state as never, send, this.ui);
    });
    if (!this.dialog.open) this.dialog.showModal();
    this.body.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus();
  }

  hide(): void {
    this.unsubscribe?.();
    this.unsubscribe = null;
    if (this.dialog.open) this.dialog.close();
  }
}

/** Shared helpers for renderers. */
export function cardHtml(c: { rank: number; suit: string } | null, hidden = false): string {
  if (!c || hidden || c.rank === 0) return '<span class="card card--back" aria-label="face-down card"></span>';
  const r = c.rank <= 10 ? String(c.rank) : ['J', 'Q', 'K', 'A'][c.rank - 11];
  const s = { S: '♠', H: '♥', D: '♦', C: '♣' }[c.suit as 'S'];
  const names = { S: 'spades', H: 'hearts', D: 'diamonds', C: 'clubs' }[c.suit as 'S'];
  const red = c.suit === 'H' || c.suit === 'D';
  return `<span class="card${red ? ' card--red' : ''}" aria-label="${r} of ${names}">${r}<small>${s}</small></span>`;
}

export const fmt = (n: number) => nf.format(n);
