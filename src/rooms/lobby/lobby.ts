import { CylinderGeometry, RingGeometry, Shape, ShapeGeometry, type Material } from 'three/webgpu';
import type { MaterialKey } from '../../render/materials';
import { meterBox, RoomBuilder, type ZoneInstance } from '../../world/roomBuilder';
import { borderedFloor, cofferedCeiling, hangChandelier, wall } from '../shared/architecture';
import { LOBBY, LOBBY_DOOR, LOBBY_STAIR_Z1 } from '../shared/layout';
import { balusterGeometry, clubChair, frame, roundTable, tableLamp, urn, WARM } from '../shared/props';

/**
 * The Grand Lobby — the mansion's hub (casino.png: "Grand Lobby / Main Hub").
 * No games here: marble medallion floor, crystal chandelier, a carpeted grand stair to a landing,
 * windows onto the night-time Riviera, and two gilded doorways branching to the West Gallery
 * (Poker · Blackjack · Baccarat) and the East Gallery (Roulette · Slots).
 *
 * Zone anchor: world origin; -Z runs from the front doors towards the staircase.
 */
const { x0: X0, x1: X1, zFront: Z_FRONT, zBack: Z_BACK, height: H, landingY: LAND_Y } = LOBBY;
const { stairZ0: STAIR_Z0, stairRun: RUN, stairRise: RISE, stairSteps: STEPS, stairHalf: STAIR_HALF } = LOBBY;
const STAIR_Z1 = LOBBY_STAIR_Z1;

