// Layer 1 → Layer 2 asset build (CLAUDE.md §7). One command rebuilds one zone or all zones:
//
//   npm run build:assets                 # every zone in blender/zones.json
//   npm run build:assets -- vip          # one zone
//   npm run build:assets -- --skip-export  # reuse blender/exports/*.glb
//
// .blend ─▶ Blender validate+export ─▶ strip library textures ─▶ dedup/flatten/instance/weld/prune
//        ─▶ KTX2 (ETC1S colour, UASTC data) ─▶ Meshopt ─▶ glTF-Validator + contract checks
//        ─▶ public/assets/rooms/<zone>/<zone>.glb + public/assets/manifest.json

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { copyFile, mkdir, readFile, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dedup, flatten, instance, join, prune, weld } from '@gltf-transform/functions';
import { Mode, toktx } from '@gltf-transform/cli';
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer';
import { meshopt } from '@gltf-transform/functions';
import sharp from 'sharp';
import { isLibraryMaterial } from '../src/render/materialNames.ts';
import { validateZoneGlb } from './validate-assets.mjs';

const ROOT = path.resolve(import.meta.dirname, '..');

// Only plain visual geometry may be merged. Anything the runtime reads by name (COLLIDER_, TRIGGER_,
// SPAWN_, PROBE_, LIGHT_, DOOR_, INTERACT_, …), carries extras, or is GPU-instanced keeps its node.
const MERGEABLE = /^(ROOM|PROP|TABLE|CHAIR)_/;
function releaseStaticNames() {
  return (doc) => {
    for (const node of doc.getRoot().listNodes()) {
      const mesh = node.getMesh();
      if (!mesh || !MERGEABLE.test(node.getName()) || node.getExtension('EXT_mesh_gpu_instancing')) continue;
      if (Object.keys(node.getExtras()).length) continue;
      node.setName('');
      mesh.setName('');
    }
  };
}
function nameMergedNodes(zone) {
  return (doc) => {
    let i = 0;
    for (const node of doc.getRoot().listNodes()) {
      const mesh = node.getMesh();
      if (node.getName() || !mesh) continue;
      if (mesh.listPrimitives().length === 0) {
        // donor node emptied by join() — its geometry now lives in the merged node
        node.dispose();
        continue;
      }
      i++;
      const idx = i < 100 ? String(i).padStart(2, '0') : `${String(Math.floor(i / 100)).padStart(2, '0')}_${String(i % 100).padStart(2, '0')}`;
      node.setName(`ROOM_${zone}_Static_${idx}`);
      mesh.setName(node.getName());
    }
  };
}

/** Nodes the runtime reads by name must never be merged into an instance batch by instance(). */
const LOGIC = /^(COLLIDER|TRIGGER|DOOR|INTERACT|PORTAL|NAV)_/;
function unshareLogicMeshes() {
  return (doc) => {
    for (const node of doc.getRoot().listNodes()) {
      const mesh = node.getMesh();
      if (!mesh || !LOGIC.test(node.getName())) continue;
      const users = mesh.listParents().filter((p) => p.propertyType === 'Node');
      if (users.length > 1) node.setMesh(mesh.clone().setName(node.getName()));
    }
  };
}

/** instance() creates unnamed batch nodes; give them their mesh's §6 name (e.g. PROP_Vip_Crystal_01). */
function nameInstanceNodes() {
  return (doc) => {
    for (const node of doc.getRoot().listNodes()) {
      if (!node.getName() && node.getMesh()) node.setName(node.getMesh().getName());
    }
  };
}
const BLENDER = process.env.BLENDER ?? 'blender';
const OUT_DIR = path.join(ROOT, 'public/assets');
// KTX-Software lives in .tools/ktx (see docs/blender-pipeline.md); glTF-Transform shells out to `ktx`
process.env.PATH = `${path.join(ROOT, '.tools/ktx/bin')}:${process.env.PATH}`;

const args = process.argv.slice(2);
const skipExport = args.includes('--skip-export');
const only = args.filter((a) => !a.startsWith('--'));

const registry = JSON.parse(await readFile(path.join(ROOT, 'blender/zones.json'), 'utf8')).zones;
const ids = only.length ? only : Object.keys(registry);
for (const id of ids) if (!registry[id]) throw new Error(`unknown zone "${id}" (not in blender/zones.json)`);
// the master layout: every zone has an explicit world transform; rotations stay on the 90° grid (AABB colliders)
for (const [id, z] of Object.entries(registry)) {
  const t = z.transform;
  if (!t || ![t.x, t.z, t.rotY].every(Number.isFinite)) throw new Error(`zone "${id}": blender/zones.json needs transform { x, z, rotY }`);
  if (Math.abs(t.rotY / (Math.PI / 2) - Math.round(t.rotY / (Math.PI / 2))) > 1e-6) throw new Error(`zone "${id}": transform.rotY must be a multiple of π/2`);
  for (const n of z.neighbors) if (!registry[n]) console.log(`  note: ${id} lists neighbour "${n}", not built yet`);
}

