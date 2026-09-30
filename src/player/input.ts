/**
 * Input-action map (§8): all bindings resolve to named actions so gamepad/touch/network
 * sources can drive the same commands later.
 */
export type Action = 'forward' | 'back' | 'left' | 'right' | 'sprint' | 'jump' | 'interact' | 'debug';

const BINDINGS: Record<Action, readonly string[]> = {
  forward: ['KeyW', 'ArrowUp'],
  back: ['KeyS', 'ArrowDown'],
  left: ['KeyA', 'ArrowLeft'],
  right: ['KeyD', 'ArrowRight'],
  sprint: ['ShiftLeft', 'ShiftRight'],
  jump: ['Space'],
  interact: ['KeyE'],
  debug: ['Backquote'],
};

export class Input {
  private down = new Set<string>();
  private pressedThisFrame = new Set<Action>();
  private lookX = 0;
  private lookY = 0;
  private locked = false;
  sensitivity = 1;

  constructor(private readonly target: HTMLElement) {
    addEventListener('keydown', (e) => {
      if (e.repeat) return;
      this.down.add(e.code);
      for (const a of Object.keys(BINDINGS) as Action[]) if (BINDINGS[a].includes(e.code)) this.pressedThisFrame.add(a);
      if (this.locked && e.code === 'Space') e.preventDefault();
    });
    addEventListener('keyup', (e) => this.down.delete(e.code));
    addEventListener('blur', () => this.down.clear());
    addEventListener('mousemove', (e) => {
      if (!this.locked) return;
      this.lookX += e.movementX;
      this.lookY += e.movementY;
    });
    document.addEventListener('pointerlockchange', () => {
      this.locked = document.pointerLockElement === this.target;
      if (!this.locked) this.down.clear();
    });
  }

  get isLocked(): boolean { return this.locked; }

  async lock(): Promise<void> {
    try {
      await this.target.requestPointerLock({ unadjustedMovement: true });
    } catch {
      await this.target.requestPointerLock(); // unadjustedMovement unsupported (e.g. Safari)
    }
  }

  held(action: Action): boolean {
    if (!this.locked) return false;
    return BINDINGS[action].some((c) => this.down.has(c));
  }

  /** True once on the frame the action was pressed. */
  pressed(action: Action): boolean { return this.pressedThisFrame.has(action); }

  /** Returns and clears accumulated mouse movement in pixels. */
  consumeLook(): { x: number; y: number } {
    const r = { x: this.lookX * this.sensitivity, y: this.lookY * this.sensitivity };
    this.lookX = this.lookY = 0;
    return r;
  }

  /** Call at the end of every frame. */
  endFrame(): void { this.pressedThisFrame.clear(); }
}
