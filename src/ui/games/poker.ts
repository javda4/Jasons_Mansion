import type { PokerState } from '../../games/poker/poker';
import { fmt, type GameUi } from '../gameView';

/** Hold'em controls — your cards, the board and the pot are on the 3D table. */
export function renderPoker(body: HTMLElement, s: PokerState, send: (c: unknown) => void, ui: GameUi): void {
  ui.stakes(false);                                   // fixed-limit: ante and raise sizes are set by the table
  const live = ['preflop', 'flop', 'turn', 'river'].includes(s.street);
  const inHand = s.seats.filter((x) => !x.folded).map((x) => x.name).join(', ');
  body.innerHTML = `
    ${live || s.street === 'showdown' ? `<span class="game__info">Pot <b>${fmt(s.pot)}</b>${live ? ` · in: ${inHand}` : ''}</span><span class="game__sep"></span>` : ''}
    ${live
      ? `<button class="primary" data-cmd="check">${s.toCall ? `Call ${fmt(s.toCall)}` : 'Check'}</button><button data-cmd="raise">Raise ${fmt(s.betSize)}</button><button data-cmd="fold">Fold</button>`
      : '<button class="primary" data-cmd="deal">Deal · ante 10</button>'}`;
  body.querySelectorAll<HTMLButtonElement>('[data-cmd]').forEach((b) => b.addEventListener('click', () => send({ type: b.dataset.cmd })));
  if (ui.busy) ui.status(s.street === 'showdown' ? 'Showdown…' : 'The dealer deals…');
  else if (s.street === 'showdown') {
    const youWon = s.winners.includes('You');
    ui.status(s.winningHand ? `${s.winners.join(' & ')} win${s.winners.length > 1 ? '' : 's'} with ${s.winningHand.toLowerCase()}. ${youWon ? `+${fmt(s.payout)}` : ''}` : 'You fold; the house takes the pot.', youWon ? 'win' : 'lose');
  } else if (live) ui.status(`${s.street[0].toUpperCase()}${s.street.slice(1)} — your action.`);
  else ui.status('Deal a hand of Texas Hold’em against the house.');
}
