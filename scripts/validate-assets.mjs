// Validates optimised zone GLBs: Khronos glTF-Validator + our contract checks (CLAUDE.md §6/§7).
// Errors fail the build; warnings print with the offending node/material name.
//
//   node scripts/validate-assets.mjs [public/assets/rooms/<zone>/<zone>.glb ...]

import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { MeshoptDecoder } from 'meshoptimizer';
import validator from 'gltf-validator';
import { gameOfTable, validateExtras } from '../src/interaction/schema.ts';
import { isLibraryMaterial } from '../src/render/materialNames.ts';

const PREFIXES = ['ROOM', 'COLLIDER', 'TRIGGER', 'PORTAL', 'DOOR', 'SPAWN', 'INTERACT', 'TABLE', 'CHAIR', 'SLOT', 'PROP', 'LIGHT', 'PROBE', 'NAV', 'AUDIO', 'ANCHOR', 'FX'];
/** FX_ effects the runtime simulates (src/fx/effects.ts). */
const FX_EFFECTS = new Set(['fire']);
/** ANCHOR_ roles the runtime presenters understand (src/tables/anchors.ts). */
const ANCHOR_ROLES = new Set(['seat', 'focus', 'dealerCards', 'playerCards', 'bankerCards', 'board', 'botCards', 'bet', 'pot', 'shoe', 'discard', 'chipTray', 'reel', 'wheel', 'layout']);
const NAME_RE = new RegExp(`^(${PREFIXES.join('|')})_([A-Z][A-Za-z0-9]*)(?:_(?:[A-Z][A-Za-z0-9]*|\\d{2}))*(?:_LOD\\d)?$`);
const MATERIAL_RE = /^MAT_[A-Z][A-Za-z0-9]*_[A-Z][A-Za-z0-9]*$/;

export const BUDGETS = { triangles: 1_500_000, textureSize: 2048, bytes: 25 * 1024 * 1024 };

