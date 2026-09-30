/** A system ticked once per frame, in registration order. */
export interface System {
  readonly name: string;
  update(dt: number, time: number): void;
}

/**
 * Single frame loop. Simulation systems receive a clamped delta so a stalled tab
 * (or a long shader compile) can never teleport the player through a wall.
 */
export class FrameLoop {
  private systems: System[] = [];
  private last = 0;
  private time = 0;
  private static readonly MAX_DT = 1 / 20;

  add(system: System): this {
    this.systems.push(system);
    return this;
  }

  /** Called from the renderer's animation loop with a high-resolution timestamp (ms). */
  tick(nowMs: number): void {
    const now = nowMs / 1000;
    const dt = this.last === 0 ? 0 : Math.min(now - this.last, FrameLoop.MAX_DT);
    this.last = now;
    this.time += dt;
    for (const s of this.systems) s.update(dt, this.time);
  }
}
