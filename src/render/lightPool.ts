import { Color, PointLight, SpotLight, Vector3, type Object3D, type Scene } from 'three/webgpu';
import type { System } from '../core/loop';
import type { Vec3 } from '../physics/types';
import type { LightDef } from '../world/roomBuilder';

/**
 * Fixed-size pool of real lights driven by the LightDefs of the visible zones.
 *
 * Why: three.js bakes the number of lights into every shader, so adding/removing lights when
 * zones stream in would recompile every material (a multi-hundred-ms hitch). Zones declare
 * lights as data; each frame the pool assigns the most relevant ones to a constant set of
 * slots and cross-fades reassignments, so the shader permutation never changes (§8: never
 * block the frame).
 */
interface Slot<L extends PointLight | SpotLight> {
  light: L;
  def: LightDef | null;
  fade: number;
}

const POINT_SLOTS = 10;
const SPOT_SLOTS = 1;
const FADE_RATE = 3.5;
const RESELECT_INTERVAL = 0.2;

export class LightPool implements System {
  readonly name = 'lights';
  private points: Slot<PointLight>[] = [];
  private spots: Slot<SpotLight>[] = [];
  private key: Slot<SpotLight>;
  private candidates: LightDef[] = [];
  private currentZone = '';
  private sinceSelect = RESELECT_INTERVAL;
  private wantedPoints = new Set<LightDef>();
  private wantedSpots = new Set<LightDef>();
  private wantedKey: LightDef | null = null;
  private readonly tmp = new Vector3();

  constructor(scene: Scene, private readonly viewer: Object3D, shadowMapSize = 2048) {
    for (let i = 0; i < POINT_SLOTS; i++) {
      const l = new PointLight(0xffffff, 0, 1, 2);
      l.name = `LIGHTPOOL_Point_${i}`;
      scene.add(l);
      this.points.push({ light: l, def: null, fade: 0 });
    }
    for (let i = 0; i < SPOT_SLOTS; i++) {
      const l = new SpotLight(0xffffff, 0, 1, 1, 0.5, 2);
      l.name = `LIGHTPOOL_Spot_${i}`;
      scene.add(l, l.target);
      this.spots.push({ light: l, def: null, fade: 0 });
    }
    const k = new SpotLight(0xffffff, 0, 1, 1, 0.5, 2);
    k.name = 'LIGHTPOOL_ShadowKey';
    k.castShadow = true;
    k.shadow.mapSize.set(shadowMapSize, shadowMapSize);
    k.shadow.bias = -0.0004;
    k.shadow.normalBias = 0.02;
    k.shadow.camera.near = 0.4;
    k.shadow.camera.far = 16;
    k.shadow.radius = 4;
    scene.add(k, k.target);
    this.key = { light: k, def: null, fade: 0 };
  }

  /** Lights of zones that are currently visible; `zone` = the zone the player is in. */
  setCandidates(defs: LightDef[], currentZone: string): void {
    this.candidates = defs;
    this.currentZone = currentZone;
    this.sinceSelect = RESELECT_INTERVAL; // reselect next frame
  }

  get stats(): string {
    const live = (s: Slot<PointLight | SpotLight>[]) => s.filter((x) => x.def && x.fade > 0).length;
    return `${live(this.points)}/${POINT_SLOTS} pt · ${live(this.spots)}/${SPOT_SLOTS} spot · key ${this.key.def ? 'on' : 'off'} (of ${this.candidates.length})`;
  }

  update(dt: number, time: number): void {
    this.sinceSelect += dt;
    if (this.sinceSelect >= RESELECT_INTERVAL) {
      this.sinceSelect = 0;
      this.select(this.viewer.getWorldPosition(this.tmp));
    }
    this.animate(this.points, this.wantedPoints, dt, time);
    this.animate(this.spots, this.wantedSpots, dt, time);
    this.animate([this.key], new Set(this.wantedKey ? [this.wantedKey] : []), dt, time);
  }

