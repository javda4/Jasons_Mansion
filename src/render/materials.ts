import { Color, MeshPhysicalMaterial, MeshStandardMaterial, Vector2, type Material, type Texture } from 'three/webgpu';
import type { TextureLibrary } from '../loading/textureLibrary';

/**
 * The runtime material library, keyed by the same `MAT_<Surface>_<Variant>` names the Blender
 * material library uses (§6) — so Phase 2 GLB materials can be swapped/upgraded by name.
 * Geometry UVs are authored in metres; `repeat` = tiles per metre.
 */
export type { MaterialKey } from './materialNames';
import type { MaterialKey } from './materialNames';

export function createMaterials(tex: TextureLibrary): Record<MaterialKey, Material> {
  const pbr = (name: string, repeat: number, params: ConstructorParameters<typeof MeshPhysicalMaterial>[0]) => {
    const t = tex.get(name, repeat);
    const m = new MeshPhysicalMaterial({
      map: t.BaseColor,
      normalMap: t.Normal,
      aoMap: t.ORM,
      roughnessMap: t.ORM,
      metalnessMap: t.ORM,
      ...params,
    });
    return m;
  };
  const tint = (hex: number) => new Color(hex);

  const marble = pbr('Marble_Calacatta', 0.35, {
    color: tint(0xd8cbb4), roughness: 1, metalness: 1, // scaled by ORM channels
    clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 3.2, // polished floor: reads the room probe strongly
    normalScale: new Vector2(0.4, 0.4),
  });
  const walnut = pbr('Wood_WalnutPolished', 0.5, {
    color: tint(0x4a3022), roughness: 0.9, metalness: 0,
    clearcoat: 1, clearcoatRoughness: 0.08, envMapIntensity: 2.2, // French-polished lacquer
    normalScale: new Vector2(0.3, 0.3),
  });

  /** Gilt / brass: our colour over scanned worn-gold micro-roughness and fine scratches (ambientCG Metal007). */
  const wornMetal = (hex: number, roughnessScale: number) => {
    const t = tex.get('Metal_WornGold', 3);
    return new MeshPhysicalMaterial({
      color: tint(hex), metalness: 1, metalnessMap: t.ORM, roughness: 0.34 * roughnessScale, roughnessMap: t.ORM,
      normalMap: t.Normal, normalScale: new Vector2(0.25, 0.25), envMapIntensity: 2.5,
    });
  };

  const lib: Record<MaterialKey, Material> = {
    MAT_Marble_Calacatta: marble,
    MAT_Marble_Nero: pbr('Marble_Calacatta', 0.5, {
      color: tint(0x2a2320), roughness: 1, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 3.2,
    }),
    MAT_Marble_Rosso: pbr('Marble_Calacatta', 0.5, {
      color: tint(0x6e2a22), roughness: 1, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 3.2,
    }),
    MAT_Wood_WalnutPolished: walnut,
    MAT_Wood_WalnutDark: pbr('Wood_WalnutPolished', 0.7, {
      color: tint(0x24170f), roughness: 0.9, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.18,
      normalScale: new Vector2(0.3, 0.3),
    }),
    MAT_Fabric_DamaskOxblood: pbr('Fabric_Damask', 1.1, {
      color: tint(0x4e0f0d), roughness: 1, metalness: 0,
      sheen: 0.35, sheenColor: tint(0x8a2a20), sheenRoughness: 0.6,
    }),
    MAT_Fabric_DamaskForest: pbr('Fabric_Damask', 1.1, {
      color: tint(0x1f4a30), roughness: 1, metalness: 0,
      sheen: 0.45, sheenColor: tint(0x4f9a66), sheenRoughness: 0.6,
    }),
    MAT_Fabric_DamaskGold: pbr('Fabric_Damask', 1.1, {
      color: tint(0x6a4a22), roughness: 1, metalness: 0,
      sheen: 0.5, sheenColor: tint(0xc9a45c), sheenRoughness: 0.5,
    }),
    MAT_Fabric_CarpetForest: pbr('Fabric_Damask', 0.9, {
      color: tint(0x1b2a20), roughness: 1, metalness: 0,
      sheen: 0.6, sheenColor: tint(0x4a6a3a), sheenRoughness: 0.7,
      normalScale: new Vector2(1.4, 1.4),
    }),
    MAT_Fabric_CarpetCrimson: pbr('Fabric_Damask', 0.9, {
      color: tint(0x5e0e0e), roughness: 1, metalness: 0,
      sheen: 0.6, sheenColor: tint(0x9a2a20), sheenRoughness: 0.7,
      normalScale: new Vector2(1.4, 1.4),
    }),
    MAT_Fabric_VelvetRed: (() => {
      const t = tex.get('Fabric_Velvet', 3);
      return new MeshPhysicalMaterial({
        color: tint(0x3a0606), normalMap: t.Normal, aoMap: t.ORM, roughnessMap: t.ORM, roughness: 0.9,
        sheen: 0.7, sheenColor: tint(0x9a2a2a), sheenRoughness: 0.4,
      });
    })(),
    MAT_Fabric_FeltGreen: pbr('Fabric_Felt', 2.5, {
      color: tint(0x1f6a3a), roughness: 1, metalness: 0,
      sheen: 0.5, sheenColor: tint(0x4a9a60), sheenRoughness: 0.8,
    }),
    MAT_Leather_Oxblood: pbr('Leather_Oxblood', 2.5, {
      color: tint(0xa8483a), roughness: 1, metalness: 0, clearcoat: 0.35, clearcoatRoughness: 0.35,
    }),
    MAT_Brass_Aged: wornMetal(0xb98a4a, 1.25),
    MAT_Gold_Gilt: wornMetal(0xd8ad5c, 0.85),
    MAT_Crystal_Clear: new MeshPhysicalMaterial({
      color: tint(0xffffff), metalness: 0, roughness: 0.02, ior: 2.0, specularIntensity: 1,
      iridescence: 0.5, iridescenceIOR: 1.6, emissive: tint(0xffc890), emissiveIntensity: 0.35,
    }),
    MAT_Emissive_Candle: new MeshStandardMaterial({
      color: tint(0x000000), emissive: tint(0xffc27a), emissiveIntensity: 40,
    }),
    MAT_Fabric_LampShade: new MeshStandardMaterial({
      color: tint(0xe9d4a8), roughness: 0.9, emissive: tint(0xffb870), emissiveIntensity: 1.6,
    }),
    MAT_Plaster_Ceiling: pbr('Plaster_Ceiling', 0.6, { color: tint(0x2c1d13), roughness: 0.9, metalness: 0, normalScale: new Vector2(0.6, 0.6) }),
  };
  for (const [k, m] of Object.entries(lib)) {
    m.name = k;
    m.userData.shared = true; // never disposed when a zone unloads
  }
  return lib;
}

export type { Texture };
