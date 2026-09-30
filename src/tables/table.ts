import { Group, Mesh, Quaternion, Vector3, type Object3D } from 'three/webgpu';
import type { AnchorDef } from '../world/roomBuilder';
import { CARD_W, CHIP_H, CHIP_R, tableAssets, type Card } from './assets';
import { easeInOut, easeOut, Tweens } from './tween';

/**
 * Building blocks every table presenter shares (§9: the 3D table presents state; it never decides it).
 * Objects are parented to ANCHOR_ nodes, so the zone's transforms and the anchors' authored orientation
 * (local −Z = the top of a card as the guest reads it) apply for free.
 */
export class TableAnchors {
  constructor(private readonly list: AnchorDef[]) {}
  get(role: string, index = 0): Object3D | undefined {
    return this.list.find((a) => a.role === role && a.index === index)?.node;
  }
  all(role: string): AnchorDef[] { return this.list.filter((a) => a.role === role).sort((a, b) => a.index - b.index); }
  extras(role: string, index = 0): Record<string, unknown> {
    return this.list.find((a) => a.role === role && a.index === index)?.extras ?? {};
  }
}

const _p = new Vector3();
const FLIP = new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), Math.PI);   // face-down about the card's length

export interface CardView { mesh: Mesh; card: Card | null; faceUp: boolean }

/** Move `obj` (already somewhere in the scene) under `parent`, keeping its world pose, then tween it to a local pose. */
function glide(tw: Tweens, obj: Object3D, parent: Object3D, to: Vector3, toQ: Quaternion, delay: number, dur: number, lift = 0.05): Promise<void> {
  let from: Vector3, fromQ: Quaternion;
  return tw.add(delay, dur, (k) => {
    obj.position.lerpVectors(from, to, k);
    obj.position.y += Math.sin(Math.PI * k) * lift;
    obj.quaternion.slerpQuaternions(fromQ, toQ, k);
  }, easeInOut, () => {
    parent.attach(obj);
    from = obj.position.clone();
    fromQ = obj.quaternion.clone();
  });
}

export class CardTable {
  readonly tw = new Tweens();
  private cards: CardView[] = [];

  constructor(readonly anchors: TableAnchors) {}

  /** Pose for the i-th card of a hand laid at `role` (a slight fan, overlapping like a dealt hand). */
  handPose(i: number, faceUp: boolean, spread = 0.72): { pos: Vector3; q: Quaternion } {
    const pos = new Vector3((i - 0.5) * CARD_W * spread, 0.0004 + i * 0.0004, -i * 0.004);
    const q = new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), (i - 0.5) * -0.03);
    if (!faceUp) q.multiply(FLIP);
    return { pos, q };
  }

  /** Deal a card from the shoe to `anchor` at the given local pose; resolves on landing. */
  deal(card: Card | null, faceUp: boolean, anchor: Object3D, pose: { pos: Vector3; q: Quaternion }, delay: number): { view: CardView; done: Promise<void> } {
    const a = tableAssets();
    const shoe = this.anchors.get('shoe') ?? anchor;
    const mesh = new Mesh(a.card(faceUp ? card : null), a.cardMaterial);
    mesh.castShadow = true;
    mesh.visible = false;
    shoe.add(mesh);
    mesh.position.set(0, 0.01, 0);
    mesh.quaternion.copy(FLIP);                                     // leaves the shoe face down
    const view: CardView = { mesh, card, faceUp };
    this.cards.push(view);
    // the glide slerps from face-down (FLIP) to the target pose, so a face-up card turns over as it lands
    const done = this.tw.add(delay, 1e-3, () => { mesh.visible = true; })
      .then(() => glide(this.tw, mesh, anchor, pose.pos, pose.q, 0, 0.42, 0.06));
    return { view, done };
  }

  /** Turn a face-down card over in place. */
  flip(view: CardView, card: Card, delay = 0): Promise<void> {
    const a = tableAssets();
    view.card = card;
    const m = view.mesh;
    const q0 = m.quaternion.clone(), q1 = q0.clone().multiply(FLIP);
    const y0 = m.position.y;
    let swapped = false;
    return this.tw.add(delay, 0.35, (k) => {
      m.quaternion.slerpQuaternions(q0, q1, k);
      m.position.y = y0 + Math.sin(Math.PI * k) * 0.03;
      if (!swapped && k > 0.5) { swapped = true; m.geometry = a.card(card); }
    }).then(() => { view.faceUp = true; m.quaternion.copy(q1); m.geometry = a.card(card); });
  }

  /** Sweep every card off the felt to the discard tray and remove them. */
  sweep(delay = 0): Promise<void> {
    const views = this.cards;
    this.cards = [];
    const to = this.anchors.get('discard') ?? this.anchors.get('shoe');
    const jobs = views.map((v, i) => {
      if (!to) { v.mesh.removeFromParent(); return Promise.resolve(); }
      return glide(this.tw, v.mesh, to, new Vector3(0, 0.02 + i * 0.001, 0), FLIP.clone(), delay + i * 0.04, 0.4, 0.04).then(() => { v.mesh.removeFromParent(); });
    });
    return Promise.all(jobs).then(() => {});
  }

  get count(): number { return this.cards.length; }

  dispose(): void {
    this.tw.flush();
    for (const v of this.cards) v.mesh.removeFromParent();
    this.cards = [];
  }
}

/** Break an amount into chip denominations (largest first), capped for display. */
export function chipsFor(amount: number, denoms: number[]): number[] {
  const out: number[] = [];
  let left = Math.round(amount);
  for (let d = denoms.length - 1; d >= 0 && out.length < 40; d--) {
    while (left >= denoms[d] && out.length < 40) { out.push(d); left -= denoms[d]; }
  }
  if (left > 0 && out.length === 0) out.push(0);
  return out;
}

/** A pile of chip stacks (one stack per denomination, side by side) as one movable group. */
export function chipPile(amount: number): Group {
  const a = tableAssets();
  const g = new Group();
  const idx = chipsFor(amount, a.denoms);
  const stacks = new Map<number, number>();
  for (const k of idx) stacks.set(k, (stacks.get(k) ?? 0) + 1);
  let s = 0;
  const n = stacks.size;
  for (const [k, count] of [...stacks.entries()].sort((x, y) => y[0] - x[0])) {
    const ox = (s - (n - 1) / 2) * CHIP_R * 2.15;
    for (let i = 0; i < count; i++) {
      const m = new Mesh(a.chip(k), a.chipMaterial);
      m.castShadow = true;
      m.position.set(ox + Math.sin(i * 2.7 + k) * 0.0008, i * CHIP_H, Math.cos(i * 1.9 + k) * 0.0008);
      m.rotation.y = i * 0.83 + k;
      g.add(m);
    }
    s++;
  }
  return g;
}

/** Slide a pile from one anchor-local pose to another (re-parenting keeps its world pose). */
export function movePile(tw: Tweens, pile: Group, to: Object3D, at: Vector3, delay: number, dur = 0.5): Promise<void> {
  let from: Vector3;
  return tw.add(delay, dur, (k) => {
    pile.position.lerpVectors(from, at, k);
    pile.position.y += Math.sin(Math.PI * k) * 0.03;
  }, easeOut, () => { to.attach(pile); pile.quaternion.identity(); from = pile.position.clone(); });
}

/** World position of an anchor-local offset (for sounds, camera focus…). */
export function worldOf(node: Object3D, local = new Vector3()): Vector3 {
  return node.localToWorld(_p.copy(local)).clone();
}

