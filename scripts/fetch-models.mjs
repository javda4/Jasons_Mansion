// Downloads CC0 photoscanned furniture / decor from Poly Haven (glTF, 1k textures) into the Blender
// props library: blender/props/polyhaven/<id>/. Blender authoring scripts import them as linked-library
// prototypes (kit.import_prop), so every placement exports as a GPU instance. Re-run any time: cached.
//
//   npm run fetch-models

import { mkdir, writeFile, access } from 'node:fs/promises';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
const OUT = path.join(ROOT, 'blender/props/polyhaven');
const UA = { 'User-Agent': 'riviera-casino-asset-pipeline' };

// id → resolution. Chosen for a 1920s Riviera salon (see docs/asset-guidelines.md).
export const MODELS = {
  sofa_02: '1k',                       // tufted leather Chesterfield
  Sofa_01: '1k',                       // Louis XV sofa
  ArmChair_01: '1k',                   // bergère (fabric recoloured to red velvet at authoring time)
  GreenChair_01: '1k',                 // Louis XV fauteuil
  gothic_coffee_table: '1k',
  ClassicConsole_01: '1k',             // carved console
  side_table_tall_01: '1k',            // pedestal stand
  ornate_mirror_01: '1k',
  vintage_grandfather_clock_01: '1k',
  mantel_clock_01: '1k',
  marble_bust_01: '1k',
  horse_statue_01: '1k',
  antique_ceramic_vase_01: '1k',       // blue-and-white chinoiserie
  brass_candleholders: '1k',
  vintage_oil_lamp: '1k',
  potted_plant_02: '1k',
};

const exists = (p) => access(p).then(() => true, () => false);

async function get(url) {
  for (let i = 0; i < 3; i++) {
    const r = await fetch(url, { headers: UA });
    if (r.ok) return r;
    await new Promise((res) => setTimeout(res, 800 * (i + 1)));
  }
  throw new Error(`${url} failed`);
}

const manifest = { source: 'polyhaven.com (CC0)', models: {} };
for (const [id, res] of Object.entries(MODELS)) {
  const dir = path.join(OUT, id);
  const info = await (await get(`https://api.polyhaven.com/info/${id}`)).json();
  const files = await (await get(`https://api.polyhaven.com/files/${id}`)).json();
  const g = files.gltf?.[res]?.gltf;
  if (!g) throw new Error(`${id}: no glTF at ${res}`);
  const main = path.join(dir, `${id}.gltf`);
  if (!(await exists(main))) {
    await mkdir(dir, { recursive: true });
    await writeFile(main, Buffer.from(await (await get(g.url)).arrayBuffer()));
    for (const [rel, f] of Object.entries(g.include ?? {})) {
      const p = path.join(dir, rel);
      await mkdir(path.dirname(p), { recursive: true });
      await writeFile(p, Buffer.from(await (await get(f.url)).arrayBuffer()));
    }
    console.log(`  ↓ ${id} (${res})`);
  }
  manifest.models[id] = { name: info.name, resolution: res, file: path.relative(ROOT, main), authors: Object.keys(info.authors ?? {}), dimensions: info.dimensions };
}
await writeFile(path.join(OUT, 'models.json'), JSON.stringify(manifest, null, 2));
console.log(`Wrote ${Object.keys(manifest.models).length} models → blender/props/polyhaven/models.json`);