/** @returns {Promise<{ errors: string[], warnings: string[], stats: Record<string, number> }>} */
export async function validateZoneGlb(file, { zone, lightmapped = false } = {}) {
  const errors = [];
  const warnings = [];
  const bytes = await readFile(file);

  // 1) Khronos glTF-Validator
  const usesBasisu = bytes.includes('KHR_texture_basisu');
  const report = await validator.validateBytes(new Uint8Array(bytes), { maxIssues: 200, uri: path.basename(file) });
  for (const m of report.issues.messages) {
    // this glTF-Validator build predates `image/ktx2` being legal under KHR_texture_basisu
    // (neither the MIME type nor the KTX2 container) — KTX2 images are verified by the encoder instead
    if (m.code === 'VALUE_NOT_IN_LIST' && /\/images\/\d+\/mimeType/.test(m.pointer ?? '') && m.message.includes('image/ktx2')) continue;
    if (m.code === 'IMAGE_UNRECOGNIZED_FORMAT' && usesBasisu) continue;
    const line = `glTF-Validator ${m.code}: ${m.message} (${m.pointer ?? ''})`;
    if (m.severity === 0) errors.push(line);
    else if (m.severity === 1) warnings.push(line);
  }

  // 2) contract checks
  await MeshoptDecoder.ready;
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
  const doc = await io.readBinary(new Uint8Array(bytes));
  const root = doc.getRoot();
  const seen = { TRIGGER: 0, PROBE: 0, COLLIDER: 0, SPAWN: 0 };
  let triangles = 0;

  for (const node of root.listNodes()) {
    const name = node.getName();
    const m = NAME_RE.exec(name);
    if (!m) { errors.push(`node "${name}": name does not match PREFIX_Zone_Name[_NN]`); continue; }
    if (zone && m[2] !== zone) errors.push(`node "${name}": zone segment "${m[2]}" != "${zone}"`);
    if (m[1] in seen) seen[m[1]]++;
    const extras = node.getExtras();
    if (extras && extras.interactable !== undefined) {
      for (const e of validateExtras(extras)) errors.push(`node "${name}": extras ${e}`);
    }
    if (m[1] === 'ANCHOR') {
      if (node.getMesh()) errors.push(`node "${name}": ANCHOR_ must be an empty`);
      if (!ANCHOR_ROLES.has(extras?.anchor)) errors.push(`node "${name}": extras.anchor must be a known role`);
      if (typeof extras?.tableId !== 'string') errors.push(`node "${name}": extras.tableId is required`);
      else if (!gameOfTable(extras.tableId)) errors.push(`node "${name}": extras.tableId "${extras.tableId}" must be <gameType>_<NN>`);
    }
    if (m[1] === 'FX') {
      if (node.getMesh()) errors.push(`node "${name}": FX_ must be an empty`);
      if (!FX_EFFECTS.has(extras?.effect)) errors.push(`node "${name}": extras.effect must be a known effect`);
    }
    const mesh = node.getMesh();
    if (mesh) {
      const inst = node.getExtension('EXT_mesh_gpu_instancing');
      const count = inst ? inst.listAttributes()[0]?.getCount() ?? 1 : 1;
      for (const prim of mesh.listPrimitives()) {
        const idx = prim.getIndices();
        const n = idx ? idx.getCount() / 3 : prim.getAttribute('POSITION').getCount() / 3;
        triangles += n * count;
        if (!['COLLIDER', 'TRIGGER', 'INTERACT'].includes(m[1]) && !prim.getAttribute('TEXCOORD_0')) warnings.push(`node "${name}": no UV0`);
      }
    }
  }
  for (const [k, n] of Object.entries(seen)) if (!n) (k === 'SPAWN' ? warnings : errors).push(`zone has no ${k}_ node`);

  // doors: DOOR_<Zone>_<Id> carries the extras, leaves _L/_R pivot on their origins, collider exists
  const names = new Set(root.listNodes().map((n) => n.getName()));
  for (const node of root.listNodes()) {
    const e = node.getExtras();
    if (!node.getName().startsWith('DOOR_') || e?.interactionType !== 'door') continue;
    for (const s of ['_L', '_R']) if (!names.has(node.getName() + s)) errors.push(`door "${node.getName()}": missing leaf ${node.getName()}${s}`);
    if (typeof e.collider !== 'string' || !names.has(e.collider)) errors.push(`door "${node.getName()}": extras.collider must name an existing COLLIDER_ node`);
  }
  if (lightmapped) {
    const withUv1 = root.listMeshes().filter((m) => m.listPrimitives().some((p) => p.getAttribute('TEXCOORD_1'))).length;
    if (!withUv1) errors.push('zone declares a lightmap but no mesh carries TEXCOORD_1');
  }

  for (const mat of root.listMaterials()) {
    const name = mat.getName();
    if (!MATERIAL_RE.test(name)) errors.push(`material "${name}": must be MAT_<Surface>_<Variant>`);
    if (isLibraryMaterial(name) && mat.getBaseColorTexture()) warnings.push(`material "${name}": library material still carries textures`);
  }
  let textureBytes = 0;
  for (const tex of root.listTextures()) {
    const size = tex.getSize();
    textureBytes += tex.getImage()?.byteLength ?? 0;
    if (size && Math.max(...size) > BUDGETS.textureSize) errors.push(`texture "${tex.getName()}": ${size.join('×')} > ${BUDGETS.textureSize}`);
    if (tex.getMimeType() !== 'image/ktx2') warnings.push(`texture "${tex.getName() || tex.getURI()}": ${tex.getMimeType()} (expected KTX2)`);
  }
  if (triangles > BUDGETS.triangles) errors.push(`zone has ${triangles.toLocaleString()} triangles (budget ${BUDGETS.triangles.toLocaleString()})`);
  if (bytes.byteLength > BUDGETS.bytes) errors.push(`file is ${(bytes.byteLength / 1048576).toFixed(1)} MB (budget 25 MB)`);

  return { errors, warnings, stats: { bytes: bytes.byteLength, triangles, textureBytes, nodes: root.listNodes().length, materials: root.listMaterials().length } };
}

// CLI
if (import.meta.url === `file://${process.argv[1]}`) {
  const files = process.argv.slice(2);
  let failed = false;
  for (const f of files) {
    const { errors, warnings, stats } = await validateZoneGlb(f);
    warnings.forEach((w) => console.log(`  warning: ${w}`));
    errors.forEach((e) => console.log(`  ERROR:   ${e}`));
    console.log(`[validate] ${f}: ${errors.length} errors, ${warnings.length} warnings, ${stats.triangles.toLocaleString()} tris`);
    failed ||= errors.length > 0;
  }
  process.exit(failed ? 1 : 0);
}
