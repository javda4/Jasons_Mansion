import { Matrix4, PerspectiveCamera, Quaternion, Vector3 } from 'three/webgpu';
import type { System } from '../core/loop';
import type { PlayerState } from '../player/controller';
import { MOVEMENT as M } from '../player/movementConfig';

/** A fixed viewpoint (e.g. seated at a table) the camera can ease into and back out of. */
export interface CameraPose {
  position: Vector3;
  lookAt: Vector3;
  /** Field of view while seated (a slight "lean in" so cards and reels read); defaults to the walking FOV. */
  fov?: number;
}

const _up = new Vector3(0, 1, 0);
const _m = new Matrix4();
const _pos = new Vector3();
const _quat = new Quaternion();

/**
 * Presents PlayerState through a camera: eye height, stair smoothing, a very subtle head bob,
 * and smooth transitions to/from seated poses (§8 camera transitions).
 */
export class FirstPersonCamera implements System {
  readonly name = 'camera';
  readonly camera: PerspectiveCamera;
  private bobPhase = 0;
  private bobAmp = 0;
  private seat: { position: Vector3; quaternion: Quaternion; fov?: number } | null = null;
  private baseFov: number;
  private seatBlend = 0; // 0 = walking view, 1 = seated view
  private walkPos = new Vector3();
  private walkQuat = new Quaternion();

  constructor(private readonly player: PlayerState, fov = 68) {
    this.camera = new PerspectiveCamera(fov, innerWidth / innerHeight, 0.1, 300);   // near < capsule radius (0.3): walls never clip; reversed depth keeps precision
    this.baseFov = fov;
    this.camera.rotation.order = 'YXZ';
  }

  get seated(): boolean { return this.seat !== null; }

  setFov(fov: number): void {
    this.baseFov = fov;
    this.camera.fov = fov;
    this.camera.updateProjectionMatrix();
  }

  resize(w: number, h: number): void {
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  /** Ease into a fixed pose (null = back to the player's own view). */
  setSeat(pose: CameraPose | null): void {
    if (!pose) { this.seat = null; return; }
    _m.lookAt(pose.position, pose.lookAt, _up);
    this.seat = { position: pose.position.clone(), quaternion: new Quaternion().setFromRotationMatrix(_m), fov: pose.fov };
  }

  update(dt: number): void {
    const p = this.player;
    p.stepOffset *= Math.exp(-14 * dt);
    if (Math.abs(p.stepOffset) < 1e-4) p.stepOffset = 0;

    const moving = p.grounded ? Math.min(p.gait, 2) : 0;
    this.bobAmp += (moving - this.bobAmp) * (1 - Math.exp(-6 * dt));
    this.bobPhase += dt * (5.6 + 2.2 * Math.max(0, p.gait - 1)) * Math.min(1, p.gait);
    const bobY = Math.sin(this.bobPhase * 2) * 0.012 * this.bobAmp;
    const bobX = Math.cos(this.bobPhase) * 0.008 * this.bobAmp;

    const c = this.camera;
    c.position.set(
      p.position.x + Math.cos(p.yaw) * bobX,
      p.position.y + M.eyeHeight - p.stepOffset + bobY,
      p.position.z - Math.sin(p.yaw) * bobX,
    );
    c.rotation.set(p.pitch, p.yaw, Math.cos(this.bobPhase) * 0.0015 * this.bobAmp);

    // seated transition: blend the walking pose toward the seat pose (critically damped feel)
    const target = this.seat ? 1 : 0;
    this.seatBlend += (target - this.seatBlend) * (1 - Math.exp(-4.5 * dt));
    if (Math.abs(target - this.seatBlend) < 1e-3) this.seatBlend = target;
    if (this.seatBlend > 0 && (this.seat || this.lastSeat)) {
      const s = this.seat ?? this.lastSeat!;
      const t = this.seatBlend * this.seatBlend * (3 - 2 * this.seatBlend);
      this.walkPos.copy(c.position);
      this.walkQuat.copy(c.quaternion);
      c.position.copy(_pos.copy(this.walkPos).lerp(s.position, t));
      c.quaternion.copy(_quat.copy(this.walkQuat).slerp(s.quaternion, t));
      const fov = this.baseFov + ((s.fov ?? this.baseFov) - this.baseFov) * t;
      if (Math.abs(fov - c.fov) > 0.01) { c.fov = fov; c.updateProjectionMatrix(); }
    } else if (c.fov !== this.baseFov) {
      c.fov = this.baseFov;
      c.updateProjectionMatrix();
    }
    if (this.seat) this.lastSeat = this.seat;
    else if (this.seatBlend === 0) this.lastSeat = null;
  }

  private lastSeat: { position: Vector3; quaternion: Quaternion; fov?: number } | null = null;
}
