import { Quaternion, Vector3 } from 'three/webgpu';
import type { EventBus } from '../core/events';
import type { System } from '../core/loop';
import type { PlayerState } from '../player/controller';
import type { DoorDef } from './roomBuilder';

const OPEN_ANGLE = (100 * Math.PI) / 180;
const OPEN_TIME = 1.3;        // seconds, full swing — heavy doors
const AUTO_CLOSE_DIST = 11;   // metres from the player
const _q = new Quaternion();
const _y = new Vector3(0, 1, 0);

interface DoorState {
  def: DoorDef;
  zone: string;
  open: number;        // 0 closed … 1 open
  want: boolean;
  waiting: boolean;    // opening requested but the far zone is still streaming
  waitingSince: number;
}

export interface ZoneAvailability {
  isReady(zoneId: string): boolean;
  request(zoneId: string): void;
}

/**
 * Door behaviour (§8): doors open on interaction, but hold closed (with a small "unlatch" nudge)
 * until the zone behind them has finished streaming — continuity is never broken by a void or
 * a loading screen. Doors close themselves once the player has walked well away.
 */
export class DoorSystem implements System {
  readonly name = 'doors';
  private doors = new Map<string, DoorState>();
  private time = 0;

  constructor(
    private readonly zones: ZoneAvailability,
    private readonly player: PlayerState,
    private readonly bus: EventBus,
  ) {}

  register(zone: string, defs: DoorDef[]): void {
    for (const def of defs) this.doors.set(def.id, { def, zone, open: 0, want: false, waiting: false, waitingSince: 0 });
  }

  unregister(zone: string): void {
    for (const [id, d] of this.doors) if (d.zone === zone) this.doors.delete(id);
  }

  /** Doors whose leaves are open at all — used for portal visibility. */
  *openLinks(): Iterable<{ a: string; b: string; open: number }> {
    for (const d of this.doors.values()) if (d.def.target && d.open > 0.001) yield { a: d.zone, b: d.def.target, open: d.open };
  }

  promptFor(doorId: string): string | null {
    const d = this.doors.get(doorId);
    if (!d) return null;
    if (d.def.extras.interactionType === 'door' && d.def.extras.locked) return d.def.extras.interactionPrompt;
    if (d.waiting) return 'One moment…';
    return d.want ? 'Close' : d.def.extras.interactionPrompt;
  }

  activate(doorId: string): void {
    const d = this.doors.get(doorId);
    if (!d) return;
    if (!d.def.target) {
      this.bus.emit('ui:toast', { text: 'This door is locked — by invitation only.' });
      d.waitingSince = this.time; // brief rattle
      return;
    }
    if (d.want || d.waiting) {
      d.want = false;
      d.waiting = false;
      return;
    }
    if (this.zones.isReady(d.def.target)) this.setWant(d, true);
    else {
      d.waiting = true;
      d.waitingSince = this.time;
      this.zones.request(d.def.target);
    }
  }

  private setWant(d: DoorState, want: boolean): void {
    if (want && !d.want) this.bus.emit('door:moved', { id: d.def.id, opening: true, position: d.def.position });
    d.want = want;
  }

  update(dt: number, time: number): void {
    this.time = time;
    const p = this.player.position;
    for (const d of this.doors.values()) {
      if (d.waiting && d.def.target && this.zones.isReady(d.def.target)) {
        d.waiting = false;
        this.setWant(d, true);
      }
      const dx = d.def.position.x - p.x, dz = d.def.position.z - p.z;
      if (d.want && d.open >= 1 && dx * dx + dz * dz > AUTO_CLOSE_DIST * AUTO_CLOSE_DIST) this.setWant(d, false);
      const wasOpen = d.open > 0;

      const target = d.want ? 1 : 0;
      const step = dt / OPEN_TIME;
      d.open = target > d.open ? Math.min(1, d.open + step) : Math.max(0, d.open - step);
      if (wasOpen && d.open === 0) this.bus.emit('door:moved', { id: d.def.id, opening: false, position: d.def.position });

      // a waiting or locked door gives a small nudge so the player sees it respond
      const nudgeT = time - d.waitingSince;
      const nudge = (d.waiting || !d.def.target) && nudgeT < 0.6 ? Math.sin(nudgeT * Math.PI * 5) * 0.025 * (1 - nudgeT / 0.6) : d.waiting ? 0.03 : 0;
      const eased = ease(d.open);
      for (const leaf of d.def.leaves) {
        const base = leaf.pivot.userData.baseQuaternion as Quaternion;
        _q.setFromAxisAngle(_y, leaf.sign * (eased * OPEN_ANGLE + Math.abs(nudge)));
        leaf.pivot.quaternion.copy(base).multiply(_q);
      }
      // passable once mostly open; solid again as soon as it starts closing
      d.def.collider.disabled = d.open > 0.8 && d.want;
    }
  }
}

function ease(t: number): number {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}
