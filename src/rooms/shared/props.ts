import {
  BoxGeometry,
  Color,
  MeshBasicMaterial,
  CylinderGeometry,
  Mesh,
  MeshPhysicalMaterial,
  PlaneGeometry,
  type Material,
  LatheGeometry,
  OctahedronGeometry,
  SphereGeometry,
  TorusGeometry,
  Vector2,
  type Matrix4,
} from 'three/webgpu';
import { at, meterBox, point, RoomBuilder, type Place } from '../../world/roomBuilder';
import { feltPrintTexture } from '../../render/proceduralArt';
import type { CasinoTableExtras, GameType } from '../../interaction/schema';

export { feltMaterial };

/**
 * Phase 1 code-built props. Each is a stand-in for a Blender linked-library asset (§6):
 * repeated parts go through `b.instance()` so the runtime draws them with one InstancedMesh.
 */

const lathe = (pts: [number, number][], seg = 24) => new LatheGeometry(pts.map(([x, y]) => new Vector2(x, y)), seg);

// ---------------------------------------------------------------- lights
/** Warm incandescent (≈2700 K). Units are physical: candela for point lights. */
export const WARM = 0xffb070;
export const CANDLE = 0xff9d52;

// ---------------------------------------------------------------- chandelier
/** A two-tier Belle Époque crystal chandelier. Built into its own group so it can sway. */
export function chandelier(b: RoomBuilder, scale = 1): void {
  const s = scale;
  // stem from ceiling
  b.add(new CylinderGeometry(0.025 * s, 0.025 * s, 1.2 * s, 10), 'MAT_Brass_Aged', { pos: [0, 0.6 * s, 0] });
  b.add(lathe([[0, -0.9], [0.1, -0.85], [0.16, -0.7], [0.09, -0.5], [0.14, -0.3], [0.2, -0.1], [0.12, 0.05], [0.05, 0.1], [0, 0.12]].map(([x, y]) => [x * s, y * s] as [number, number])), 'MAT_Gold_Gilt', { pos: [0, 0, 0] });
  // canopy at ceiling
  b.add(lathe([[0, 0], [0.32, 0], [0.26, -0.08], [0.1, -0.16], [0, -0.16]].map(([x, y]) => [x * s, y * s] as [number, number])), 'MAT_Gold_Gilt', { pos: [0, 1.25 * s, 0] });

  const tiers = [
    { r: 1.05, y: -0.55, n: 14 },
    { r: 0.66, y: -0.05, n: 9 },
    { r: 0.34, y: 0.35, n: 6 },
  ];
  for (const t of tiers) {
    const R = t.r * s, Y = t.y * s;
    b.add(new TorusGeometry(R, 0.022 * s, 8, 64), 'MAT_Gold_Gilt', { pos: [0, Y, 0], rot: [Math.PI / 2, 0, 0] });
    b.add(new TorusGeometry(R * 0.55, 0.012 * s, 6, 48), 'MAT_Gold_Gilt', { pos: [0, Y + 0.02 * s, 0], rot: [Math.PI / 2, 0, 0] });
    for (let i = 0; i < t.n; i++) {
      const a = (i / t.n) * Math.PI * 2;
      const x = Math.cos(a) * R, z = Math.sin(a) * R;
      // arm spoke back to the body
      b.add(new CylinderGeometry(0.01 * s, 0.01 * s, R, 6), 'MAT_Gold_Gilt', { pos: [x / 2, Y, z / 2], rot: [0, -a, Math.PI / 2] });
      b.instance('ChandelierCup', () => lathe([[0, 0], [0.045, 0.0], [0.05, 0.04], [0.03, 0.06], [0, 0.06]], 12), 'MAT_Gold_Gilt', { pos: [x, Y + 0.02 * s, z], scale: [s, s, s] });
      b.instance('ChandelierCandle', () => new CylinderGeometry(0.014, 0.014, 0.14, 10), 'MAT_Fabric_LampShade', { pos: [x, Y + 0.15 * s, z], scale: [s, s, s] });
      b.instance('ChandelierFlame', () => new SphereGeometry(0.02, 10, 8), 'MAT_Emissive_Candle', { pos: [x, Y + 0.245 * s, z], scale: [s, s * 1.8, s] });
      // hanging crystal strand + pendant
      for (let k = 0; k < 4; k++) {
        b.instance('Crystal', () => new OctahedronGeometry(0.022, 0), 'MAT_Crystal_Clear', { pos: [x * 0.97, Y - (0.05 + k * 0.055) * s, z * 0.97], scale: [s, s * 1.5, s] });
      }
      b.instance('CrystalPendant', () => new OctahedronGeometry(0.035, 0), 'MAT_Crystal_Clear', { pos: [x * 0.97, Y - 0.3 * s, z * 0.97], scale: [s * 0.7, s * 2.2, s * 0.7] });
      // swag between arms: crystals along a sagging arc
      const a2 = ((i + 1) / t.n) * Math.PI * 2;
      for (let k = 1; k < 6; k++) {
        const u = k / 6;
        const aa = a + (a2 - a) * u;
        const sag = Math.sin(u * Math.PI) * 0.16 * s;
        b.instance('Crystal', () => new OctahedronGeometry(0.022, 0), 'MAT_Crystal_Clear', { pos: [Math.cos(aa) * R * 0.99, Y - 0.03 * s - sag, Math.sin(aa) * R * 0.99], scale: [s * 0.8, s, s * 0.8] });
      }
    }
  }
  // crystal cascade below the body
  for (let ring = 0; ring < 7; ring++) {
    const rr = (0.55 - ring * 0.07) * s;
    const n = Math.max(6, Math.round(26 - ring * 3));
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2 + ring * 0.3;
      b.instance('Crystal', () => new OctahedronGeometry(0.022, 0), 'MAT_Crystal_Clear', { pos: [Math.cos(a) * rr, (-0.75 - ring * 0.09) * s, Math.sin(a) * rr], scale: [s, s * 1.6, s] });
    }
  }
  b.instance('CrystalPendant', () => new OctahedronGeometry(0.035, 0), 'MAT_Crystal_Clear', { pos: [0, -1.5 * s, 0], scale: [s * 1.6, s * 3.2, s * 1.6] });
}

