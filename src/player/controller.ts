import type { System } from '../core/loop';
import type { CollisionWorld, Vec3 } from '../physics/types';
import type { Input } from './input';
import { MOVEMENT as M } from './movementConfig';

/** Simulation state only — no render objects (§10: keep sim separate from presentation). */
export interface PlayerState {
  id: string;
  position: Vec3;   // feet
  velocity: Vec3;
  yaw: number;
  pitch: number;
  grounded: boolean;
  /** Accumulated step-up height the camera still has to ease into. */
  stepOffset: number;
  /** Horizontal speed / walkSpeed, for head-bob amplitude. */
  gait: number;
}

export function createPlayerState(spawn: Vec3, yaw: number): PlayerState {
  return {
    id: 'local', position: { ...spawn }, velocity: { x: 0, y: 0, z: 0 },
    yaw, pitch: 0, grounded: true, stepOffset: 0, gait: 0,
  };
}

/** Kinematic capsule character controller. */
export class PlayerController implements System {
  readonly name = 'player';
  private capsule = { radius: M.capsuleRadius, height: M.capsuleHeight, stepHeight: M.stepHeight };

  constructor(
    readonly state: PlayerState,
    private readonly input: Input,
    private world: CollisionWorld,
  ) {}

  setWorld(world: CollisionWorld): void { this.world = world; }

  update(dt: number): void {
    if (dt === 0) return;
    const s = this.state;
    const { input } = this;

    const look = input.consumeLook();
    s.yaw -= look.x * M.mouseSensitivity;
    s.pitch = Math.max(-M.pitchLimit, Math.min(M.pitchLimit, s.pitch - look.y * M.mouseSensitivity));

    // wish direction in world space (yaw 0 faces -Z)
    const f = (input.held('forward') ? 1 : 0) - (input.held('back') ? 1 : 0);
    const r = (input.held('right') ? 1 : 0) - (input.held('left') ? 1 : 0);
    let wx = 0, wz = 0;
    if (f !== 0 || r !== 0) {
      const sin = Math.sin(s.yaw), cos = Math.cos(s.yaw);
      wx = -sin * f + cos * r;
      wz = -cos * f - sin * r;
      const len = Math.hypot(wx, wz);
      wx /= len; wz /= len;
    }
    const speed = input.held('sprint') ? M.sprintSpeed : M.walkSpeed;
    const tx = wx * speed, tz = wz * speed;

    const accel = (wx !== 0 || wz !== 0 ? M.groundAccel : M.groundDecel) * (s.grounded ? 1 : M.airControl);
    const k = 1 - Math.exp(-accel * dt);
    s.velocity.x += (tx - s.velocity.x) * k;
    s.velocity.z += (tz - s.velocity.z) * k;

    if (s.grounded && input.pressed('jump')) {
      s.velocity.y = M.jumpSpeed;
      s.grounded = false;
    }
    s.velocity.y -= M.gravity * dt;

    const res = this.world.moveCapsule(
      s.position,
      { x: s.velocity.x * dt, y: s.velocity.y * dt, z: s.velocity.z * dt },
      this.capsule,
      s.grounded ? M.snapDown : 0.02,
    );
    // derive actual velocity from the resolved move so walls kill momentum
    s.velocity.x = (res.position.x - s.position.x) / dt;
    s.velocity.z = (res.position.z - s.position.z) / dt;
    if (res.grounded || res.hitCeiling) s.velocity.y = 0;
    const dropped = s.position.y - res.position.y;
    s.position = res.position;
    s.grounded = res.grounded;
    s.stepOffset += res.steppedUp;
    // stepping down stairs: also ease the camera instead of snapping
    if (res.grounded && dropped > 0.02 && dropped < M.snapDown + 0.01) s.stepOffset -= dropped;
    s.gait = Math.hypot(s.velocity.x, s.velocity.z) / M.walkSpeed;
  }
}
