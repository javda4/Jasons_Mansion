import { RED, type RouletteState } from '../../games/roulette/roulette';
import { fmt, type GameUi } from '../gameView';

export function renderRoulette(body: HTMLElement, s: RouletteState, send: (c: unknown) => void, ui: GameUi): void {
  const staked = s.bets.reduce((t, b) => t + b.amount, 0);
  const justSpun = ui.lastEvents.some((e) => e.type === 'spin');
  const colour = (n: number) => (n === 0 ? 'green' : RED.has(n) ? 'red' : 'black');
  // layout rows: 3,6,…36 / 2,5,…35 / 1,4,…34 like the felt
  const rows = [3, 2, 1].map((r) => Array.from({ length: 12 }, (_, i) => i * 3 + r));
  body.innerHTML = `
    <div class="game__row" style="gap:18px">
      <div class="rl-result ${justSpun ? 'rl-spinning' : ''}" style="background:${s.lastResult === null ? 'transparent' : colour(s.lastResult) === 'red' ? '#8e1414' : colour(s.lastResult) === 'green' ? '#136b33' : '#141010'}"
        aria-label="last result">${s.lastResult ?? '–'}</div>
      <div><div class="game__label">Recent</div><div class="rl-history">${s.history.map((n) => `<span>${n}</span>`).join('')}</div></div>
      <div style="margin-left:auto" class="game__label">On the table: <b>${fmt(staked)}</b></div>
    </div>
    ${ui.chipSelector()}
    <div class="game__row" style="align-items:stretch">
      <button class="rl-num rl-zero" data-straight="0" style="width:3em">0</button>
      <div class="rl-grid" style="flex:1">${rows.flat().map((n) => `<button class="rl-num" data-straight="${n}" data-c="${RED.has(n) ? 'r' : 'b'}">${n}</button>`).join('')}</div>
    </div>
    <div class="game__row">
      ${[['dozen', 1, '1–12'], ['dozen', 2, '13–24'], ['dozen', 3, '25–36'], ['low', 0, '1–18'], ['even', 0, 'Pair'], ['red', 0, 'Rouge'], ['black', 0, 'Noir'], ['odd', 0, 'Impair'], ['high', 0, '19–36']]
        .map(([k, v, l]) => `<button data-kind="${k}" data-value="${v}">${l}</button>`).join('')}
    </div>
    <div class="game__row"><button data-cmd="spin" ${s.bets.length ? '' : 'disabled'}>Spin</button><button data-cmd="clear" ${s.bets.length ? '' : 'disabled'}>Clear bets</button></div>`;
  body.querySelectorAll<HTMLButtonElement>('[data-straight]').forEach((b) => b.addEventListener('click', () =>
    send({ type: 'bet', bet: { kind: 'straight', value: Number(b.dataset.straight), amount: ui.stake } })));
  body.querySelectorAll<HTMLButtonElement>('[data-kind]').forEach((b) => b.addEventListener('click', () =>
    send({ type: 'bet', bet: { kind: b.dataset.kind, value: Number(b.dataset.value) || undefined, amount: ui.stake } })));
  body.querySelectorAll<HTMLButtonElement>('[data-cmd]').forEach((b) => b.addEventListener('click', () => send({ type: b.dataset.cmd })));
  if (justSpun && s.lastResult !== null) {
    const n = s.lastResult;
    ui.status(`${n} ${colour(n) === 'red' ? 'rouge' : colour(n) === 'black' ? 'noir' : 'zéro'}. ${s.lastPayout > 0 ? `You win +${fmt(s.lastPayout)}.` : s.lastPayout < 0 ? `${fmt(s.lastPayout)}.` : 'Even.'}`, s.lastPayout > 0 ? 'win' : 'lose');
  } else if (s.bets.length) ui.status(`${s.bets.length} bet${s.bets.length > 1 ? 's' : ''} placed — faites vos jeux, then spin.`);
  else ui.status('Choose a stake, place bets on the layout, then spin.');
}