// ---------------------------------------------------------------- sconce
/** Two-arm wall sconce with small silk shades, mounted on a wall facing local +Z. */
export function sconce(b: RoomBuilder, place: Place | Matrix4): void {
  b.instance('SconcePlate', () => lathe([[0, 0], [0.07, 0], [0.09, 0.08], [0.06, 0.22], [0.08, 0.32], [0.02, 0.4], [0, 0.4]], 16), 'MAT_Gold_Gilt', at(place, { pos: [0, -0.2, 0.02], rot: [0, 0, 0], scale: [1, 1, 0.35] }));
  for (const side of [-1, 1]) {
    b.instance('SconceArm', () => new TorusGeometry(0.13, 0.012, 6, 16, Math.PI), 'MAT_Gold_Gilt', at(place, { pos: [side * 0.13, -0.05, 0.1], rot: [0, 0, side > 0 ? Math.PI : 0] }));
    b.instance('SconceCup', () => lathe([[0, 0], [0.035, 0], [0.04, 0.03], [0, 0.03]], 12), 'MAT_Gold_Gilt', at(place, { pos: [side * 0.26, -0.05, 0.1] }));
    b.instance('SconceCandle', () => new CylinderGeometry(0.012, 0.012, 0.1, 8), 'MAT_Fabric_LampShade', at(place, { pos: [side * 0.26, 0.03, 0.1] }));
    b.instance('SconceShade', () => new CylinderGeometry(0.045, 0.085, 0.12, 20, 1, true), 'MAT_Fabric_LampShade', at(place, { pos: [side * 0.26, 0.13, 0.1] }));
    b.instance('SconceFlame', () => new SphereGeometry(0.016, 8, 6), 'MAT_Emissive_Candle', at(place, { pos: [side * 0.26, 0.095, 0.1], scale: [1, 1.7, 1] }));
  }
}

// ---------------------------------------------------------------- seating
/** Deep leather club chair, origin at floor centre, facing local +Z. */
export function clubChair(b: RoomBuilder, place: Place): void {
  const P = (local: Place) => at(place, local);
  b.instance('ChairSeat', () => roundedBox(0.62, 0.2, 0.58), 'MAT_Leather_Oxblood', P({ pos: [0, 0.42, 0.04] }), true);
  b.instance('ChairBase', () => meterBox(0.72, 0.28, 0.7), 'MAT_Leather_Oxblood', P({ pos: [0, 0.22, 0] }), true);
  b.instance('ChairBack', () => new CylinderGeometry(0.38, 0.36, 0.52, 24, 1, false, Math.PI * 0.62, Math.PI * 0.76), 'MAT_Leather_Oxblood', P({ pos: [0, 0.62, 0.04], scale: [1, 1, 0.95] }), true);
  for (const side of [-1, 1]) {
    b.instance('ChairArm', () => new CylinderGeometry(0.07, 0.07, 0.64, 16), 'MAT_Leather_Oxblood', P({ pos: [side * 0.32, 0.58, 0.02], rot: [Math.PI / 2, 0, 0] }), true);
    b.instance('ChairArmSide', () => meterBox(0.14, 0.3, 0.64), 'MAT_Leather_Oxblood', P({ pos: [side * 0.32, 0.42, 0.02] }), true);
  }
  for (const [x, z] of [[-0.3, -0.28], [0.3, -0.28], [-0.3, 0.3], [0.3, 0.3]]) {
    b.instance('ChairFoot', () => new CylinderGeometry(0.025, 0.018, 0.08, 8), 'MAT_Wood_WalnutDark', P({ pos: [x, 0.04, z] }));
  }
  const m = toWorld(place);
  b.collider(`Chair_${b.colliders.length}`, [m[0] - 0.36, 0, m[2] - 0.36], [m[0] + 0.36, 0.95, m[2] + 0.36]);
}

