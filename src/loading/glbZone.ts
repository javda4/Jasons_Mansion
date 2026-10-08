import { Box3, Group, InstancedMesh, MeshBasicMaterial, Matrix4, Mesh, Quaternion, Vector3, type Light, type Material, type MeshPhysicalMaterial, type MeshStandardMaterial, type Object3D, type SpotLight, type Texture, type WebGPURenderer } from 'three/webgpu';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import type { Aabb, Vec3 } from '../physics/types';
import { isLibraryMaterial, type MaterialKey } from '../render/materialNames';
import { isNightView, nightViewMaterial } from '../render/nightView';
import type { DoorExtras } from '../interaction/schema';
import type { AnchorDef, DoorDef, EffectDef, LightDef, ZoneInstance } from '../world/roomBuilder';
import { assetUrl } from './assetUrl';

/**
 * Layer 2 → 3: turns an optimised zone GLB into the same `ZoneInstance` the code-built zones
 * produce, by reading the §6 naming contract:
 *
 *   COLLIDER_*  → axis-aligned collision boxes (removed from the render graph)
 *   TRIGGER_*_Bounds → zone volume
 *   SPAWN_*     → arrival point; facing = the empty's Blender local +Z (glTF local +Y)
 *   PROBE_*     → reflection-probe capture point
 *   LIGHT_*     → KHR_lights_punctual → LightDef (the LightPool owns all real lights);
 *                 extras: castShadow, flicker; bakeOnly lights live only in the lightmap
 *   ANCHOR_*      → game-presentation poses (extras: anchor role, tableId, index) — src/tables
 *   FX_*        → runtime-simulated effects (extras: effect kind + size), e.g. hearth fire — src/fx
 *   DOOR_<Zone>_<Id> → empty with door extras (+ `collider`), leaves DOOR_…_L/_R pivot on their
 *                 origins (hinges); local +Y (Blender +Z) points to the owning room
 *   TEXCOORD_1  → baked lightmap (hybrid lighting; see blender/tools/bake_lightmap.py)
 *   MAT_*       → library material names are swapped for the shared runtime material
 *   MAT_*_SeaView → the window-view backdrop: swapped for the live night view (render/nightView.ts)
 *
 * Decoding runs off the main thread: KTX2 transcoding in a worker (Basis WASM), Meshopt in WASM.
 */
let loader: GLTFLoader | null = null;
const INVISIBLE = new MeshBasicMaterial({ visible: false });
INVISIBLE.userData.shared = true;
let ktx2: KTX2Loader | null = null;

export function initGlbLoader(renderer: WebGPURenderer): void {
  ktx2 = new KTX2Loader().setTranscoderPath(assetUrl('/assets/libs/basis/')).detectSupport(renderer);
  loader = new GLTFLoader().setKTX2Loader(ktx2).setMeshoptDecoder(MeshoptDecoder);
}

export interface LightmapRef {
  url: string;
  /** π / encodeScale from the bake (irradiance units matching three.js lights). */
  intensity: number;
}

const _box = new Box3();
const _m = new Matrix4();
const _v = new Vector3();
const _q = new Quaternion();

