// Bake a zone's lightmap with Cycles (GPU), producing <zone>_baked.blend + T_<Zone>_Lightmap.png/json.
//
//   npm run bake -- lobby [size=2048] [samples=256]
//
// Baking is slow and its outputs are source artefacts, so it is a separate step from build:assets.
import { execFileSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
const [id, size = '2048', samples = '256'] = process.argv.slice(2);
const registry = JSON.parse(await readFile(path.join(ROOT, 'blender/zones.json'), 'utf8')).zones;
const z = registry[id];
if (!z?.lightmap || !z.source) throw new Error(`zone "${id}" has no source/lightmap entry in blender/zones.json`);
execFileSync(process.env.BLENDER ?? 'blender', ['-b', path.join(ROOT, 'blender', z.source), '--python', path.join(ROOT, 'blender/tools/bake_lightmap.py'), '--', id, z.zone, size, samples], { stdio: 'inherit' });
