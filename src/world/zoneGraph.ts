import type { Material } from 'three/webgpu';
import { loadGlbZone } from '../loading/glbZone';
import type { MaterialKey } from '../render/materialNames';
import { compose, HALL_SLOTS, LOBBY_SLOTS, type Transform2 } from '../rooms/shared/layout';
import type { ZoneInstance } from './roomBuilder';
import type { ZoneManifestEntry } from './zoneManager';
import { assetUrl } from '../loading/assetUrl';

/**
 * The mansion's zone graph (§8). Blender-authored zones come from the generated
 * `public/assets/manifest.json` (scripts/build-assets.mjs); code-built zones are the fallback for
 * any zone the manifest doesn't (yet) provide. Each zone is its own chunk / GLB, so rooms stream.
 *
 *            [roulette]      [slots]                [poker]      [blackjack]
 *                 \          /                          \          /
 *   [vip] — hall_east — LOBBY — hall_west — [baccarat]
 */

type SlotName = keyof typeof HALL_SLOTS | keyof typeof LOBBY_SLOTS;

/** Shape of public/assets/manifest.json (generated — never hand-edited). */
export interface AssetManifest {
  zones: Record<string, {
    title: string;
    asset: string;
    bytes: number;
    hash: string;
    preload: boolean;
    priority: number;
    neighbors: string[];
    attach?: { zone: string; slot: SlotName };
    transform?: Transform2;
    lightmap?: { url: string; intensity: number; hash: string };
  }>;
}

/** Per-zone runtime modules for GLB zones (animation / special logic, CLAUDE.md §5 rooms/). */
const ENHANCERS: Record<string, () => Promise<(inst: ZoneInstance) => void>> = {
  roulette: () => import('../rooms/roulette/runtime').then((m) => m.enhanceRoulette),
  slots: () => import('../rooms/slots/runtime').then((m) => m.enhanceSlots),
};

const hallWest: Transform2 = LOBBY_SLOTS.west;
const hallEast: Transform2 = LOBBY_SLOTS.east;

/** Code-built fallbacks (Phase 1–5), used when a zone has no built GLB. */
function codeZones(vipAvailable: boolean): ZoneManifestEntry[] {
  const vip = vipAvailable
    ? { target: 'vip', prompt: 'Enter the Salon Privé', plaque: ['Salon Privé', 'Réservé aux membres'] }
    : { prompt: 'Salon Privé — by invitation', plaque: ['Salon Privé', 'Réservé'], locked: true };
  return [
    {
      id: 'lobby', title: 'Grand Lobby', neighbors: ['hall_west', 'hall_east'], preload: true,
      transform: { x: 0, z: 0, rotY: 0 },
      load: () => import('../rooms/lobby/lobby').then((m) => m.buildLobby),
    },
    {
      id: 'hall_west', title: 'West Gallery', neighbors: ['lobby', 'poker', 'blackjack', 'baccarat'], transform: hallWest,
      load: () => import('../rooms/hallway/hallway').then((m) => (mats) => m.buildHallway('hall_west', 'HallWest', mats, {
        left: { target: 'poker', prompt: 'Enter the Poker Room', plaque: ['Salon de Poker', "Texas Hold'em"] },
        right: { target: 'blackjack', prompt: 'Enter the Blackjack Room', plaque: ['Salon Blackjack', 'Vingt-et-Un'] },
        end: { target: 'baccarat', prompt: 'Enter the Baccarat Room', plaque: ['Salon Baccarat', 'Chemin de Fer'] },
        back: 'lobby',
      })),
    },
    {
      id: 'hall_east', title: 'East Gallery', neighbors: ['lobby', 'roulette', 'slots'], transform: hallEast,
      load: () => import('../rooms/hallway/hallway').then((m) => (mats) => m.buildHallway('hall_east', 'HallEast', mats, {
        left: { target: 'roulette', prompt: 'Enter the Roulette Room', plaque: ['Salon de Roulette', 'Faites vos jeux'] },
        right: { target: 'slots', prompt: 'Enter the Slot Room', plaque: ['Machines à Sous', 'Salle des Jackpots'] },
        end: vip,
        back: 'lobby',
      })),
    },
    { id: 'poker', title: 'Poker Room', neighbors: ['hall_west'], transform: compose(hallWest, HALL_SLOTS.left), load: () => import('../rooms/poker/poker').then((m) => m.buildPokerRoom) },
    { id: 'blackjack', title: 'Blackjack Room', neighbors: ['hall_west'], transform: compose(hallWest, HALL_SLOTS.right), load: () => import('../rooms/blackjack/blackjack').then((m) => m.buildBlackjackRoom) },
    { id: 'baccarat', title: 'Baccarat Room', neighbors: ['hall_west'], transform: compose(hallWest, HALL_SLOTS.end), load: () => import('../rooms/baccarat/baccarat').then((m) => m.buildBaccaratRoom) },
    { id: 'roulette', title: 'Roulette Room', neighbors: ['hall_east'], transform: compose(hallEast, HALL_SLOTS.left), load: () => import('../rooms/roulette/roulette').then((m) => m.buildRouletteRoom) },
    { id: 'slots', title: 'Slot Room', neighbors: ['hall_east'], transform: compose(hallEast, HALL_SLOTS.right), load: () => import('../rooms/slots/slots').then((m) => m.buildSlotRoom) },
  ];
}

export function buildZoneGraph(manifest: AssetManifest): ZoneManifestEntry[] {
  const glb = manifest.zones;
  const zones = new Map(codeZones(!!glb.vip).map((z) => [z.id, z]));

  const resolve = (id: string, depth = 0): Transform2 | undefined => {
    const z = glb[id];
    if (!z) return zones.get(id)?.transform;
    if (z.transform) return z.transform;
    if (!z.attach || depth > 8) return undefined;
    const parent = resolve(z.attach.zone, depth + 1);
    const slots = (z.attach.zone === 'lobby' ? LOBBY_SLOTS : HALL_SLOTS) as Record<string, Transform2>;
    const slot = slots[z.attach.slot];
    return parent && slot ? compose(parent, slot) : undefined;
  };

  for (const [id, z] of Object.entries(glb)) {
    const transform = resolve(id);
    if (!transform) { console.warn(`[zones] manifest zone ${id} has no resolvable transform`); continue; }
    zones.set(id, {
      id, title: z.title, neighbors: z.neighbors, preload: z.preload, transform,
      load: async () => {
        const enhance = ENHANCERS[id] ? await ENHANCERS[id]() : null;
        return async (mats: Record<MaterialKey, Material>) => {
          const inst = await loadGlbZone(id, `${assetUrl(z.asset)}?v=${z.hash}`, mats, z.lightmap && { url: `${assetUrl(z.lightmap.url)}?v=${z.lightmap.hash}`, intensity: z.lightmap.intensity });
          enhance?.(inst);
          return inst;
        };
      },
    });
  }
  // neighbour links are symmetric
  for (const z of zones.values()) {
    for (const n of z.neighbors) {
      const nb = zones.get(n);
      if (nb && !nb.neighbors.includes(z.id)) nb.neighbors = [...nb.neighbors, z.id];
    }
  }
  return [...zones.values()];
}
