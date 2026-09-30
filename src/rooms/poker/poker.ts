import type { Material } from 'three/webgpu';
import type { MaterialKey } from '../../render/materials';
import { RoomBuilder, type ZoneInstance } from '../../world/roomBuilder';
import { FLOORS, hangChandelier, roomInstance, roomShell } from '../shared/architecture';
import { ROOM_DOOR } from '../shared/layout';
import { clubChair, feltMaterial, pendantLamp, pokerTable, roundTable, tableLamp } from '../shared/props';

/**
 * Salon de Poker (casino.png "Poker Room — Texas Hold'em"; reference photo of the green room):
 * forest-green damask, dark carpet, oval tables under low brass pendants, a club-chair corner.
 * Zone anchor: entrance threshold (door from the West Gallery), room runs to local -Z.
 */
export function buildPokerRoom(materials: Record<MaterialKey, Material>): ZoneInstance {
  const W = 14, D = 12, H = 5.2;
  const b = new RoomBuilder('Poker', materials);
  roomShell(b, {
    width: W, depth: D, height: H, field: 'MAT_Fabric_DamaskForest', floor: FLOORS.forestCarpet,
    entrance: ROOM_DOOR, paintingBays: { left: [0, 2], right: [1, 3], back: [0, 3] },
  });
  const felt = feltMaterial('poker', '#1f5a34', 0);
  ([[-3.4, -4.4], [3.4, -4.4], [-3.4, -8.9], [3.4, -8.9]] as const).forEach(([x, z], i) => {
    pokerTable(b, { pos: [x, 0, z] }, felt, `poker_${String(i + 1).padStart(2, '0')}`);
    pendantLamp(b, { pos: [x, 1.75, z], scale: [1.6, 1, 1] }, H, 16);
    b.sound({ name: `Chips_${i + 1}`, sound: 'chips', position: { x, y: 0.9, z }, gain: 0.35, mode: 'random', interval: [4, 11] });
    b.sound({ name: `Cards_${i + 1}`, sound: 'cardFlick', position: { x, y: 0.9, z }, gain: 0.3, mode: 'random', interval: [3, 9] });
  });
  // quiet corner for spectators
  roundTable(b, { pos: [-5.6, 0, -1.8] }, 0.32, 0.58);
  clubChair(b, { pos: [-4.5, 0, -1.8], rotY: -Math.PI / 2 });
  tableLamp(b, { pos: [-5.6, 0.6, -1.8] }, 4);
  hangChandelier(b, 0, -6.6, H, { scale: 0.7, drop: 1.2, intensity: 30, key: true });
  return roomInstance(b, 'poker', W, D, H);
}