  /**
   * Instantly light a set of defs around `at` (used while capturing a reflection probe),
   * run `fn`, then restore the exact previous state.
   */
  withLightsAt(defs: LightDef[], at: Vec3, fn: () => void): void {
    const save = [...this.points, ...this.spots, this.key].map((s) => ({ s, def: s.def, fade: s.fade, int: s.light.intensity }));
    const p = new Vector3(at.x, at.y, at.z);
    const ranked = rank(defs, p, '');
    const assign = <L extends PointLight | SpotLight>(slots: Slot<L>[], list: LightDef[]) => {
      slots.forEach((s, i) => {
        s.def = list[i] ?? null;
        s.fade = s.def ? 1 : 0;
        if (s.def) configure(s.light, s.def);
        s.light.intensity = s.def ? s.def.intensity : 0;
      });
    };
    assign(this.points, ranked.filter((d) => d.kind === 'point').slice(0, POINT_SLOTS));
    assign(this.spots, ranked.filter((d) => d.kind === 'spot' && !d.castShadow).slice(0, SPOT_SLOTS));
    assign([this.key], ranked.filter((d) => d.castShadow).slice(0, 1));
    try {
      fn();
    } finally {
      for (const { s, def, fade, int } of save) {
        s.def = def;
        s.fade = fade;
        if (def) configure(s.light, def);
        s.light.intensity = int;
      }
    }
  }

  private select(eye: Vector3): void {
    const ranked = rank(this.candidates, eye, this.currentZone);
    const keep = <L extends PointLight | SpotLight>(slots: Slot<L>[], list: LightDef[], n: number) => {
      // hysteresis: a light that is already live keeps its slot while it ranks within n+2
      const grace = new Set(list.slice(0, n + 2));
      const out = new Set<LightDef>();
      for (const s of slots) if (s.def && s.fade > 0 && grace.has(s.def)) out.add(s.def);
      for (const d of list) {
        if (out.size >= n) break;
        out.add(d);
      }
      return out;
    };
    this.wantedPoints = keep(this.points, ranked.filter((d) => d.kind === 'point'), POINT_SLOTS);
    this.wantedSpots = keep(this.spots, ranked.filter((d) => d.kind === 'spot' && !d.castShadow), SPOT_SLOTS);
    const keys = ranked.filter((d) => d.castShadow);
    this.wantedKey = keys.find((d) => d.zone === this.currentZone) ?? keys[0] ?? null;
  }

  private animate<L extends PointLight | SpotLight>(slots: Slot<L>[], wanted: Set<LightDef>, dt: number, time: number): void {
    const assigned = new Set(slots.map((s) => s.def));
    // fade out unwanted
    for (const s of slots) {
      if (s.def && !wanted.has(s.def)) {
        s.fade = Math.max(0, s.fade - dt * FADE_RATE);
        if (s.fade === 0) s.def = null;
      } else if (s.def) {
        s.fade = Math.min(1, s.fade + dt * FADE_RATE);
      }
    }
    // assign newly wanted lights to free slots
    for (const def of wanted) {
      if (assigned.has(def)) continue;
      const free = slots.find((s) => s.def === null);
      if (!free) break;
      free.def = def;
      free.fade = 0;
      configure(free.light, def);
    }
    for (const s of slots) {
      if (!s.def) { s.light.intensity = 0; continue; }
      const f = s.def.flicker ? 1 + Math.sin(time * 7.3 + hash(s.def.id)) * 0.012 + Math.sin(time * 13.1 + hash(s.def.id) * 2) * 0.008 : 1;
      s.light.intensity = s.def.intensity * smooth(s.fade) * f;
    }
  }
}

function configure(l: PointLight | SpotLight, d: LightDef): void {
  l.position.set(d.position.x, d.position.y, d.position.z);
  (l.color as Color).setHex(d.color);
  l.distance = d.range;
  if ((l as SpotLight).isSpotLight) {
    const s = l as SpotLight;
    s.angle = d.angle ?? 0.9;
    s.penumbra = d.penumbra ?? 0.6;
    const t = d.target ?? { x: d.position.x, y: 0, z: d.position.z };
    s.target.position.set(t.x, t.y, t.z);
    s.target.updateMatrixWorld();
  }
}

/** Relevance: brightness at the viewer, boosted for the current zone. */
function rank(defs: LightDef[], eye: Vector3, zone: string): LightDef[] {
  const score = (d: LightDef) => {
    const dx = d.position.x - eye.x, dy = d.position.y - eye.y, dz = d.position.z - eye.z;
    const dist2 = dx * dx + dy * dy + dz * dz;
    if (dist2 > (d.range + 8) * (d.range + 8)) return -1;
    return (d.intensity / (1 + dist2)) * (d.zone === zone ? 3 : 1);
  };
  return defs
    .map((d) => [d, score(d)] as const)
    .filter(([, s]) => s > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([d]) => d);
}

function smooth(t: number): number {
  return t * t * (3 - 2 * t);
}

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return (h % 1000) / 100;
}
