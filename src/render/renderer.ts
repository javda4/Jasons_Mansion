import {
  AgXToneMapping,
  PCFShadowMap,
  RenderPipeline,
  UnsignedByteType,
  WebGPURenderer,
  type PerspectiveCamera,
  type Scene,
} from 'three/webgpu';
import {
  builtinAOContext,
  clearcoat,
  clearcoatRoughness,
  float,
  length,
  max,
  metalness,
  min,
  mix,
  mrt,
  roughness,
  smoothstep,
  uniform,
  vec2,
  vec3,
  normalView,
  output,
  packNormalToRGB,
  pass,
  renderOutput,
  sample,
  screenUV,
  unpackRGBToNormal,
  velocity,
} from 'three/tsl';
import { ao } from 'three/addons/tsl/display/GTAONode.js';
import { bloom } from 'three/addons/tsl/display/BloomNode.js';
import { traa } from 'three/addons/tsl/display/TRAANode.js';
import { smaa } from 'three/addons/tsl/display/SMAANode.js';
import { ssr } from 'three/addons/tsl/display/SSRNode.js';
import type { QualityTier } from '../core/events';

export interface RenderContext {
  renderer: WebGPURenderer;
  backend: 'WebGPU' | 'WebGL2';
}

export async function createRenderer(canvas: HTMLCanvasElement, forceWebGL: boolean): Promise<RenderContext> {
  const renderer = new WebGPURenderer({
    canvas,
    antialias: false, // AA is done in post (TRAA/SMAA) per quality tier
    forceWebGL,
    powerPreference: 'high-performance',
    reversedDepthBuffer: true, // float depth, far → 0: no z-fighting on mouldings, sills and glass at a distance
  });
  await renderer.init();

  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5)); // refined per quality tier in PostStack.setTier
  renderer.setSize(innerWidth, innerHeight, false);
  // Colour management (§8): linear workflow, sRGB output (default), AgX filmic tone mapping.
  renderer.toneMapping = AgXToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFShadowMap;
  // Several passes render per frame; the debug overlay resets counters once per frame.
  renderer.info.autoReset = false;

  const backend = (renderer.backend as { isWebGPUBackend?: boolean }).isWebGPUBackend ? 'WebGPU' : 'WebGL2';
  return { renderer, backend };
}


/** Only true light sources bloom (threshold ≥ 1 in linear HDR); highlights on gilt stay crisp. */
const BLOOM = { strength: 0.2, radius: 0.45, threshold: 1.0 };
/** Linear HDR ceiling applied before TRAA (see the anti-firefly note in the high tier). */
const FIREFLY_CLAMP = 20;
/** Share of a metal's reflectance that SSR adds (the env probe already supplies the broad reflection). */
const METAL_SSR = 0.45;

/**
 * Quality-tiered post stack, all authored once in TSL so it compiles for WebGPU and WebGL2:
 *  - high:   depth/normal/velocity/reflectivity pre-pass → GTAO (ambient term) + SSR
 *            (marble, lacquer, brass reflect the actual room) → TRAA + emissive bloom → grade
 *  - medium: scene → bloom → SMAA
 *  - low:    scene only (no AA)
 * Restrained on purpose: no chromatic aberration, lens dirt or heavy vignette (§8).
 */
export class PostStack {
  readonly pipeline: RenderPipeline;
  /** How strongly clearcoated dielectrics (marble, lacquer) take screen-space reflections. */
  readonly ssrStrength = uniform(0.35);
  /** Linear exposure multiplier applied before tone mapping (live; 1 = the authored look). */
  get exposure(): { value: number } { return EXPOSURE; }
  /** SSR ray-march quality (0–1); tuned for 60 fps at 2× DPR on the reference machine. */
  ssrQuality = 0.25;
  /** Per-channel ceiling on the SSR contribution (linear HDR units). */
  ssrClamp = 1.6;
  /** Screen-space reflections on the high tier. */
  useSSR = true;
  ssr: { quality: { value: number }; resolutionScale: number } | null = null;
  /** Dev aid: 'ssr' shows only the reflection buffer. */
  debugView: 'ssr' | null = null;
  private disposables: { dispose(): void }[] = [];

  constructor(
    private readonly renderer: WebGPURenderer,
    private readonly scene: Scene,
    private readonly camera: PerspectiveCamera,
  ) {
    this.pipeline = new RenderPipeline(renderer);
  }

