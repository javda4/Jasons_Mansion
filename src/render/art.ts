import { SRGBColorSpace, TextureLoader, type Texture } from 'three/webgpu';
import { assetUrl } from '../loading/assetUrl';

/** A public-domain painting from public/assets/art/art.json (fetched by scripts/fetch-art.mjs). */
export interface Artwork {
  id: string;
  title: string;
  artist: string;
  date: string;
  /** Original width / height; textures are stored 1024² and un-stretched by the canvas size. */
  aspect: number;
  texture: Texture;
}

let works: Artwork[] = [];

/** Loads every artwork texture up front (≈ 3 MB); code-built rooms hang them synchronously. */
export async function loadArt(manifestUrl: string, anisotropy: number): Promise<void> {
  const manifest = await fetch(manifestUrl).then((r) => (r.ok ? r.json() : { works: [] }), () => ({ works: [] }));
  const loader = new TextureLoader();
  works = await Promise.all((manifest.works as Omit<Artwork, 'texture'>[]).map(async (w) => {
    const texture = await loader.loadAsync(assetUrl(`${(w as { url?: string }).url}`));
    texture.colorSpace = SRGBColorSpace;
    texture.anisotropy = anisotropy;
    texture.userData.shared = true;
    return { ...w, texture };
  }));
}

/** Deterministic choice for a frame; `prefer` biases towards landscape (>1) or portrait (<1). */
export function pickArtwork(seed: number, prefer?: 'landscape' | 'portrait'): Artwork | null {
  if (!works.length) return null;
  const pool = prefer ? works.filter((w) => (prefer === 'landscape' ? w.aspect >= 1 : w.aspect < 1)) : works;
  const list = pool.length ? pool : works;
  return list[Math.abs(Math.floor(seed)) % list.length];
}
