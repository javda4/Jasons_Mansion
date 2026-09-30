import { Box3, CylinderGeometry, Group, Mesh, MeshStandardMaterial, Vector3, type Object3D } from 'three/webgpu';
import { betReturn, type RouletteBet, type RouletteState } from '../../games/roulette/roulette';
import type { GameEvent } from '../../games/shared/types';
import { tableAssets } from '../../tables/assets';
import { chipPile, movePile, TableAnchors } from '../../tables/table';
import { easeOut, linear, Tweens } from '../../tables/tween';
import type { AnchorDef, ZoneInstance } from '../../world/roomBuilder';

/**
 * Roulette room runtime (§5 rooms/) for the Blender-authored zone. Rotors (`PROP_Roulette_Rotor_NN`,
 * extras `{ rotor: tableId }`) idle and spin up on a spin; the ball circles the track, drops and settles in
 * the pocket of the engine's result (§9: it shows the result, never picks it). Chips sit on the printed
 * layout (ANCHOR_ `layout` extras carry the bet-box positions) and are collected or paid after the spin.
 */
interface Rotor { pivot: Group; tableId: string; base: number; angle: number; boostAt: number }

export function enhanceRoulette(inst: ZoneInstance): void {
  const rotors: Rotor[] = [];
  const found: Object3D[] = [];
  inst.root.traverse((o) => { if (typeof o.userData.rotor === 'string') found.push(o); });
  for (const node of found) {
    // spin about the geometric centre: mesh quantization can move node origins (see glbZone doors)
    const centre = new Box3().setFromObject(node).getCenter(new Vector3());
    const pivot = new Group();
    pivot.name = `${node.name}_Pivot`;
    node.parent!.add(pivot);
    pivot.position.copy(pivot.parent!.worldToLocal(centre.clone()));
    pivot.updateMatrixWorld(true);
    pivot.attach(node);
    rotors.push({ pivot, tableId: node.userData.rotor, base: 0.35 + rotors.length * 0.07, angle: rotors.length, boostAt: -1e9 });
  }
  const byTable = new Map<string, AnchorDef[]>();
  for (const a of inst.anchors ?? []) (byTable.get(a.tableId) ?? byTable.set(a.tableId, []).get(a.tableId)!).push(a);
  const tables = new Map<string, RouletteTable>();

  let now = 0, last = 0;
  inst.animate.push((t) => {
    const dt = Math.min(0.1, t - last);
    last = now = t;
    for (const r of rotors) {
      const extra = 7 * Math.exp(-(t - r.boostAt) / 1.6);
      r.angle += (r.base + extra) * dt;
      r.pivot.rotation.y = r.angle;
    }
    for (const tb of tables.values()) tb.tick(t);
  });
  const tableFor = (tableId: string): RouletteTable | undefined => {
    let tb = tables.get(tableId);
    const anchors = byTable.get(tableId);
    const rotor = rotors.find((x) => x.tableId === tableId);
    if (!tb && anchors?.some((a) => a.role === 'wheel') && rotor) tables.set(tableId, (tb = new RouletteTable(new TableAnchors(anchors), rotor, () => now)));
    return tb;
  };
  // every wheel shows a ball resting in a pocket, played or not
  for (const id of byTable.keys()) tableFor(id);
  inst.onGameState = (tableId, state, events) => tableFor(tableId)?.update(state as RouletteState | null, events as GameEvent[]);
}

const keyOf = (b: RouletteBet) => `${b.kind}:${b.value ?? ''}`;
const TO_GUEST = new Vector3(0, 0, 0.55);        // layout-local: +Z points at the players' rail
/** The printed layout is ~2× a real one (it must read from the overhead seat), so chips and ball scale with it. */
const CHIP_SCALE = 1.7;
const BALL_SCALE = 1.35;