  setTier(tier: QualityTier): void {
    // Render resolution is part of the tier: TRAA reconstructs detail well enough that 1.5× on a
    // 2× Retina display is visually near-identical and ~70 % cheaper, which pays for SSR (§H budgets).
    const dpr = Math.min(devicePixelRatio, { high: 1.5, medium: 1.25, low: 1 }[tier]);
    if (this.renderer.getPixelRatio() !== dpr) {
      this.renderer.setPixelRatio(dpr);
      this.renderer.setSize(innerWidth, innerHeight, false);
    }
    this.disposables.forEach((d) => d.dispose());
    this.disposables = [];
    const { scene, camera, pipeline } = this;
    const scenePass = pass(scene, camera);
    this.disposables.push(scenePass);

    this.renderer.shadowMap.enabled = tier !== 'low';

    if (tier === 'high') {
      pipeline.outputColorTransform = true;
      // depth / normals / velocity pre-pass (feeds GTAO, SSR and TRAA)
      const prePass = pass(scene, camera);
      prePass.transparent = false;
      prePass.setMRT(mrt({ output: packNormalToRGB(normalView), velocity }));
      prePass.getTexture('output').type = UnsignedByteType;
      const prePassNormal = sample((uv) => unpackRGBToNormal(prePass.getTextureNode().sample(uv)));
      const prePassDepth = prePass.getTextureNode('depth');
      const prePassVelocity = prePass.getTextureNode('velocity');

      const aoPass = ao(prePassDepth, prePassNormal, camera);
      aoPass.resolutionScale = 0.5;
      aoPass.radius.value = 0.6;
      scenePass.contextNode = builtinAOContext(aoPass.getTextureNode().sample(screenUV).r);

      let beauty = scenePass.getTextureNode('output') as unknown as TslNode;
      let ssrPass: ReturnType<typeof ssr> | null = null;
      if (this.useSSR) {
        // SSR weights reflections by "metalness"; clearcoat is what makes marble and French-polished
        // walnut glossy, so feed reflectivity = max(metalness, clearcoat × strength) and a clearcoat-aware
        // roughness. Material properties only exist in a pass that runs the lighting model, so the
        // beauty pass writes them next to its colour.
        const reflectivity = max(metalness.mul(METAL_SSR), clearcoat.mul(this.ssrStrength));
        const glossRough = mix(roughness, min(roughness, clearcoatRoughness), clearcoat);
        scenePass.setMRT(mrt({ output, metalrough: vec2(reflectivity, glossRough) }));
        scenePass.getTexture('metalrough').type = UnsignedByteType;
        const metalRough = scenePass.getTextureNode('metalrough');
        ssrPass = ssr(scenePass.getTextureNode('output'), prePassDepth, prePassNormal, {
          metalnessNode: metalRough.r, roughnessNode: metalRough.g, reflectNonMetals: true, camera,
        });
        ssrPass.resolutionScale = 0.5;
        ssrPass.maxDistance.value = 6;
        ssrPass.thickness.value = 0.05;
        ssrPass.quality.value = this.ssrQuality; // ray-march steps: the main cost at 2× DPR
        this.ssr = ssrPass;
        // clamp: reflections of tiny HDR emitters (candle flames ≈ 40×) otherwise smear into specks
        beauty = beauty.add(min(ssrPass.rgb, vec3(this.ssrClamp))) as unknown as TslNode;
        this.disposables.push(ssrPass);
      } else {
        this.ssr = null;
      }

      // Anti-firefly: sub-pixel emitters (candle bulbs ≈ 40×) jitter in and out of pixels under TRAA; clamping
      // the extreme tail before the temporal resolve keeps them steady without dimming anything visible.
      beauty = min(beauty, vec3(FIREFLY_CLAMP)) as unknown as TslNode;
      const traaPass = traa(beauty, prePassDepth, prePassVelocity, camera);
      traaPass.useSubpixelCorrection = false;
      // Bloom reads the *resolved* image: blooming the raw jittered frame made every bulb's halo shimmer.
      const resolved = (traaPass as unknown as { getTextureNode(): Parameters<typeof bloom>[0] }).getTextureNode(); // (missing from the .d.ts)
      const bloomPass = bloom(resolved, BLOOM.strength, BLOOM.radius, BLOOM.threshold);
      pipeline.outputNode = this.debugView === 'ssr' && ssrPass ? ssrPass : grade(traaPass.add(bloomPass) as unknown as TslNode);
      this.disposables.push(prePass, aoPass, traaPass, bloomPass);
    } else if (tier === 'medium') {
      pipeline.outputColorTransform = false;
      const bloomPass = bloom(scenePass, BLOOM.strength, BLOOM.radius, BLOOM.threshold);
      // SMAA must run on display-referred (tone-mapped sRGB) colour
      pipeline.outputNode = smaa(renderOutput(grade(scenePass.add(bloomPass) as unknown as TslNode)));
      this.disposables.push(bloomPass);
    } else {
      pipeline.outputColorTransform = true;
      pipeline.outputNode = (scenePass as unknown as TslNode).mul(EXPOSURE) as unknown as typeof pipeline.outputNode;
    }
    pipeline.needsUpdate = true;
  }

  render(): void {
    this.pipeline.render();
  }
}

/**
 * Restrained colour grade in linear light (before tone mapping): a touch of warmth, gentle
 * saturation and a very soft vignette — "cinematic", not "game demo" (§8).
 */
type TslNode = ReturnType<typeof vec3>;

/** Scene exposure in linear light (eye adaptation, e.g. when seated at a brightly lit table). */
const EXPOSURE = uniform(1);

function grade(color: TslNode) {
  const c = color.rgb.mul(vec3(1.035, 1.0, 0.955)).mul(EXPOSURE);
  const luma = c.dot(vec3(0.2126, 0.7152, 0.0722));
  const saturated = mix(vec3(luma), c, float(1.06));
  const vignette = float(1).sub(smoothstep(0.35, 1.1, length(screenUV.sub(0.5).mul(vec2(1.6, 1.2)))).mul(0.14));
  return saturated.mul(vignette);
}
