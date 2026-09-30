import { PAYTABLE, type SlotSymbol, type SlotsState } from '../../games/slots/slots';
import { fmt, type GameUi } from '../gameView';

const GLYPH: Record<SlotSymbol, [string, string]> = {
  cherry: ['🍒', 'cherry'], lemon: ['🍋', 'lemon'], bell: ['🔔', 'bell'], bar: ['▬', 'bar'], seven: ['7', 'seven'], diamond: ['♦', 'diamond'],
};

export function renderSlots(body: HTMLElement, s: SlotsState, send: (c: unknown) => void, ui: GameUi): void {
  const spun = ui.lastEvents.some((e) => e.type === 'spin');
  body.innerHTML = `
    <div class="game__row" style="gap:20px;align-items:flex-start">
      <div class="reels" role="img" aria-label="${s.reels.map((r) => GLYPH[r][1]).join(', ')}">
        ${s.reels.map((r, i) => `<div class="reel ${spun ? 'reel--spin' : ''}" style="animation-delay:${i * 120}ms">${GLYPH[r][0]}</div>`).join('')}
      </div>
      <div class="game__label" style="line-height:1.7">Three of a kind pays:<br>
        ${Object.entries(PAYTABLE).map(([k, v]) => `${GLYPH[k as SlotSymbol][0]} ×${v}`).join(' · ')}<br>Two cherries ×2 · one cherry returns the stake</div>
    </div>
    ${ui.chipSelector()}
    <div class="game__row"><button data-cmd="spin">Spin</button></div>`;
  body.querySelector<HTMLButtonElement>('[data-cmd="spin"]')!.addEventListener('click', () => send({ type: 'spin', bet: ui.stake }));
  if (spun) {
    const net = s.lastWin - s.lastBet;
    ui.status(s.lastWin ? `Win ${fmt(s.lastWin)}${net > 0 ? ` (+${fmt(net)})` : ''}!` : 'No win this time.', s.lastWin > s.lastBet ? 'win' : s.lastWin ? '' : 'lose');
  } else ui.status('Choose a stake and spin.');
}
