import { handTotal, type BaccaratSide, type BaccaratState } from '../../games/baccarat/baccarat';
import { fmt, type GameUi } from '../gameView';

const LABEL: Record<BaccaratSide, string> = { player: 'Joueur', banker: 'Banque', tie: 'Égalité' };

/** Punto banco controls — the croupier deals on the 3D felt. */
export function renderBaccarat(body: HTMLElement, s: BaccaratState, send: (c: unknown) => void, ui: GameUi): void {
  body.innerHTML = `
    ${s.player.length ? `<span class="game__info">Joueur <b>${handTotal(s.player)}</b> · Banque <b>${handTotal(s.banker)}</b></span><span class="game__sep"></span>` : ''}
    <span class="game__info">Bet ${fmt(ui.stake)} on</span>
    <button data-on="player">Joueur 1:1</button><button data-on="banker">Banque 0.95:1</button><button data-on="tie">Égalité 8:1</button>`;
  body.querySelectorAll<HTMLButtonElement>('[data-on]').forEach((b) => b.addEventListener('click', () => send({ type: 'deal', on: b.dataset.on, amount: ui.stake })));
  if (ui.busy) ui.status('The croupier deals the coup…');
  else if (s.winner && s.bet) {
    const won = s.payout > 0;
    ui.status(`${LABEL[s.winner]} wins ${handTotal(s.winner === 'banker' ? s.banker : s.player)}. ${won ? `+${fmt(s.payout)}` : s.payout < 0 ? fmt(s.payout) : 'Stake returned.'}`, won ? 'win' : s.payout < 0 ? 'lose' : '');
  } else ui.status('Choose a stake, then bet on Joueur, Banque or Égalité.');
}
