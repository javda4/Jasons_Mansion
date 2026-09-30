import type { Material, Mesh, Object3D, PerspectiveCamera, Scene, Texture, WebGPURenderer } from 'three/webgpu';
import type { EventBus } from '../core/events';
import type { System } from '../core/loop';
import type { InteractionSystem } from '../interaction/interactionSystem';
import { AabbCollisionWorld } from '../physics/aabbWorld';
import type { Aabb, Capsule, CollisionWorld, MoveResult, Vec3 } from '../physics/types';
import type { PlayerState } from '../player/controller';
import type { LightPool } from '../render/lightPool';
import type { MaterialKey } from '../render/materials';
import type { ProbeManager } from '../render/probe';
import type { DoorSystem, ZoneAvailability } from './doors';
import type { ZoneInstance } from './roomBuilder';
import type { SoundEmitterDef } from '../audio/audioEngine';
import { decide, type ZoneGraph } from './streamingPolicy';

export type ZoneState = 'unloaded' | 'loading' | 'loaded' | 'active' | 'unloading';

/** A manifest entry (§7). Phase 2 generates these from the asset build; `load` then fetches a GLB. */
export interface ZoneManifestEntry {
  id: string;
  title: string;
  neighbors: readonly string[];
  /** World placement of the zone's local origin (its entrance anchor). */
  transform: { x: number; z: number; rotY: number };
  preload?: boolean;
  /** Code-built zones return a sync builder; GLB zones an async one (see loading/glbZone.ts). */
  load: () => Promise<(materials: Record<MaterialKey, Material>) => ZoneInstance | Promise<ZoneInstance>>;
}

interface ZoneRecord {
  entry: ZoneManifestEntry;
  state: ZoneState;
  instance: ZoneInstance | null;
  loadMs?: number;
}

const STREAM_INTERVAL = 0.25;
const UNLOAD_AFTER = 20; // seconds out of range before a zone is released
const APPROACH_RADIUS = 6; // metres from a door at which its far zone is escalated

/**
 * Owns the zone graph and lifecycle (§8 Zone streaming):
 * `unloaded → loading → loaded (hidden) → active → unloading`.
 * Visibility is portal-based: the current zone plus zones seen through open doors.
 */
export class ZoneManager implements System, ZoneAvailability {
  readonly name = 'zones';
  private zones = new Map<string, ZoneRecord>();
  private graph: ZoneGraph;
  private current = '';
  private visible = new Set<string>();
  /** Forces the next visibility pass (zones/doors were added or removed). */
  private visibilityDirty = true;
  private outOfRange = new Map<string, number>();
  private requested: string[] = [];
  private loading: string | null = null;
  private sinceStream = STREAM_INTERVAL;
  private time = 0;
  private collision = new AabbCollisionWorld([]);
  /** Stable handle given to the player controller; delegates to the rebuilt world. */
  readonly collisionWorld: CollisionWorld = {
    moveCapsule: (from: Vec3, delta: Vec3, c: Capsule, snap: number): MoveResult => this.collision.moveCapsule(from, delta, c, snap),
    groundHeight: (x: number, z: number, r: number, maxY: number) => this.collision.groundHeight(x, z, r, maxY),
  };
  doors!: DoorSystem;

  constructor(
    manifest: readonly ZoneManifestEntry[],
    private readonly deps: {
      scene: Scene;
      renderer: WebGPURenderer;
      camera: PerspectiveCamera;
      bus: EventBus;
      player: PlayerState;
      materials: Record<MaterialKey, Material>;
      lights: LightPool;
      probes: ProbeManager;
      interaction: InteractionSystem;
    },
  ) {
    this.graph = Object.fromEntries(manifest.map((e) => [e.id, e.neighbors]));
    for (const entry of manifest) this.zones.set(entry.id, { entry, state: 'unloaded', instance: null });
  }

  // ---------------------------------------------------------------- queries
  isReady(id: string): boolean {
    const z = this.zones.get(id);
    return !!z && (z.state === 'loaded' || z.state === 'active');
  }