/** Casino dining chair (for game tables), origin at floor centre, facing local +Z. */
export function tableChair(b: RoomBuilder, place: Place): void {
  const P = (local: Place) => at(place, local);
  b.instance('TChairSeat', () => roundedBox(0.46, 0.1, 0.44), 'MAT_Fabric_VelvetRed', P({ pos: [0, 0.48, 0] }), true);
  b.instance('TChairBack', () => roundedBox(0.44, 0.52, 0.07), 'MAT_Fabric_VelvetRed', P({ pos: [0, 0.8, -0.22], rot: [-0.12, 0, 0] }), true);
  b.instance('TChairFrame', () => meterBox(0.48, 0.05, 0.46), 'MAT_Wood_WalnutPolished', P({ pos: [0, 0.42, 0] }), true);
  for (const [x, z] of [[-0.2, -0.19], [0.2, -0.19], [-0.2, 0.19], [0.2, 0.19]]) {
    b.instance('TChairLeg', () => new CylinderGeometry(0.022, 0.016, 0.42, 8), 'MAT_Wood_WalnutPolished', P({ pos: [x, 0.21, z] }), true);
  }
}

// ---------------------------------------------------------------- tables
/** Half-moon blackjack table, flat (dealer) side on local -Z, players around local +Z. */
export function blackjackTable(b: RoomBuilder, place: Place): void {
  const P = (local: Place) => at(place, local);
  const R = 1.25;
  b.add(new CylinderGeometry(R, R, 0.04, 64, 1, false, -Math.PI / 2, Math.PI), 'MAT_Fabric_FeltGreen', P({ pos: [0, 0.78, 0] }));
  b.add(new CylinderGeometry(R + 0.02, R - 0.1, 0.16, 64, 1, false, -Math.PI / 2, Math.PI), 'MAT_Wood_WalnutPolished', P({ pos: [0, 0.68, 0] }));
  b.add(new TorusGeometry(R + 0.03, 0.055, 12, 64, Math.PI), 'MAT_Leather_Oxblood', P({ pos: [0, 0.8, 0], rot: [Math.PI / 2, 0, 0] }));
  b.add(new TorusGeometry(R - 0.03, 0.008, 6, 64, Math.PI), 'MAT_Gold_Gilt', P({ pos: [0, 0.802, 0], rot: [Math.PI / 2, 0, 0] }));
  b.add(meterBox(2 * R + 0.1, 0.2, 0.18), 'MAT_Wood_WalnutPolished', P({ pos: [0, 0.7, -0.05] }));
  b.add(meterBox(0.9, 0.08, 0.3), 'MAT_Wood_WalnutDark', P({ pos: [0, 0.82, 0.12] })); // chip tray
  b.add(new CylinderGeometry(0.28, 0.4, 0.62, 24), 'MAT_Wood_WalnutDark', P({ pos: [0, 0.31, 0.3] }));
  // players' chairs around the arc
  for (let i = 0; i < 5; i++) {
    const a = -Math.PI / 2 + ((i + 0.5) / 5) * Math.PI;
    const px = Math.sin(a) * (R + 0.55), pz = Math.cos(a) * (R + 0.55);
    tableChair(b, { pos: localToWorld(place, [px, 0, pz]), rotY: (place.rotY ?? 0) + a + Math.PI });
  }
  const c = toWorld(place);
  b.collider(`Table_${b.colliders.length}`, [c[0] - 1.3, 0, c[2] - 1.3], [c[0] + 1.3, 0.85, c[2] + 1.3]);
}

/** Round pedestal table with a marble top. */
export function roundTable(b: RoomBuilder, place: Place, radius = 0.45, height = 0.72, collide = true): void {
  const P = (local: Place) => at(place, local);
  b.add(new CylinderGeometry(radius, radius, 0.04, 48), 'MAT_Marble_Nero', P({ pos: [0, height, 0] }));
  b.add(new TorusGeometry(radius, 0.018, 8, 48), 'MAT_Gold_Gilt', P({ pos: [0, height, 0], rot: [Math.PI / 2, 0, 0] }));
  b.add(lathe([[0, 0], [radius * 0.55, 0], [radius * 0.5, 0.05], [0.07, 0.14], [0.05, height * 0.5], [0.08, height * 0.8], [0.1, height - 0.02], [0, height - 0.02]], 24), 'MAT_Wood_WalnutPolished', P({ pos: [0, 0, 0] }));
  if (collide) {
    const c = toWorld(place);
    b.collider(`RoundTable_${b.colliders.length}`, [c[0] - radius, 0, c[2] - radius], [c[0] + radius, height + 0.02, c[2] + radius]);
  }
}