class RouletteTable {
  private tw = new Tweens();
  private piles = new Map<string, { pile: Group; amount: number; bet: RouletteBet }>();
  private ball: Mesh;
  private ballPocket: number | null;               // index in the wheel order while resting
  private dolly: Mesh | null = null;
  private readonly layout: Object3D;
  private readonly wheel: Object3D;
  /** offset: angle of pocket 0's leading edge in the zone frame (a wheel whose art isn't aligned to +X). */
  private readonly W: { trackRadius: number; trackZ: number; pocketRadius: number; pocketZ: number; order: number[]; offset?: number };
  private readonly L: { numbers: [number, number][]; dozens: [number, number][]; outside: [number, number][]; outsideKeys: string[] };

  constructor(private readonly a: TableAnchors, private readonly rotor: Rotor, private readonly clock: () => number) {
    this.layout = a.get('layout')!;
    this.wheel = a.get('wheel')!;
    this.W = a.extras('wheel') as RouletteTable['W'];
    this.L = a.extras('layout') as RouletteTable['L'];
    const assets = tableAssets();
    this.ball = new Mesh(assets.ball, assets.ballMaterial);
    this.ball.castShadow = true;
    this.ball.scale.setScalar(BALL_SCALE);
    this.wheel.add(this.ball);
    this.ballPocket = Math.floor(Math.random() * 37);
  }

  /** Layout-plan position of a bet box, in the layout anchor's frame (plan y → −Z). */
  private spot(b: RouletteBet): Vector3 {
    const L = this.L;
    const xy = b.kind === 'straight' ? L.numbers[b.value ?? 0] : b.kind === 'dozen' ? L.dozens[(b.value ?? 1) - 1] : L.outside[L.outsideKeys.indexOf(b.kind)];
    return new Vector3(xy[0], 0, -xy[1]);
  }

  /** World position of pocket `i` right now (it turns with the rotor). */
  private pocketWorld(i: number, out = new Vector3()): Vector3 {
    const th = (this.W.offset ?? 0) + (2 * Math.PI * (i + 0.5)) / 37;
    out.set(this.W.pocketRadius * Math.cos(th), 0, -this.W.pocketRadius * Math.sin(th));
    this.rotor.pivot.localToWorld(out);
    out.y = this.wheel.getWorldPosition(_w).y + this.W.pocketZ + 0.0095 * BALL_SCALE;
    return out;
  }

  private trackWorld(psi: number, radius: number, z: number, out = new Vector3()): Vector3 {
    return this.wheel.localToWorld(out.set(radius * Math.cos(psi), z, -radius * Math.sin(psi)));
  }

  tick(t: number): void {
    this.tw.update(t);
    if (this.ballPocket !== null) this.ball.position.copy(this.wheel.worldToLocal(this.pocketWorld(this.ballPocket, _p)));
  }

  async update(s: RouletteState | null, events: GameEvent[]): Promise<void> {
    if (!s) { this.clear(); return; }
    if (events.some((e) => e.type === 'cleared')) {
      await Promise.all([...this.piles.values()].map(({ pile }, i) => movePile(this.tw, pile, this.layout, TO_GUEST.clone(), i * 0.03, 0.4).then(() => { pile.removeFromParent(); })));
      this.piles.clear();
    }
    const spin = events.find((e) => e.type === 'spin');
    if (!spin) { this.syncBets(s.bets); return; }
    this.dolly?.removeFromParent();
    this.dolly = null;
    this.rotor.boostAt = this.clock();
    await this.throwBall(Number(spin.result));
    await this.settle(Number(spin.result));
  }

  private syncBets(bets: RouletteBet[]): void {
    const want = new Map<string, { amount: number; bet: RouletteBet }>();
    for (const b of bets) {
      const k = keyOf(b);
      want.set(k, { amount: (want.get(k)?.amount ?? 0) + b.amount, bet: b });
    }
    for (const [k, w] of want) {
      const cur = this.piles.get(k);
      if (cur && cur.amount === w.amount) continue;
      cur?.pile.removeFromParent();
      const pile = chipPile(w.amount);
      pile.scale.setScalar(CHIP_SCALE);
      const at = this.spot(w.bet);
      this.layout.add(pile);
      this.piles.set(k, { pile, amount: w.amount, bet: w.bet });
      if (cur) pile.position.copy(at);
      else { pile.position.copy(at).add(TO_GUEST); void movePile(this.tw, pile, this.layout, at, 0, 0.45); }
    }
  }