  request(id: string): void {
    if (!this.isReady(id) && !this.requested.includes(id)) this.requested.unshift(id);
    this.sinceStream = STREAM_INTERVAL;
  }

  get currentId(): string { return this.current; }
  get currentTitle(): string { return this.zones.get(this.current)?.entry.title ?? '—'; }
  instance(id: string): ZoneInstance | null { return this.zones.get(id)?.instance ?? null; }
  /** Forward a game event to whichever loaded zone owns the table. */
  gameEvent(tableId: string, event: { type: string; [k: string]: unknown }): void {
    for (const z of this.zones.values()) z.instance?.onGameEvent?.(tableId, event);
  }

  /** Sound emitters of the zones currently drawn (the audio engine polls this). */
  visibleSounds(): SoundEmitterDef[] {
    return [...this.visible].flatMap((id) => this.zones.get(id)?.instance?.sounds ?? []);
  }

  get activeColliders(): Aabb[] { return [...this.zones.values()].flatMap((z) => z.instance?.colliders ?? []); }

  describe(): string {
    return [...this.zones.values()]
      .map((z) => `${z.entry.id.padEnd(10)} ${z.state}${this.visible.has(z.entry.id) ? ' · visible' : ''}${z.loadMs ? ` · ${z.loadMs.toFixed(0)} ms` : ''}`)
      .join('\n');
  }

  // ---------------------------------------------------------------- loading
  /** Blocking initial load (behind the entry curtain). */
  async loadNow(id: string): Promise<ZoneInstance> {
    await this.load(id);
    const inst = this.zones.get(id)!.instance!;
    this.setCurrent(id);
    return inst;
  }

  private async load(id: string): Promise<void> {
    const z = this.zones.get(id);
    if (!z || z.state !== 'unloaded') return;
    this.loading = id;
    this.setState(z, 'loading');
    const t0 = performance.now();
    try {
      const build = await z.entry.load();
      await nextFrame();
      const inst = await build(this.deps.materials);
      applyTransform(inst, z.entry.transform, id);
      const t1 = performance.now();
      // compile pipelines before the zone can ever be seen (§8)
      await this.deps.renderer.compileAsync(inst.root, this.deps.camera, this.deps.scene);
      if (__DEBUG__) console.info(`[zones] ${id}: fetch+decode+build ${(t1 - t0).toFixed(0)} ms, compile ${(performance.now() - t1).toFixed(0)} ms`);
      if ((z.state as ZoneState) !== 'loading') return; // cancelled meanwhile
      inst.root.visible = false;
      this.deps.scene.add(inst.root);
      z.instance = inst;
      await nextFrame();
      this.captureProbe(id, inst);
      this.detachDoorLeaves(inst);
      this.doors.register(id, inst.doors);
      this.visibilityDirty = true;
      this.rebuildCollision();
      z.loadMs = performance.now() - t0;
      this.setState(z, 'loaded');
      this.validateGraph(z);
    } catch (err) {
      console.error(`[zones] failed to load ${id}`, err);
      this.setState(z, 'unloaded');
    } finally {
      this.loading = null;
    }
  }

  private unload(id: string): void {
    const z = this.zones.get(id);
    if (!z?.instance || id === this.current) return;
    this.setState(z, 'unloading');
    const root = z.instance.root;
    this.deps.scene.remove(root);
    disposeTree(root);
    for (const d of z.instance.doors) for (const l of d.leaves) { this.deps.scene.remove(l.pivot); disposeTree(l.pivot); }
    this.visibilityDirty = true;
    this.doors.unregister(id);
    this.deps.probes.release(id);
    z.instance = null;
    this.rebuildCollision();
    this.setState(z, 'unloaded');
  }

