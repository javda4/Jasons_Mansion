import type { Material } from 'three/webgpu';
import { loadGlbZone } from '../loading/glbZone';
import type { MaterialKey } from '../render/materialNames';
import type { Transform2 } from '../rooms/shared/layout';
import type { ZoneInstance } from './roomBuilder';
import type { ZoneManifestEntry } from './zoneManager';
import { assetUrl } from '../loading/assetUrl';

/**
 * The mansion's zone graph (§8), read from the generated `public/assets/manifest.json`
 * (scripts/build-assets.mjs). Every zone is a Blender-authored GLB with an explicit world transform from the
 * master layout (`blender/zones.json`); doors are the portals between neighbours. Plan: docs/mansion-plan.md.
 */

/** Shape of public/assets/manifest.json (generated, never hand-edited). */
export interface AssetManifest {
  zones: Record<string, {
    title: string;
    asset: string;
    bytes: number;
    hash: string;
    preload: boolean;
    priority: number;
    neighbors: string[];
    transform: Transform2;
    always?: boolean;
    lightmap?: { url: string; intensity: number; hash: string };
  }>;
}

/** Room-specific runtime modules (animation, special logic: CLAUDE.md §5 rooms/), keyed by zone id. */
const ROOM_MODULES: Record<string, () => Promise<(inst: ZoneInstance) => void>> = {};

export function buildZoneGraph(manifest: AssetManifest): ZoneManifestEntry[] {
  const zones = new Map<string, ZoneManifestEntry>();
  for (const [id, z] of Object.entries(manifest.zones)) {
    if (!z.transform) { console.warn(`[zones] manifest zone ${id} has no transform`); continue; }
    zones.set(id, {
      id, title: z.title, neighbors: z.neighbors, preload: z.preload, transform: z.transform, always: !!z.always,
      load: async () => {
        const room = ROOM_MODULES[id] ? await ROOM_MODULES[id]() : null;
        return async (mats: Record<MaterialKey, Material>) => {
          const inst = await loadGlbZone(id, `${assetUrl(z.asset)}?v=${z.hash}`, mats, z.lightmap && { url: `${assetUrl(z.lightmap.url)}?v=${z.lightmap.hash}`, intensity: z.lightmap.intensity });
          await (await import('../tables/attach')).attachGameTables(inst);   // the zone's game tables, whatever room
          room?.(inst);
          if (inst.effects?.length) (await import('../fx/effects')).attachEffects(inst);
          return inst;
        };
      },
    });
  }
  // neighbour links are symmetric; drop links to zones that aren't built yet
  for (const z of zones.values()) {
    z.neighbors = z.neighbors.filter((n) => zones.has(n));
    for (const n of z.neighbors) {
      const nb = zones.get(n)!;
      if (!nb.neighbors.includes(z.id)) nb.neighbors = [...nb.neighbors, z.id];
    }
  }
  return [...zones.values()];
}

/** The zone the player starts in: the preloaded one (lowest priority number), else the first. */
export function startZone(manifest: AssetManifest): string {
  const [first] = Object.entries(manifest.zones).filter(([, z]) => !z.always).sort(([, a], [, b]) => Number(b.preload) - Number(a.preload) || a.priority - b.priority);
  if (!first) throw new Error('manifest has no zones: run npm run build:assets');
  return first[0];
}