export async function loadGlbZone(id: string, url: string, materials: Record<MaterialKey, Material>, lightmap?: LightmapRef): Promise<ZoneInstance> {
  if (!loader || !ktx2) throw new Error('initGlbLoader() must run before loading GLB zones');
  const [gltf, lightmapTex] = await Promise.all([loader.loadAsync(url), lightmap ? ktx2.loadAsync(lightmap.url) : Promise.resolve(null)]);
  const root = gltf.scene as Group;
  root.name = `ZONE_${id}`;
  root.updateMatrixWorld(true);

  const colliders: Aabb[] = [];
  const lights: LightDef[] = [];
  let bounds: Aabb | null = null;
  let spawn: ZoneInstance['spawn'];
  let probe: Vec3 | null = null;
  const remove: Object3D[] = [];
  const doorNodes: Object3D[] = [];
  const sounds: ZoneInstance['sounds'] = [];
  const anchors: AnchorDef[] = [];
  const effects: EffectDef[] = [];
  const byName = new Map<string, Object3D>();

  root.traverse((o) => {
    if (remove.some((r) => isAncestor(r, o))) return;
    const name = o.name;
    if (name) byName.set(name, o);
    if ((o as Light).isLight) {
      const extras = { ...(o.parent?.userData ?? {}), ...o.userData };
      if (!extras.bakeOnly) lights.push(toLightDef(o as Light)); // bake-only lights exist only in the lightmap
      remove.push(o);
    } else if (name.startsWith('COLLIDER_')) {
      boxesOf(o).forEach((b, i) => colliders.push({ id: i ? `${name}_${i}` : name, ...b }));
      remove.push(o);
    } else if (name.startsWith('TRIGGER_') && name.endsWith('_Bounds')) {
      bounds = { id: name, ...boxesOf(o)[0] };
      remove.push(o);
    } else if (name.startsWith('SPAWN_')) {
      o.getWorldPosition(_v);
      const dir = new Vector3(0, 1, 0).applyQuaternion(o.getWorldQuaternion(_q));
      spawn = { position: { x: _v.x, y: _v.y, z: _v.z }, yaw: Math.atan2(-dir.x, -dir.z) };
    } else if (name.startsWith('PROBE_')) {
      o.getWorldPosition(_v);
      probe = { x: _v.x, y: _v.y, z: _v.z };
    } else if (name.startsWith('AUDIO_') && typeof o.userData.sound === 'string') {
      const e = o.userData;
      o.getWorldPosition(_v);
      sounds.push({
        id: name, sound: e.sound, position: { x: _v.x, y: _v.y, z: _v.z }, gain: Number(e.gain ?? 0.5),
        mode: e.mode === 'random' ? 'random' : 'loop',
        interval: e.mode === 'random' ? [Number(e.intervalMin ?? 6), Number(e.intervalMax ?? 14)] : undefined,
      });
    } else if (name.startsWith('DOOR_') && o.userData.interactionType === 'door') {
      doorNodes.push(o);
    } else if (name.startsWith('ANCHOR_') && typeof o.userData.anchor === 'string') {
      // stays in the graph (zone transforms move it); presenters read its world pose on demand
      const { anchor, tableId, index, ...extras } = o.userData as { anchor: string; tableId: string; index?: number };
      anchors.push({ role: anchor, tableId, index: Number(index ?? 0), node: o, extras });
    } else if (name.startsWith('FX_') && typeof o.userData.effect === 'string') {
      const { effect, ...extras } = o.userData as { effect: string };
      effects.push({ effect, node: o, extras });
    }
    const mesh = o as Mesh;
    if (mesh.isMesh && name.startsWith('INTERACT_')) {
      // interaction volume: hit by the interaction ray, never drawn
      mesh.material = INVISIBLE;
      return;
    }
    if (mesh.isMesh) {
      const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      const swapped = mats.map((m) => (isLibraryMaterial(m.name) ? materials[m.name] : isNightView(m.name) ? nightViewMaterial() : m));
      for (const m of swapped) if (FELT.test(m.name)) matteCloth(m);
      mesh.material = Array.isArray(mesh.material) ? swapped : swapped[0];
      // the night view is drawn last among opaques: hidden behind the walls, its per-pixel sky and sea is never run
      if (swapped.some((m) => isNightView(m.name) || m.name === 'MAT_NightView')) mesh.renderOrder = 1000;
      const emissiveOnly = swapped.every((m) => m.name.startsWith('MAT_Emissive') || /Fire|SeaView|Window/.test(m.name));
      mesh.castShadow = !emissiveOnly;
      mesh.receiveShadow = true;
    }
  });
  for (const r of remove) r.removeFromParent();

  const doors = doorNodes.map((d) => toDoorDef(id, d, byName, colliders));
  if (lightmapTex && lightmap) applyLightmap(root, lightmapTex, lightmap.intensity);

  if (!bounds) throw new Error(`${id}: GLB has no TRIGGER_*_Bounds`);
  if (!probe) throw new Error(`${id}: GLB has no PROBE_ node`);
  return { id, root, colliders, lights, doors, bounds, spawn, probe, animate: [], sounds, anchors, effects };
}

/**
 * Baize is a matte wool cloth: almost no specular. glTF's default dielectric F0 plus the room's bright
 * environment laid a pale tan veil over every table (the felt read grey-green under a chandelier), so zone
 * felts (`MAT_<Zone>_Felt*`) get their specular and environment reflections turned right down.
 */
const FELT = /^MAT_[A-Za-z]+_Felt/;
function matteCloth(m: Material): void {
  const p = m as MeshPhysicalMaterial;
  if (p.userData.matteCloth) return;
  p.userData.matteCloth = true;
  if (p.isMeshPhysicalMaterial) p.specularIntensity = 0.1;
  if ('envMapIntensity' in p) p.envMapIntensity = 0.35;
}

function isAncestor(a: Object3D, o: Object3D): boolean {
  for (let p: Object3D | null = o.parent; p; p = p.parent) if (p === a) return true;
  return false;
}

/** World AABBs of a node — one per instance when the pipeline batched identical colliders. */
function boxesOf(o: Object3D): { min: Vec3; max: Vec3 }[] {
  const out: { min: Vec3; max: Vec3 }[] = [];
  const push = () => out.push({ min: { x: _box.min.x, y: _box.min.y, z: _box.min.z }, max: { x: _box.max.x, y: _box.max.y, z: _box.max.z } });
  const im = o as InstancedMesh;
  if (im.isInstancedMesh) {
    im.geometry.computeBoundingBox();
    for (let i = 0; i < im.count; i++) {
      im.getMatrixAt(i, _m);
      _box.copy(im.geometry.boundingBox!).applyMatrix4(_m.premultiply(im.matrixWorld));
      push();
    }
  } else {
    _box.setFromObject(o);
    push();
  }
  return out;
}

