import { DoubleSide, MeshBasicNodeMaterial, SRGBColorSpace, TextureLoader, Vector3, type Material, type Node } from 'three/webgpu';
import {
  abs,
  asin,
  atan,
  cameraPosition,
  clamp,
  dot,
  exp,
  float,
  fract,
  hash,
  max,
  mix,
  mx_noise_float,
  normalize,
  positionWorld,
  pow,
  reflect,
  select,
  smoothstep,
  step,
  texture,
  time,
  uniform,
  vec2,
  vec3,
} from 'three/tsl';
import { assetUrl } from '../loading/assetUrl';

/**
 * The view from the mansion's windows (§8 rendering), drawn per pixel from the viewing direction, so every window
 * shows its own part of the night and the view shifts correctly as the guest walks past. glTF can't carry this:
 * zones author a backdrop with a `MAT_*_SeaView` material outside each sea wall, and glbZone swaps it for this one.
 *
 * - Sky: a real night-sky photograph (Poly Haven qwantani_moonrise_puresky, CC0), tone-mapped by
 *   `npm run make-night-sky` into the sky hemisphere (rows horizon → zenith, columns azimuth from north), plus the
 *   moon's glow.
 * - Sea: the Mediterranean far below the cliff: animated swell (noise normals) reflecting the sky with Fresnel, a
 *   glittering moon path, haze to the horizon.
 * - Coast: a dark headland along the eastern horizon, pricked with the warm lights of towns and villas.
 *
 * Frame: world Y up; north (the sea) is world −Z; azimuth grows towards east (+X).
 */
const TAU = Math.PI * 2;
const CLIFF = 28;                       // the terrace stands this far above the sea (m)
const SKY = 0.2;                        // the photograph's level against the lamplit rooms' exposure

let shared: MeshBasicNodeMaterial | null = null;
const moonDir = uniform(new Vector3(0.3, 0.24, -0.92).normalize());

export function nightViewMaterial(): Material {
  if (shared) return shared;
  const sky = new TextureLoader().load(assetUrl('/assets/env/T_NightSky.jpg'));
  sky.colorSpace = SRGBColorSpace;
  fetch(assetUrl('/assets/env/T_NightSky.json')).then((r) => r.json()).then((j: { moon: { az: number; el: number } }) => {
    const { az, el } = j.moon;
    moonDir.value.set(Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el)).normalize();
  }).catch(() => {});

  // sky radiance in direction d (d.y ≥ 0): the photograph, darkened to a night that sits behind lamplit rooms
  const skyAt = (d: Node<'vec3'>) => {
    const az = atan(d.x, d.z.negate());
    const u = fract(az.div(TAU).add(0.5));                           // north at the centre; the wrap is due south
    const v = clamp(asin(clamp(d.y, 0.0, 1.0)).div(Math.PI / 2), 0.004, 0.996);
    return vec3(texture(sky, vec2(u, v)).level(float(0)).rgb).mul(SKY);     // fixed LOD: no mip seam where u wraps
  };

  const dir = normalize(positionWorld.sub(cameraPosition));
  const up = dir.y;

  // ---- sky with the moon's glow and the coast along the eastern horizon
  const az = atan(dir.x, dir.z.negate());
  const el = asin(clamp(up, -1.0, 1.0));
  const md = max(dot(dir, moonDir), 0.0);
  const skyCol = skyAt(dir).add(vec3(1.0, 0.95, 0.85).mul(pow(md, 1800.0).mul(3.0).add(pow(md, 60.0).mul(0.05))));
  // headland: east of north (az 0.55 … 1.7 rad), a ridge 0.4–2.4° high
  const onCoast = smoothstep(0.5, 0.62, az).mul(float(1.0).sub(smoothstep(1.6, 1.75, az)));
  const ridge = float(0.007).add(mx_noise_float(vec3(az.mul(9.0), 0.0, 3.1)).add(0.6).mul(0.018)).mul(onCoast);
  const land = step(el, ridge).mul(onCoast);
  const cell = vec2(az.mul(2400.0), el.mul(2400.0)).floor();
  const lamp = step(0.9965, hash(cell.x.add(cell.y.mul(1.7)))).mul(step(el, ridge.mul(0.6)));
  const landCol = vec3(0.004, 0.005, 0.008).add(vec3(1.0, 0.72, 0.4).mul(lamp).mul(1.4));
  const skyOrLand = mix(skyCol, landCol, land);

  // ---- the sea below the cliff
  const t = float(CLIFF).add(cameraPosition.y).div(max(up.negate(), 0.0004));
  const p = cameraPosition.xz.add(dir.xz.mul(t));
  const fade = float(1.0).div(float(1.0).add(t.mul(0.012)));               // far swell flattens (no shimmer)
  // swell: a sum of directional waves (analytic slope, cheap per pixel), fading with distance
  const waves: [number, number, number, number][] = [[0.11, 0.07, 0.8, 0.5], [-0.06, 0.13, 1.1, 0.35], [0.21, -0.17, 1.7, 0.18], [-0.31, -0.23, 2.3, 0.1]];
  let gx: Node<'float'> = float(0.0);
  let gz: Node<'float'> = float(0.0);
  for (const [kx, kz, w, a] of waves) {
    const c = p.x.mul(kx).add(p.y.mul(kz)).add(time.mul(w)).cos().mul(a);
    gx = gx.add(c.mul(kx));
    gz = gz.add(c.mul(kz));
  }
  const nx = gx.mul(fade).mul(8.0);
  const nz = gz.mul(fade).mul(8.0);
  const n = normalize(vec3(nx.mul(0.35), 1.0, nz.mul(0.35)));
  const r0 = reflect(dir, n);
  const r = normalize(vec3(r0.x, abs(r0.y), r0.z));
  const cosI = max(dot(dir.negate(), n), 0.0);
  const fresnel = float(0.02).add(float(0.98).mul(pow(float(1.0).sub(cosI), 5.0)));
  const glitter = pow(max(dot(r, moonDir), 0.0), 380.0).mul(5.0).add(pow(max(dot(r, moonDir), 0.0), 40.0).mul(0.08));
  const deep = vec3(0.002, 0.006, 0.011);
  const horizonCol = skyAt(normalize(vec3(dir.x, 0.004, dir.z)));
  const seaCol = mix(deep, skyAt(r), fresnel).add(vec3(1.0, 0.93, 0.8).mul(glitter).mul(fade.add(0.25)));
  const haze = float(1.0).sub(exp(t.mul(-0.0011)));
  const seaFinal = mix(seaCol, horizonCol, haze.mul(0.85));

  const mat = new MeshBasicNodeMaterial({ name: 'MAT_NightView' });
  mat.colorNode = select(up.greaterThan(0.0), skyOrLand, seaFinal);
  mat.side = DoubleSide;           // a backdrop: drawn whichever way the exporter wound it
  mat.toneMapped = true;
  mat.fog = false;
  shared = mat;
  return mat;
}

/** True for the window-view materials authored in Blender (`MAT_<Zone>_SeaView`). */
export const isNightView = (name: string): boolean => /_SeaView$/.test(name);
