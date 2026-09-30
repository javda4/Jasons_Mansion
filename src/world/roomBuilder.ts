import {
  BoxGeometry,
  BufferGeometry,
  Euler,
  Group,
  InstancedMesh,
  Matrix4,
  Mesh,
  Quaternion,
  Vector3,
  type Material,
  type Object3D,
} from 'three/webgpu';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import type { Aabb, Vec3 } from '../physics/types';
import type { MaterialKey } from '../render/materials';
import type { InteractionExtras } from '../interaction/schema';
import type { SoundEmitterDef } from '../audio/audioEngine';

/** A light declared by a zone (the `LIGHT_` role). The runtime LightPool decides which are live. */
export interface LightDef {
  id: string;
  kind: 'point' | 'spot';
  position: Vec3;
  color: number;
  /** candela */
  intensity: number;
  range: number;
  target?: Vec3;
  angle?: number;
  penumbra?: number;
  /** Candidate for the single shadow-casting slot. */
  castShadow?: boolean;
  /** Open flame (fireplace, real candles) — never electric fittings. */
  flicker?: boolean;
  /** Owning zone id — set by the ZoneManager on registration. */
  zone?: string;
}

/** An openable door (the `DOOR_` role). Leaves are pivots on the hinge axis. */
export interface DoorDef {
  id: string;
  leaves: { pivot: Object3D; sign: 1 | -1 }[];
  collider: Aabb;
  /** Zone behind the door, or null for a locked/decorative door. */
  target: string | null;
  /** Centre of the opening at floor level. */
  position: Vec3;
  extras: InteractionExtras;
}

/**
 * What a zone looks like to the runtime once it's loaded — whether it came from a GLB
 * (Phase 2+: parsed from ROOM_/COLLIDER_/SPAWN_/LIGHT_/DOOR_ nodes) or from code (now).
 * Everything is in zone-local space; the ZoneManager applies the manifest's world transform.
 */
export interface ZoneInstance {
  id: string;
  root: Group;
  colliders: Aabb[];
  lights: LightDef[];
  doors: DoorDef[];
  /** Zone volume (the `TRIGGER_<Zone>_Bounds` role) — decides which zone the player is in. */
  bounds: Aabb;
  spawn?: { position: Vec3; yaw: number };
  /** Reflection-probe capture point (PROBE_ node). */
  probe: Vec3;
  /** Per-frame animation hooks (chandelier sway, roulette rotor, slot toppers). */
  animate: ((time: number) => void)[];
  /** Positional sound emitters (the `AUDIO_` role). */
  sounds?: SoundEmitterDef[];
  /**
   * 3D presentation of game events at this zone's tables (§9: the table subscribes to events,
   * it never decides outcomes) — e.g. the roulette wheel spinning up.
   */
  onGameEvent?: (tableId: string, event: { type: string; [k: string]: unknown }) => void;
  /**
   * State-driven presentation (src/tables): reconcile a table's 3D cards/chips/reels with the engine's
   * snapshot; the promise resolves when the animation finishes (the HUD waits for it). `state = null`
   * clears the table (the guest left).
   */
  onGameState?: (tableId: string, state: unknown | null, events: { type: string; [k: string]: unknown }[]) => Promise<void> | void;
  /** Game presentation anchors (the `ANCHOR_` role): seats, card spots, reels, wheels — see src/tables. */
  anchors?: AnchorDef[];
  /** Runtime-simulated effects (the `FX_` prefix): hearth fire, … — see src/fx. */
  effects?: EffectDef[];
}

/** An `FX_` marker: the effect kind, its node (origin = the effect's base centre) and its size extras. */
export interface EffectDef {
  effect: string;
  node: Object3D;
  extras: Record<string, unknown>;
}

/** An authored pose the table presenters build on; `node` stays in the zone graph so its world transform is live. */
export interface AnchorDef {
  role: string;
  tableId: string;
  index: number;
  node: Object3D;
  extras: Record<string, unknown>;
}

const _q = new Quaternion();
const _s = new Vector3();
const _p = new Vector3();
const _e = new Euler();
const _v = new Vector3();

export interface Place {
  pos: [number, number, number];
  rotY?: number;
  rot?: [number, number, number];
  scale?: [number, number, number];
}