  /** The croupier's throw: the ball runs the track against the rotor, slows, drops and settles. */
  private throwBall(result: number): Promise<void> {
    const W = this.W;
    const target = W.order.indexOf(result);
    this.ballPocket = null;
    const psi0 = Math.random() * Math.PI * 2;
    const run = 3.6, drop = 1.7, w0 = 13, w1 = 3.2;
    const tmp = new Vector3(), end = new Vector3();
    const psiAt = (t: number) => psi0 + w0 * t - ((w0 - w1) / (2 * run)) * t * t;    // decelerating, against the rotor
    return this.tw.add(0, run, (k) => {
      this.ball.position.copy(this.wheel.worldToLocal(this.trackWorld(psiAt(k * run), W.trackRadius, W.trackZ, tmp)));
    }, linear).then(() => this.tw.add(0, drop, (k) => {
      const psi = psiAt(run) + w1 * k * drop * (1 - k * 0.5);
      const r = W.trackRadius + (W.pocketRadius - W.trackRadius) * easeOut(Math.min(1, k * 1.4));
      const free = this.trackWorld(psi, r, W.trackZ + (W.pocketZ - W.trackZ) * easeOut(Math.min(1, k * 1.6)), tmp);
      free.lerp(this.pocketWorld(target, end), k * k * (3 - 2 * k));
      free.y += Math.abs(Math.sin(k * Math.PI * 3)) * 0.014 * (1 - k);            // clatters over the frets
      this.ball.position.copy(this.wheel.worldToLocal(free));
    }, linear)).then(() => { this.ballPocket = target; });
  }

  private async settle(result: number): Promise<void> {
    // brass dolly on the winning number
    const dolly = new Mesh(DOLLY_GEOMETRY, DOLLY_MATERIAL);
    dolly.position.copy(this.spot({ kind: 'straight', value: result, amount: 0 })).add(new Vector3(0, 0.025, 0));
    dolly.castShadow = true;
    this.layout.add(dolly);
    this.dolly = dolly;
    const tray = this.a.get('chipTray') ?? this.wheel;
    const jobs: Promise<void>[] = [];
    let i = 0;
    for (const [k, p] of this.piles) {
      const ret = betReturn({ ...p.bet, amount: p.amount }, result);
      if (ret === 0) {
        jobs.push(movePile(this.tw, p.pile, tray, new Vector3(0, 0.02, 0), 0.3 + i * 0.05, 0.5).then(() => { p.pile.removeFromParent(); }));
      } else {
        const win = chipPile(ret - p.amount);
        win.scale.setScalar(CHIP_SCALE);
        this.layout.add(win);
        win.position.copy(this.spot(p.bet)).add(new Vector3(0.045 * CHIP_SCALE, 0, 0));
        jobs.push(this.tw.wait(0.9).then(() => Promise.all([
          movePile(this.tw, win, this.layout, TO_GUEST.clone(), 0, 0.6).then(() => { win.removeFromParent(); }),
          movePile(this.tw, p.pile, this.layout, TO_GUEST.clone().add(new Vector3(-0.04, 0, 0)), 0, 0.6).then(() => { p.pile.removeFromParent(); }),
        ])).then(() => {}));
      }
      this.piles.delete(k);
      i++;
    }
    await Promise.all(jobs);
  }

  private clear(): void {
    this.tw.flush();
    for (const p of this.piles.values()) p.pile.removeFromParent();
    this.piles.clear();
    this.dolly?.removeFromParent();
    this.dolly = null;
  }
}

const _w = new Vector3();
const _p = new Vector3();
const DOLLY_GEOMETRY = new CylinderGeometry(0.011, 0.016, 0.05, 20);
DOLLY_GEOMETRY.userData.shared = true;
const DOLLY_MATERIAL = new MeshStandardMaterial({ color: 0xc9a24e, metalness: 1, roughness: 0.32 });
DOLLY_MATERIAL.userData.shared = true;
