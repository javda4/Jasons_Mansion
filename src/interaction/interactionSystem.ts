import { Raycaster, Vector2, type Camera, type Object3D } from 'three/webgpu';
import type { EventBus } from '../core/events';
import type { System } from '../core/loop';
import type { Input } from '../player/input';
import { validateExtras, type InteractionExtras, type InteractionType } from './schema';

const MAX_DISTANCE = 3.2;
const CENTER = new Vector2(0, 0);

export interface InteractionHandler {
  /** Prompt to show while focused (may be dynamic, e.g. "Close"); null hides the prompt. */
  prompt(extras: InteractionExtras & Record<string, unknown>): string | null;
  activate(extras: InteractionExtras & Record<string, unknown>, object: Object3D): void;
}

/**
 * One generic interaction system (§8): a centre-screen ray finds the nearest interactable
 * (anything whose userData carries valid extras), the HUD shows its prompt, E activates the
 * handler registered for its `interactionType`. New types = new handler + schema entry.
 */
export class InteractionSystem implements System {
  readonly name = 'interaction';
  private raycaster = new Raycaster();
  private handlers = new Map<InteractionType, InteractionHandler>();
  private targets: Object3D[] = [];
  private focused: { obj: Object3D; prompt: string } | null = null;
  private validated = new WeakSet<Object3D>();

  constructor(
    private readonly camera: Camera,
    private readonly input: Input,
    private readonly bus: EventBus,
  ) {
    this.raycaster.far = MAX_DISTANCE;
  }

  register(type: InteractionType, handler: InteractionHandler): void {
    this.handlers.set(type, handler);
  }

  /** Called by the zone manager whenever the set of visible zones changes. */
  setTargets(roots: Object3D[]): void {
    const list: Object3D[] = [];
    for (const r of roots) {
      r.traverseVisible((o) => {
        if (o.userData.interactable !== true) return;
        if (!this.validated.has(o)) {
          const errs = validateExtras(o.userData);
          if (errs.length) { console.warn(`[interaction] ${o.name}: ${errs.join('; ')}`); return; }
          this.validated.add(o);
        }
        list.push(o);
      });
    }
    this.targets = list;
  }

  update(): void {
    let next: { obj: Object3D; prompt: string } | null = null;
    if (this.input.isLocked && this.targets.length) {
      this.raycaster.setFromCamera(CENTER, this.camera);
      const hit = this.raycaster.intersectObjects(this.targets, false)[0];
      if (hit) {
        const extras = hit.object.userData as InteractionExtras & Record<string, unknown>;
        const prompt = this.handlers.get(extras.interactionType)?.prompt(extras) ?? null;
        if (prompt) next = { obj: hit.object, prompt };
      }
    }
    if (next?.obj !== this.focused?.obj || next?.prompt !== this.focused?.prompt) {
      this.focused = next;
      this.bus.emit('interaction:focus', next ? { id: next.obj.name, prompt: next.prompt } : null);
    }
    if (this.focused && this.input.pressed('interact')) {
      const extras = this.focused.obj.userData as InteractionExtras & Record<string, unknown>;
      this.handlers.get(extras.interactionType)?.activate(extras, this.focused.obj);
      this.bus.emit('interaction:activated', { id: this.focused.obj.name, ...extras });
    }
  }
}
