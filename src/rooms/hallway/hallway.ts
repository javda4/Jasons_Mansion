import { TorusGeometry, type Material } from 'three/webgpu';
import type { MaterialKey } from '../../render/materials';
import { RoomBuilder, type ZoneInstance } from '../../world/roomBuilder';
import { borderedFloor, cofferedCeiling, hangChandelier, runner, wall, type DoorSpec } from '../shared/architecture';
import { HALL, LOBBY_DOOR, ROOM_DOOR, WALL } from '../shared/layout';
import { tableLamp, urn } from '../shared/props';

export interface HallLink {
  target?: string;
  prompt: string;
  plaque: string[];
  locked?: boolean;
}

/**
 * A gallery hallway (casino.png: "Hallway / to casino rooms"): walnut panelling, arched ribs,
 * sconces every bay, a crimson runner, and three doors — left, right and at the far end.
 *
 * Zone anchor: centre of the doorway on the lobby wall's inner face, floor level; the gallery
 * runs to local -Z. Game rooms attach at HALL_SLOTS (see layout.ts).
 */
export function buildHallway(
  id: string,
  name: string,
  materials: Record<MaterialKey, Material>,
  links: { left: HallLink; right: HallLink; end: HallLink; back: string },
): ZoneInstance {
  const b = new RoomBuilder(name, materials);
  const { width: W, length: L, height: H, sideBays } = HALL;
  const hw = W / 2;
  const door = (l: HallLink, doorId: string): DoorSpec => ({ id: doorId, prompt: l.prompt, target: l.target, locked: l.locked });

  borderedFloor(b, -hw, hw, -L, 0, { field: 'MAT_Wood_WalnutPolished', band: 'MAT_Marble_Nero', margin: 'MAT_Wood_WalnutDark', m: 0.25, bw: 0.12 });
  runner(b, 0, -WALL - 0.05, -L + 0.4, 2.0);
  cofferedCeiling(b, -hw, hw, -L, -WALL, H, 1.9);

  // entrance wall (the lobby's wall provides mass and jambs)
  wall(b, { pos: [hw, 0, -WALL], rotY: Math.PI }, W, H, { bays: 1, thickness: 0, jambs: false, openings: [{ bay: 0, ...LOBBY_DOOR }] });
  const side = { bays: sideBays, paintingBays: [1, 3], sconceAfter: [0, 1, 2, 3], sconceIntensity: 4 };
  wall(b, { pos: [-hw, 0, -WALL], rotY: Math.PI / 2 }, L - WALL, H, {
    ...side, openings: [{ bay: 2, ...ROOM_DOOR, plaque: links.left.plaque, door: door(links.left, 'Left') }],
  });
  wall(b, { pos: [hw, 0, -L], rotY: -Math.PI / 2 }, L - WALL, H, {
    ...side, openings: [{ bay: 2, ...ROOM_DOOR, plaque: links.right.plaque, door: door(links.right, 'Right') }],
  });
  wall(b, { pos: [-hw, 0, -L], rotY: 0 }, W, H, {
    bays: 1, openings: [{ bay: 0, ...ROOM_DOOR, plaque: links.end.plaque, door: door(links.end, 'End') }],
  });

  // arched ribs across the gallery at every pilaster
  const bay = (L - WALL) / sideBays;
  const r = hw - 0.12;
  for (let i = 1; i < sideBays; i++) {
    const z = -WALL - i * bay;
    b.add(new TorusGeometry(r, 0.07, 8, 40, Math.PI), 'MAT_Wood_WalnutPolished', { pos: [0, H - r - 0.02, z], scale: [1, 1, 2.6] });
    b.add(new TorusGeometry(r - 0.07, 0.018, 6, 40, Math.PI), 'MAT_Gold_Gilt', { pos: [0, H - r - 0.02, z] });
  }

  // console tables with lamps near the far end
  for (const [x, z, rot] of [[-hw + 0.25, -WALL - 4.5 * bay, Math.PI / 2], [hw - 0.25, -WALL - 4.5 * bay, -Math.PI / 2]] as const) {
    b.box([1.3, 0.05, 0.42], 'MAT_Marble_Nero', [x, 0.84, z], { rotY: rot });
    b.box([1.2, 0.14, 0.38], 'MAT_Wood_WalnutPolished', [x, 0.75, z], { rotY: rot });
    b.collider(`Console_${b.next()}`, [x - 0.22, 0, z - 0.65], [x + 0.22, 0.9, z + 0.65]);
    tableLamp(b, { pos: [x, 0.865, z + 0.35] }, 5);
    urn(b, { pos: [x, 0.865, z - 0.35] }, 0.3);
  }

  hangChandelier(b, 0, -WALL - 1.5 * bay, H, { scale: 0.5, drop: 0.95, intensity: 22, key: true });
  hangChandelier(b, 0, -WALL - 3.5 * bay, H, { scale: 0.5, drop: 0.95, intensity: 22 });

  const root = b.build();
  return {
    id, root, colliders: b.colliders, lights: b.lights, doors: b.doors, animate: b.animate,
    bounds: { id: `TRIGGER_${name}_Bounds`, min: { x: -hw, y: -1, z: -L }, max: { x: hw, y: H, z: 0 } },
    probe: { x: 0, y: 1.7, z: -L / 2 },
  };
}
