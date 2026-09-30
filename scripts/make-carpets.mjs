// Builds photoreal carpet textures from public-domain photographs of real antique carpets
// (The Metropolitan Museum of Art Open Access, CC0):
//
//   whole rugs (runners, area rugs) → blender/textures_src/carpets/T_<Name>_{BaseColor,Normal,ORM}.png
//                                     (zone-unique materials; the asset build compresses them to KTX2)
//   a seamless wall-to-wall tile    → the shared library texture set `Carpet_Gul`
//                                     (blender/textures_src/polyhaven/ + public/assets/textures/ + textures.json)
//
//   npm run make-carpets
//
// The photo supplies the design and colour; the pile (fibre normal + roughness) is synthesised, since a
// museum photograph is lit flat on purpose.

import { mkdir, writeFile, readFile, access, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import sharp from 'sharp';

const ROOT = path.resolve(import.meta.dirname, '..');
const SRC = path.join(ROOT, 'blender/textures_src/carpets');
const LIB = path.join(ROOT, 'blender/textures_src/polyhaven');
const WEB = path.join(ROOT, 'public/assets/textures');
const API = 'https://collectionapi.metmuseum.org/public/collection/v1';

/** Whole rugs keep their borders; `size` is [across, along] in texels (power of two). */
const RUGS = [
  { name: 'Runner_Mamluk', met: 452100, size: [512, 2048], grade: { brightness: 0.92, saturation: 1.08 } },
  { name: 'Runner_PalmTrees', met: 446999, size: [512, 2048], grade: { brightness: 0.9, saturation: 1.05 } },
  { name: 'Rug_Kazak', met: 452581, size: [1024, 1024], grade: { brightness: 0.9, saturation: 1.0 }, inset: [0.03, 0.075] }, // trim the fringe (modelled instead)
];
/** Repeating field carpets: a whole number of pattern periods, made seamless. */
const TILES = [
  { name: 'Carpet_Gul', met: 452598, periods: [2, 4], size: 1024, grade: { brightness: 0.78, saturation: 1.05 } },
];

const exists = (p) => access(p).then(() => true, () => false);

async function metImage(id) {
  const file = path.join(SRC, 'originals', `met_${id}.jpg`);
  if (!(await exists(file))) {
    const o = await (await fetch(`${API}/objects/${id}`)).json();
    if (!o.isPublicDomain) throw new Error(`Met ${id} is not public domain`);
    const r = await fetch(o.primaryImage);
    if (!r.ok) throw new Error(`Met ${id} image -> ${r.status}`);
    await mkdir(path.dirname(file), { recursive: true });
    await writeFile(file, Buffer.from(await r.arrayBuffer()));
    console.log(`  ↓ Met ${id} — ${o.title} (${o.objectDate})`);
  }
  return file;
}

/** Bounding box of the carpet against the museum's plain backdrop (colour distance from the frame median). */
async function carpetBounds(file, inset = [0.012, 0.008]) {
  const { data, info } = await sharp(file).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const { width: w, height: h } = info;
  const px = (x, y) => { const i = (y * w + x) * 3; return [data[i], data[i + 1], data[i + 2]]; };
  const frame = [];
  for (let x = 0; x < w; x += 7) frame.push(px(x, 2), px(x, h - 3));
  for (let y = 0; y < h; y += 7) frame.push(px(2, y), px(w - 3, y));
  const bg = [0, 1, 2].map((c) => frame.map((p) => p[c]).sort((a, b) => a - b)[frame.length >> 1]);
  const isCarpet = (x, y) => { const p = px(x, y); return Math.hypot(p[0] - bg[0], p[1] - bg[1], p[2] - bg[2]) > 38; };
  const colFrac = (x) => { let n = 0, t = 0; for (let y = 0; y < h; y += 3) { t++; if (isCarpet(x, y)) n++; } return n / t; };
  const rowFrac = (y) => { let n = 0, t = 0; for (let x = 0; x < w; x += 3) { t++; if (isCarpet(x, y)) n++; } return n / t; };
  let x0 = 0, x1 = w - 1, y0 = 0, y1 = h - 1;
  while (x0 < w && colFrac(x0) < 0.6) x0++;
  while (x1 > 0 && colFrac(x1) < 0.6) x1--;
  while (y0 < h && rowFrac(y0) < 0.6) y0++;
  while (y1 > 0 && rowFrac(y1) < 0.6) y1--;
  // inset past the ragged selvedge / fringe so no backdrop survives
  const ix = Math.round((x1 - x0) * inset[0]), iy = Math.round((y1 - y0) * inset[1]);
  return { left: x0 + ix, top: y0 + iy, width: x1 - x0 - 2 * ix, height: y1 - y0 - 2 * iy };
}

// ---------------------------------------------------------------- synthesised pile
function hash2(x, y, s) { let h = (x * 374761393 + y * 668265263 + s * 1442695041) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967295; }
function valueNoise(w, h, cell, seed, wrap = true) {
  const out = new Float32Array(w * h), cw = Math.max(1, Math.round(w / cell)), ch = Math.max(1, Math.round(h / cell));
  const g = (i, j) => hash2(wrap ? ((i % cw) + cw) % cw : i, wrap ? ((j % ch) + ch) % ch : j, seed);
  for (let y = 0; y < h; y++) {
    const fy = (y / h) * ch, j = Math.floor(fy), ty = fy - j, sy = ty * ty * (3 - 2 * ty);
    for (let x = 0; x < w; x++) {
      const fx = (x / w) * cw, i = Math.floor(fx), tx = fx - i, sx = tx * tx * (3 - 2 * tx);
      const a = g(i, j) + (g(i + 1, j) - g(i, j)) * sx, b = g(i, j + 1) + (g(i + 1, j + 1) - g(i, j + 1)) * sx;
      out[y * w + x] = a + (b - a) * sy;
    }
  }
  return out;
}

/** Height field for knotted wool pile: per-knot jitter, tufts, soft wear, plus the design's own relief. */
function pileHeight(lum, w, h, seed) {
  const tufts = valueNoise(w, h, 5, seed), wear = valueNoise(w, h, 90, seed + 1), clumps = valueNoise(w, h, 22, seed + 2);
  const out = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) {
    const x = i % w, y = (i / w) | 0;
    const knot = hash2(x, y, seed + 3);
    // darker (denser-dyed) knots sit a hair proud, as abrash and wear leave them
    out[i] = 0.34 * knot + 0.3 * tufts[i] + 0.16 * clumps[i] + 0.12 * wear[i] + 0.08 * (1 - lum[i]);
  }
  return out;
}
function normalFromHeight(hf, w, h, strength) {
  const out = Buffer.alloc(w * h * 3);
  const at = (x, y) => hf[((y + h) % h) * w + ((x + w) % w)];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const dx = (at(x + 1, y) - at(x - 1, y)) * strength, dy = (at(x, y + 1) - at(x, y - 1)) * strength;
    const len = Math.hypot(dx, dy, 1), i = (y * w + x) * 3;
    out[i] = Math.round((-dx / len * 0.5 + 0.5) * 255);
    out[i + 1] = Math.round((dy / len * 0.5 + 0.5) * 255); // OpenGL (+Y) convention, as glTF expects
    out[i + 2] = Math.round((1 / len * 0.5 + 0.5) * 255);
  }
  return out;
}
function ormFromHeight(hf, w, h) {
  const out = Buffer.alloc(w * h * 3);
  for (let i = 0; i < w * h; i++) {
    out[i * 3] = Math.round(255 * (0.78 + 0.22 * hf[i]));          // AO: crevices between tufts
    out[i * 3 + 1] = Math.round(255 * (0.97 - 0.12 * hf[i]));      // roughness: wool, a touch of lustre on the tips
    out[i * 3 + 2] = 0;                                             // metalness
  }
  return out;
}