  /**
   * Doors are portals shared by two zones but authored in one of them. Their leaves are lifted
   * out of the owning zone's root (keeping world transforms) so a door stays drawn and
   * interactable from the other side even while its owner zone is hidden behind it.
   */
  private detachDoorLeaves(inst: ZoneInstance): void {
    inst.root.updateMatrixWorld(true);
    for (const door of inst.doors) {
      for (const leaf of door.leaves) {
        this.deps.scene.attach(leaf.pivot);
        leaf.pivot.userData.baseQuaternion = leaf.pivot.quaternion.clone(); // doors load closed
        leaf.pivot.visible = false;
      }
    }
  }

  private captureProbe(id: string, inst: ZoneInstance): void {
    const others = [...this.zones.values()].filter((o) => o.instance && o.instance !== inst).map((o) => [o.instance!.root, o.instance!.root.visible] as const);
    for (const [r] of others) r.visible = false;
    inst.root.visible = true;
    inst.animate.forEach((f) => f(0));
    this.deps.lights.withLightsAt(inst.lights, inst.probe, () => this.deps.probes.capture(id, inst.probe));
    inst.root.visible = false;
    for (const [r, v] of others) r.visible = v;
  }

  private rebuildCollision(): void {
    this.collision = new AabbCollisionWorld(this.activeColliders);
  }

  private validateGraph(z: ZoneRecord): void {
    for (const d of z.instance!.doors) {
      if (d.target && !z.entry.neighbors.includes(d.target)) console.warn(`[zones] ${z.entry.id}: door ${d.id} targets ${d.target}, which is not a manifest neighbour`);
    }
  }

  private setState(z: ZoneRecord, state: ZoneState): void {
    z.state = state;
    this.deps.bus.emit('zone:state', { zoneId: z.entry.id, state });
  }

  // ---------------------------------------------------------------- per frame
  update(dt: number, time: number): void {
    this.time = time;
    this.updateCurrent();
    this.updateVisibility();
    for (const id of this.visible) this.zones.get(id)?.instance?.animate.forEach((f) => f(time));

    this.sinceStream += dt;
    if (this.sinceStream >= STREAM_INTERVAL && this.current) {
      this.sinceStream = 0;
      this.escalateApproachedDoors();
      this.stream();
    }
  }

  /** Walking up to a door jumps the zone behind it to the front of the queue (§8). */
  private escalateApproachedDoors(): void {
    const p = this.deps.player.position;
    for (const z of this.zones.values()) {
      for (const d of z.instance?.doors ?? []) {
        if (!d.target || this.isReady(d.target) || this.requested.includes(d.target)) continue;
        if ((d.position.x - p.x) ** 2 + (d.position.z - p.z) ** 2 < APPROACH_RADIUS ** 2) this.requested.push(d.target);
      }
    }
  }

  private stream(): void {
    const loaded = new Set([...this.zones.values()].filter((z) => z.instance).map((z) => z.entry.id));
    const decision = decide(this.graph, this.current, loaded, this.outOfRange, this.time, {
      idle: this.loading === null && this.requested.length === 0,
      unloadAfter: UNLOAD_AFTER,
      pinned: new Set([...this.visible, ...this.requested]),
    });
    for (const id of decision.unload) this.unload(id);
    if (this.loading) return;
    this.requested = this.requested.filter((id) => !this.isReady(id));
    const next = this.requested[0] ?? decision.load[0]?.id;
    if (next) void this.load(next);
  }

  private updateCurrent(): void {
    const p = this.deps.player.position;
    const inside = (id: string) => {
      const b = this.zones.get(id)?.instance?.bounds;
      return !!b && p.x >= b.min.x && p.x <= b.max.x && p.z >= b.min.z && p.z <= b.max.z && p.y >= b.min.y - 1 && p.y <= b.max.y;
    };
    if (this.current && inside(this.current)) return;
    for (const [id, z] of this.zones) {
      if (z.instance && inside(id)) {
        this.setCurrent(id);
        return;
      }
    }
  }

  private setCurrent(id: string): void {
    const prev = this.zones.get(this.current);
    if (prev && prev.state === 'active') this.setState(prev, 'loaded');
    this.current = id;
    this.setState(this.zones.get(id)!, 'active');
    this.deps.probes.activate(id);
    this.deps.bus.emit('zone:entered', { zoneId: id });
  }