function toLightDef(l: Light): LightDef {
  // GLTFLoader names the light after its node; extras land on the node object
  const node = l.name ? l : (l.parent ?? l);
  const extras = { ...(l.parent?.userData ?? {}), ...l.userData };
  l.getWorldPosition(_v);
  const def: LightDef = {
    id: node.name || 'LIGHT_Unnamed',
    kind: (l as SpotLight).isSpotLight ? 'spot' : 'point',
    position: { x: _v.x, y: _v.y, z: _v.z },
    color: l.color.getHex(),
    intensity: l.intensity, // KHR_lights_punctual: candela (exported in SPEC mode)
    range: (l as SpotLight).distance || 8,
    flicker: extras.flicker === true,
    castShadow: extras.castShadow === true,
  };
  if ((l as SpotLight).isSpotLight) {
    const s = l as SpotLight;
    def.angle = s.angle;
    def.penumbra = s.penumbra;
    s.target.getWorldPosition(_v);
    def.target = { x: _v.x, y: _v.y, z: _v.z };
  }
  return def;
}

/** DOOR_ empty + DOOR_…_L/_R leaves (origins on the hinges) → DoorDef driven by the DoorSystem. */
function toDoorDef(zone: string, node: Object3D, byName: Map<string, Object3D>, colliders: Aabb[]): DoorDef {
  const { collider: colliderName, ...extras } = node.userData as DoorExtras & { collider?: string };
  const doorId = node.name;
  node.getWorldPosition(_v);
  const position = { x: _v.x, y: _v.y, z: _v.z };
  // room side: the empty's Blender local +Z = glTF local +Y; leaves swing away from it
  const away = new Vector3(0, 1, 0).applyQuaternion(node.getWorldQuaternion(_q)).negate();
  const leaves: DoorDef['leaves'] = [];
  const doorCentre = new Vector3(position.x, position.y, position.z);
  for (const suffix of ['_L', '_R']) {
    const leaf = byName.get(doorId + suffix);
    if (!leaf || !leaf.parent) { console.warn(`[glb] ${zone}: ${doorId} is missing leaf ${doorId}${suffix}`); continue; }
    // The hinge is derived from geometry, not the node origin: mesh quantization may move origins.
    // It is the leaf's vertical edge farthest from the door centre, mid-thickness, at floor level.
    const box = new Box3().setFromObject(leaf);
    const centre = box.getCenter(new Vector3());
    const out = centre.clone().sub(doorCentre).setY(0);
    const alongX = Math.abs(out.x) > Math.abs(out.z);
    const hinge = new Vector3(
      alongX ? (out.x > 0 ? box.max.x : box.min.x) : centre.x,
      box.min.y,
      alongX ? centre.z : (out.z > 0 ? box.max.z : box.min.z),
    );
    const pivot = new Group();
    pivot.name = `${leaf.name}_Hinge`;
    leaf.parent.add(pivot);
    pivot.parent!.updateMatrixWorld(true);
    pivot.position.copy(pivot.parent!.worldToLocal(hinge.clone()));
    pivot.updateMatrixWorld(true);
    pivot.attach(leaf); // keeps the leaf's world transform
    // rotating +θ about Y moves the free edge along (v.z, -v.x); choose θ's sign so it heads "away"
    const v = centre.sub(hinge);
    const sign: 1 | -1 = v.z * away.x - v.x * away.z >= 0 ? 1 : -1;
    pivot.userData.baseQuaternion = pivot.quaternion.clone();
    leaf.traverse((m) => { if ((m as Mesh).isMesh) Object.assign(m.userData, extras, { doorId }); });
    leaves.push({ pivot, sign });
  }
  const collider = colliders.find((c) => c.id === colliderName);
  if (!collider) throw new Error(`${zone}: ${doorId} references missing collider ${colliderName}`);
  return { id: doorId, leaves, collider, target: extras.target ?? null, position, extras: extras as DoorExtras };
}

/**
 * Baked lighting: every mesh carrying TEXCOORD_1 gets the zone lightmap. Library materials are
 * shared across zones, so lightmapped meshes use per-zone clones (textures stay shared).
 */
function applyLightmap(root: Object3D, tex: Texture, intensity: number): void {
  tex.channel = 1;
  const clones = new Map<Material, Material>();
  root.traverse((o) => {
    const mesh = o as Mesh;
    if (!mesh.isMesh || !mesh.geometry.attributes.uv1) return;
    const swap = (m: Material) => {
      let c = clones.get(m);
      if (!c) {
        c = m.clone();
        const sm = c as MeshStandardMaterial;
        sm.lightMap = tex;
        sm.lightMapIntensity = intensity;
        c.userData = { ...m.userData, shared: false, sharedTextures: true };
        clones.set(m, c);
      }
      return c;
    };
    mesh.material = Array.isArray(mesh.material) ? mesh.material.map(swap) : swap(mesh.material);
  });
}