async function writeSet(name, rgb, w, h, seed, strength, dirs) {
  const lum = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) lum[i] = (0.2126 * rgb[i * 3] + 0.7152 * rgb[i * 3 + 1] + 0.0722 * rgb[i * 3 + 2]) / 255;
  const hf = pileHeight(lum, w, h, seed);
  const maps = {
    BaseColor: sharp(rgb, { raw: { width: w, height: h, channels: 3 } }),
    Normal: sharp(normalFromHeight(hf, w, h, strength), { raw: { width: w, height: h, channels: 3 } }),
    ORM: sharp(ormFromHeight(hf, w, h), { raw: { width: w, height: h, channels: 3 } }),
  };
  const files = {};
  for (const [kind, img] of Object.entries(maps)) {
    for (const d of dirs) {
      const f = path.join(d.dir, `T_${name}_${kind}.${d.ext}`);
      await (d.ext === 'jpg' ? img.clone().jpeg({ quality: 90 }) : img.clone().png()).toFile(f);
      files[kind] ??= [];
      files[kind].push(f);
    }
  }
  return files;
}

async function graded(file, bounds, grade) {
  return sharp(file).extract(bounds).modulate({ brightness: grade.brightness, saturation: grade.saturation });
}

// ---------------------------------------------------------------- whole rugs
await mkdir(SRC, { recursive: true });
const rugMeta = {};
for (const rug of RUGS) {
  const file = await metImage(rug.met);
  const b = await carpetBounds(file, rug.inset);
  const [w, h] = rug.size;
  const portrait = b.height >= b.width; // store rugs "along" = texture V
  let img = await graded(file, b, rug.grade);
  if (!portrait) img = img.rotate(90);
  const rgb = await img.resize(w, h, { fit: 'fill', kernel: 'lanczos3' }).removeAlpha().raw().toBuffer();
  await writeSet(rug.name, rgb, w, h, rug.met, 5.0, [{ dir: SRC, ext: 'png' }]);
  rugMeta[rug.name] = { met: rug.met, aspect: +((portrait ? b.height / b.width : b.width / b.height)).toFixed(4) };
  console.log(`  ✓ ${rug.name}: Met ${rug.met}, carpet ${b.width}×${b.height}px → ${w}×${h}, length/width ${rugMeta[rug.name].aspect}`);
}

