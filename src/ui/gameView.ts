import type { GameSession, Wallet } from '../games/shared/session';
import type { GameEvent, GameType } from '../games/shared/types';
import './gameView.css';
import { renderBaccarat } from './games/baccarat';
import { renderBlackjack } from './games/blackjack';
import { renderPoker } from './games/poker';
import { renderRoulette } from './games/roulette';
import { renderSlots } from './games/slots';

/** Per-game controls: info + actions for `body`, commands via `send`. UI only — no rules, no cards (the table shows them). */
export type GameRenderer = (body: HTMLElement, state: never, send: (cmd: unknown) => void, ui: GameUi) => void;

export interface GameUi {
  /** Selected stake (shared chip selector). */
  stake: number;
  /** True while the 3D table is still animating the last command: controls are disabled, the outcome waits. */
  busy: boolean;
  status(text: string, tone?: 'win' | 'lose' | ''): void;
  /** Show or hide the stake chips (poker plays a fixed ante). */
  stakes(visible: boolean): void;
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
 * The 2D half of a table: a slim lacquer-and-gilt control bar along the bottom of the seated view — the
 * game itself happens on the 3D table (src/tables). Non-modal, so the table stays clickable (roulette bets
 * are placed on the felt); Esc leaves. It subscribes to a GameSession and never decides outcomes (§9), and
 * it waits for the table's animation (`present`) before revealing a result or the new chip count.
 */
export class GameView {
  private dialog: HTMLDialogElement;
  private body: HTMLElement;
  private chips: HTMLElement;
  private stakeRow: HTMLElement;
  private statusEl: HTMLElement;
  private unsubscribe: (() => void) | null = null;
  private token = 0;
  private sendFn: ((cmd: unknown) => void) | null = null;
  readonly ui: GameUi;
  onLeave: () => void = () => {};
  /** Presentation hook for engine events (sounds). */
  onEvents: (events: GameEvent[]) => void = () => {};
  /** The 3D table's presentation of a new state; resolves when its animation has finished. */
  present: (state: unknown, events: GameEvent[]) => Promise<void> = () => Promise.resolve();

  constructor(private readonly wallet: Wallet) {
    this.dialog = document.createElement('dialog');
    this.dialog.className = 'game';
    this.dialog.setAttribute('aria-labelledby', 'game-title');
    this.dialog.innerHTML = `
      <div class="game__bar">
        <div class="game__meta">
          <h2 class="game__title" id="game-title"></h2>
          <p class="game__status" id="game-status" role="status" aria-live="polite"></p>
          <span class="game__chips">Chips <b id="game-chips"></b></span>
        </div>
        <div class="game__controls">
          <div class="game__body" id="game-body"></div>
          <div class="game__stakes" id="game-stakes" role="radiogroup" aria-label="Stake">
            ${STAKES.map((s, i) => `<button type="button" class="chip chip--${i}" data-stake="${s}" role="radio" aria-checked="${s === 25}" aria-label="Stake ${s}"><span>${s}</span></button>`).join('')}
          </div>
          <button type="button" class="game__leave" data-leave>Leave <kbd>Esc</kbd></button>
        </div>
      </div>`;
    document.body.append(this.dialog);
    this.body = this.dialog.querySelector('#game-body')!;
    this.chips = this.dialog.querySelector('#game-chips')!;
    this.stakeRow = this.dialog.querySelector('#game-stakes')!;
    this.statusEl = this.dialog.querySelector('#game-status')!;
    this.dialog.querySelector('[data-leave]')!.addEventListener('click', () => this.onLeave());
    // non-modal: Esc is ours to handle
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && this.dialog.open) { e.preventDefault(); this.onLeave(); } });
    this.stakeRow.addEventListener('click', (e) => {
      const b = (e.target as HTMLElement).closest<HTMLElement>('[data-stake]');
      if (!b) return;
      this.ui.stake = Number(b.dataset.stake);
      this.stakeRow.querySelectorAll('[data-stake]').forEach((x) => x.setAttribute('aria-checked', String(x === b)));
    });
    const self = this;
    this.ui = {
      stake: 25,
      busy: false,
      lastEvents: [],
      status: (text, tone = '') => { self.statusEl.textContent = text; self.statusEl.dataset.tone = tone; },
      stakes: (visible) => { self.stakeRow.hidden = !visible; },
    };
  }

  get open(): boolean { return this.dialog.open; }

  /** Send a command to the open table (e.g. a bet placed by clicking the 3D layout). */
  send(cmd: unknown): void { this.sendFn?.(cmd); }

  show(session: GameSession, tableLabel: string): void {
    this.unsubscribe?.();
    const token = ++this.token;
    this.dialog.querySelector('#game-title')!.textContent = `${TITLES[session.gameType]} · ${tableLabel}`;
    this.ui.status('');
    this.ui.busy = false;
    this.ui.stakes(true);
    const render = RENDERERS[session.gameType];
    const send = (this.sendFn = (cmd: unknown) => {
      if (this.ui.busy) return;
      const events = session.dispatch(cmd);
      const err = events.find((e) => e.type === 'error');
      if (err) this.ui.status(String(err.message), 'lose');
    });
    let balance = this.wallet.balance;
    const draw = (state: unknown) => {
      this.chips.textContent = nf.format(balance);
      render(this.body, state as never, send, this.ui);
      if (this.ui.busy) this.body.querySelectorAll<HTMLButtonElement>('button').forEach((b) => { b.disabled = true; });
    };
    this.unsubscribe = session.subscribe((state, events) => {
      this.ui.lastEvents = events;
      if (!events.length) { balance = this.wallet.balance; draw(state); return; }
      if (events.some((e) => e.type === 'error')) return;
      this.onEvents(events);
      this.ui.busy = true;
      draw(state);
      this.present(state, events).catch((err) => console.warn('[table] presentation failed', err)).finally(() => {
        if (token !== this.token) return;
        this.ui.busy = false;
        balance = this.wallet.balance;          // the chip count moves when the chips do
        draw(state);
      });
    });
    if (!this.dialog.open) this.dialog.show();
    this.body.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus();
  }

  hide(): void {
    this.token++;
    this.sendFn = null;
    this.unsubscribe?.();
    this.unsubscribe = null;
    if (this.dialog.open) this.dialog.close();
  }
}

export const fmt = (n: number) => nf.format(n);
