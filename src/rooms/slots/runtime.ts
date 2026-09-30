import { Color, InstancedMesh, Matrix4, type Mesh, type MeshStandardMaterial } from 'three/webgpu';
import type { SlotsState } from '../../games/slots/slots';
import { tableAssets } from '../../tables/assets';
import { Tweens } from '../../tables/tween';
import type { ZoneInstance } from '../../world/roomBuilder';

/**
 * Slot room runtime (§5 rooms/). Every machine's three reels are drums on its `ANCHOR_ … reel` empties,
 * drawn as ONE instanced mesh for the whole room. A spin rolls the reels down and stops them one by one on
 * the engine's symbols (§9: the reels show the result, they don't choose it), with a small mechanical
 * bounce. The cabinets' bulbs (`MAT_Slots_Lights`) glow warm with a slow, gentle breathing — not a flicker.
 */
interface Reel { index: number; tableId: string; reel: number; base: Matrix4; angle: number }

export function enhanceSlots(inst: ZoneInstance): void {
  // ---- bulbs
  const mats = new Set<MeshStandardMaterial>();
  inst.root.traverse((o) => {
    const m = (o as Mesh).material as MeshStandardMaterial | undefined;
    if (m && !Array.isArray(m) && m.name === 'MAT_Slots_Lights') mats.add(m);
  });
  const warm = new Color().setHSL(0.09, 0.95, 0.55);
  for (const m of mats) m.emissive.copy(warm);

  // ---- reels
  const anchors = (inst.anchors ?? []).filter((a) => a.role === 'reel');
  const assets = tableAssets();
  const stops = assets.reelStops;
  const reels: Reel[] = [];
  const tw = new Tweens();
  let mesh: InstancedMesh | null = null;
  const rot = new Matrix4();
  const m4 = new Matrix4();
  if (anchors.length) {
    const r0 = anchors[0].extras;
    const geometry = assets.reel(Number(r0.radius ?? 0.115), Number(r0.width ?? 0.125));
    mesh = new InstancedMesh(geometry, assets.reelMaterial, anchors.length);
    mesh.name = `PROP_${inst.id}_Reels`;
    inst.root.updateMatrixWorld(true);
    const toRoot = new Matrix4().copy(inst.root.matrixWorld).invert();
    anchors.forEach((a, i) => {
      const base = new Matrix4().multiplyMatrices(toRoot, a.node.matrixWorld);
      // idle: each machine rests on some line of symbols
      const k = (a.tableId.length * 7 + a.index * 5 + i) % stops.length;
      reels.push({ index: i, tableId: a.tableId, reel: a.index, base, angle: angleFor(k, stops.length) });
    });
    reels.forEach((r) => write(r));
    inst.root.add(mesh);
  }

  function write(r: Reel): void {
    m4.multiplyMatrices(r.base, rot.makeRotationX(r.angle));
    mesh!.setMatrixAt(r.index, m4);
    mesh!.instanceMatrix.needsUpdate = true;
  }

  inst.animate.push((t) => {
    const breath = 3.6 + Math.sin(t * 1.3) * 0.35;           // slow, subtle
    for (const m of mats) m.emissiveIntensity = breath;
    tw.update(t);
  });

  inst.onGameState = (tableId, state, events) => {
    const spin = events.find((e) => e.type === 'spin');
    if (!spin || !state || !mesh) return;
    const symbols = (state as SlotsState).reels;
    const mine = reels.filter((r) => r.tableId === tableId).sort((a, b) => a.reel - b.reel);
    return Promise.all(mine.map((r, i) => {
      const options = stops.map((s, k) => (s === symbols[i] ? k : -1)).filter((k) => k >= 0);
      const k = options[Math.floor(Math.random() * options.length)] ?? 0;
      const target = angleFor(k, stops.length);
      const from = r.angle;
      // roll downward (angle decreasing) several turns, landing exactly on the target stop
      const delta = 2 * Math.PI * (3 + i) + mod(from - target, 2 * Math.PI);
      const dur = 1.5 + i * 0.45;
      return tw.add(0, dur, (u) => {
        r.angle = from - delta * reelEase(u);
        write(r);
      }, (u) => u);
    })).then(() => {});
  };
}

/** Rotation that puts stop `k` (0 = top of the strip) at the payline. */
function angleFor(k: number, n: number): number {
  const v = 1 - (k + 0.5) / n;
  return -2 * Math.PI * v;
}
const mod = (a: number, m: number) => ((a % m) + m) % m;
/** Spin up briefly, run, then decelerate with a small overshoot-and-settle "clunk". */
function reelEase(u: number): number {
  if (u < 0.08) return 0.5 * (u / 0.08) * (u / 0.08) * 0.08;             // quick spin-up
  const k = (u - 0.08) / 0.92;
  const base = 0.04 + 0.96 * (1 - Math.pow(1 - k, 3));
  const clunk = k > 0.9 ? Math.sin(((k - 0.9) / 0.1) * Math.PI) * 0.004 : 0;
  return Math.min(1 + clunk, base + clunk);
}
