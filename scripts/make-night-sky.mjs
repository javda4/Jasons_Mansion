// The night sky seen from the mansion's windows: Poly Haven qwantani_moonrise_puresky (CC0) → a tone-mapped sky
// hemisphere + moon direction for the runtime window-view material (src/render/nightView.ts).
//
//   npm run make-night-sky
import { execFileSync } from 'node:child_process';
import { access, copyFile, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

const ROOT = path.resolve(import.meta.dirname, '..');
const SRC = path.join(ROOT, 'blender/textures_src/env');
const OUT = path.join(ROOT, 'public/assets/env');
const URL = 'https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/4k/qwantani_moonrise_puresky_4k.hdr';
const hdr = path.join(SRC, 'qwantani_moonrise_puresky_4k.hdr');

await mkdir(SRC, { recursive: true });
await mkdir(OUT, { recursive: true });
if (!(await access(hdr).then(() => true, () => false))) {
  const r = await fetch(URL, { headers: { 'User-Agent': 'riviera-mansion-asset-pipeline' } });
  if (!r.ok) throw new Error(`${URL}: ${r.status}`);
  await writeFile(hdr, Buffer.from(await r.arrayBuffer()));
  console.log('  ↓ qwantani_moonrise_puresky_4k.hdr');
}
execFileSync(process.env.BLENDER ?? 'blender', ['-b', '--factory-startup', '--python', path.join(ROOT, 'blender/tools/make_night_sky.py'), '--', hdr, SRC], { stdio: ['ignore', 'pipe', 'inherit'] })
  .toString().split('\n').filter((l) => l.includes('[night-sky]')).forEach((l) => console.log(l));
await sharp(path.join(SRC, 'T_NightSky.png')).jpeg({ quality: 88, mozjpeg: true }).toFile(path.join(OUT, 'T_NightSky.jpg'));
await copyFile(path.join(SRC, 'T_NightSky.json'), path.join(OUT, 'T_NightSky.json'));
console.log('Wrote public/assets/env/T_NightSky.jpg + .json');
