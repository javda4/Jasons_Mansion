import type { Material } from 'three/webgpu';
import type { MaterialKey } from '../../render/materials';
import { RoomBuilder, type ZoneInstance } from '../../world/roomBuilder';
import { FLOORS, hangChandelier, roomInstance, roomShell } from '../shared/architecture';
import { ROOM_DOOR } from '../shared/layout';
import { blackjackTablePrinted, feltMaterial } from '../shared/props';

/**
 * Salon Blackjack (casino.png "Blackjack Room — Classic Tables"): oxblood damask, crimson carpet,
 * half-moon tables with printed felt, a crystal chandelier, tall windows over the sea.
 */
export function buildBlackjackRoom(materials: Record<MaterialKey, Material>): ZoneInstance {
  const W = 14, D = 12, H = 5.6;
  const b = new RoomBuilder('Blackjack', materials);
  roomShell(b, {
    width: W, depth: D, height: H, field: 'MAT_Fabric_DamaskOxblood', floor: FLOORS.crimsonCarpet,
    entrance: ROOM_DOOR, windowBays: { back: [1, 2] }, paintingBays: { left: [1], right: [2] },
  });
  const felt = feltMaterial('blackjack', '#1d5e36', Math.PI / 2);
  ([[-3.6, -5.2], [3.6, -5.2], [-3.6, -9.6], [3.6, -9.6]] as const).forEach(([x, z], i) => {
    // dealer faces the entrance; players sit on the entrance side (+Z)
    blackjackTablePrinted(b, { pos: [x, 0, z] }, felt, `blackjack_${String(i + 1).padStart(2, '0')}`);
    b.sound({ name: `Cards_${i + 1}`, sound: 'cardFlick', position: { x, y: 0.9, z }, gain: 0.3, mode: 'random', interval: [2.5, 7] });
    b.sound({ name: `Chips_${i + 1}`, sound: 'chips', position: { x, y: 0.9, z }, gain: 0.3, mode: 'random', interval: [5, 12] });
  });
  hangChandelier(b, -3.6, -7.4, H, { scale: 0.75, drop: 1.3, intensity: 36, key: true });
  hangChandelier(b, 3.6, -7.4, H, { scale: 0.75, drop: 1.3, intensity: 36 });
  return roomInstance(b, 'blackjack', W, D, H);
}
