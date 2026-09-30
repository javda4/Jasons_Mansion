import { MeshPhysicalMaterial, MeshStandardMaterial, type Material } from 'three/webgpu';
import type { MaterialKey } from '../../render/materials';
import { rouletteLayoutTexture, rouletteWheelTexture } from '../../render/proceduralArt';
import { RoomBuilder, type ZoneInstance } from '../../world/roomBuilder';
import { FLOORS, hangChandelier, roomInstance, roomShell } from '../shared/architecture';
import { ROOM_DOOR } from '../shared/layout';
import { rouletteTable } from '../shared/props';

/**
 * Salon de Roulette (casino.png "Roulette Room — The Classic"): oxblood walls, crimson carpet,
 * several chandeliers, French single-zero tables whose wheels turn slowly.
 */
export function buildRouletteRoom(materials: Record<MaterialKey, Material>): ZoneInstance {
  const W = 14, D = 12, H = 5.8;
  const b = new RoomBuilder('Roulette', materials);
  roomShell(b, {
    width: W, depth: D, height: H, field: 'MAT_Fabric_DamaskOxblood', floor: FLOORS.crimsonCarpet,
    entrance: ROOM_DOOR, paintingBays: { left: [0, 2], right: [1, 3], back: [0, 3] },
  });
  const wheel = new MeshPhysicalMaterial({ map: rouletteWheelTexture(), roughness: 0.25, clearcoat: 1, clearcoatRoughness: 0.05 });
  wheel.name = 'MAT_Roulette_Wheel';
  const layout = new MeshStandardMaterial({ map: rouletteLayoutTexture(), roughness: 0.95 });
  layout.name = 'MAT_Roulette_Layout';

  const tables: [number, number, number][] = [[-3.2, -4.4, 0], [3.4, -4.4, 0], [-3.2, -9.0, 0], [3.4, -9.0, 0]];
  const boosts = new Map<string, { at: number }>();
  let now = 0;
  tables.forEach(([x, z, rot], i) => {
    const tableId = `roulette_${String(i + 1).padStart(2, '0')}`;
    const rotor = rouletteTable(b, { pos: [x, 0, z], rotY: rot }, wheel, layout, tableId);
    const speed = 0.35 + i * 0.07;
    b.sound({ name: `Ball_${i + 1}`, sound: 'rouletteBall', position: { x, y: 0.95, z }, gain: 0.35, mode: 'random', interval: [18, 40] });
    b.sound({ name: `Chips_${i + 1}`, sound: 'chips', position: { x, y: 0.9, z }, gain: 0.3, mode: 'random', interval: [5, 12] });
    // the croupier's spin: a burst of speed that bleeds away over ~5 s
    let angle = i, last = 0;
    b.animate.push((t) => {
      const dt = Math.min(0.1, t - last);
      last = now = t;
      const boost = boosts.get(tableId);
      const extra = boost ? 7 * Math.exp(-(t - boost.at) / 1.6) : 0;
      angle += (speed + extra) * dt;
      rotor.rotation.y = angle;
    });
  });
  hangChandelier(b, -3.2, -6.7, H, { scale: 0.7, drop: 1.3, intensity: 32, key: true });
  hangChandelier(b, 3.4, -6.7, H, { scale: 0.7, drop: 1.3, intensity: 32 });
  const inst = roomInstance(b, 'roulette', W, D, H);
  inst.onGameEvent = (tableId, event) => { if (event.type === 'spin') boosts.set(tableId, { at: now }); };
  return inst;
}