/** Table lamp with silk shade; declares its light. */
export function tableLamp(b: RoomBuilder, place: Place, intensity = 6): void {
  const P = (local: Place) => at(place, local);
  b.instance('LampBase', () => lathe([[0, 0], [0.09, 0], [0.1, 0.03], [0.05, 0.08], [0.07, 0.2], [0.03, 0.3], [0.015, 0.44], [0, 0.44]], 20), 'MAT_Brass_Aged', P({ pos: [0, 0, 0] }), true);
  b.instance('LampShade', () => new CylinderGeometry(0.12, 0.22, 0.26, 32, 1, true), 'MAT_Fabric_LampShade', P({ pos: [0, 0.54, 0] }));
  b.instance('LampBulb', () => new SphereGeometry(0.035, 10, 8), 'MAT_Emissive_Candle', P({ pos: [0, 0.48, 0] }));
  b.light({ name: `TableLamp_${b.next()}`, kind: 'point', position: point(place, [0, 0.5, 0]), color: WARM, intensity, range: 6 });
}

/** Gilded urn (placeholder for a floral centrepiece). */
export function urn(b: RoomBuilder, place: Place, h = 0.6): void {
  b.add(lathe([[0, 0], [0.12, 0], [0.13, 0.03], [0.07, 0.08], [0.08, 0.14], [0.2, 0.3], [0.22, 0.42], [0.16, 0.52], [0.19, 0.58], [0.2, 0.6], [0, 0.6]].map(([x, y]) => [x * h / 0.6, y * h / 0.6] as [number, number]), 32), 'MAT_Gold_Gilt', at(place));
}

// ---------------------------------------------------------------- architecture pieces
/** Turned baluster, origin at its foot. */
export function balusterGeometry(h = 0.78) {
  return lathe([[0, 0], [0.05, 0], [0.05, 0.06], [0.03, 0.09], [0.028, 0.18], [0.05, 0.34], [0.055, 0.42], [0.03, 0.56], [0.022, 0.66], [0.04, 0.7], [0.04, h], [0, h]], 12);
}

/** Tall panelled double door (closed), origin at floor centre of the opening, facing local +Z. */
export function grandDoor(b: RoomBuilder, place: Place | Matrix4, w = 2.2, h = 3.3): void {
  const P = (local: Place) => at(place, local);
  // architrave
  b.add(meterBox(w + 0.5, 0.3, 0.14), 'MAT_Gold_Gilt', P({ pos: [0, h + 0.15, 0.05] }));
  b.add(meterBox(w + 0.8, 0.12, 0.2), 'MAT_Wood_WalnutPolished', P({ pos: [0, h + 0.36, 0.06] }));
  b.add(lathe([[0, 0], [0.22, 0], [0.26, 0.1], [0.18, 0.28], [0.08, 0.36], [0, 0.4]], 20), 'MAT_Gold_Gilt', P({ pos: [0, h + 0.42, 0.12], scale: [1.2, 1, 0.3] }));
  for (const side of [-1, 1]) {
    b.add(meterBox(0.22, h + 0.3, 0.16), 'MAT_Wood_WalnutPolished', P({ pos: [side * (w / 2 + 0.11), (h + 0.3) / 2, 0.05] }));
    b.add(meterBox(0.04, h + 0.2, 0.04), 'MAT_Gold_Gilt', P({ pos: [side * (w / 2 + 0.03), (h + 0.2) / 2, 0.14] }));
  }
  // two leaves with raised, gilt-edged panels
  const lw = w / 2;
  for (const side of [-1, 1]) {
    const cx = side * lw / 2;
    b.add(meterBox(lw - 0.01, h, 0.08), 'MAT_Wood_WalnutDark', P({ pos: [cx, h / 2, 0.02] }));
    const panels: [number, number][] = [[0.35, 0.9], [1.35, 1.5], [2.95, 0.5]];
    for (const [y0, ph] of panels) {
      if (y0 + ph > h - 0.1) continue;
      b.add(meterBox(lw - 0.26, ph, 0.03), 'MAT_Wood_WalnutPolished', P({ pos: [cx, y0 + ph / 2, 0.075] }));
      frame(b, P({ pos: [cx, y0 + ph / 2, 0.09] }), lw - 0.22, ph + 0.04, 0.02);
    }
    b.instance('DoorHandle', () => lathe([[0, 0], [0.018, 0], [0.03, 0.05], [0.015, 0.14], [0.03, 0.2], [0, 0.22]], 12), 'MAT_Gold_Gilt', P({ pos: [side * 0.09, 1.02, 0.1], rot: [0, 0, 0] }));
  }
}

