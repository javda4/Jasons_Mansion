import type { Aabb, Capsule, CollisionWorld, MoveResult, Vec3 } from './types';

const SKIN = 0.001;
const MAX_SUBSTEP = 0.08; // metres; smaller than the thinnest wall so fast moves can't tunnel

/**
 * Phase 1 collision backend: a vertical capsule against axis-aligned boxes.
 * Horizontal motion treats the capsule as a circle in XZ; vertical motion uses the highest
 * box top under the circle. Stairs are simply stacked boxes lower than `stepHeight`.
 * Phase 2 adds a triangle-mesh (BVH) backend behind the same `CollisionWorld` interface.
 */
export class AabbCollisionWorld implements CollisionWorld {
  constructor(private readonly boxes: readonly Aabb[]) {}

  moveCapsule(from: Vec3, delta: Vec3, capsule: Capsule, snapDown: number): MoveResult {
    const pos = { ...from };
    let steppedUp = 0;
    let hitCeiling = false;

    // --- horizontal, sub-stepped ---
    const horiz = Math.hypot(delta.x, delta.z);
    const steps = Math.max(1, Math.ceil(horiz / MAX_SUBSTEP));
    for (let i = 0; i < steps; i++) {
      pos.x += delta.x / steps;
      pos.z += delta.z / steps;
      this.resolveHorizontal(pos, capsule);
      // step-up: climb onto any ledge now under us that is within stepHeight
      const ground = this.groundHeight(pos.x, pos.z, capsule.radius * 0.9, pos.y + capsule.stepHeight);
      if (ground > pos.y && this.headroom(pos.x, pos.z, capsule.radius, ground, capsule.height)) {
        steppedUp += ground - pos.y;
        pos.y = ground;
      }
    }

    // --- vertical ---
    pos.y += delta.y;
    if (delta.y > 0) {
      const ceiling = this.ceilingHeight(pos.x, pos.z, capsule.radius, pos.y - delta.y + capsule.height);
      if (pos.y + capsule.height > ceiling) {
        pos.y = ceiling - capsule.height - SKIN;
        hitCeiling = true;
      }
    }
    const ground = this.groundHeight(pos.x, pos.z, capsule.radius * 0.9, pos.y + (delta.y <= 0 ? capsule.stepHeight : 0));
    let grounded = false;
    if (delta.y <= 0 && pos.y - ground <= snapDown) {
      pos.y = ground;
      grounded = true;
    }
    return { position: pos, grounded, hitCeiling, steppedUp };
  }

  groundHeight(x: number, z: number, radius: number, maxY: number): number {
    let best = -Infinity;
    for (const b of this.boxes) {
      if (b.disabled || b.max.y > maxY + SKIN || b.max.y <= best) continue;
      if (circleOverlapsRect(x, z, radius, b)) best = b.max.y;
    }
    return best;
  }

  private ceilingHeight(x: number, z: number, radius: number, minY: number): number {
    let best = Infinity;
    for (const b of this.boxes) {
      if (b.disabled || b.min.y < minY - SKIN || b.min.y >= best) continue;
      if (circleOverlapsRect(x, z, radius, b)) best = b.min.y;
    }
    return best;
  }

  private headroom(x: number, z: number, radius: number, feetY: number, height: number): boolean {
    return this.ceilingHeight(x, z, radius, feetY + 0.05) >= feetY + height;
  }

  /** Pushes the capsule circle out of every box that overlaps its body (above the step band). */
  private resolveHorizontal(pos: Vec3, c: Capsule): void {
    const bodyMin = pos.y + c.stepHeight;
    const bodyMax = pos.y + c.height;
    for (let iter = 0; iter < 4; iter++) {
      let moved = false;
      for (const b of this.boxes) {
        if (b.disabled || b.max.y <= bodyMin || b.min.y >= bodyMax) continue;
        const cx = clamp(pos.x, b.min.x, b.max.x);
        const cz = clamp(pos.z, b.min.z, b.max.z);
        let dx = pos.x - cx;
        let dz = pos.z - cz;
        const d2 = dx * dx + dz * dz;
        if (d2 >= c.radius * c.radius) continue;
        if (d2 > 1e-12) {
          const d = Math.sqrt(d2);
          const push = c.radius - d + SKIN;
          pos.x += (dx / d) * push;
          pos.z += (dz / d) * push;
        } else {
          // centre is inside the box: exit via the nearest face
          const exits = [pos.x - b.min.x, b.max.x - pos.x, pos.z - b.min.z, b.max.z - pos.z];
          const m = exits.indexOf(Math.min(...exits));
          if (m === 0) pos.x = b.min.x - c.radius - SKIN;
          else if (m === 1) pos.x = b.max.x + c.radius + SKIN;
          else if (m === 2) pos.z = b.min.z - c.radius - SKIN;
          else pos.z = b.max.z + c.radius + SKIN;
          dx = dz = 0;
        }
        moved = true;
      }
      if (!moved) break;
    }
  }
}

function clamp(v: number, lo: number, hi: number): number {
  return v < lo ? lo : v > hi ? hi : v;
}

function circleOverlapsRect(x: number, z: number, r: number, b: Aabb): boolean {
  const dx = x - clamp(x, b.min.x, b.max.x);
  const dz = z - clamp(z, b.min.z, b.max.z);
  return dx * dx + dz * dz < r * r;
}
