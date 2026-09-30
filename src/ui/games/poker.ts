import type { PokerState } from '../../games/poker/poker';
import { cardHtml, fmt, type GameUi } from '../gameView';

export function renderPoker(body: HTMLElement, s: PokerState, send: (c: unknown) => void, ui: GameUi): void {
  const live = ['preflop', 'flop', 'turn', 'river'].includes(s.street);
  const board = [...s.board, ...Array(5 - s.board.length).fill(null)];
  body.innerHTML = `
    <div class="hand"><span class="hand__label">Board</span>${board.map((c) => (c ? cardHtml(c) : '<span class="card card--back" style="opacity:.25"></span>')).join('')}
      <span class="hand__total" style="margin-left:auto">Pot ${fmt(s.pot)}</span></div>
    ${s.seats.map((seat) => `
      <div class="hand" style="min-height:70px;opacity:${seat.folded ? 0.4 : 1}">
        <span class="hand__label">${seat.name}${seat.folded ? ' · fold' : ''}</span>
        ${seat.hole.map((c) => cardHtml(c, !seat.isPlayer && s.street !== 'showdown')).join('')}
      </div>`).join('')}
    <div class="game__row">
      ${live
        ? `<button data-cmd="check">${s.toCall ? 'Call' : 'Check'}</button><button data-cmd="raise">Raise ${fmt(s.betSize)}</button><button data-cmd="fold">Fold</button>`
        : '<button data-cmd="deal">Deal (ante 10)</button>'}
    </div>`;
  body.querySelectorAll<HTMLButtonElement>('[data-cmd]').forEach((b) => b.addEventListener('click', () => send({ type: b.dataset.cmd })));
  if (s.street === 'showdown') {
    const youWon = s.winners.includes('You');
    ui.status(s.winningHand ? `${s.winners.join(' & ')} win${s.winners.length > 1 ? '' : 's'} with ${s.winningHand.toLowerCase()}. ${youWon ? `+${fmt(s.payout)}` : ''}` : 'You fold; the house takes the pot.', youWon ? 'win' : 'lose');
  } else if (live) ui.status(`${s.street[0].toUpperCase()}${s.street.slice(1)} — your action.`);
  else ui.status('Deal a hand of Texas Hold’em against the house.');
}
