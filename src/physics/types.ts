/**
 * Render-agnostic collision contract (§8 Collision). No three.js imports here, so the same
 * world data and queries can run in a worker or on an authoritative server later.
 */
export interface Vec3 { x: number; y: number; z: number }

/** Axis-aligned box collider, e.g. produced from a `COLLIDER_` node. */
export interface Aabb {
  id: string;
  min: Vec3;
  max: Vec3;
  /** Dynamic colliders (e.g. an open door) are switched off instead of removed. */
  disabled?: boolean;
}

export interface Capsule {
  radius: number;
  height: number;   // total height, feet to crown
  stepHeight: number; // max ledge the controller climbs without jumping
}

export interface MoveResult {
  /** New feet position. */
  position: Vec3;
  grounded: boolean;
  /** True when a ceiling stopped upward motion. */
  hitCeiling: boolean;
  /** Height the feet were raised this move by stepping onto a ledge (for camera smoothing). */
  steppedUp: number;
}

export interface CollisionWorld {
  /** Moves a capsule (feet at `from`) by `delta`, sliding along walls and stepping up ledges. */
  moveCapsule(from: Vec3, delta: Vec3, capsule: Capsule, snapDown: number): MoveResult;
  /** Height of the highest walkable surface under (x,z) at or below `maxY`, or -Infinity. */
  groundHeight(x: number, z: number, radius: number, maxY: number): number;
}
