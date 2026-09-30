import { Color, CylinderGeometry, MeshStandardMaterial, type Material } from 'three/webgpu';
import type { MaterialKey } from '../../render/materials';
import { slotScreenTexture } from '../../render/proceduralArt';
import { RoomBuilder, type ZoneInstance } from '../../world/roomBuilder';
import { FLOORS, hangChandelier, roomInstance, roomShell } from '../shared/architecture';
import { ROOM_DOOR } from '../shared/layout';
import { slotMachine } from '../shared/props';

/**
 * Machines à Sous (casino.png "Slot Room — Jackpot Awaits"): rows of modular slot machines
 * (instanced — ~40 machines in a handful of draw calls) with glowing reel windows and chasing
 * topper lights, crimson carpet, a chandelier overhead.
 */
export function buildSlotRoom(materials: Record<MaterialKey, Material>): ZoneInstance {
  const W = 14, D = 14, H = 5.4;
  const b = new RoomBuilder('Slots', materials);
  roomShell(b, {
    width: W, depth: D, height: H, field: 'MAT_Fabric_DamaskOxblood', floor: FLOORS.crimsonCarpet,
    entrance: ROOM_DOOR, bays: { side: 4, back: 4, front: 3 }, paintingBays: { left: [1, 2], right: [1, 2] },
  });

  const screen = new MeshStandardMaterial({ color: 0x000000, emissive: 0xffffff, emissiveMap: slotScreenTexture(11), emissiveIntensity: 0.7, roughness: 0.2 });
  screen.name = 'MAT_Slot_Screen';
  const lights = new MeshStandardMaterial({ color: 0x000000, emissive: new Color(0xffb040), emissiveIntensity: 6 });
  lights.name = 'MAT_Slot_Lights';
  const hue = new Color();
  b.animate.push((t) => {
    hue.setHSL((0.08 + Math.sin(t * 0.6) * 0.06 + 1) % 1, 1, 0.55);
    lights.emissive.copy(hue);
    lights.emissiveIntensity = 5 + Math.sin(t * 5) * 1.5;
  });

  let slotCount = 0;
  const slotId = () => `slots_${String(++slotCount).padStart(2, '0')}`;
  // two back-to-back banks down the room plus a row along the back wall
  const pitch = 0.74;
  for (const bankX of [-3.3, 3.3]) {
    for (let k = 0; k < 7; k++) {
      const z = -3.6 - k * pitch;
      slotMachine(b, { pos: [bankX - 0.34, 0, z], rotY: -Math.PI / 2 }, screen, lights, slotId());
      slotMachine(b, { pos: [bankX + 0.34, 0, z], rotY: Math.PI / 2 }, screen, lights, slotId());
      for (const side of [-1, 1]) {
        b.instance('SlotStool', () => new CylinderGeometry(0.2, 0.2, 0.1, 20), 'MAT_Fabric_VelvetRed', { pos: [bankX + side * 1.15, 0.66, z] }, true);
        b.instance('SlotStoolStem', () => new CylinderGeometry(0.03, 0.12, 0.62, 12), 'MAT_Brass_Aged', { pos: [bankX + side * 1.15, 0.31, z] });
      }
    }
  }
  for (let k = 0; k < 12; k++) {
    const x = -4.1 + k * pitch;
    slotMachine(b, { pos: [x, 0, -D + 0.5], rotY: 0 }, screen, lights, slotId());
    b.instance('SlotStool', () => new CylinderGeometry(0.2, 0.2, 0.1, 20), 'MAT_Fabric_VelvetRed', { pos: [x, 0.66, -D + 1.55] }, true);
    b.instance('SlotStoolStem', () => new CylinderGeometry(0.03, 0.12, 0.62, 12), 'MAT_Brass_Aged', { pos: [x, 0.31, -D + 1.55] });
  }
  for (const x of [-3.3, 3.3]) b.sound({ name: `Chime_${x < 0 ? 'L' : 'R'}`, sound: 'slotChime', position: { x, y: 1.5, z: -5.8 }, gain: 0.25, mode: 'random', interval: [2, 6] });
  // a little coloured spill from the machines onto the carpet
  for (const x of [-3.3, 3.3]) {
    b.light({ name: `SlotGlow_${b.next()}`, kind: 'point', position: { x, y: 1.6, z: -5.8 }, color: 0xff7a3a, intensity: 5, range: 6 });
  }
  hangChandelier(b, 0, -7, H, { scale: 0.85, drop: 1.4, intensity: 40, key: true });
  return roomInstance(b, 'slots', W, D, H);
}
