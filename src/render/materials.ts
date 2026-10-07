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
    color: tint(0x4a3022), roughness: 1, metalness: 0,
    // hand-rubbed satin, not lacquer: a faint, broad sheen (a mirror clearcoat read as plastic on every panel)
    clearcoat: 0.22, clearcoatRoughness: 0.38, envMapIntensity: 0.9,
    normalScale: new Vector2(0.45, 0.45),
  });

  /** Gilt / brass: our colour over scanned worn-gold micro-roughness and fine scratches (ambientCG Metal007).
   *  Aged, hand-burnished finish — a soft glow, not a mirror: century-old gilding is rubbed and dulled. */
  const wornMetal = (hex: number, roughnessScale: number, env = 1.3) => {
    const t = tex.get('Metal_WornGold', 3);
    return new MeshPhysicalMaterial({
      color: tint(hex), metalness: 1, metalnessMap: t.ORM, roughness: 0.34 * roughnessScale, roughnessMap: t.ORM,
      normalMap: t.Normal, normalScale: new Vector2(0.35, 0.35), envMapIntensity: env,
    });
  };

  const carpet = (hex: number) => {
    const t = tex.get('Carpet_Gul', 1 / 0.77, 1 / 0.517); // one tile = 0.77 × 0.517 m of the original carpet
    return new MeshPhysicalMaterial({
      map: t.BaseColor, normalMap: t.Normal, aoMap: t.ORM, roughnessMap: t.ORM, color: tint(hex),
      roughness: 1, metalness: 0, normalScale: new Vector2(0.9, 0.9), envMapIntensity: 0.3,
      sheen: 0.22, sheenColor: tint(0x6a1a12), sheenRoughness: 0.85, // wool pile: a faint sheen in the dye's colour
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
    MAT_Marble_Bardiglio: pbr('Marble_Calacatta', 0.42, { // Italian blue-grey marble for the floor's checker and inlays
      color: tint(0x8f9296), roughness: 1, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.035, envMapIntensity: 3.0,
      normalScale: new Vector2(0.4, 0.4),
    }),
    MAT_Wood_WalnutPolished: walnut,
    MAT_Wood_WalnutDark: pbr('Wood_WalnutPolished', 0.7, {
      color: tint(0x24170f), roughness: 1, metalness: 0, clearcoat: 0.12, clearcoatRoughness: 0.45, envMapIntensity: 0.8,
      normalScale: new Vector2(0.45, 0.45),
    }),
    MAT_Fabric_DamaskOxblood: pbr('Fabric_Damask', 1.1, {
      color: tint(0x4e0f0d), roughness: 1, metalness: 0,
      sheen: 0.2, sheenColor: tint(0x7a2a20), sheenRoughness: 0.8, envMapIntensity: 0.6,
    }),
    MAT_Fabric_DamaskForest: pbr('Fabric_Damask', 1.1, {
      color: tint(0x1f4a30), roughness: 1, metalness: 0,
      sheen: 0.25, sheenColor: tint(0x4f9a66), sheenRoughness: 0.8, envMapIntensity: 0.6,
    }),
    MAT_Fabric_DamaskGold: pbr('Fabric_Damask', 1.1, {
      color: tint(0x6a4a22), roughness: 1, metalness: 0,
      sheen: 0.3, sheenColor: tint(0xc9a45c), sheenRoughness: 0.75, envMapIntensity: 0.6,
    }),
    // Wall-to-wall carpet: a real Turkmen (Salor) carpet photographed by the Met, made into a seamless
    // tile at its true scale (scripts/make-carpets.mjs) with a synthesised wool-pile normal/roughness.
    MAT_Fabric_CarpetForest: carpet(0x6f8a68),
    MAT_Fabric_CarpetCrimson: carpet(0xbfaea6),
    MAT_Fabric_VelvetRed: (() => {
      const t = tex.get('Fabric_Velvet', 3);
      return new MeshPhysicalMaterial({
        // plush crimson velvet (casino.png poker room): deep body colour, bright pile sheen at grazing angles
        color: tint(0x560a0d), normalMap: t.Normal, normalScale: new Vector2(0.55, 0.55), aoMap: t.ORM, roughnessMap: t.ORM,
        roughness: 0.92, envMapIntensity: 0.5, sheen: 0.7, sheenColor: tint(0x9c2a26), sheenRoughness: 0.45,
      });
    })(),
    MAT_Fabric_FeltGreen: pbr('Fabric_Felt', 2.5, {
      color: tint(0x1f6a3a), roughness: 1, metalness: 0,
      sheen: 0.5, sheenColor: tint(0x4a9a60), sheenRoughness: 0.8,
    }),
    MAT_Leather_Oxblood: pbr('Leather_Oxblood', 2.5, {
      color: tint(0xa8483a), roughness: 1, metalness: 0, clearcoat: 0.12, clearcoatRoughness: 0.5, envMapIntensity: 0.8,
    }),
    MAT_Brass_Aged: wornMetal(0x9c7640, 1.7, 1.1),
    MAT_Gold_Gilt: wornMetal(0xb88e4c, 1.55, 1.2),
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
    // Mansion salons: oak point de Hongrie, satin-waxed (clearcoat ≤ 0.2), and ivory-painted boiserie
    MAT_Wood_Parquet: pbr('Wood_Parquet', 1 / 3.4, {
      color: tint(0xe0c9a8), roughness: 1, metalness: 0, clearcoat: 0.15, clearcoatRoughness: 0.4, envMapIntensity: 0.9,
    }),
    MAT_Paint_Ivory: pbr('Plaster_Ceiling', 0.5, {
      color: tint(0xd9ccb0), roughness: 0.62, metalness: 0, normalScale: new Vector2(0.25, 0.25), envMapIntensity: 0.6,
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
