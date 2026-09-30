import { describe, expect, it } from 'vitest';
import { AabbCollisionWorld } from './aabbWorld';
import type { Aabb, Capsule } from './types';

const capsule: Capsule = { radius: 0.3, height: 1.8, stepHeight: 0.35 };
const box = (id: string, min: [number, number, number], max: [number, number, number]): Aabb => ({
  id, min: { x: min[0], y: min[1], z: min[2] }, max: { x: max[0], y: max[1], z: max[2] },
});

const floor = box('floor', [-10, -1, -10], [10, 0, 10]);
const wall = box('wall', [2, 0, -10], [2.2, 4, 10]);
const step = box('step', [-1, 0, -3], [1, 0.18, -2]);
const tallStep = box('tall', [-1, 0, 3], [1, 0.6, 4]);

const world = new AabbCollisionWorld([floor, wall, step, tallStep]);

describe('AabbCollisionWorld', () => {
  it('stands on the floor', () => {
    const r = world.moveCapsule({ x: 0, y: 0.02, z: 0 }, { x: 0, y: -0.05, z: 0 }, capsule, 0.1);
    expect(r.grounded).toBe(true);
    expect(r.position.y).toBe(0);
  });

  it('stops at a wall and never passes through it, even with a huge delta', () => {
    const r = world.moveCapsule({ x: 0, y: 0, z: 0 }, { x: 5, y: 0, z: 0 }, capsule, 0.1);
    expect(r.position.x).toBeLessThanOrEqual(2 - capsule.radius);
  });

  it('slides along a wall', () => {
    const r = world.moveCapsule({ x: 1.69, y: 0, z: 0 }, { x: 0.5, y: 0, z: 0.5 }, capsule, 0.1);
    expect(r.position.z).toBeCloseTo(0.5, 2);
    expect(r.position.x).toBeLessThan(2 - capsule.radius + 0.01);
  });

  it('steps up a stair tread', () => {
    const r = world.moveCapsule({ x: 0, y: 0, z: -1 }, { x: 0, y: 0, z: -1.5 }, capsule, 0.1);
    expect(r.position.y).toBeCloseTo(0.18);
    expect(r.steppedUp).toBeCloseTo(0.18);
  });

  it('is blocked by a ledge taller than stepHeight', () => {
    const r = world.moveCapsule({ x: 0, y: 0, z: 2 }, { x: 0, y: 0, z: 2 }, capsule, 0.1);
    expect(r.position.y).toBe(0);
    expect(r.position.z).toBeLessThanOrEqual(3 - capsule.radius + 0.01);
  });

  it('falls when not supported', () => {
    const r = world.moveCapsule({ x: 0, y: 2, z: 0 }, { x: 0, y: -0.1, z: 0 }, capsule, 0.1);
    expect(r.grounded).toBe(false);
    expect(r.position.y).toBeCloseTo(1.9);
  });

  it('ignores disabled colliders (open doors)', () => {
    const door = box('door', [-1, 0, -6], [1, 3, -5.9]);
    const w = new AabbCollisionWorld([floor, door]);
    const blocked = w.moveCapsule({ x: 0, y: 0, z: -5 }, { x: 0, y: 0, z: -2 }, capsule, 0.1);
    expect(blocked.position.z).toBeGreaterThan(-5.9 + capsule.radius - 0.01);
    door.disabled = true;
    const open = w.moveCapsule({ x: 0, y: 0, z: -5 }, { x: 0, y: 0, z: -2 }, capsule, 0.1);
    expect(open.position.z).toBeCloseTo(-7);
  });
});