// ---------------------------------------------------------------- seamless field tiles
function period(profile, lo, hi) {
  const n = profile.length, mean = profile.reduce((a, b) => a + b, 0) / n;
  const p = profile.map((v) => v - mean);
  let best = lo, bestR = -Infinity;
  for (let k = lo; k <= hi; k++) {
    let r = 0;
    for (let i = 0; i + k < n; i++) r += p[i] * p[i + k];
    r /= n - k;
    if (r > bestR) { bestR = r; best = k; }
  }
  return best;
}

const texturesJson = path.join(WEB, 'textures.json');
const manifest = JSON.parse(await readFile(texturesJson, 'utf8'));
for (const t of TILES) {
  const file = await metImage(t.met);
  const b = await carpetBounds(file);
  // analyse the field only (skip the borders)
  const field = { left: b.left + Math.round(b.width * 0.12), top: b.top + Math.round(b.height * 0.1), width: Math.round(b.width * 0.76), height: Math.round(b.height * 0.8) };
  const { data, info } = await sharp(file).extract(field).greyscale().raw().toBuffer({ resolveWithObject: true });
  const cols = new Array(info.width).fill(0), rows = new Array(info.height).fill(0);
  for (let y = 0; y < info.height; y++) for (let x = 0; x < info.width; x++) { const v = data[y * info.width + x]; cols[x] += v; rows[y] += v; }
  const px = period(cols, Math.round(info.width * 0.12), Math.round(info.width * 0.45));
  const py = period(rows, Math.round(info.height * 0.05), Math.round(info.height * 0.3));
  const tw = px * t.periods[0], th = py * t.periods[1], m = Math.round(Math.min(tw, th) * 0.12);
  const src = { left: field.left + Math.round(px * 0.3), top: field.top + Math.round(py * 0.3), width: tw + m, height: th + m };
  const { data: s, info: si } = await (await graded(file, src, t.grade)).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  // cross-fade the margin onto the opposite edge: the tile's left/top edge continues its right/bottom edge
  const out = Buffer.alloc(tw * th * 3);
  const get = (x, y, c) => s[(y * si.width + x) * 3 + c];
  for (let y = 0; y < th; y++) for (let x = 0; x < tw; x++) {
    const wx = x < m ? x / m : 1, wy = y < m ? y / m : 1;
    for (let c = 0; c < 3; c++) {
      // only sample past the tile where the fade actually needs it (the margin is m wide)
      const a = get(x, y, c), bx = wx < 1 ? get(x + tw, y, c) : a;
      const top = a * wx + bx * (1 - wx);
      let bot = top;
      if (wy < 1) { const by = get(x, y + th, c), bxy = wx < 1 ? get(x + tw, y + th, c) : by; bot = by * wx + bxy * (1 - wx); }
      out[(y * tw + x) * 3 + c] = Math.round(top * wy + bot * (1 - wy));
    }
  }
  const rgb = await sharp(out, { raw: { width: tw, height: th, channels: 3 } }).resize(t.size, t.size, { fit: 'fill', kernel: 'lanczos3' }).raw().toBuffer();
  const files = await writeSet(t.name, rgb, t.size, t.size, t.met, 4.0, [{ dir: LIB, ext: 'jpg' }, { dir: WEB, ext: 'jpg' }]);
  // physical tile size from the carpet's catalogue dimensions (metres), so the design keeps its real scale
  const o = await (await fetch(`${API}/objects/${t.met}`)).json();
  const cm = [...(o.dimensions ?? '').matchAll(/\(([\d.]+) cm\)/g)].map((mm) => +mm[1] / 100);
  const carpetW = Math.min(...cm.slice(0, 2)), mPerPx = carpetW / b.width;
  const tile = [+(tw * mPerPx).toFixed(3), +(th * mPerPx).toFixed(3)];
  const entry = { source: `met:${t.met}`, tileMetres: tile, maps: {} };
  for (const [kind, fl] of Object.entries(files)) {
    const web = fl.find((f) => f.startsWith(WEB));
    const buf = await readFile(web);
    entry.maps[kind] = { url: `/assets/textures/${path.basename(web)}`, bytes: (await stat(web)).size, hash: createHash('sha256').update(buf).digest('hex').slice(0, 16) };
  }
  manifest.materials[t.name] = entry;
  console.log(`  ✓ ${t.name}: Met ${t.met}, period ${px}×${py}px, tile ${tw}×${th}px = ${tile[0]}×${tile[1]} m`);
}
await writeFile(texturesJson, JSON.stringify(manifest, null, 2));
await writeFile(path.join(SRC, 'carpets.json'), JSON.stringify({ source: 'The Metropolitan Museum of Art — Open Access (CC0)', rugs: rugMeta }, null, 2));
console.log('Wrote carpets → blender/textures_src/carpets/, Carpet_Gul → textures.json');