/** Rectangular gilt frame (four thin bars) centred at `place`, lying in local XY. */
export function frame(b: RoomBuilder, place: Place | Matrix4, w: number, h: number, t: number): void {
  b.add(meterBox(w, t, t), 'MAT_Gold_Gilt', at(place, { pos: [0, h / 2 - t / 2, 0] }));
  b.add(meterBox(w, t, t), 'MAT_Gold_Gilt', at(place, { pos: [0, -h / 2 + t / 2, 0] }));
  b.add(meterBox(t, h, t), 'MAT_Gold_Gilt', at(place, { pos: [w / 2 - t / 2, 0, 0] }));
  b.add(meterBox(t, h, t), 'MAT_Gold_Gilt', at(place, { pos: [-w / 2 + t / 2, 0, 0] }));
}

// ---------------------------------------------------------------- helpers
function roundedBox(w: number, h: number, d: number) {
  // cheap "upholstered" look: a box with slightly domed top via a flattened sphere cap
  const g = new SphereGeometry(0.5, 20, 12);
  g.scale(w, h * 1.6, d);
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    // flatten sides towards a box so it reads as a cushion
    const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    const k = 1.35;
    pos.setXYZ(i, Math.sign(x) * Math.min(Math.abs(x) * k, w / 2), Math.sign(y) * Math.min(Math.abs(y), h / 2), Math.sign(z) * Math.min(Math.abs(z) * k, d / 2));
  }
  g.computeVertexNormals();
  return g;
}

function toWorld(p: Place): [number, number, number] {
  return p.pos;
}

function localToWorld(p: Place, local: [number, number, number]): [number, number, number] {
  const a = p.rotY ?? 0;
  const c = Math.cos(a), s = Math.sin(a);
  return [p.pos[0] + local[0] * c + local[2] * s, p.pos[1] + local[1], p.pos[2] - local[0] * s + local[2] * c];
}

// ================================================================ game-room furniture
// Visual only: tables are set dressing until Phase 5 attaches `casinoTable` extras + game sessions.

/** Mesh with its own (non-library) material, e.g. printed felt or a screen texture. */
export function uniqueMesh(b: RoomBuilder, geo: import('three/webgpu').BufferGeometry, mat: Material, place: Place | Matrix4, name: string): Mesh {
  const mesh = new Mesh(geo, mat);
  mesh.applyMatrix4(at(place));
  mesh.name = name;
  mesh.receiveShadow = true;
  b.root.add(mesh);
  return mesh;
}

function feltMaterial(kind: 'blackjack' | 'baccarat' | 'poker', base: string, rotation: number): MeshPhysicalMaterial {
  const tex = feltPrintTexture(kind, base);
  tex.center.set(0.5, 0.5);
  tex.rotation = rotation;
  const m = new MeshPhysicalMaterial({ map: tex, roughness: 0.95, sheen: 0.5, sheenColor: new Color(0x4a9a60), sheenRoughness: 0.8 });
  m.name = `MAT_Felt_${kind}`;
  return m;
}

/** Oval poker table seating eight, long axis on local X. */
export function pokerTable(b: RoomBuilder, place: Place, felt: Material, tableId: string): void {
  const P = (local: Place) => at(place, local);
  const sx = 1.75, R = 0.78;
  uniqueMesh(b, new CylinderGeometry(R, R, 0.04, 64), felt, P({ pos: [0, 0.78, 0], scale: [sx, 1, 1] }), `TABLE_${b.zone}_${b.next()}_Felt`);
  b.add(new CylinderGeometry(R + 0.04, R - 0.08, 0.16, 64), 'MAT_Wood_WalnutPolished', P({ pos: [0, 0.68, 0], scale: [sx, 1, 1] }));
  b.add(new TorusGeometry(R + 0.06, 0.07, 12, 72), 'MAT_Leather_Oxblood', P({ pos: [0, 0.8, 0], rot: [Math.PI / 2, 0, 0], scale: [sx, 1, 1] }));
  b.add(new TorusGeometry(R - 0.12, 0.008, 6, 72), 'MAT_Gold_Gilt', P({ pos: [0, 0.802, 0], rot: [Math.PI / 2, 0, 0], scale: [sx * 0.97, 1, 1] }));
  b.add(new CylinderGeometry(0.3, 0.45, 0.62, 24), 'MAT_Wood_WalnutDark', P({ pos: [0, 0.31, 0], scale: [1.8, 1, 1] }));
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2 + Math.PI / 8;
    const px = Math.cos(a) * (R * sx + 0.5), pz = Math.sin(a) * (R + 0.55);
    tableChair(b, { pos: localToWorld(place, [px, 0, pz]), rotY: (place.rotY ?? 0) + Math.atan2(-px, -pz) });
  }
  // chip stacks for life
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2;
    const h = 0.02 + (i % 3) * 0.012;
    b.instance('ChipStack', () => new CylinderGeometry(0.02, 0.02, 1, 16), i % 2 ? 'MAT_Marble_Rosso' : 'MAT_Marble_Nero',
      P({ pos: [Math.cos(a) * R * sx * 0.72, 0.8 + h / 2, Math.sin(a) * R * 0.62], scale: [1, h, 1] }));
  }
  b.colliderBox(`Table_${b.next()}`, place, [-R * sx - 0.1, 0, -R - 0.1], [R * sx + 0.1, 0.9, R + 0.1]);
  tableVolume(b, 'poker', tableId, [2 * R * sx + 0.3, 1.1, 2 * R + 0.3], at(place, { pos: [0, 0.55, 0] }));
}