/**
 * Code-side stand-in for the Blender authoring layer. It mirrors the delivery contract:
 * static geometry is merged per material (few draw calls), repeated props are instanced,
 * colliders are separate simple boxes, lights/doors are data, and nodes carry §6 names.
 */
export class RoomBuilder {
  private staticGeo = new Map<MaterialKey, BufferGeometry[]>();
  private instances = new Map<string, { geo: BufferGeometry; mat: MaterialKey | Material; matrices: Matrix4[]; shadow: boolean }>();
  readonly colliders: Aabb[] = [];
  readonly lights: LightDef[] = [];
  readonly doors: DoorDef[] = [];
  readonly sounds: SoundEmitterDef[] = [];
  readonly root: Group;
  readonly animate: ((time: number) => void)[] = [];
  private counter = 0;

  constructor(
    readonly zone: string,
    readonly materials: Record<MaterialKey, Material>,
    rootName = `ROOM_${zone}_Main`,
  ) {
    this.root = new Group();
    this.root.name = rootName;
  }

  /** Unique suffix for generated node names. */
  next(): string {
    return String(++this.counter).padStart(2, '0');
  }

  /** Adds static geometry (consumed: it is transformed in place). */
  add(geo: BufferGeometry, mat: MaterialKey, place: Place | Matrix4): this {
    geo.applyMatrix4(toMatrix(place));
    let list = this.staticGeo.get(mat);
    if (!list) this.staticGeo.set(mat, (list = []));
    list.push(prepare(geo));
    return this;
  }

  /** A box whose UVs are in metres (so tiling materials keep a constant texel density). */
  box(size: [number, number, number], mat: MaterialKey, pos: [number, number, number], opts: { collide?: boolean; rotY?: number } = {}): this {
    const [w, h, d] = size;
    const m = toMatrix({ pos, rotY: opts.rotY });
    this.add(meterBox(w, h, d), mat, m);
    if (opts.collide) this.colliderBox(`${mat.replace('MAT_', '')}_${this.next()}`, m, [-w / 2, -h / 2, -d / 2], [w / 2, h / 2, d / 2]);
    return this;
  }

  /** Invisible collision-only box (the `COLLIDER_` role), zone-local, axis-aligned. */
  collider(name: string, min: [number, number, number], max: [number, number, number]): Aabb {
    const c: Aabb = {
      id: `COLLIDER_${this.zone}_${name}`,
      min: { x: Math.min(min[0], max[0]), y: Math.min(min[1], max[1]), z: Math.min(min[2], max[2]) },
      max: { x: Math.max(min[0], max[0]), y: Math.max(min[1], max[1]), z: Math.max(min[2], max[2]) },
    };
    this.colliders.push(c);
    return c;
  }

  /** Collider from a box in some local frame (rotations must be multiples of 90° about Y). */
  colliderBox(name: string, frame: Place | Matrix4, min: [number, number, number], max: [number, number, number]): Aabb {
    const [lo, hi] = transformBox(toMatrix(frame), min, max);
    return this.collider(name, lo, hi);
  }

  /** Registers one instance of a shared mesh (repeated props → one InstancedMesh per key). */
  instance(key: string, geo: () => BufferGeometry, mat: MaterialKey | Material, place: Place | Matrix4, castShadow = false): this {
    let entry = this.instances.get(key);
    if (!entry) this.instances.set(key, (entry = { geo: prepare(geo()), mat, matrices: [], shadow: castShadow }));
    entry.matrices.push(toMatrix(place));
    return this;
  }

  /** Declares a light in zone-local space. */
  light(def: Omit<LightDef, 'id'> & { name: string }): this {
    const { name, ...rest } = def;
    this.lights.push({ id: `LIGHT_${this.zone}_${name}`, ...rest });
    return this;
  }

  /** Declares a positional sound emitter in zone-local space. */
  sound(def: Omit<SoundEmitterDef, 'id'> & { name: string }): this {
    const { name, ...rest } = def;
    this.sounds.push({ id: `AUDIO_${this.zone}_${name}`, ...rest });
    return this;
  }

