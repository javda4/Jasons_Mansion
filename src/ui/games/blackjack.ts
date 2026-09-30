import { handValue, type BlackjackState } from '../../games/blackjack/blackjack';
import { fmt, type GameUi } from '../gameView';

const OUTCOME: Record<string, [string, 'win' | 'lose' | '']> = {
  blackjack: ['Blackjack! Paid three to two.', 'win'], win: ['You win.', 'win'], push: ['Push — your stake is returned.', ''],
  lose: ['The house wins.', 'lose'], bust: ['Bust.', 'lose'],
};

/** Blackjack controls — the cards are dealt on the 3D felt. */
export function renderBlackjack(body: HTMLElement, s: BlackjackState, send: (c: unknown) => void, ui: GameUi): void {
  const inHand = s.phase === 'player';
  const shown = s.dealerHidden ? s.dealer.slice(0, 1) : s.dealer;
  const you = s.player.length ? handValue(s.player) : null;
  body.innerHTML = `
    ${s.player.length ? `<span class="game__info">You <b>${you!.soft && you!.total < 21 ? `${you!.total - 10}/${you!.total}` : you!.total}</b> · Dealer <b>${handValue(shown).total}</b></span><span class="game__sep"></span>` : ''}
    ${inHand
      ? `<button class="primary" data-cmd="hit">Hit</button><button data-cmd="stand">Stand</button>
         <button data-cmd="double" ${s.player.length === 2 && s.chips >= s.bet ? '' : 'disabled'}>Double</button>`
      : `<button class="primary" data-cmd="deal">Deal ${fmt(ui.stake)}</button>`}`;
  body.querySelectorAll<HTMLButtonElement>('[data-cmd]').forEach((b) => b.addEventListener('click', () => {
    const t = b.dataset.cmd!;
    send(t === 'deal' ? { type: 'deal', bet: ui.stake } : { type: t });
  }));
  if (ui.busy) ui.status(inHand || s.phase === 'settled' ? 'The dealer deals…' : '');
  else if (s.phase === 'settled' && s.outcome) {
    const [text, tone] = OUTCOME[s.outcome];
    ui.status(`${text} ${s.payout > 0 ? `+${fmt(s.payout)}` : s.payout < 0 ? fmt(s.payout) : ''}`, tone);
  } else if (inHand) ui.status(`Your bet ${fmt(s.bet)} — hit or stand?`);
  else ui.status('Choose a stake and deal.');
}
