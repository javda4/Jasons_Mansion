// Fetches CC0 PBR source textures from Poly Haven into blender/textures_src (Layer 1 source),
// then publishes web copies + a texture manifest into public/assets/textures (Layer 2 output).
//
// Phase 1 ships JPG; the KTX2 (ETC1S/UASTC) step is added with the Phase 2 asset pipeline
// (see docs/architecture.md §G). Re-run any time: files already present are skipped.
//
//   npm run fetch-textures

import { mkdir, writeFile, access, copyFile, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';
import { execFileSync } from 'node:child_process';

const ROOT = path.resolve(import.meta.dirname, '..');
const SRC_DIR = path.join(ROOT, 'blender/textures_src/polyhaven');
const OUT_DIR = path.join(ROOT, 'public/assets/textures');

// id -> { res, maps }. Map keys are Poly Haven file keys; values are our T_ map suffixes.
const MAPS = { Diffuse: 'BaseColor', nor_gl: 'Normal', arm: 'ORM' };
const TEXTURES = {
  marble_01: { res: '2k', material: 'Marble_Calacatta' },
  black_walnut_veneer_01: { res: '2k', material: 'Wood_WalnutPolished' },
  quatrefoil_jacquard_fabric: { res: '1k', material: 'Fabric_Damask' },
  brown_leather: { res: '1k', material: 'Leather_Oxblood' },
  caban: { res: '1k', material: 'Fabric_Felt' },
  velour_velvet: { res: '1k', material: 'Fabric_Velvet' },
  plastered_wall: { res: '1k', material: 'Plaster_Ceiling' },
  herringbone_parquet: { res: '2k', material: 'Wood_Parquet' },   // Mansion: point de Hongrie in the salons (3.4 m tile)
};
// ambientCG (CC0) sets: zip of separate maps; roughness/metalness are packed into our ORM layout
const AMBIENTCG = {
  Metal007: { res: '1K', material: 'Metal_WornGold' },
};

const exists = (p) => access(p).then(() => true, () => false);
const pot = (n) => 2 ** Math.round(Math.log2(n));

/** GPU/KTX2 rule (§6): power-of-two sizes. A few scans ship at e.g. 1024×1037 — resample them. */
async function ensurePowerOfTwo(file) {
  const { width, height } = await sharp(file).metadata();
  if (width === pot(width) && height === pot(height)) return;
  const buf = await sharp(file).resize(pot(width), pot(height), { fit: 'fill', kernel: 'lanczos3' }).jpeg({ quality: 92 }).toBuffer();
  await writeFile(file, buf);
  console.log(`  ⤢ ${path.basename(file)} ${width}×${height} → ${pot(width)}×${pot(height)}`);
}

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

const manifest = { generated: new Date().toISOString(), source: 'polyhaven.com (CC0)', materials: {} };
// keep sets produced by other scripts (make-carpets `met:<id>`, make-game-textures `generated:…`)
try {
  const prev = JSON.parse(await readFile(path.join(OUT_DIR, 'textures.json'), 'utf8'));
  for (const [k, v] of Object.entries(prev.materials ?? {})) if (/^(met|generated):/.test(String(v.source ?? ''))) manifest.materials[k] = v;
} catch { /* first run */ }

await mkdir(SRC_DIR, { recursive: true });
await mkdir(OUT_DIR, { recursive: true });

for (const [id, { res, material }] of Object.entries(TEXTURES)) {
  const files = await fetchJson(`https://api.polyhaven.com/files/${id}`);
  const entry = { polyhavenId: id, resolution: res, maps: {} };

  for (const [phKey, suffix] of Object.entries(MAPS)) {
    const file = files[phKey]?.[res]?.jpg;
    if (!file) { console.warn(`  ! ${id}: no ${phKey} @ ${res}`); continue; }

    const name = `T_${material}_${suffix}.jpg`;
    const srcPath = path.join(SRC_DIR, name);
    if (!(await exists(srcPath))) {
      const r = await fetch(file.url);
      if (!r.ok) throw new Error(`${file.url} -> ${r.status}`);
      await writeFile(srcPath, Buffer.from(await r.arrayBuffer()));
      console.log(`  ↓ ${name}`);
    }
    await ensurePowerOfTwo(srcPath);

    const outPath = path.join(OUT_DIR, name);
    await copyFile(srcPath, outPath);
    const buf = await readFile(outPath);
    entry.maps[suffix] = {
      url: `/assets/textures/${name}`,
      bytes: (await stat(outPath)).size,
      hash: createHash('sha256').update(buf).digest('hex').slice(0, 16),
    };
  }
  manifest.materials[material] = entry;
}

for (const [id, { res, material }] of Object.entries(AMBIENTCG)) {
  const dir = path.join(SRC_DIR, '..', 'ambientcg', id);
  await mkdir(dir, { recursive: true });
  const zip = path.join(dir, `${id}_${res}-JPG.zip`);
  if (!(await exists(zip))) {
    const r = await fetch(`https://ambientcg.com/get?file=${id}_${res}-JPG.zip`);
    if (!r.ok) throw new Error(`ambientCG ${id} -> ${r.status}`);
    await writeFile(zip, Buffer.from(await r.arrayBuffer()));
    execFileSync('unzip', ['-o', '-q', zip, '-d', dir]);
    console.log(`  ↓ ${id} (ambientCG)`);
  }
  const map = (suffix) => path.join(dir, `${id}_${res}-JPG_${suffix}.jpg`);
  const out = { BaseColor: `T_${material}_BaseColor.jpg`, Normal: `T_${material}_Normal.jpg`, ORM: `T_${material}_ORM.jpg` };
  await copyFile(map('Color'), path.join(SRC_DIR, out.BaseColor));
  await copyFile(map('NormalGL'), path.join(SRC_DIR, out.Normal));
  // ORM: R = occlusion (none → white), G = roughness, B = metalness
  const size = (await sharp(map('Roughness')).metadata()).width;
  const [rough, metal] = await Promise.all([map('Roughness'), map('Metalness')].map((f) => sharp(f).greyscale().resize(size, size).raw().toBuffer()));
  const orm = Buffer.alloc(size * size * 3);
  for (let i = 0; i < size * size; i++) { orm[i * 3] = 255; orm[i * 3 + 1] = rough[i]; orm[i * 3 + 2] = metal[i]; }
  await sharp(orm, { raw: { width: size, height: size, channels: 3 } }).jpeg({ quality: 92 }).toFile(path.join(SRC_DIR, out.ORM));
  const entry = { source: `ambientcg:${id}`, resolution: res, maps: {} };
  for (const [kind, name] of Object.entries(out)) {
    await ensurePowerOfTwo(path.join(SRC_DIR, name));
    await copyFile(path.join(SRC_DIR, name), path.join(OUT_DIR, name));
    const buf = await readFile(path.join(OUT_DIR, name));
    entry.maps[kind] = { url: `/assets/textures/${name}`, bytes: buf.byteLength, hash: createHash('sha256').update(buf).digest('hex').slice(0, 16) };
  }
  manifest.materials[material] = entry;
}

await writeFile(path.join(OUT_DIR, 'textures.json'), JSON.stringify(manifest, null, 2));
console.log(`Wrote ${Object.keys(manifest.materials).length} materials -> public/assets/textures/textures.json`);