export function buildLobby(materials: Record<MaterialKey, Material>): ZoneInstance {
  const b = new RoomBuilder('Lobby', materials);

  borderedFloor(b, X0, X1, Z_BACK, Z_FRONT, { field: 'MAT_Marble_Calacatta', band: 'MAT_Marble_Nero', m: 0.7, bw: 0.35 });
  medallion(b);
  cofferedCeiling(b, X0, X1, Z_BACK, Z_FRONT, H, 2);
  b.add(new CylinderGeometry(1.1, 1.25, 0.1, 64), 'MAT_Gold_Gilt', { pos: [0, H - 0.39, -5] }); // ceiling rose

  const side = { bays: LOBBY.sideBays, sconceAfter: [0, 2, 4] };
  // left wall → West Gallery
  wall(b, { pos: [X0, 0, Z_FRONT], rotY: Math.PI / 2 }, Z_FRONT - STAIR_Z1, H, {
    ...side, paintingBays: [1, 4],
    openings: [{ bay: 2, ...LOBBY_DOOR, plaque: ['Poker · Blackjack · Baccarat', 'Galerie Ouest'], door: { id: 'West', target: 'hall_west', prompt: 'Enter the West Gallery' } }],
  });
  // right wall → East Gallery, windows onto the sea
  wall(b, { pos: [X1, 0, STAIR_Z1], rotY: -Math.PI / 2 }, Z_FRONT - STAIR_Z1, H, {
    ...side, windowBays: [1, 5],
    openings: [{ bay: 3, ...LOBBY_DOOR, plaque: ['Roulette · Machines à Sous', 'Galerie Est'], door: { id: 'East', target: 'hall_east', prompt: 'Enter the East Gallery' } }],
  });
  // walls around the landing
  wall(b, { pos: [X1, LAND_Y, Z_BACK], rotY: -Math.PI / 2 }, STAIR_Z1 - Z_BACK, H - LAND_Y, { bays: 1 });
  wall(b, { pos: [X0, LAND_Y, STAIR_Z1], rotY: Math.PI / 2 }, STAIR_Z1 - Z_BACK, H - LAND_Y, { bays: 1 });
  wall(b, { pos: [X0, LAND_Y, Z_BACK], rotY: 0 }, X1 - X0, H - LAND_Y, {
    bays: 5, paintingBays: [0, 4],
    openings: [{ bay: 2, width: 2.2, height: 3.3, door: { id: 'Apartments', prompt: 'Private Apartments', locked: true } }],
  });
  // entrance wall with the front doors (exterior arrives in a later phase)
  wall(b, { pos: [X1, 0, Z_FRONT], rotY: Math.PI }, X1 - X0, H, {
    bays: 5, paintingBays: [0, 4],
    openings: [{ bay: 2, width: 2.4, height: 3.6, door: { id: 'Front', prompt: 'The Front Doors — the terrace is closed tonight', locked: true } }],
  });

  staircase(b);

  // centrepiece
  roundTable(b, { pos: [0, 0, -5] }, 0.7, 0.78);
  urn(b, { pos: [0, 0.8, -5] }, 0.7);

  // seating by the windows (front right) and beside the stair (both sides)
  const group = (x: number, z: number, facing: number) => {
    roundTable(b, { pos: [x, 0, z] }, 0.34, 0.58);
    clubChair(b, { pos: [x, 0, z + 1.2], rotY: Math.PI });
    clubChair(b, { pos: [x - facing * 1.2, 0, z - 0.2], rotY: facing * Math.PI / 2 });
    clubChair(b, { pos: [x, 0, z - 1.3], rotY: 0 });
    tableLamp(b, { pos: [x, 0.6, z] }, 6);
  };
  group(5.9, 0.4, 1);
  group(-5.9, -9.6, -1);
  group(5.9, -9.6, 1);

  // console by the entrance
  b.box([1.6, 0.06, 0.5], 'MAT_Marble_Nero', [-6.9, 0.86, 1.4], { rotY: Math.PI / 2 });
  b.box([1.5, 0.16, 0.44], 'MAT_Wood_WalnutPolished', [-6.9, 0.76, 1.4], { rotY: Math.PI / 2 });
  for (const dz of [-0.62, 0.62]) b.box([0.08, 0.68, 0.08], 'MAT_Gold_Gilt', [-6.9, 0.34, 1.4 + dz]);
  b.collider('Console_01', [-7.2, 0, 0.55], [-6.6, 0.9, 2.25]);
  tableLamp(b, { pos: [-6.9, 0.89, 1.9] }, 6);
  urn(b, { pos: [-6.9, 0.89, 1.0] }, 0.32);

  hangChandelier(b, 0, -5, H, { scale: 1.25, drop: 1.6, intensity: 90, key: true });
  b.light({ name: 'Moon_01', kind: 'spot', position: { x: X1 + 3, y: 5, z: -3 }, target: { x: 0, y: 0, z: -6 }, color: 0x8aa0d8, intensity: 25, range: 30, angle: 0.7, penumbra: 1 });

  const root = b.build();
  return {
    id: 'lobby', root, colliders: b.colliders, lights: b.lights, doors: b.doors, animate: b.animate,
    bounds: { id: 'TRIGGER_Lobby_Bounds', min: { x: X0, y: -1, z: Z_BACK }, max: { x: X1, y: H, z: Z_FRONT } },
    spawn: { position: { x: 0, y: 0, z: 2.2 }, yaw: 0 },
    probe: { x: 0, y: 1.7, z: -4 },
  };
}

function medallion(b: RoomBuilder) {
  // inlaid medallion under the chandelier (thin stacked discs, 1–2 mm apart)
  const mz = -5;
  const disc = (r: number, y: number, mat: MaterialKey) =>
    b.add(new CylinderGeometry(r, r, 0.002, 96), mat, { pos: [0, y, mz] });
  disc(3.0, 0.001, 'MAT_Marble_Nero');
  b.add(new RingGeometry(2.78, 2.86, 96), 'MAT_Gold_Gilt', { pos: [0, 0.0025, mz], rot: [-Math.PI / 2, 0, 0] });
  disc(2.7, 0.0022, 'MAT_Marble_Rosso');
  disc(2.3, 0.0034, 'MAT_Marble_Calacatta');
  b.add(new RingGeometry(1.12, 1.18, 96), 'MAT_Gold_Gilt', { pos: [0, 0.0046, mz], rot: [-Math.PI / 2, 0, 0] });
  // compass-rose star
  const star = (outer: number, inner: number, points: number, rot: number) => {
    const s = new Shape();
    for (let i = 0; i <= points * 2; i++) {
      const r = i % 2 === 0 ? outer : inner;
      const a = (i / (points * 2)) * Math.PI * 2 + rot;
      if (i === 0) s.moveTo(Math.cos(a) * r, Math.sin(a) * r);
      else s.lineTo(Math.cos(a) * r, Math.sin(a) * r);
    }
    const g = new ShapeGeometry(s);
    scaleUV(g, 1);
    return g;
  };
  b.add(star(2.2, 0.55, 8, Math.PI / 8), 'MAT_Marble_Nero', { pos: [0, 0.0048, mz], rot: [-Math.PI / 2, 0, 0] });
  b.add(star(2.0, 0.4, 4, 0), 'MAT_Marble_Rosso', { pos: [0, 0.006, mz], rot: [-Math.PI / 2, 0, 0] });
  disc(0.3, 0.007, 'MAT_Marble_Calacatta');
  b.add(new RingGeometry(0.3, 0.34, 64), 'MAT_Gold_Gilt', { pos: [0, 0.0081, mz], rot: [-Math.PI / 2, 0, 0] });
}

