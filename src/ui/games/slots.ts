import type { SlotsState } from '../../games/slots/slots';
import { fmt, type GameUi } from '../gameView';

/** Slot controls — the reels turn in the machine in front of you. */
export function renderSlots(body: HTMLElement, s: SlotsState, send: (c: unknown) => void, ui: GameUi): void {
  const spun = ui.lastEvents.some((e) => e.type === 'spin');
  body.innerHTML = `<span class="game__info">Three alike pay up to <b>×150</b> · cherries pay</span><span class="game__sep"></span>
    <button class="primary" data-cmd="spin">Pull · ${fmt(ui.stake)}</button>`;
  body.querySelector<HTMLButtonElement>('[data-cmd="spin"]')!.addEventListener('click', () => send({ type: 'spin', bet: ui.stake }));
  if (ui.busy && spun) ui.status('The reels are turning…');
  else if (spun) {
    const net = s.lastWin - s.lastBet;
    ui.status(s.lastWin ? `Win ${fmt(s.lastWin)}${net > 0 ? ` (+${fmt(net)})` : ''}!` : 'No win this time.', s.lastWin > s.lastBet ? 'win' : s.lastWin ? '' : 'lose');
  } else ui.status('Choose a stake and pull the lever.');
}
