import { handValue, type BlackjackState } from '../../games/blackjack/blackjack';
import { cardHtml, fmt, type GameUi } from '../gameView';

const OUTCOME: Record<string, [string, 'win' | 'lose' | '']> = {
  blackjack: ['Blackjack! Paid three to two.', 'win'], win: ['You win.', 'win'], push: ['Push — your stake is returned.', ''],
  lose: ['The house wins.', 'lose'], bust: ['Bust.', 'lose'],
};

export function renderBlackjack(body: HTMLElement, s: BlackjackState, send: (c: unknown) => void, ui: GameUi): void {
  const inHand = s.phase === 'player';
  const dealerShown = s.dealerHidden ? s.dealer.slice(0, 1) : s.dealer;
  body.innerHTML = `
    <div class="hand"><span class="hand__label">Dealer</span>${s.dealer.map((c, i) => cardHtml(c, s.dealerHidden && i === 1)).join('')}
      <span class="hand__total">${s.dealer.length ? handValue(dealerShown).total : ''}</span></div>
    <div class="hand"><span class="hand__label">You</span>${s.player.map((c) => cardHtml(c)).join('')}
      <span class="hand__total">${s.player.length ? handValue(s.player).total : ''}</span></div>
    ${inHand ? '' : ui.chipSelector()}
    <div class="game__row">
      ${inHand
        ? `<button data-cmd="hit">Hit</button><button data-cmd="stand">Stand</button>
           <button data-cmd="double" ${s.player.length === 2 && s.chips >= s.bet ? '' : 'disabled'}>Double</button>`
        : `<button data-cmd="deal">Deal</button>`}
    </div>`;
  body.querySelectorAll<HTMLButtonElement>('[data-cmd]').forEach((b) => b.addEventListener('click', () => {
    const t = b.dataset.cmd!;
    send(t === 'deal' ? { type: 'deal', bet: ui.stake } : { type: t });
  }));
  if (s.phase === 'settled' && s.outcome) {
    const [text, tone] = OUTCOME[s.outcome];
    ui.status(`${text} ${s.payout > 0 ? `+${fmt(s.payout)}` : s.payout < 0 ? fmt(s.payout) : ''}`, tone);
  } else if (inHand) ui.status(`Bet ${fmt(s.bet)} — hit or stand?`);
  else ui.status('Choose a stake and deal.');
}
