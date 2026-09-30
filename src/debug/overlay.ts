import { Group, LineBasicMaterial, LineSegments, BoxGeometry, EdgesGeometry, Mesh, type Scene, type WebGPURenderer } from 'three/webgpu';
import type { System } from '../core/loop';
import type { Aabb } from '../physics/types';
import type { PlayerState } from '../player/controller';

/**
 * Dev-only debug overlay (§8). Everything here is behind `__DEBUG__` at the call site so it is
 * tree-shaken out of production builds. Toggle with the ` key or `?debug`.
 */
export class DebugOverlay implements System {
  readonly name = 'debug';
  private el: HTMLDivElement;
  private frames = 0;
  private acc = 0;
  private fps = 0;
  private worst = 0;
  private colliderViz: Group | null = null;
  visible: boolean;

  constructor(
    private readonly renderer: WebGPURenderer,
    private readonly scene: Scene,
    private readonly player: PlayerState,
    private readonly info: { backend: string; zone: () => string; zones: () => string; lights: () => string; tier: () => string; textureMB: number; colliders: () => Aabb[] },
    visible: boolean,
  ) {
    this.visible = visible;
    this.el = document.createElement('div');
    Object.assign(this.el.style, {
      position: 'fixed', top: '12px', right: '12px', zIndex: '20', padding: '10px 12px',
      font: '12px/1.45 ui-monospace, Menlo, monospace', color: '#f3e6c8', whiteSpace: 'pre',
      background: 'rgb(10 7 4 / 0.78)', border: '1px solid rgb(201 164 92 / 0.4)', pointerEvents: 'none',
    });
    document.body.append(this.el);
    this.el.hidden = !visible;
  }

  toggle(): void {
    this.visible = !this.visible;
    this.el.hidden = !this.visible;
    this.setColliders(this.visible);
  }

  setColliders(on: boolean): void {
    if (on && this.colliderViz) { this.scene.remove(this.colliderViz); this.colliderViz = null; }
    if (on && !this.colliderViz) {
      this.colliderViz = new Group();
      this.colliderViz.name = 'DEBUG_Colliders';
      const mat = new LineBasicMaterial({ color: 0x40ff90, transparent: true, opacity: 0.55, depthTest: true });
      const edges = new EdgesGeometry(new BoxGeometry(1, 1, 1));
      for (const b of this.info.colliders()) {
        const l = new LineSegments(edges, mat);
        l.scale.set(b.max.x - b.min.x, b.max.y - b.min.y, b.max.z - b.min.z);
        l.position.set((b.min.x + b.max.x) / 2, (b.min.y + b.max.y) / 2, (b.min.z + b.max.z) / 2);
        this.colliderViz.add(l);
      }
      this.scene.add(this.colliderViz);
    }
    if (this.colliderViz) this.colliderViz.visible = on;
  }

  /** Call once per frame before rendering; reads last frame's counters then resets them. */
  update(dt: number): void {
    const r = this.renderer.info.render;
    const draws = r.drawCalls, tris = r.triangles;
    this.renderer.info.reset();
    this.frames++;
    this.acc += dt;
    this.worst = Math.max(this.worst, dt);
    if (this.acc < 0.5 || !this.visible) return;
    this.fps = this.frames / this.acc;
    const p = this.player.position;
    const mem = this.renderer.info.memory as { geometries?: number; textures?: number };
    this.el.textContent =
      `${this.info.backend} · tier ${this.info.tier()}\n` +
      `FPS        ${this.fps.toFixed(0).padStart(4)}   (${(1000 / this.fps).toFixed(1)} ms, worst ${(this.worst * 1000).toFixed(1)})\n` +
      `draw calls ${String(draws).padStart(4)}   (all passes)\n` +
      `triangles  ${(tris / 1000).toFixed(0).padStart(4)} k\n` +
      `geo / tex  ${mem.geometries ?? '?'} / ${mem.textures ?? '?'}   src tex ${this.info.textureMB.toFixed(1)} MB\n` +
      `zone       ${this.info.zone()}\n` +
      `lights     ${this.info.lights()}\n` +
      `pos        ${p.x.toFixed(2)} ${p.y.toFixed(2)} ${p.z.toFixed(2)}  ${this.player.grounded ? 'grounded' : 'air'}\n` +
      `yaw/pitch  ${(this.player.yaw * 57.3 % 360).toFixed(0)}° / ${(this.player.pitch * 57.3).toFixed(0)}°\n` +
      `── zones ──\n${this.info.zones()}`;
    this.frames = 0;
    this.acc = 0;
    this.worst = 0;
  }
}

export type { Mesh };
