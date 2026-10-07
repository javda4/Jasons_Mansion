/**
 * World placement of a zone (Y-up, rotation about Y), as written by the asset build from the master layout
 * `blender/zones.json` into the manifest. Rotations are multiples of 90° (colliders stay axis-aligned).
 */
export interface Transform2 { x: number; z: number; rotY: number }
