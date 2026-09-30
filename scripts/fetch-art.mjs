// Fetches public-domain paintings (CC0) from The Metropolitan Museum of Art Open Access API for the
// mansion's picture frames. Sources → blender/textures_src/art/, web copies + art.json → public/assets/art/.
//
//   npm run fetch-art
//
// Each image is resampled to 1024×1024 (power-of-two for KTX2) and its original aspect ratio is
// recorded; canvases are sized to that aspect, so the stretch is undone on screen.

import { mkdir, writeFile, access } from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

const ROOT = path.resolve(import.meta.dirname, '..');
const SRC = path.join(ROOT, 'blender/textures_src/art');
const OUT = path.join(ROOT, 'public/assets/art');
const API = 'https://collectionapi.metmuseum.org/public/collection/v1';

// Riviera / Belle Époque mood: coasts, harbours by night, portraits, flowers
const QUERIES = [
  ['Antibes', 2], ['Menton', 1], ['Mediterranean', 2], ['Bordighera', 1], ['Cap Martin', 1],
  ['moonlight', 2], ['harbor', 1], ['portrait of a woman', 2], ['roses', 1],
];
// the mansion's era: 1840–1925 European / American easel paintings (no altarpieces)
const DEPARTMENTS = new Set(['European Paintings', 'The American Wing', 'Robert Lehman Collection']);
const inEra = (o) => o.objectBeginDate >= 1840 && o.objectBeginDate <= 1925;
const WANT = 12;

const exists = (p) => access(p).then(() => true, () => false);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const slug = (s) => s.normalize('NFKD').replace(/[^\w]+/g, '_').replace(/^_|_$/g, '').slice(0, 40);

async function json(url) {
  for (let attempt = 0; attempt < 3; attempt++) {
    const r = await fetch(url);
    if (r.ok) return r.json();
    await sleep(500 * (attempt + 1));
  }
  throw new Error(`${url} failed`);
}

await mkdir(SRC, { recursive: true });
await mkdir(OUT, { recursive: true });
const manifest = { source: 'The Metropolitan Museum of Art — Open Access (CC0)', works: [] };
const seen = new Set();

for (const [q, take] of QUERIES) {
  if (manifest.works.length >= WANT) break;
  const { objectIDs } = await json(`${API}/search?hasImages=true&isPublicDomain=true&medium=Paintings&q=${encodeURIComponent(q)}`).catch(() => ({ objectIDs: [] }));
  if (!objectIDs) continue;
  let got = 0;
  for (const id of objectIDs.slice(0, 60)) {
    if (got >= take || manifest.works.length >= WANT || seen.has(id)) continue;
    const o = await json(`${API}/objects/${id}`).catch(() => null);
    await sleep(80); // be polite to the API
    if (!o || !o.isPublicDomain || o.classification !== 'Paintings' || !o.primaryImageSmall) continue;
    if (!DEPARTMENTS.has(o.department) || !inEra(o)) continue;
    seen.add(id);
    const key = `${slug(o.artistDisplayName || 'Anon')}_${id}`;
    const srcFile = path.join(SRC, 'originals', `${key}.jpg`);
    if (!(await exists(srcFile))) {
      await mkdir(path.dirname(srcFile), { recursive: true });
      const img = await fetch(o.primaryImage || o.primaryImageSmall);
      if (!img.ok) continue;
      await writeFile(srcFile, Buffer.from(await img.arrayBuffer()));
    }
    const meta = await sharp(srcFile).metadata();
    const aspect = +(meta.width / meta.height).toFixed(4);
    if (aspect < 0.45 || aspect > 2.2) continue; // skip scrolls and panoramas
    const webName = `${key}.jpg`;
    // power-of-two working copy (Blender uses it; the web gets the same pixels)
    const potFile = path.join(SRC, `T_Art_${key}_BaseColor.jpg`);
    await sharp(srcFile).resize(1024, 1024, { fit: 'fill', kernel: 'lanczos3' }).jpeg({ quality: 88, mozjpeg: true }).toFile(potFile);
    await sharp(potFile).toFile(path.join(OUT, webName));
    manifest.works.push({
      id: key, title: o.title, artist: o.artistDisplayName || 'Unknown', date: o.objectDate, aspect,
      url: `/assets/art/${webName}`, src: path.relative(ROOT, potFile), metObjectId: id, metUrl: o.objectURL,
    });
    got++;
    console.log(`  ✓ ${o.artistDisplayName || 'Unknown'} — ${o.title} (${o.objectDate}), aspect ${aspect}`);
  }
}

await writeFile(path.join(OUT, 'art.json'), JSON.stringify(manifest, null, 2));
await writeFile(path.join(SRC, 'art.json'), JSON.stringify(manifest, null, 2)); // for the Blender authoring scripts
console.log(`Wrote ${manifest.works.length} works → public/assets/art/art.json`);