  object(obj: Object3D, name: string): this {
    obj.name = name;
    this.root.add(obj);
    return this;
  }

  build(): Group {
    for (const [mat, geos] of this.staticGeo) {
      const merged = mergeGeometries(geos, false);
      if (!merged) throw new Error(`merge failed for ${mat}`);
      geos.forEach((g) => g.dispose());
      merged.computeBoundingSphere();
      const mesh = new Mesh(merged, this.materials[mat]);
      mesh.name = `${this.root.name}_${mat.replace('MAT_', '')}`;
      mesh.castShadow = !mat.startsWith('MAT_Emissive') && mat !== 'MAT_Plaster_Ceiling';
      mesh.receiveShadow = true;
      this.root.add(mesh);
    }
    for (const [key, { geo, mat, matrices, shadow }] of this.instances) {
      const im = new InstancedMesh(geo, typeof mat === 'string' ? this.materials[mat] : mat, matrices.length);
      matrices.forEach((m, i) => im.setMatrixAt(i, m));
      im.computeBoundingSphere();
      im.name = `PROP_${this.zone}_${key}`;
      im.castShadow = shadow;
      im.receiveShadow = true;
      this.root.add(im);
    }
    this.staticGeo.clear();
    this.instances.clear();
    return this.root;
  }
}

export function toMatrix(p: Place | Matrix4): Matrix4 {
  if (p instanceof Matrix4) return p.clone();
  if (p.rot) _q.setFromEuler(_e.set(...p.rot));
  else _q.setFromAxisAngle(_p.set(0, 1, 0), p.rotY ?? 0);
  _s.set(...(p.scale ?? [1, 1, 1]));
  return new Matrix4().compose(new Vector3(...p.pos), _q, _s);
}

/** Composes a parent transform with a local placement (for props made of instanced parts). */
export function at(parent: Place | Matrix4, local: Place = { pos: [0, 0, 0] }): Matrix4 {
  return toMatrix(parent).multiply(toMatrix(local));
}

/** Transforms a point by a placement. */
export function point(frame: Place | Matrix4, p: [number, number, number]): Vec3 {
  _v.set(...p).applyMatrix4(toMatrix(frame));
  return { x: _v.x, y: _v.y, z: _v.z };
}

function transformBox(m: Matrix4, min: [number, number, number], max: [number, number, number]): [[number, number, number], [number, number, number]] {
  const lo: [number, number, number] = [Infinity, Infinity, Infinity];
  const hi: [number, number, number] = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < 8; i++) {
    _v.set(i & 1 ? max[0] : min[0], i & 2 ? max[1] : min[1], i & 4 ? max[2] : min[2]).applyMatrix4(m);
    const c = [_v.x, _v.y, _v.z];
    for (let k = 0; k < 3; k++) {
      lo[k] = Math.min(lo[k], c[k]);
      hi[k] = Math.max(hi[k], c[k]);
    }
  }
  return [lo, hi];
}

/** Normalises attributes so every geometry can be merged: position, normal, uv; indexed. */
function prepare(geo: BufferGeometry): BufferGeometry {
  for (const name of Object.keys(geo.attributes)) {
    if (name !== 'position' && name !== 'normal' && name !== 'uv') geo.deleteAttribute(name);
  }
  if (!geo.index) {
    const count = geo.attributes.position.count;
    geo.setIndex(Array.from({ length: count }, (_, i) => i));
  }
  if (!geo.attributes.normal) geo.computeVertexNormals();
  geo.morphAttributes = {};
  geo.clearGroups();
  return geo;
}

/** BoxGeometry with per-face UVs scaled to metres. Face order: +x, -x, +y, -y, +z, -z. */
export function meterBox(w: number, h: number, d: number): BoxGeometry {
  const g = new BoxGeometry(w, h, d);
  const uv = g.attributes.uv;
  const spans: [number, number][] = [[d, h], [d, h], [w, d], [w, d], [w, h], [w, h]];
  for (let face = 0; face < 6; face++) {
    const [su, sv] = spans[face];
    for (let v = 0; v < 4; v++) {
      const i = face * 4 + v;
      uv.setXY(i, uv.getX(i) * su, uv.getY(i) * sv);
    }
  }
  return g;
}
