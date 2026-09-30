import { Plane, Raycaster, Vector2, Vector3, type Camera } from 'three/webgpu';
import type { RouletteBet } from '../games/roulette/roulette';
import type { AnchorDef } from '../world/roomBuilder';

/**
 * Click-to-bet on the printed roulette layout: cast the pointer onto the felt plane of the table's
 * `layout` anchor and find the bet box under it (box centres come from the anchor's extras, i.e. the same
 * data the felt texture was printed from). Returns null off the layout.
 */
const ray = new Raycaster();
const plane = new Plane();
const hit = new Vector3();
const n = new Vector3();

export function pickRouletteBet(anchors: AnchorDef[], camera: Camera, ndc: Vector2, amount: number): Omit<RouletteBet, 'amount'> & { amount: number } | null {
  const a = anchors.find((x) => x.role === 'layout');
  if (!a) return null;
  const node = a.node;
  node.updateWorldMatrix(true, false);
  n.set(0, 1, 0).transformDirection(node.matrixWorld);
  plane.setFromNormalAndCoplanarPoint(n, node.getWorldPosition(hit));
  ray.setFromCamera(ndc, camera);
  if (!ray.ray.intersectPlane(plane, hit)) return null;
  node.worldToLocal(hit);
  const x = hit.x, y = -hit.z;                                  // anchor plane → layout plan (y = −Z)
  type HalfSize = [number, number];
  const e = a.extras as { numbers: [number, number][]; dozens: [number, number][]; outside: [number, number][]; outsideKeys: string[];
    cell?: HalfSize; zero?: HalfSize; dozen?: HalfSize; out?: HalfSize };
  // box half-sizes come with the layout (each table's printed felt differs); defaults = our own felt
  const [cw, ch] = e.cell ?? [0.065, 0.11], [zw, zh] = e.zero ?? [0.07, 0.33];
  const [dw, dh] = e.dozen ?? [0.26, 0.05], [ow, oh] = e.out ?? [0.13, 0.06];
  const inside = (c: [number, number], hw: number, hh: number) => Math.abs(x - c[0]) <= hw && Math.abs(y - c[1]) <= hh;
  if (inside(e.numbers[0], zw, zh)) return { kind: 'straight', value: 0, amount };
  for (let v = 1; v <= 36; v++) if (inside(e.numbers[v], cw, ch)) return { kind: 'straight', value: v, amount };
  for (let d = 0; d < 3; d++) if (inside(e.dozens[d], dw, dh)) return { kind: 'dozen', value: d + 1, amount };
  for (let k = 0; k < e.outside.length; k++) if (inside(e.outside[k], ow, oh)) return { kind: e.outsideKeys[k] as RouletteBet['kind'], amount };
  return null;
}