function staircase(b: RoomBuilder) {
  const half = STAIR_HALF;
  for (let i = 0; i < STEPS; i++) {
    const top = (i + 1) * RISE;
    const z0 = STAIR_Z0 - i * RUN, z1 = z0 - RUN;
    // solid step (marble tread with nosing), carpet runner on top, brass stair rod at the riser
    b.box([2 * half, top, RUN], 'MAT_Marble_Calacatta', [0, top / 2, (z0 + z1) / 2], { collide: true });
    b.box([2 * half + 0.04, 0.03, 0.05], 'MAT_Marble_Calacatta', [0, top - 0.015, z0 + 0.01]);
    b.box([3.3, 0.012, RUN + 0.02], 'MAT_Fabric_CarpetCrimson', [0, top + 0.006, (z0 + z1) / 2]);
    b.box([3.3, RISE, 0.012], 'MAT_Fabric_CarpetCrimson', [0, top - RISE / 2, z0 + 0.03]);
    b.instance('StairRod', () => new CylinderGeometry(0.009, 0.009, 3.4, 8), 'MAT_Brass_Aged', { pos: [0, top - RISE + 0.012, z0 + 0.045], rot: [0, 0, Math.PI / 2] });
  }
  // gold border lines on the runner
  for (const x of [-1.62, 1.62]) {
    for (let i = 0; i < STEPS; i++) {
      const top = (i + 1) * RISE, z0 = STAIR_Z0 - i * RUN;
      b.box([0.04, 0.014, RUN + 0.02], 'MAT_Gold_Gilt', [x, top + 0.007, z0 - RUN / 2]);
    }
  }
  // landing (walnut-panelled front face below, marble on top)
  const landD = STAIR_Z1 - Z_BACK;
  b.box([X1 - X0, LAND_Y - 0.04, landD], 'MAT_Wood_WalnutPolished', [0, (LAND_Y - 0.04) / 2, (STAIR_Z1 + Z_BACK) / 2]);
  b.collider('Landing', [X0, 0, Z_BACK], [X1, LAND_Y, STAIR_Z1]);
  b.box([X1 - X0, 0.04, landD + 0.06], 'MAT_Marble_Calacatta', [0, LAND_Y - 0.02, (STAIR_Z1 + Z_BACK) / 2 + 0.03]);
  b.box([3.3, 0.012, landD], 'MAT_Fabric_CarpetCrimson', [0, LAND_Y + 0.006, (STAIR_Z1 + Z_BACK) / 2]);
  for (const side of [-1, 1]) {
    // panelled landing face
    const cx = side * (half + (X1 - half) / 2);
    const w = X1 - half - 0.2;
    b.box([w - 0.3, LAND_Y - 0.6, 0.03], 'MAT_Wood_WalnutDark', [cx, LAND_Y / 2, STAIR_Z1 + 0.02]);
    frame(b, { pos: [cx, LAND_Y / 2, STAIR_Z1 + 0.04] }, w - 0.26, LAND_Y - 0.56, 0.03);
    // stair stringer walls
    b.box([0.2, LAND_Y + 0.1, STAIR_Z0 - STAIR_Z1 + 0.1], 'MAT_Wood_WalnutPolished', [side * (half + 0.1), (LAND_Y + 0.1) / 2, (STAIR_Z0 + STAIR_Z1) / 2]);
  }

  // balustrades
  const railH = 0.95;
  const balusters = (x0: number, z0: number, y0: number, x1: number, z1: number, y1: number, id: string) => {
    const len = Math.hypot(x1 - x0, z1 - z0);
    const n = Math.max(2, Math.floor(len / 0.17));
    for (let k = 0; k <= n; k++) {
      const u = k / n;
      b.instance('Baluster', () => balusterGeometry(railH - 0.08), 'MAT_Gold_Gilt',
        { pos: [x0 + (x1 - x0) * u, y0 + (y1 - y0) * u + 0.04, z0 + (z1 - z0) * u] }, true);
    }
    // handrail (walnut) + base rail
    const dx = x1 - x0, dz = z1 - z0, dy = y1 - y0;
    const slope = Math.atan2(dy, Math.hypot(dx, dz));
    const yaw = Math.atan2(dx, dz);
    const railLen = Math.hypot(len, dy);
    const mid: [number, number, number] = [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2];
    b.add(meterBox(0.12, 0.08, railLen + 0.1), 'MAT_Wood_WalnutPolished', { pos: [mid[0], mid[1] + railH, mid[2]], rot: [-slope, yaw, 0] });
    b.add(meterBox(0.1, 0.05, railLen), 'MAT_Wood_WalnutPolished', { pos: [mid[0], mid[1] + 0.03, mid[2]], rot: [-slope, yaw, 0] });
    void id;
  };
  // landing front edge (either side of the stair opening)
  for (const side of [-1, 1]) {
    const xa = side * (half + 0.2), xb = side * (X1 - 0.3);
    balusters(xa, STAIR_Z1 - 0.12, LAND_Y, xb, STAIR_Z1 - 0.12, LAND_Y, `Landing_${side}`);
    b.collider(`Balustrade_Landing_${side}`, [Math.min(xa, xb), LAND_Y, STAIR_Z1 - 0.2], [Math.max(xa, xb), LAND_Y + 1.1, STAIR_Z1]);
    // along the stair (on the stringer)
    balusters(side * (half + 0.1), STAIR_Z0 - 0.1, 0.2, side * (half + 0.1), STAIR_Z1 - 0.12, LAND_Y, `Stair_${side}`);
    b.collider(`Balustrade_Stair_${side}`, [side * half - (side < 0 ? 0.2 : 0), 0, STAIR_Z1 - 0.2], [side * half + (side > 0 ? 0.2 : 0), LAND_Y + 1.1, STAIR_Z0]);
    // newel posts: foot of the stair with a glowing globe lamp, and at the landing
    for (const [z, y] of [[STAIR_Z0 + 0.15, 0], [STAIR_Z1 - 0.12, LAND_Y]] as const) {
      const x = side * (half + 0.15);
      b.box([0.3, 1.25, 0.3], 'MAT_Wood_WalnutPolished', [x, y + 0.625, z]);
      b.box([0.36, 0.08, 0.36], 'MAT_Gold_Gilt', [x, y + 1.25, z]);
      b.collider(`Newel_${side}_${z.toFixed(1)}`, [x - 0.18, y, z - 0.18], [x + 0.18, y + 1.3, z + 0.18]);
      if (y === 0) {
        urn(b, { pos: [x, 1.29, z] }, 0.28);
        b.instance('NewelGlobe', () => new CylinderGeometry(0.1, 0.13, 0.34, 24), 'MAT_Fabric_LampShade', { pos: [x, 1.75, z] });
        b.instance('NewelStem', () => new CylinderGeometry(0.02, 0.02, 0.4, 8), 'MAT_Brass_Aged', { pos: [x, 1.5, z] });
        b.light({ name: `Newel_${side < 0 ? 'L' : 'R'}`, kind: 'point', position: { x, y: 1.85, z }, color: WARM, intensity: 6, range: 6 });
      }
    }
  }
}

function scaleUV(g: ShapeGeometry | RingGeometry, k: number) {
  const uv = g.attributes.uv, pos = g.attributes.position;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, pos.getX(i) * k, pos.getY(i) * k);
}