/** Half-moon blackjack table with printed felt, flat (dealer) side on local -Z. */
export function blackjackTablePrinted(b: RoomBuilder, place: Place, felt: Material, tableId: string): void {
  const P = (local: Place) => at(place, local);
  const R = 1.25;
  uniqueMesh(b, new CylinderGeometry(R, R, 0.04, 64, 1, false, -Math.PI / 2, Math.PI), felt, P({ pos: [0, 0.78, 0] }), `TABLE_${b.zone}_${b.next()}_Felt`);
  b.add(new CylinderGeometry(R + 0.02, R - 0.1, 0.16, 64, 1, false, -Math.PI / 2, Math.PI), 'MAT_Wood_WalnutPolished', P({ pos: [0, 0.68, 0] }));
  b.add(new TorusGeometry(R + 0.03, 0.055, 12, 64, Math.PI), 'MAT_Leather_Oxblood', P({ pos: [0, 0.8, 0], rot: [Math.PI / 2, 0, 0] }));
  b.add(meterBox(2 * R + 0.1, 0.2, 0.18), 'MAT_Wood_WalnutPolished', P({ pos: [0, 0.7, -0.05] }));
  b.add(meterBox(0.9, 0.06, 0.28), 'MAT_Wood_WalnutDark', P({ pos: [0, 0.82, 0.14] }));
  for (let i = 0; i < 12; i++) {
    b.instance('ChipTray', () => new CylinderGeometry(0.019, 0.019, 0.16, 12), i % 3 === 0 ? 'MAT_Marble_Rosso' : i % 3 === 1 ? 'MAT_Marble_Nero' : 'MAT_Gold_Gilt',
      P({ pos: [-0.38 + i * 0.07, 0.87, 0.14], rot: [Math.PI / 2, 0, 0] }));
  }
  b.instance('CardShoe', () => meterBox(0.16, 0.1, 0.3), 'MAT_Wood_WalnutDark', P({ pos: [0.75, 0.85, 0.2], rotY: 0.3 }));
  b.add(new CylinderGeometry(0.28, 0.4, 0.62, 24), 'MAT_Wood_WalnutDark', P({ pos: [0, 0.31, 0.3] }));
  for (let i = 0; i < 5; i++) {
    const a = -Math.PI / 2 + ((i + 0.5) / 5) * Math.PI;
    const px = Math.sin(a) * (R + 0.55), pz = Math.cos(a) * (R + 0.55);
    tableChair(b, { pos: localToWorld(place, [px, 0, pz]), rotY: (place.rotY ?? 0) + a + Math.PI });
  }
  b.colliderBox(`Table_${b.next()}`, place, [-R - 0.05, 0, -0.2], [R + 0.05, 0.9, R + 0.05]);
  tableVolume(b, 'blackjack', tableId, [2 * R + 0.3, 1.1, R + 0.5], at(place, { pos: [0, 0.55, R / 2] }));
}

