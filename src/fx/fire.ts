import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Color,
  IcosahedronGeometry,
  InstancedMesh,
  Matrix4,
  Mesh,
  MeshBasicNodeMaterial,
  MeshStandardNodeMaterial,
  Vector3,
  type Material,
  type MeshStandardMaterial,
} from 'three/webgpu';
import {
  abs,
  attribute,
  cameraPosition,
  clamp,
  float,
  length,
  max,
  mix,
  modelWorldMatrixInverse,
  mx_fractal_noise_float,
  mx_noise_float,
  normalWorld,
  normalize,
  positionGeometry,
  positionWorld,
  pow,
  smoothstep,
  time,
  uniform,
  vec2,
  vec3,
  vec4,
} from 'three/tsl';
import type { EffectDef, ZoneInstance } from '../world/roomBuilder';

/**
 * A living wood fire on an `FX_` marker (origin = centre of the flame bed; local +Y up, X along the logs).
 *
 * - Flames: ~17 camera-facing tongues in ONE draw call. Each is a quad whose shape is cut from rising,
 *   domain-warped fractal noise inside a tapering envelope and coloured along a blackbody ramp
 *   (deep red → orange → yellow-white), additive and HDR so the bloom pass gives the glow. Tongues
 *   lick, break up at the tips and never repeat — the painted card this replaces was a still image.
 * - Embers: the zone's log and ash materials (MAT_Vip_LogBark / _LogEnd / _Ashes) get an emissive
 *   node: thin glowing cracks on the logs' undersides and ends near the flame, and pulsing coals in
 *   the ash, all breathing slowly.
 * - Sparks: a few dozen tiny HDR embers that pop off the logs and drift up the chimney.
 * Light itself comes from the zone's LIGHT_ (flicker) via the LightPool, as before.
 */
export function attachFire(inst: ZoneInstance, def: EffectDef): void {
  const W = Number(def.extras.width ?? 0.6);
  const D = Number(def.extras.depth ?? 0.2);
  const H = Number(def.extras.height ?? 0.5);
  const node = def.node;

  // world → fire-local, refreshed each frame (the zone root can be placed after load)
  const toFire = uniform(new Matrix4());
  const firePos = (): ReturnType<typeof vec3> => toFire.mul(vec4(positionWorld, 1)).xyz as unknown as ReturnType<typeof vec3>;

  const flames = new Mesh(flameGeometry(W, D, H), flameMaterial());
  flames.name = `${node.name}_Flames`;
  flames.frustumCulled = false;            // vertices are expanded in the shader
  flames.renderOrder = 10;
  node.add(flames);

  const glowMats = emberMaterials(inst, firePos, W, D);
  const sparks = new Sparks(W, D, H);
  node.add(sparks.mesh);

  let last = 0;
  inst.animate.push((t) => {
    const dt = Math.min(0.1, Math.max(0, t - last));
    last = t;
    toFire.value.copy(node.matrixWorld).invert();
    sparks.update(t, dt);
  });
  if (!glowMats) console.warn(`[fx] ${inst.id}: no MAT_*_LogBark / _Ashes materials — fire without embers`);
}

// ---------------------------------------------------------------------------------------------- flames

interface Tongue { x: number; z: number; w: number; h: number }

function tongues(W: number, D: number, H: number): Tongue[] {
  let s = 1927;
  const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const out: Tongue[] = [];
  // main tongues: tallest over the middle of the bed, from the gap between the logs
  for (let i = 0; i < 11; i++) {
    const x = (i / 10 - 0.5) * W * 0.9 + (rnd() - 0.5) * 0.05;
    const centre = 1 - Math.pow((2 * x) / W, 2);
    out.push({ x, z: (rnd() - 0.5) * D * 0.8, w: 0.14 + rnd() * 0.1, h: H * (0.45 + 0.55 * centre) * (0.7 + rnd() * 0.3) });
  }
  // low licks along the logs
  for (let i = 0; i < 6; i++) {
    out.push({ x: (rnd() - 0.5) * W, z: (rnd() - 0.5) * D, w: 0.08 + rnd() * 0.06, h: H * (0.18 + rnd() * 0.18) });
  }
  return out;
}

/** Quads collapsed to their base point; the vertex shader expands them towards the camera (cylindrical billboards). */
function flameGeometry(W: number, D: number, H: number): BufferGeometry {
  const ts = tongues(W, D, H);
  const pos = new Float32Array(ts.length * 4 * 3);
  const corner = new Float32Array(ts.length * 4 * 2);
  const data = new Float32Array(ts.length * 4 * 4);
  const index: number[] = [];
  ts.forEach((tg, i) => {
    const c = [[-0.5, 0], [0.5, 0], [0.5, 1], [-0.5, 1]];
    for (let k = 0; k < 4; k++) {
      const v = i * 4 + k;
      pos.set([tg.x, 0, tg.z], v * 3);
      corner.set(c[k], v * 2);
      data.set([tg.w, tg.h, i * 7.13 + 0.37, i * 1.618], v * 4);
    }
    const b = i * 4;
    index.push(b, b + 1, b + 2, b, b + 2, b + 3);
  });
  const g = new BufferGeometry();
  g.setAttribute('position', new BufferAttribute(pos, 3));
  g.setAttribute('aCorner', new BufferAttribute(corner, 2));
  g.setAttribute('aTongue', new BufferAttribute(data, 4));
  g.setIndex(index);
  return g;
}

