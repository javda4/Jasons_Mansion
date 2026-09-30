import { Box3, Group, Vector3, type Object3D } from 'three/webgpu';
import type { ZoneInstance } from '../../world/roomBuilder';

/**
 * Roulette room runtime (§5 rooms/: per-room animation + special logic) for the Blender-authored
 * zone: rotors are `PROP_Roulette_Rotor_NN` nodes with extras `{ rotor: tableId }`. They idle
 * slowly and spin up when a spin event arrives from that table's game session (§9: the table
 * presents events; it never decides the result).
 */
export function enhanceRoulette(inst: ZoneInstance): void {
  const rotors: { pivot: Group; tableId: string; base: number; angle: number; boostAt: number }[] = [];
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
  let now = 0, last = 0;
  inst.animate.push((t) => {
    const dt = Math.min(0.1, t - last);
    last = now = t;
    for (const r of rotors) {
      const extra = 7 * Math.exp(-(t - r.boostAt) / 1.6);
      r.angle += (r.base + extra) * dt;
      r.pivot.rotation.y = r.angle;
    }
  });
  inst.onGameEvent = (tableId, event) => {
    if (event.type !== 'spin') return;
    const r = rotors.find((x) => x.tableId === tableId);
    if (r) r.boostAt = now;
  };
}
