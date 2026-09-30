import { RED, type RouletteState } from '../../games/roulette/roulette';
import { fmt, type GameUi } from '../gameView';

/**
 * Roulette controls. Bets are placed by clicking the printed layout on the 3D table (main.ts raycasts the
 * felt); the buttons here cover the outside bets and a numbered bet for keyboard players.
 */
export function renderRoulette(body: HTMLElement, s: RouletteState, send: (c: unknown) => void, ui: GameUi): void {
  const staked = s.bets.reduce((t, b) => t + b.amount, 0);
  const justSpun = ui.lastEvents.some((e) => e.type === 'spin');
  const colour = (n: number) => (n === 0 ? '#136b33' : RED.has(n) ? '#8e1414' : '#141010');
  body.innerHTML = `
    ${s.lastResult !== null && !(ui.busy && justSpun) ? `<span class="rl-last" style="background:${colour(s.lastResult)}" aria-label="last result">${s.lastResult}</span>` : ''}
    <span class="rl-history" aria-label="recent results">${s.history.slice(0, 8).map((n) => `<span class="${RED.has(n) ? 'r' : ''}">${n}</span>`).join('')}</span>
    <span class="game__sep"></span>
    <span class="game__info">On the table <b>${fmt(staked)}</b></span>
    ${[['red', 'Rouge'], ['black', 'Noir'], ['even', 'Pair'], ['odd', 'Impair'], ['low', '1–18'], ['high', '19–36']].map(([k, l]) => `<button data-kind="${k}">${l}</button>`).join('')}
    <label class="rl-hint">No. <input class="rl-num-input" type="number" min="0" max="36" inputmode="numeric" aria-label="Bet on number"></label>
    <span class="game__sep"></span>
    <button class="primary" data-cmd="spin" ${s.bets.length ? '' : 'disabled'}>Spin</button><button data-cmd="clear" ${s.bets.length ? '' : 'disabled'}>Clear</button>`;
  body.querySelectorAll<HTMLButtonElement>('[data-kind]').forEach((b) => b.addEventListener('click', () =>
    send({ type: 'bet', bet: { kind: b.dataset.kind, amount: ui.stake } })));
  const num = body.querySelector<HTMLInputElement>('.rl-num-input')!;
  num.addEventListener('keydown', (e) => {
    const n = Number(num.value);
    if (e.key === 'Enter' && Number.isInteger(n) && n >= 0 && n <= 36) send({ type: 'bet', bet: { kind: 'straight', value: n, amount: ui.stake } });
  });
  body.querySelectorAll<HTMLButtonElement>('[data-cmd]').forEach((b) => b.addEventListener('click', () => send({ type: b.dataset.cmd })));
  if (ui.busy && justSpun) ui.status('Rien ne va plus — the ball is rolling…');
  else if (justSpun && s.lastResult !== null) {
    const n = s.lastResult;
    ui.status(`${n} ${n === 0 ? 'zéro' : RED.has(n) ? 'rouge' : 'noir'}. ${s.lastPayout > 0 ? `You win +${fmt(s.lastPayout)}.` : s.lastPayout < 0 ? `${fmt(s.lastPayout)}.` : 'Even.'}`, s.lastPayout > 0 ? 'win' : 'lose');
  } else if (s.bets.length) ui.status('Faites vos jeux — click the layout to add chips, then spin.');
  else ui.status('Choose a chip, then click a number or box on the layout.');
}