function flameMaterial(): MeshBasicNodeMaterial {
  const m = new MeshBasicNodeMaterial();
  m.name = 'MAT_Runtime_Flame';
  m.transparent = true;
  m.depthWrite = false;
  m.blending = AdditiveBlending;
  m.toneMapped = true;
  m.fog = false;

  const corner = attribute('aCorner', 'vec2');
  const tg = attribute('aTongue', 'vec4');         // w, h, seed, phase
  const seed = tg.z, phase = tg.w;

  // ---- vertex: face the camera about the vertical axis, breathe and sway
  const camLocal = modelWorldMatrixInverse.mul(vec4(cameraPosition, 1)).xyz;
  const toCam = camLocal.sub(positionGeometry);
  const flat = normalize(vec3(toCam.x, 0, toCam.z).add(vec3(1e-4, 0, 0)));
  const right = vec3(flat.z, 0, flat.x.negate());
  const breathe = float(0.82).add(mx_noise_float(vec2(time.mul(1.3).add(seed), phase)).mul(0.22));
  const h = tg.y.mul(breathe);
  const sway = corner.y.mul(corner.y).mul(mx_noise_float(vec2(time.mul(0.9).add(phase), seed)).mul(0.05));
  m.positionNode = positionGeometry
    .add(right.mul(corner.x.mul(tg.x).add(sway)))
    .add(vec3(0, corner.y.mul(h), 0));

  // ---- fragment: rising turbulent noise inside a tapering envelope
  const x = corner.x, y = corner.y;
  const t = time;
  const warp = mx_fractal_noise_float(vec3(x.mul(2.2), y.mul(1.7).sub(t.mul(1.1)), seed), 3);
  const xw = x.add(warp.mul(0.24).mul(y.add(0.15)));
  const n = mx_fractal_noise_float(vec3(xw.mul(3.4), y.mul(2.8).sub(t.mul(2.6)), seed.mul(1.7).add(t.mul(0.15))), 4);
  const halfW = pow(float(1).sub(y), 0.6).mul(0.46);
  const env = smoothstep(halfW, halfW.mul(0.3), abs(xw));
  const body = env.mul(float(1).sub(y.mul(0.85)));
  const flame = clamp(body.mul(1.45).add(n.mul(0.6)).sub(0.42), 0, 1).mul(smoothstep(0, 0.07, y));
  const heat = pow(flame, 1.4);
  const deep = vec3(0.55, 0.06, 0.0), orange = vec3(1.0, 0.33, 0.04), yellow = vec3(1.0, 0.7, 0.24), white = vec3(1.0, 0.9, 0.68);
  let col = mix(deep, orange, smoothstep(0.02, 0.35, heat));
  col = mix(col, yellow, smoothstep(0.35, 0.72, heat));
  col = mix(col, white, smoothstep(0.78, 1.0, heat));
  // a faint blue root where the gas first ignites
  const root = smoothstep(0.14, 0.0, y).mul(env).mul(0.35);
  const rgb = col.mul(heat).mul(5.5).add(vec3(0.12, 0.2, 0.75).mul(root));
  m.colorNode = vec4(rgb, 1);
  return m;
}

// ---------------------------------------------------------------------------------------------- embers

function emberMaterials(inst: ZoneInstance, firePos: () => ReturnType<typeof vec3>, W: number, D: number): boolean {
  const kinds: Record<string, 'bark' | 'end' | 'ash'> = {};
  const swapped = new Map<Material, Material>();
  inst.root.traverse((o) => {
    const mesh = o as Mesh;
    if (!mesh.isMesh || Array.isArray(mesh.material)) return;
    const m = mesh.material as MeshStandardMaterial;
    const kind = /_LogBark$/.test(m.name) ? 'bark' : /_LogEnd$/.test(m.name) ? 'end' : /_Ashes$/.test(m.name) ? 'ash' : null;
    if (!kind) return;
    kinds[m.name] = kind;
    let n = swapped.get(m);
    if (!n) {
      n = emberMaterial(m, kind, firePos, W, D);
      swapped.set(m, n);
    }
    mesh.material = n;
  });
  return swapped.size > 0;
}

