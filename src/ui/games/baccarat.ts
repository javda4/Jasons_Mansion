import { handTotal, type BaccaratSide, type BaccaratState } from '../../games/baccarat/baccarat';
import { cardHtml, fmt, type GameUi } from '../gameView';

const LABEL: Record<BaccaratSide, string> = { player: 'Joueur', banker: 'Banque', tie: 'Égalité' };

export function renderBaccarat(body: HTMLElement, s: BaccaratState, send: (c: unknown) => void, ui: GameUi): void {
  body.innerHTML = `
    <div class="hand"><span class="hand__label">Joueur</span>${s.player.map((c) => cardHtml(c)).join('')}<span class="hand__total">${s.player.length ? handTotal(s.player) : ''}</span></div>
    <div class="hand"><span class="hand__label">Banque</span>${s.banker.map((c) => cardHtml(c)).join('')}<span class="hand__total">${s.banker.length ? handTotal(s.banker) : ''}</span></div>
    ${ui.chipSelector()}
    <div class="game__row"><span class="game__label">Bet on</span>
      <button data-on="player">Player 1:1</button><button data-on="banker">Banker 0.95:1</button><button data-on="tie">Tie 8:1</button></div>`;
  body.querySelectorAll<HTMLButtonElement>('[data-on]').forEach((b) => b.addEventListener('click', () => send({ type: 'deal', on: b.dataset.on, amount: ui.stake })));
  if (s.winner && s.bet) {
    const won = s.payout > 0;
    ui.status(`${LABEL[s.winner]} wins ${handTotal(s.winner === 'banker' ? s.banker : s.player)}. ${won ? `+${fmt(s.payout)}` : s.payout < 0 ? fmt(s.payout) : 'Stake returned.'}`, won ? 'win' : s.payout < 0 ? 'lose' : '');
  } else ui.status('Choose a stake, then bet on Player, Banker or Tie.');
}
