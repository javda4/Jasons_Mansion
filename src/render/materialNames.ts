/**
 * Names of the shared runtime material library (§6 `MAT_<Surface>_<Variant>`).
 * Contract: a Blender material with one of these names is a *library material* — the asset build
 * strips its textures from the GLB and the runtime substitutes the shared library material.
 * Any other `MAT_` name is a zone-unique material and ships fully (KTX2) inside the GLB.
 * Plain TS with no imports so the Node asset pipeline can read it directly.
 */
export const MATERIAL_KEYS = [
  'MAT_Marble_Calacatta', 'MAT_Marble_Nero', 'MAT_Marble_Rosso', 'MAT_Marble_Bardiglio',
  'MAT_Wood_WalnutPolished', 'MAT_Wood_WalnutDark',
  'MAT_Fabric_DamaskOxblood', 'MAT_Fabric_DamaskForest', 'MAT_Fabric_DamaskGold',
  'MAT_Fabric_CarpetCrimson', 'MAT_Fabric_CarpetForest', 'MAT_Fabric_VelvetRed',
  'MAT_Fabric_FeltGreen', 'MAT_Leather_Oxblood',
  'MAT_Brass_Aged', 'MAT_Gold_Gilt', 'MAT_Crystal_Clear',
  'MAT_Emissive_Candle', 'MAT_Fabric_LampShade', 'MAT_Plaster_Ceiling',
] as const;

export type MaterialKey = (typeof MATERIAL_KEYS)[number];

export function isLibraryMaterial(name: string): name is MaterialKey {
  return (MATERIAL_KEYS as readonly string[]).includes(name);
}