/** Kidney-ended baccarat table: long oval for 12 with printed felt. */
export function baccaratTable(b: RoomBuilder, place: Place, felt: Material, tableId: string): void {
  const P = (local: Place) => at(place, local);
  const sx = 2.1, R = 0.95;
  uniqueMesh(b, new CylinderGeometry(R, R, 0.04, 72), felt, P({ pos: [0, 0.78, 0], scale: [sx, 1, 1] }), `TABLE_${b.zone}_${b.next()}_Felt`);
  b.add(new CylinderGeometry(R + 0.04, R - 0.08, 0.16, 72), 'MAT_Wood_WalnutPolished', P({ pos: [0, 0.68, 0], scale: [sx, 1, 1] }));
  b.add(new TorusGeometry(R + 0.06, 0.07, 12, 80), 'MAT_Leather_Oxblood', P({ pos: [0, 0.8, 0], rot: [Math.PI / 2, 0, 0], scale: [sx, 1, 1] }));
  b.add(new TorusGeometry(R + 0.13, 0.012, 6, 80), 'MAT_Gold_Gilt', P({ pos: [0, 0.76, 0], rot: [Math.PI / 2, 0, 0], scale: [sx * 0.985, 1, 1] }));
  b.add(new CylinderGeometry(0.35, 0.5, 0.62, 24), 'MAT_Wood_WalnutDark', P({ pos: [-0.9, 0.31, 0] }));
  b.add(new CylinderGeometry(0.35, 0.5, 0.62, 24), 'MAT_Wood_WalnutDark', P({ pos: [0.9, 0.31, 0] }));
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2 + Math.PI / 12;
    if (Math.abs(Math.sin(a)) > 0.9 && Math.sin(a) < 0) continue; // croupier's seat gap
    const px = Math.cos(a) * (R * sx + 0.5), pz = Math.sin(a) * (R + 0.6);
    tableChair(b, { pos: localToWorld(place, [px, 0, pz]), rotY: (place.rotY ?? 0) + Math.atan2(-px, -pz) });
  }
  b.colliderBox(`Table_${b.next()}`, place, [-R * sx - 0.1, 0, -R - 0.1], [R * sx + 0.1, 0.9, R + 0.1]);
  tableVolume(b, 'baccarat', tableId, [2 * R * sx + 0.3, 1.1, 2 * R + 0.3], at(place, { pos: [0, 0.55, 0] }));
}

/** Roulette table: wheel bowl at local -X end, betting layout along +X. Returns the rotor to spin. */
export function rouletteTable(b: RoomBuilder, place: Place, wheelMat: Material, layoutMat: Material, tableId: string): Mesh {
  const P = (local: Place) => at(place, local);
  const L = 3.2, W = 1.35;
  // cabinet
  b.add(meterBox(L, 0.12, W), 'MAT_Wood_WalnutPolished', P({ pos: [0.2, 0.72, 0] }));
  b.add(meterBox(L - 0.3, 0.6, W - 0.35), 'MAT_Wood_WalnutDark', P({ pos: [0.2, 0.36, 0] }));
  b.add(meterBox(L + 0.08, 0.06, W + 0.08), 'MAT_Leather_Oxblood', P({ pos: [0.2, 0.81, 0] }));
  const layout = new PlaneGeometry(L - 1.3, W - 0.2);
  uniqueMesh(b, layout, layoutMat, P({ pos: [0.75, 0.842, 0], rot: [-Math.PI / 2, 0, 0] }), `TABLE_${b.zone}_${b.next()}_Layout`);
  // wheel bowl
  const wx = 0.2 - L / 2 + 0.55;
  b.add(lathe([[0, 0], [0.5, 0], [0.56, 0.06], [0.56, 0.14], [0.52, 0.16], [0.44, 0.12], [0.36, 0.1], [0, 0.1]], 48), 'MAT_Wood_WalnutPolished', P({ pos: [wx, 0.78, 0] }));
  b.add(new TorusGeometry(0.54, 0.018, 8, 64), 'MAT_Gold_Gilt', P({ pos: [wx, 0.94, 0], rot: [Math.PI / 2, 0, 0] }));
  const rotor = uniqueMesh(b, new CylinderGeometry(0.38, 0.4, 0.05, 64), wheelMat, P({ pos: [wx, 0.9, 0] }), `PROP_${b.zone}_RouletteRotor_${b.next()}`);
  b.add(lathe([[0, 0], [0.05, 0], [0.03, 0.06], [0.012, 0.12], [0.03, 0.14], [0, 0.17]], 16), 'MAT_Gold_Gilt', P({ pos: [wx, 0.92, 0] }));
  // player chairs along the layout's long side
  for (let i = 0; i < 4; i++) {
    tableChair(b, { pos: localToWorld(place, [-0.2 + i * 0.62, 0, W / 2 + 0.55]), rotY: (place.rotY ?? 0) + Math.PI });
  }
  b.colliderBox(`Table_${b.next()}`, place, [0.2 - L / 2 - 0.05, 0, -W / 2 - 0.05], [0.2 + L / 2 + 0.05, 0.95, W / 2 + 0.05]);
  tableVolume(b, 'roulette', tableId, [L + 0.3, 1.1, W + 0.3], at(place, { pos: [0.2, 0.55, 0] }));
  return rotor;
}

/**
 * Modular slot machine (§6: Base / Screen / Lights / ButtonPanel), all parts instanced so a whole
 * room of machines costs a handful of draw calls. Faces local +Z.
 */
