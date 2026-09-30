import { RepeatWrapping, SRGBColorSpace, TextureLoader, type Texture } from 'three/webgpu';
import { assetUrl } from './assetUrl';

/** Shape of the generated `public/assets/textures/textures.json` (see scripts/fetch-textures.mjs). */
interface TextureManifest {
  materials: Record<string, { maps: Partial<Record<MapKind, { url: string; bytes: number; hash: string }>> }>;
}
export type MapKind = 'BaseColor' | 'Normal' | 'ORM';
export type MaterialTextures = Partial<Record<MapKind, Texture>>;

/**
 * Loads texture sets by material name from the generated manifest — never from hard-coded URLs.
 * Phase 2 swaps JPG for KTX2 (KTX2Loader, worker transcoding) behind this same API.
 */
export class TextureLibrary {
  private sets = new Map<string, MaterialTextures>();
  totalBytes = 0;

  constructor(private readonly anisotropy: number) {}

  async load(manifestUrl: string, onProgress?: (done: number, total: number) => void): Promise<void> {
    const manifest: TextureManifest = await (await fetch(manifestUrl)).json();
    const loader = new TextureLoader();
    const jobs: Promise<void>[] = [];
    let done = 0;
    let total = 0;

    for (const [name, entry] of Object.entries(manifest.materials)) {
      const set: MaterialTextures = {};
      this.sets.set(name, set);
      for (const [kind, map] of Object.entries(entry.maps) as [MapKind, { url: string; bytes: number; hash: string }][]) {
        total++;
        this.totalBytes += map.bytes;
        jobs.push(
          loader.loadAsync(`${assetUrl(map.url)}?v=${map.hash}`).then((tex) => {
            tex.wrapS = tex.wrapT = RepeatWrapping;
            tex.anisotropy = this.anisotropy;
            if (kind === 'BaseColor') tex.colorSpace = SRGBColorSpace;
            set[kind] = tex;
            onProgress?.(++done, total);
          }),
        );
      }
    }
    await Promise.all(jobs);
  }

  /** Returns clones (sharing GPU source) with a tiling repeat applied. */
  get(name: string, repeat = 1): MaterialTextures {
    const set = this.sets.get(name);
    if (!set) throw new Error(`Texture set "${name}" missing from manifest`);
    const out: MaterialTextures = {};
    for (const [k, t] of Object.entries(set) as [MapKind, Texture][]) {
      const c = t.clone();
      c.repeat.set(repeat, repeat);
      out[k] = c;
    }
    return out;
  }
}