function emberMaterial(src: MeshStandardMaterial, kind: 'bark' | 'end' | 'ash', firePos: () => ReturnType<typeof vec3>, W: number, D: number): MeshStandardNodeMaterial {
  const m = new MeshStandardNodeMaterial();
  m.name = src.name;
  m.color.copy(src.color);
  // smoke-darkened, part-charred bark; grey-black ash (the photo sets are daylight-bright)
  m.color.multiplyScalar(kind === 'bark' ? 0.26 : kind === 'ash' ? 0.18 : 1);
  m.map = src.map;
  m.normalMap = src.normalMap;
  m.normalScale.copy(src.normalScale);
  m.roughness = src.roughness;
  m.metalness = src.metalness;
  m.roughnessMap = src.roughnessMap;
  m.metalnessMap = src.metalnessMap;
  m.aoMap = src.aoMap;
  m.envMapIntensity = 0.4;

  const p = firePos();
  const r = length(vec2(p.x.div(W * 0.62), p.z.div(D * 1.4)));
  const near = smoothstep(1.05, 0.25, r);                 // 1 in the heart of the fire
  const breath = float(0.62).add(mx_noise_float(vec3(positionWorld.xz.mul(5), time.mul(0.55))).mul(0.38));
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ember = (g: any) =>
    mix(vec3(0.9, 0.12, 0.01), vec3(1.0, 0.45, 0.08), clamp(g.mul(1.6), 0, 1)).mul(g).mul(7);

  let glow;
  if (kind === 'ash') {
    // scattered coals: noise blobs, brightest under the logs
    const coals = pow(max(mx_fractal_noise_float(vec3(positionWorld.xz.mul(16), time.mul(0.12)), 3), 0), 2.2);
    glow = near.mul(near).mul(coals.mul(2.4).add(0.03)).mul(breath);
  } else {
    // thin ridged cracks in the char
    // thin, sparse cracks only where the wood faces the coals (undersides, lower flanks) and the end grain
    const cracks = pow(float(1).sub(abs(mx_noise_float(positionWorld.mul(vec3(38, 38, 38))))), 22);
    const patchy = smoothstep(0.0, 0.5, mx_noise_float(positionWorld.mul(vec3(9, 9, 9))));
    const under = kind === 'end' ? float(0.55) : smoothstep(-0.15, -0.85, normalWorld.y);
    const low = smoothstep(0.2, 0.02, p.y);
    glow = near.mul(under.mul(low.mul(0.6).add(0.4))).mul(cracks.mul(patchy).mul(1.6).add(under.mul(0.05))).mul(breath);
  }
  m.emissiveNode = ember(glow);
  return m;
}

// ---------------------------------------------------------------------------------------------- sparks

const SPARKS = 36;

class Sparks {
  readonly mesh: InstancedMesh;
  private readonly p = Array.from({ length: SPARKS }, () => ({ pos: new Vector3(), vel: new Vector3(), life: 0, age: 1, size: 0 }));
  private readonly m4 = new Matrix4();
  private next = 0;

  constructor(private readonly W: number, private readonly D: number, private readonly H: number) {
    const mat = new MeshBasicNodeMaterial();
    mat.name = 'MAT_Runtime_Spark';
    mat.blending = AdditiveBlending;
    mat.transparent = true;
    mat.depthWrite = false;
    mat.color = new Color(1, 0.42, 0.08).multiplyScalar(14);   // HDR: small but they bloom
    const geo = new IcosahedronGeometry(1, 0);
    this.mesh = new InstancedMesh(geo, mat, SPARKS);
    this.mesh.name = 'FX_Runtime_Sparks';
    this.mesh.frustumCulled = false;
    for (let i = 0; i < SPARKS; i++) this.mesh.setMatrixAt(i, this.m4.makeScale(0, 0, 0));
  }

  update(t: number, dt: number): void {
    // irregular bursts: a pop now and then, sometimes a small shower
    if (t >= this.next) {
      const n = Math.random() < 0.18 ? 4 + Math.floor(Math.random() * 5) : 1;
      for (let k = 0; k < n; k++) this.spawn();
      this.next = t + 0.08 + Math.random() * Math.random() * 1.2;
    }
    this.p.forEach((s, i) => {
      if (s.age >= s.life) { this.mesh.setMatrixAt(i, this.m4.makeScale(0, 0, 0)); return; }
      s.age += dt;
      s.vel.x += (Math.random() - 0.5) * 1.6 * dt;
      s.vel.z += (Math.random() - 0.5) * 1.0 * dt;
      s.vel.y += (0.35 - s.vel.y * 0.5) * dt;              // buoyant, with drag
      s.pos.addScaledVector(s.vel, dt);
      const k = 1 - s.age / s.life;
      const tw = 0.6 + 0.4 * Math.sin(s.age * 40 + i);       // twinkle as they tumble
      const r = s.size * k * tw;
      this.mesh.setMatrixAt(i, this.m4.makeScale(r, r * 2.2, r).setPosition(s.pos));
    });
    this.mesh.instanceMatrix.needsUpdate = true;
  }

  private spawn(): void {
    const s = this.p.find((q) => q.age >= q.life);
    if (!s) return;
    s.pos.set((Math.random() - 0.5) * this.W * 0.8, 0.08 + Math.random() * this.H * 0.3, (Math.random() - 0.5) * this.D);
    s.vel.set((Math.random() - 0.5) * 0.3, 0.5 + Math.random() * 0.9, (Math.random() - 0.5) * 0.2);
    s.life = 0.6 + Math.random() * 1.3;
    s.age = 0;
    s.size = 0.0025 + Math.random() * 0.003;
  }
}