  /** Current zone + zones reachable through open doors (two portals deep). */
  private updateVisibility(): void {
    const next = new Set<string>([this.current]);
    const links = [...this.doors.openLinks()];
    for (let depth = 0; depth < 2; depth++) {
      for (const l of links) {
        if (next.has(l.a) && this.isReady(l.b)) next.add(l.b);
        if (next.has(l.b) && this.isReady(l.a)) next.add(l.a);
      }
    }
    let changed = this.visibilityDirty || next.size !== this.visible.size;
    for (const id of next) if (!this.visible.has(id)) changed = true;
    if (!changed) return;
    this.visibilityDirty = false;
    this.visible = next;
    const roots: Object3D[] = [];
    const lights = [];
    for (const [id, z] of this.zones) {
      if (!z.instance) continue;
      z.instance.root.visible = next.has(id);
      if (next.has(id)) {
        roots.push(z.instance.root);
        lights.push(...z.instance.lights);
      }
      // a door is drawn (and can be used) when either of the zones it joins is visible
      for (const d of z.instance.doors) {
        const show = next.has(id) || (d.target !== null && next.has(d.target));
        for (const l of d.leaves) {
          l.pivot.visible = show;
          if (show) roots.push(l.pivot);
        }
      }
    }
    this.deps.lights.setCandidates(lights, this.current);
    this.deps.interaction.setTargets(roots);
  }
}

// ------------------------------------------------------------------ helpers

function nextFrame(): Promise<void> {
  return new Promise((r) => requestAnimationFrame(() => r()));
}

/** Places a zone-local instance in the world (rotations are multiples of 90° about Y). */
function applyTransform(inst: ZoneInstance, t: { x: number; z: number; rotY: number }, zoneId: string): void {
  const c = Math.cos(t.rotY), s = Math.sin(t.rotY);
  const tp = (v: Vec3) => {
    const x = t.x + v.x * c + v.z * s;
    const z = t.z - v.x * s + v.z * c;
    v.x = round(x);
    v.z = round(z);
  };
  const tb = (b: Aabb) => {
    const a = { x: b.min.x, y: 0, z: b.min.z }, d = { x: b.max.x, y: 0, z: b.max.z };
    tp(a); tp(d);
    b.min.x = Math.min(a.x, d.x); b.max.x = Math.max(a.x, d.x);
    b.min.z = Math.min(a.z, d.z); b.max.z = Math.max(a.z, d.z);
  };
  inst.root.position.set(t.x, 0, t.z);
  inst.root.rotation.set(0, t.rotY, 0);
  inst.root.updateMatrixWorld(true);
  inst.colliders.forEach(tb);
  tb(inst.bounds);
  for (const l of inst.lights) {
    tp(l.position);
    if (l.target) tp(l.target);
    l.zone = zoneId;
  }
  for (const d of inst.doors) tp(d.position);
  for (const s of inst.sounds ?? []) { tp(s.position); s.id = `${zoneId}:${s.id}`; }
  tp(inst.probe);
  if (inst.spawn) {
    tp(inst.spawn.position);
    inst.spawn.yaw += t.rotY;
  }
}

function round(v: number): number {
  return Math.round(v * 1e5) / 1e5;
}

function disposeTree(root: Object3D): void {
  root.traverse((o) => {
    const m = o as Mesh;
    if (!m.isMesh) return;
    m.geometry.dispose();
    const mats = Array.isArray(m.material) ? m.material : [m.material];
    for (const mat of mats) {
      if (mat.userData.shared) continue;
      if (mat.userData.sharedTextures) {
        // per-zone clone of a library material: only the lightmap belongs to this zone
        (mat as Material & { lightMap?: Texture | null }).lightMap?.dispose();
      } else {
        for (const v of Object.values(mat)) if ((v as Texture)?.isTexture) (v as Texture).dispose();
      }
      mat.dispose();
    }
  });
}
