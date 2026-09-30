import { Color, type Mesh, type MeshStandardMaterial } from 'three/webgpu';
import type { ZoneInstance } from '../../world/roomBuilder';

/** Slot room runtime: the machines' topper lights (material `MAT_Slots_Lights`) chase in colour. */
export function enhanceSlots(inst: ZoneInstance): void {
  const mats = new Set<MeshStandardMaterial>();
  inst.root.traverse((o) => {
    const m = (o as Mesh).material as MeshStandardMaterial | undefined;
    if (m && !Array.isArray(m) && m.name === 'MAT_Slots_Lights') mats.add(m);
  });
  const hue = new Color();
  inst.animate.push((t) => {
    hue.setHSL((0.08 + Math.sin(t * 0.6) * 0.06 + 1) % 1, 1, 0.55);
    for (const m of mats) {
      m.emissive.copy(hue);
      m.emissiveIntensity = 5 + Math.sin(t * 5) * 1.5;
    }
  });
}
