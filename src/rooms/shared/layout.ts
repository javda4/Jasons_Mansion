/**
 * Mansion layout constants shared by the zone manifest and the zone builders.
 * (In Phase 2 these come from the Blender master layout via the generated manifest.)
 */
export const WALL = 0.3;

export const LOBBY = {
  x0: -8, x1: 8, zFront: 4, zBack: -20, height: 7.2,
  landingY: 2.04, stairZ0: -12, stairRun: 0.34, stairRise: 0.17, stairSteps: 12, stairHalf: 2.6,
  sideBays: 6,
} as const;
export const LOBBY_STAIR_Z1 = LOBBY.stairZ0 - LOBBY.stairSteps * LOBBY.stairRun;
const lobbySideBay = (LOBBY.zFront - LOBBY_STAIR_Z1) / LOBBY.sideBays;
/** Both hallway doorways sit in side-wall bay 2 (left) / 3 (right) — the same world Z. */
export const LOBBY_DOOR_Z = LOBBY.zFront - 2.5 * lobbySideBay;
export const LOBBY_DOOR = { width: 2.6, height: 3.6 } as const;

export const HALL = { width: 3.8, length: 20, height: 4.9, sideBays: 5 } as const;
const hallBay = (HALL.length - WALL) / HALL.sideBays;
/** Side doors are in bay 2 of both hallway walls, i.e. this local Z. */
export const HALL_SIDE_DOOR_Z = -WALL - 2.5 * hallBay;
export const ROOM_DOOR = { width: 2.2, height: 3.1 } as const;

export interface Transform2 { x: number; z: number; rotY: number }

/** world = parent ∘ local (Y-up, rotations about Y). */
export function compose(parent: Transform2, local: Transform2): Transform2 {
  const c = Math.cos(parent.rotY), s = Math.sin(parent.rotY);
  return {
    x: parent.x + local.x * c + local.z * s,
    z: parent.z - local.x * s + local.z * c,
    rotY: parent.rotY + local.rotY,
  };
}

/** Where the galleries attach to the lobby (its doorways on the west/east walls). */
export const LOBBY_SLOTS = {
  west: { x: -8, z: LOBBY_DOOR_Z, rotY: Math.PI / 2 },
  east: { x: 8, z: LOBBY_DOOR_Z, rotY: -Math.PI / 2 },
} as const satisfies Record<string, Transform2>;

/** Where a room attaches to a hallway (room-local origin = its entrance threshold, facing -Z). */
export const HALL_SLOTS = {
  left: { x: -(HALL.width / 2 + WALL), z: HALL_SIDE_DOOR_Z, rotY: Math.PI / 2 },
  right: { x: HALL.width / 2 + WALL, z: HALL_SIDE_DOOR_Z, rotY: -Math.PI / 2 },
  end: { x: 0, z: -(HALL.length + WALL), rotY: 0 },
} as const satisfies Record<string, Transform2>;