export function slotMachine(b: RoomBuilder, place: Place, screen: Material, lights: Material, tableId: string): void {
  const P = (local: Place) => at(place, local);
  b.instance('SlotMachine_Base', () => meterBox(0.62, 1.05, 0.6), 'MAT_Wood_WalnutDark', P({ pos: [0, 0.525, 0] }), true);
  b.instance('SlotMachine_Cabinet', () => meterBox(0.6, 0.85, 0.42), 'MAT_Gold_Gilt', P({ pos: [0, 1.48, -0.08] }), true);
  b.instance('SlotMachine_Bezel', () => meterBox(0.52, 0.66, 0.03), 'MAT_Wood_WalnutDark', P({ pos: [0, 1.5, 0.14] }));
  b.instance('SlotMachine_Screen', () => new PlaneGeometry(0.44, 0.55), screen, P({ pos: [0, 1.5, 0.157] }));
  b.instance('SlotMachine_ButtonPanel', () => meterBox(0.6, 0.06, 0.26), 'MAT_Leather_Oxblood', P({ pos: [0, 1.08, 0.2], rot: [0.25, 0, 0] }));
  b.instance('SlotMachine_Buttons', () => new CylinderGeometry(0.022, 0.022, 0.02, 12), lights, P({ pos: [0.18, 1.12, 0.22], rot: [0.25, 0, 0] }));
  b.instance('SlotMachine_Topper', () => new CylinderGeometry(0.3, 0.3, 0.14, 32, 1, false, 0, Math.PI), 'MAT_Gold_Gilt', P({ pos: [0, 1.9, -0.08], rot: [Math.PI / 2, 0, 0] }));
  b.instance('SlotMachine_Lights', () => new TorusGeometry(0.3, 0.02, 6, 24, Math.PI), lights, P({ pos: [0, 1.9, 0.0] }));
  b.instance('SlotMachine_Lever', () => new CylinderGeometry(0.012, 0.012, 0.4, 8), 'MAT_Brass_Aged', P({ pos: [0.36, 1.3, 0.0] }));
  b.instance('SlotMachine_LeverKnob', () => new SphereGeometry(0.04, 12, 8), 'MAT_Marble_Rosso', P({ pos: [0.36, 1.52, 0.0] }));
  b.colliderBox(`Slot_${b.next()}`, place, [-0.34, 0, -0.32], [0.34, 2, 0.34]);
  tableVolume(b, 'slots', tableId, [0.66, 2.0, 0.7], at(place, { pos: [0, 1.0, 0.02] }));
}

/** Brass pendant lamp (hangs low over card tables); declares its light. */
export function pendantLamp(b: RoomBuilder, place: Place, ceilingY: number, intensity = 22): void {
  const [x, y, z] = place.pos;
  b.instance('PendantRod', () => new CylinderGeometry(0.008, 0.008, 1, 6), 'MAT_Brass_Aged', { pos: [x, (ceilingY + y) / 2 + 0.1, z], scale: [1, ceilingY - y - 0.2, 1] });
  b.instance('PendantShade', () => new CylinderGeometry(0.16, 0.55, 0.28, 40, 1, true), 'MAT_Brass_Aged', { pos: [x, y + 0.14, z], scale: [place.scale?.[0] ?? 1, 1, place.scale?.[2] ?? 1] }, true);
  b.instance('PendantGlow', () => new CylinderGeometry(0.5, 0.5, 0.01, 40), 'MAT_Fabric_LampShade', { pos: [x, y + 0.01, z], scale: [place.scale?.[0] ?? 1, 1, place.scale?.[2] ?? 1] });
  // a short-range point under the shade: spot slots are scarce (each costs a full per-pixel light at 2× DPR)
  b.light({ name: `Pendant_${b.next()}`, kind: 'point', position: { x, y: y - 0.12, z }, color: WARM, intensity, range: 4.5 });
}

// ================================================================ interaction volumes

const INVISIBLE = new MeshBasicMaterial({ visible: false });
INVISIBLE.name = 'MAT_Invisible_Interact';
INVISIBLE.userData.shared = true;

const PROMPTS: Record<GameType, string> = {
  poker: "Play Texas Hold'em", blackjack: 'Play Blackjack', baccarat: 'Play Baccarat', roulette: 'Play Roulette', slots: 'Play the Slot',
};

/**
 * Invisible `INTERACT_` volume carrying `casinoTable` extras (§6). The interaction ray hits it;
 * the renderer skips it (material.visible = false). A GLB-authored room would export the same
 * node with the same custom properties.
 */
export function tableVolume(b: RoomBuilder, gameType: GameType, tableId: string, size: [number, number, number], place: Place | Matrix4): Mesh {
  const mesh = new Mesh(new BoxGeometry(...size), INVISIBLE);
  mesh.applyMatrix4(at(place));
  mesh.name = `INTERACT_${b.zone}_${tableId.replace(/(^|_)(\w)/g, (_, _u, c: string) => c.toUpperCase())}`;
  const extras: CasinoTableExtras = { interactable: true, interactionType: 'casinoTable', interactionPrompt: PROMPTS[gameType], gameType, tableId };
  Object.assign(mesh.userData, extras);
  b.root.add(mesh);
  return mesh;
}