await MeshoptEncoder.ready;
await MeshoptDecoder.ready;
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });

const manifestPath = path.join(OUT_DIR, 'manifest.json');
const manifest = await readFile(manifestPath, 'utf8').then(JSON.parse, () => ({ zones: {} }));
for (const id of Object.keys(manifest.zones)) {
  if (!registry[id]) { delete manifest.zones[id]; console.log(`  retired zone "${id}" dropped from the manifest`); }
  else manifest.zones[id] = { ...manifest.zones[id], title: registry[id].title, neighbors: registry[id].neighbors, transform: registry[id].transform };
}
let failed = false;

for (const id of ids) {
  const z = registry[id];
  const raw = path.join(ROOT, 'blender/exports', `${id}.glb`);
  const out = path.join(OUT_DIR, 'rooms', id, `${id}.glb`);
  const t0 = performance.now();
  console.log(`\n▶ ${id} (${z.title})`);

  // 1) Blender: validate naming/authoring rules, export raw GLB
  if (!skipExport) {
    execFileSync(BLENDER, ['-b', path.join(ROOT, 'blender', z.blend), '--python', path.join(ROOT, 'blender/tools/export_zone.py'), '--', id, z.zone, raw], { stdio: ['ignore', 'pipe', 'inherit'] })
      .toString().split('\n').filter((l) => /\[(validate|export)\]|ERROR|warning/.test(l)).forEach((l) => console.log('  ' + l.trim()));
  }
  const rawBytes = (await stat(raw)).size;

  // 2) optimise
  const doc = await io.read(raw);
  const root = doc.getRoot();
  const materialsBefore = new Set(root.listMaterials().map((m) => m.getName()));
  let stripped = 0;
  for (const mat of root.listMaterials()) {
    if (!isLibraryMaterial(mat.getName())) continue;
    // library material: the runtime substitutes the shared one by name, so ship no textures
    mat.setBaseColorTexture(null).setNormalTexture(null).setOcclusionTexture(null)
      .setMetallicRoughnessTexture(null).setEmissiveTexture(null);
    for (const ext of mat.listExtensions()) ext.dispose();
    stripped++;
  }
  // Contract-safe pruning: SPAWN_/PROBE_/AUDIO_ markers are childless empties (keepLeaves), and
  // library materials get textures at runtime so their UVs must survive (keepAttributes).
  // Transforms' own cleanup passes use default prune options, so they are disabled here.
  const safePrune = () => prune({ keepLeaves: true, keepAttributes: true, keepExtras: true });
  await doc.transform(
    safePrune(),
    dedup({ keepUniqueNames: true }),       // library materials are identified by name — never merge them
    unshareLogicMeshes(),                  // colliders/doors/triggers must keep their own nodes
    flatten({ cleanup: false }),           // world transforms baked so shared meshes can be batched
    instance({ min: 2, cleanup: false }),  // linked duplicates → EXT_mesh_gpu_instancing
    nameInstanceNodes(),
    releaseStaticNames(),
    join({ keepNamed: true, cleanup: false }), // merge static visuals per material → few draw calls
    nameMergedNodes(z.zone),
    weld({ cleanup: false }),
    safePrune(),
    // photoscanned props (Poly Haven map names): data maps at 512 — they're small on screen and UASTC is heavy
    toktx({ encoder: sharp, mode: Mode.UASTC, slots: /^(normal|occlusion|metallicRoughness)/, pattern: /(_nor_gl|_arm|_rough|_metal)/i, level: 2, rdo: true, zstd: 18, resize: [512, 512] }),
    // real carpets (make-carpets): pile detail reads at half resolution; their colour keeps full size
    toktx({ encoder: sharp, mode: Mode.UASTC, slots: /^(normal|occlusion|metallicRoughness)/, pattern: /^T_(Rug|Runner)_/, level: 2, rdo: true, zstd: 18, resize: [512, 1024] }),
    // Kraffing pack (TX_… images, 2048² throughout): data maps at 1024 — the pieces are table-sized, UASTC is heavy
    toktx({ encoder: sharp, mode: Mode.UASTC, slots: /^(normal|occlusion|metallicRoughness)/, pattern: /^TX_/, level: 2, rdo: true, zstd: 18, resize: [1024, 1024] }),
    toktx({ encoder: sharp, mode: Mode.ETC1S, slots: /^(baseColor|emissive)/, quality: 192, resize: [2048, 2048] }),
    toktx({ encoder: sharp, mode: Mode.UASTC, slots: /^(normal|occlusion|metallicRoughness)/, level: 2, rdo: true, zstd: 18, resize: [2048, 2048] }),
    meshopt({ encoder: MeshoptEncoder, level: 'medium' }),
  );
  const lost = [...materialsBefore].filter((n) => !root.listMaterials().some((m) => m.getName() === n));
  if (lost.length) { console.log(`  ERROR:   optimisation dropped materials: ${lost.join(', ')}`); failed = true; continue; }
  await mkdir(path.dirname(out), { recursive: true });
  await io.write(out, doc);

  // 3) validate (fails the build on errors)
  const { errors, warnings, stats } = await validateZoneGlb(out, { zone: z.zone, lightmapped: !!z.lightmap });
  warnings.forEach((w) => console.log(`  warning: ${w}`));
  errors.forEach((e) => console.log(`  ERROR:   ${e}`));
  if (errors.length) { failed = true; continue; }

  // 4) baked lightmap → KTX2 (UASTC keeps smooth gradients; sRGB transfer; mipmapped)
  let lightmap;
  if (z.lightmap) {
    const src = path.join(ROOT, 'blender', `${z.lightmap}.png`);
    const meta = JSON.parse(await readFile(path.join(ROOT, 'blender', `${z.lightmap}.json`), 'utf8'));
    const lmOut = path.join(path.dirname(out), `${id}_lightmap.ktx2`);
    execFileSync('ktx', ['create', '--format', 'R8G8B8_SRGB', '--encode', 'uastc', '--uastc-quality', '2', '--uastc-rdo',
      '--zstd', '18', '--generate-mipmap', src, lmOut], { stdio: 'inherit' });
    const lmBytes = await readFile(lmOut);
    lightmap = {
      url: `/assets/rooms/${id}/${id}_lightmap.ktx2`, bytes: lmBytes.byteLength,
      hash: createHash('sha256').update(lmBytes).digest('hex').slice(0, 16), intensity: meta.intensity,
    };
    console.log(`  ✓ lightmap ${meta.size}² → ${(lmBytes.byteLength / 1024).toFixed(0)} KiB KTX2 (intensity ${meta.intensity.toFixed(3)})`);
  }

  // 5) manifest entry (generated — sizes and hashes are never hand-maintained)
  const bytes = await readFile(out);
  manifest.zones[id] = {
    title: z.title,
    asset: `/assets/rooms/${id}/${id}.glb`,
    bytes: bytes.byteLength,
    hash: createHash('sha256').update(bytes).digest('hex').slice(0, 16),
    preload: !!z.preload,
    ...(z.always ? { always: true } : {}),
    priority: z.priority ?? 2,
    neighbors: z.neighbors,
    transform: z.transform,
    dependencies: ['textures/library'],
    ...(lightmap ? { lightmap } : {}),
    stats: { triangles: stats.triangles, nodes: stats.nodes, materials: stats.materials, textureBytes: stats.textureBytes },
  };
  const kb = (n) => `${(n / 1024).toFixed(0)} KiB`;
  console.log(`  ✓ ${kb(rawBytes)} → ${kb(bytes.byteLength)} · ${stats.triangles.toLocaleString()} tris · ${stripped} library materials stripped · ${((performance.now() - t0) / 1000).toFixed(1)} s`);
}

manifest.generated = new Date().toISOString();
await mkdir(OUT_DIR, { recursive: true });
await writeFile(manifestPath, JSON.stringify(manifest, null, 2));

// runtime decoders shipped next to the assets (KTX2 transcoder is WASM, runs in a worker)
const basisSrc = path.join(ROOT, 'node_modules/three/examples/jsm/libs/basis');
await mkdir(path.join(OUT_DIR, 'libs/basis'), { recursive: true });
for (const f of ['basis_transcoder.js', 'basis_transcoder.wasm']) await copyFile(path.join(basisSrc, f), path.join(OUT_DIR, 'libs/basis', f));

console.log(`\n${failed ? '✗ asset build failed' : '✓ manifest written'} → ${path.relative(ROOT, manifestPath)}`);
process.exit(failed ? 1 : 0);
