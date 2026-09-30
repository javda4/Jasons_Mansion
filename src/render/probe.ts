import { PMREMGenerator, Vector3, type RenderTarget, type Scene, type WebGPURenderer } from 'three/webgpu';
import type { Vec3 } from '../physics/types';

/**
 * Per-zone reflection probes (§F). Each zone is captured into its own prefiltered (PMREM) cube
 * once, after it streams in. The scene always uses ONE shared environment texture; entering a
 * zone GPU-copies that zone's probe into it — swapping the texture object itself would force
 * every material to rebuild its shader nodes. Phase 3 replaces live capture with baked `PROBE_`
 * captures shipped as KTX2.
 */
export class ProbeManager {
  private pmrem: PMREMGenerator;
  private probes = new Map<string, RenderTarget>();
  private shared: RenderTarget | null = null;
  private active = '';

  constructor(
    private readonly renderer: WebGPURenderer,
    private readonly scene: Scene,
    private readonly intensity: number,
  ) {
    this.pmrem = new PMREMGenerator(renderer);
  }

  /** Renders the scene (as currently set up by the caller) from `at` into the zone's probe. */
  capture(zoneId: string, at: Vec3): void {
    const prevEnv = this.scene.environment;
    this.scene.environment = null;
    const opts = { size: 256, position: new Vector3(at.x, at.y, at.z) };
    const rt = this.pmrem.fromScene(this.scene, 0.015, 0.1, 60, { ...opts, renderTarget: this.probes.get(zoneId) ?? null });
    this.probes.set(zoneId, rt);
    if (!this.shared) {
      this.shared = this.pmrem.fromScene(this.scene, 0.015, 0.1, 60, opts);
      this.active = zoneId;
      this.scene.environment = this.shared.texture;
      this.scene.environmentIntensity = this.intensity;
    } else {
      this.scene.environment = prevEnv;
    }
  }

  activate(zoneId: string): void {
    if (zoneId === this.active || !this.shared) return;
    const rt = this.probes.get(zoneId);
    if (!rt) return;
    this.renderer.copyTextureToTexture(rt.texture, this.shared.texture);
    this.active = zoneId;
  }

  release(zoneId: string): void {
    this.probes.get(zoneId)?.dispose();
    this.probes.delete(zoneId);
  }
}
