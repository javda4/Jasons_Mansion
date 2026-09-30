import { CylinderGeometry, type Material } from 'three/webgpu';
import type { MaterialKey } from '../../render/materials';
import { at, RoomBuilder, type ZoneInstance } from '../../world/roomBuilder';
import { FLOORS, hangChandelier, painting, roomInstance, roomShell } from '../shared/architecture';
import { ROOM_DOOR } from '../shared/layout';
import { baccaratTable, clubChair, feltMaterial, roundTable, tableLamp } from '../shared/props';

/**
 * Salon Baccarat (casino.png "Baccarat Room — Elegant & Refined"): gold damask, a single long
 * table on a marble floor behind velvet ropes, a grand tapestry on the back wall.
 */
export function buildBaccaratRoom(materials: Record<MaterialKey, Material>): ZoneInstance {
  const W = 12, D = 12, H = 5.8;
  const b = new RoomBuilder('Baccarat', materials);
  roomShell(b, {
    width: W, depth: D, height: H, field: 'MAT_Fabric_DamaskGold', floor: FLOORS.marble,
    entrance: ROOM_DOOR, bays: { side: 3, back: 3, front: 3 }, paintingBays: { left: [0, 2], right: [0, 2] },
  });
  // the tapestry: a large painted canvas centred on the back wall
  painting(b, at({ pos: [0, 3.0, -D + 0.12] }), 3.2, 2.6, 404);

  const felt = feltMaterial('baccarat', '#1a5230', Math.PI / 2);
  baccaratTable(b, { pos: [0, 0, -6.4] }, felt, 'baccarat_01');
  b.sound({ name: 'Cards', sound: 'cardFlick', position: { x: 0, y: 0.9, z: -6.4 }, gain: 0.3, mode: 'random', interval: [3, 8] });
  b.sound({ name: 'Chips', sound: 'chips', position: { x: 0, y: 0.9, z: -6.4 }, gain: 0.3, mode: 'random', interval: [6, 14] });
  // brass stanchions with velvet rope around the table
  const posts: [number, number][] = [];
  for (let i = 0; i < 14; i++) {
    const a = (i / 14) * Math.PI * 2;
    posts.push([Math.cos(a) * 3.7, -6.4 + Math.sin(a) * 2.6]);
  }
  posts.forEach(([x, z], i) => {
    if (i === 3 || i === 4) return; // opening facing the entrance
    b.instance('Stanchion', () => new CylinderGeometry(0.025, 0.025, 0.95, 10), 'MAT_Brass_Aged', { pos: [x, 0.475, z] }, true);
    b.instance('StanchionBase', () => new CylinderGeometry(0.14, 0.16, 0.04, 20), 'MAT_Brass_Aged', { pos: [x, 0.02, z] });
    b.instance('StanchionTop', () => new CylinderGeometry(0.04, 0.03, 0.06, 12), 'MAT_Gold_Gilt', { pos: [x, 0.97, z] });
    const [nx, nz] = posts[(i + 1) % posts.length];
    if (i === 2) return; // no rope across the opening
    const dx = nx - x, dz = nz - z, len = Math.hypot(dx, dz);
    b.instance('VelvetRope', () => new CylinderGeometry(0.018, 0.018, 1, 8).rotateX(Math.PI / 2), 'MAT_Fabric_VelvetRed',
      { pos: [(x + nx) / 2, 0.86, (z + nz) / 2], rotY: Math.atan2(dx, dz), scale: [1, 1, len] });
  });
  // seating by the entrance
  for (const x of [-4.2, 4.2]) {
    roundTable(b, { pos: [x, 0, -1.9] }, 0.3, 0.58);
    clubChair(b, { pos: [x, 0, -3.0], rotY: 0 });
    tableLamp(b, { pos: [x, 0.6, -1.9] }, 4);
  }
  hangChandelier(b, 0, -6.4, H, { scale: 1.0, drop: 1.15, intensity: 64, key: true });
  return roomInstance(b, 'baccarat', W, D, H);
}
