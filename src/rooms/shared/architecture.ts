import {
  CylinderGeometry,
  Group,
  Matrix4,
  Mesh,
  MeshStandardMaterial,
  PlaneGeometry,
  Quaternion,
  RingGeometry,
  Shape,
  ShapeGeometry,
  Vector3,
  type Material,
} from 'three/webgpu';
import type { MaterialKey } from '../../render/materials';
import { oilPaintingTexture, plaqueTexture, rivieraNightTexture } from '../../render/proceduralArt';
import { pickArtwork } from '../../render/art';
import { at, meterBox, point, RoomBuilder, type Place } from '../../world/roomBuilder';
import { chandelier, frame, sconce, WARM } from './props';

/**
 * Shared architectural vocabulary for every zone — the code-side equivalent of the Blender
 * trim sheets / linked architectural kit (§6). Walls are authored in a local frame:
 * the wall runs along +X from 0..len, height 0..h, the room side is +Z, the wall mass is -Z.
 */

export const WALL_T = 0.3;

export interface DoorSpec {
  id: string;
  prompt: string;
  /** Zone behind the door; omit (with locked) for decorative doors. */
  target?: string;
  locked?: boolean;
}

export interface Opening {
  bay: number;
  width: number;
  height: number;
  door?: DoorSpec;
  plaque?: string[];
}

export interface WallOpts {
  bays: number;
  openings?: Opening[];
  windowBays?: number[];
  paintingBays?: number[];
  /** Put a lit sconce on the pilaster after these bays. */
  sconceAfter?: number[];
  /** Wall mass depth behind the surface; 0 = no collider/jambs (another zone owns the wall). */
  thickness?: number;
  field?: MaterialKey;
  sconceIntensity?: number;
  /** Line openings with jambs (false when the neighbouring zone's wall already does). */
  jambs?: boolean;
}

export function wall(b: RoomBuilder, origin: Place, len: number, h: number, o: WallOpts): void {
  const P = (local: Place): Matrix4 => at(origin, local);
  const box = (size: [number, number, number], mat: MaterialKey, pos: [number, number, number]) =>
    b.add(meterBox(...size), mat, P({ pos }));
  const T = o.thickness ?? WALL_T;
  const field = o.field ?? 'MAT_Fabric_DamaskOxblood';

  const wainH = 1.0, railH = 0.07;
  const friezeH = Math.min(0.55, h * 0.08), corniceH = Math.min(0.45, h * 0.07);
  const fieldTop = h - friezeH - corniceH;
  const bayW = len / o.bays;
  const pilW = 0.42;

  // continuous frieze, dentils and stepped cornice
  box([len, friezeH, 0.08], 'MAT_Wood_WalnutPolished', [len / 2, fieldTop + friezeH / 2, 0.08]);
  for (let x = 0.07; x < len; x += 0.16) {
    b.instance('Dentil', () => meterBox(0.07, 0.09, 0.06), 'MAT_Gold_Gilt', P({ pos: [x, fieldTop + friezeH - 0.08, 0.15] }));
  }
  const steps: [number, number, MaterialKey][] = [[corniceH * 0.27, 0.14, 'MAT_Gold_Gilt'], [corniceH * 0.35, 0.2, 'MAT_Wood_WalnutPolished'], [corniceH * 0.38, 0.3, 'MAT_Gold_Gilt']];
  let y = fieldTop + friezeH;
  for (const [sh, depth, mat] of steps) {
    box([len, sh, depth], mat, [len / 2, y + sh / 2, depth / 2]);
    y += sh;
  }
  // backing above the field (behind frieze) — full length
  box([len, h - fieldTop, 0.04], 'MAT_Wood_WalnutDark', [len / 2, (h + fieldTop) / 2, 0.02]);

  const segment = (x0: number, x1: number, top: number) => {
    const w = x1 - x0;
    if (w <= 0.01) return;
    const cx = (x0 + x1) / 2;
    box([w, top, 0.04], 'MAT_Wood_WalnutDark', [cx, top / 2, 0.02]);
    box([w, wainH, 0.05], 'MAT_Wood_WalnutPolished', [cx, wainH / 2, 0.065]);
    box([w, 0.1, 0.09], 'MAT_Wood_WalnutPolished', [cx, 0.05, 0.085]);
    box([w, railH, 0.07], 'MAT_Gold_Gilt', [cx, wainH + railH / 2, 0.08]);
    if (T > 0) b.colliderBox(`Wall_${b.next()}`, origin, [x0, 0, -T], [x1, h, 0]);
  };

  for (let i = 0; i < o.bays; i++) {
    const x0 = i * bayW, x1 = x0 + bayW, cx = x0 + bayW / 2;
    const innerW = bayW - pilW - 0.24;
    const opening = o.openings?.find((op) => op.bay === i);

    if (opening) {
      const ox0 = cx - opening.width / 2, ox1 = cx + opening.width / 2;
      segment(x0, ox0, fieldTop);
      segment(ox1, x1, fieldTop);
      // panel above the opening up to the frieze
      box([opening.width, fieldTop - opening.height, 0.05], 'MAT_Wood_WalnutPolished', [cx, (fieldTop + opening.height) / 2, 0.03]);
      if (T > 0) b.colliderBox(`Lintel_${b.next()}`, origin, [ox0, opening.height, -T], [ox1, h, 0]);
      doorway(b, P({ pos: [cx, 0, 0] }), opening, o.jambs === false ? 0 : T, fieldTop);
      continue;
    }

    segment(x0, x1, fieldTop);
    // raised panel in the wainscot
    box([innerW, wainH - 0.34, 0.03], 'MAT_Wood_WalnutDark', [cx, wainH / 2 + 0.05, 0.1]);
    frame(b, P({ pos: [cx, wainH / 2 + 0.05, 0.11] }), innerW + 0.04, wainH - 0.3, 0.03);

    const fieldH = fieldTop - (wainH + railH) - 0.24;
    const fieldY = wainH + railH + 0.12 + fieldH / 2;
    if (o.windowBays?.includes(i)) {
      windowBay(b, origin, cx, innerW, wainH + railH, fieldTop);
      continue;
    }
    box([innerW, fieldH, 0.02], field, [cx, fieldY, 0.05]);
    frame(b, P({ pos: [cx, fieldY, 0.07] }), innerW + 0.06, fieldH + 0.06, 0.03);
    if (o.paintingBays?.includes(i)) painting(b, P({ pos: [cx, fieldY + 0.1, 0.09] }), Math.min(innerW - 0.5, 1.6), Math.min(fieldH - 0.7, 2.6), Math.round(i * 31 + len * 7));
  }

  // pilasters on bay boundaries (half-width at the ends where adjoining walls meet)
  for (let i = 0; i <= o.bays; i++) {
    const w = i === 0 || i === o.bays ? pilW / 2 : pilW;
    const px = i === 0 ? w / 2 : i === o.bays ? len - w / 2 : i * bayW;
    box([w, fieldTop, 0.13], 'MAT_Wood_WalnutPolished', [px, fieldTop / 2, 0.1]);
    if (fieldTop > 2.4) box([w - 0.12, fieldTop - 1.6, 0.02], 'MAT_Wood_WalnutDark', [px, fieldTop / 2 + 0.3, 0.17]);
    box([w + 0.06, 0.22, 0.17], 'MAT_Gold_Gilt', [px, fieldTop - 0.11, 0.1]);
    box([w + 0.06, 0.28, 0.17], 'MAT_Wood_WalnutPolished', [px, 0.14, 0.1]);
    if (o.sconceAfter?.includes(i - 1) && i > 0 && i < o.bays) {
      const sy = Math.min(2.75, fieldTop - 0.6);
      sconce(b, P({ pos: [px, sy, 0.19] }));
      b.light({
        name: `Sconce_${b.next()}`, kind: 'point', position: point(origin, [px, sy + 0.1, 0.45]),
        color: WARM, intensity: o.sconceIntensity ?? 5, range: 6,
      });
    }
  }
}

/** Opening surround, jambs, optional plaque and door leaves. `m` = floor centre of the opening on the wall surface. */
function doorway(b: RoomBuilder, m: Matrix4, op: Opening, T: number, fieldTop: number): void {
  const { width: w, height: h } = op;
  const P = (local: Place) => at(m, local);
  // jambs + head lining the wall thickness
  if (T > 0) {
    for (const side of [-1, 1]) b.add(meterBox(0.06, h, T), 'MAT_Wood_WalnutPolished', P({ pos: [side * (w / 2 - 0.03), h / 2, -T / 2] }));
    b.add(meterBox(w, 0.06, T), 'MAT_Wood_WalnutPolished', P({ pos: [0, h - 0.03, -T / 2] }));
    b.add(meterBox(w, 0.02, T), 'MAT_Marble_Nero', P({ pos: [0, 0.01, -T / 2] })); // threshold
  }
  // architrave on the room face
  for (const side of [-1, 1]) {
    b.add(meterBox(0.2, h + 0.2, 0.08), 'MAT_Wood_WalnutPolished', P({ pos: [side * (w / 2 + 0.1), (h + 0.2) / 2, 0.06] }));
    b.add(meterBox(0.035, h + 0.12, 0.03), 'MAT_Gold_Gilt', P({ pos: [side * (w / 2 + 0.03), (h + 0.12) / 2, 0.11] }));
  }
  b.add(meterBox(w + 0.5, 0.22, 0.12), 'MAT_Wood_WalnutPolished', P({ pos: [0, h + 0.11, 0.07] }));
  b.add(meterBox(w + 0.62, 0.06, 0.16), 'MAT_Gold_Gilt', P({ pos: [0, h + 0.25, 0.08] }));

  if (op.plaque) {
    const ph = Math.min(0.5, fieldTop - h - 0.45);
    if (ph > 0.18) {
      const pw = Math.min(w + 0.3, ph * 4);
      const tex = plaqueTexture(op.plaque);
      const mat = new MeshStandardMaterial({ map: tex, roughness: 0.35, metalness: 0.2, emissive: 0xffffff, emissiveMap: tex, emissiveIntensity: 0.08 });
      mat.name = 'MAT_Plaque';
      const plaque = new Mesh(new PlaneGeometry(pw, ph), mat);
      plaque.applyMatrix4(P({ pos: [0, h + 0.36 + ph / 2, 0.12] }));
      plaque.name = `PROP_${b.zone}_Plaque_${b.next()}`;
      b.root.add(plaque);
      frame(b, P({ pos: [0, h + 0.36 + ph / 2, 0.13] }), pw + 0.06, ph + 0.06, 0.03);
    }
  }

  if (op.door) doorLeaves(b, m, w, h, T, op.door);
}

/**
 * Double door (the `DOOR_` role). Each leaf is a pivot on its hinge axis (§6: door origin on the
 * hinge); leaves swing away from the room side (-Z). Its collider fills the opening while closed.
 */
function doorLeaves(b: RoomBuilder, m: Matrix4, w: number, h: number, T: number, spec: DoorSpec): void {
  const lw = w / 2 - 0.01;
  const extras = spec.target
    ? { interactable: true as const, interactionType: 'door' as const, interactionPrompt: spec.prompt, target: spec.target }
    : { interactable: true as const, interactionType: 'door' as const, interactionPrompt: spec.prompt, locked: true };
  const leaves: { pivot: Group; sign: 1 | -1 }[] = [];

  for (const side of [-1, 1] as const) {
    const lb = new RoomBuilder(b.zone, b.materials, `DOOR_${b.zone}_${spec.id}_${side < 0 ? 'L' : 'R'}`);
    // leaf built hinge-at-origin, extending +X
    const add = (size: [number, number, number], mat: MaterialKey, pos: [number, number, number]) => lb.add(meterBox(...size), mat, { pos });
    add([lw, h - 0.02, 0.07], 'MAT_Wood_WalnutDark', [lw / 2, h / 2, 0]);
    for (const face of [-1, 1]) {
      const panels: [number, number][] = [[0.3, 0.8], [1.25, Math.max(0.6, h - 2.0)], [h - 0.6, 0.35]];
      for (const [y0, ph] of panels) {
        if (y0 + ph > h - 0.15) continue;
        add([lw - 0.24, ph, 0.02], 'MAT_Wood_WalnutPolished', [lw / 2, y0 + ph / 2, face * 0.045]);
        frame(lb, { pos: [lw / 2, y0 + ph / 2, face * 0.058] }, lw - 0.2, ph + 0.04, 0.02);
      }
      lb.instance('DoorHandle', () => meterBox(0.03, 0.26, 0.03), 'MAT_Gold_Gilt', { pos: [lw - 0.09, 1.05, face * 0.075] });
      lb.instance('DoorEscutcheon', () => meterBox(0.06, 0.34, 0.01), 'MAT_Brass_Aged', { pos: [lw - 0.09, 1.05, face * 0.058] });
    }
    const leaf = lb.build();
    const extrasTagged = { ...extras, doorId: `DOOR_${b.zone}_${spec.id}` };
    leaf.traverse((o) => { if ((o as Mesh).isMesh) Object.assign(o.userData, extrasTagged); });

    const pivot = new Group();
    pivot.name = `DOOR_${b.zone}_${spec.id}_${side < 0 ? 'L' : 'R'}_Hinge`;
    // left hinge at -w/2 (leaf extends +X); right hinge at +w/2, leaf turned 180° (extends -X)
    const hinge = at(m, { pos: [side * (w / 2 - 0.005), 0.01, -T / 2], rotY: side < 0 ? 0 : Math.PI });
    const pos = new Vector3(), q = new Quaternion(), s = new Vector3();
    hinge.decompose(pos, q, s);
    pivot.position.copy(pos);
    pivot.quaternion.copy(q);
    pivot.userData.baseQuaternion = q.clone();
    pivot.add(leaf);
    b.root.add(pivot);
    leaves.push({ pivot, sign: side < 0 ? 1 : -1 });
  }

  const collider = b.colliderBox(`Door_${spec.id}`, m, [-w / 2, 0, -T], [w / 2, h, 0]);
  const c = point(m, [0, 0, -T / 2]);
  b.doors.push({ id: `DOOR_${b.zone}_${spec.id}`, leaves, collider, target: spec.target ?? null, position: c, extras });
}

// ------------------------------------------------------------------ floors & ceilings

export function borderedFloor(b: RoomBuilder, x0: number, x1: number, z0: number, z1: number, o: {
  field: MaterialKey; band: MaterialKey; margin?: MaterialKey; m?: number; bw?: number;
}): void {
  const W = x1 - x0, D = z1 - z0, cx = (x0 + x1) / 2, cz = (z0 + z1) / 2;
  const m = o.m ?? 0.6, band = o.bw ?? 0.3, margin = o.margin ?? o.field;
  const slab = (w: number, d: number, x: number, z: number, mat: MaterialKey) => b.box([w, 0.2, d], mat, [x, -0.1, z]);
  slab(W, m, cx, z1 - m / 2, margin);
  slab(W, m, cx, z0 + m / 2, margin);
  slab(m, D - 2 * m, x0 + m / 2, cz, margin);
  slab(m, D - 2 * m, x1 - m / 2, cz, margin);
  const iw = W - 2 * m, id = D - 2 * m;
  slab(iw, band, cx, z1 - m - band / 2, o.band);
  slab(iw, band, cx, z0 + m + band / 2, o.band);
  slab(band, id - 2 * band, x0 + m + band / 2, cz, o.band);
  slab(band, id - 2 * band, x1 - m - band / 2, cz, o.band);
  slab(iw - 2 * band, id - 2 * band, cx, cz, o.field);
  b.collider(`Floor_${b.next()}`, [x0 - 0.5, -0.5, z0 - 0.5], [x1 + 0.5, 0, z1 + 0.5]);
}

export function cofferedCeiling(b: RoomBuilder, x0: number, x1: number, z0: number, z1: number, H: number, spacing = 2): void {
  const W = x1 - x0, D = z1 - z0, cx = (x0 + x1) / 2, cz = (z0 + z1) / 2;
  b.box([W, 0.3, D], 'MAT_Plaster_Ceiling', [cx, H + 0.15, cz]);
  const beamW = 0.26, beamD = Math.min(0.34, H * 0.06);
  const nx = Math.max(1, Math.round(W / spacing)), nz = Math.max(1, Math.round(D / spacing));
  for (let i = 1; i < nx; i++) {
    const x = x0 + (i * W) / nx;
    b.box([beamW, beamD, D], 'MAT_Wood_WalnutPolished', [x, H - beamD / 2, cz]);
    b.box([0.06, 0.012, D], 'MAT_Gold_Gilt', [x, H - beamD - 0.006, cz]);
  }
  for (let i = 1; i < nz; i++) {
    const z = z0 + (i * D) / nz;
    b.box([W, beamD, beamW], 'MAT_Wood_WalnutPolished', [cx, H - beamD / 2 - 0.001, z]);
    b.box([W, 0.012, 0.06], 'MAT_Gold_Gilt', [cx, H - beamD - 0.007, z]);
  }
}

/** Crystal chandelier hung from the ceiling with its light(s). Optionally the room's shadow key. */
export function hangChandelier(b: RoomBuilder, x: number, z: number, ceilingY: number, o: {
  scale?: number; drop?: number; intensity?: number; key?: boolean;
} = {}): void {
  const s = o.scale ?? 1;
  const drop = o.drop ?? 1.6 * s;
  const cb = new RoomBuilder(b.zone, b.materials, `PROP_${b.zone}_Chandelier_${b.next()}`);
  chandelier(cb, s);
  const g = cb.build();
  g.position.set(x, ceilingY - drop, z);
  b.root.add(g);
  const phase = x * 0.7 + z * 0.3;
  b.animate.push((t) => {
    g.rotation.z = Math.sin(t * 0.37 + phase) * 0.0035;
    g.rotation.x = Math.sin(t * 0.29 + phase + 1.3) * 0.0028;
  });
  const cy = ceilingY - drop - 0.7 * s;
  b.light({ name: `Chandelier_${b.next()}`, kind: 'point', position: { x, y: cy, z }, color: WARM, intensity: o.intensity ?? 90 * s * s, range: 22 * s });
  if (o.key) {
    b.light({
      name: `Chandelier_Key_${b.next()}`, kind: 'spot', position: { x, y: cy - 0.3, z }, target: { x, y: 0, z },
      color: WARM, intensity: (o.intensity ?? 90 * s * s) * 1.9, range: 18, angle: 1.0, penumbra: 0.9, castShadow: true,
    });
  }
}

/** Long runner carpet with gilt border strips, lying on the floor along local Z. */
export function runner(b: RoomBuilder, x: number, z0: number, z1: number, width: number): void {
  const len = Math.abs(z1 - z0), cz = (z0 + z1) / 2;
  b.box([width, 0.012, len], 'MAT_Fabric_CarpetCrimson', [x, 0.006, cz]);
  for (const side of [-1, 1]) b.box([0.04, 0.014, len], 'MAT_Gold_Gilt', [x + side * (width / 2 - 0.12), 0.007, cz]);
}

// ------------------------------------------------------------------ windows & paintings

function windowBay(b: RoomBuilder, origin: Place, cx: number, w: number, y0: number, y1: number): void {
  const P = (local: Place): Matrix4 => at(origin, local);
  const ww = Math.min(w, 1.9), top = y1 - 0.3, bottom = y0 + 0.25;
  const hh = top - bottom;
  const tex = rivieraNightTexture(Math.round(cx * 13));
  const mat = new MeshStandardMaterial({ color: 0x000000, emissive: 0xffffff, emissiveMap: tex, emissiveIntensity: 1.1, roughness: 0.1 });
  mat.name = 'MAT_Window_NightView';
  const shape = new Shape();
  shape.moveTo(-ww / 2, 0);
  shape.lineTo(ww / 2, 0);
  shape.lineTo(ww / 2, hh - ww / 2);
  shape.absarc(0, hh - ww / 2, ww / 2, 0, Math.PI, false);
  shape.lineTo(-ww / 2, 0);
  const g = new ShapeGeometry(shape, 24);
  const uv = g.attributes.uv, pos = g.attributes.position;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, pos.getX(i) / ww + 0.5, pos.getY(i) / hh);
  const view = new Mesh(g, mat);
  view.applyMatrix4(P({ pos: [cx, bottom, 0.03] }));
  view.name = `PROP_${b.zone}_WindowView_${b.next()}`;
  b.root.add(view);
  const bar = (sw: number, sh: number, x: number, yy: number) => b.add(meterBox(sw, sh, 0.05), 'MAT_Wood_WalnutPolished', P({ pos: [x, yy, 0.06] }));
  bar(0.06, hh, cx, bottom + hh / 2);
  for (let k = 1; k < 4; k++) bar(ww, 0.04, cx, bottom + (hh - ww / 2) * (k / 4));
  b.add(meterBox(ww + 0.5, 0.08, 0.3), 'MAT_Marble_Nero', P({ pos: [cx, bottom - 0.04, 0.15] }));
  for (const side of [-1, 1]) b.add(meterBox(0.12, hh - ww / 2, 0.12), 'MAT_Gold_Gilt', P({ pos: [cx + side * (ww / 2 + 0.06), bottom + (hh - ww / 2) / 2, 0.08] }));
  const arch = new RingGeometry(ww / 2, ww / 2 + 0.12, 48, 1, 0, Math.PI);
  b.add(arch, 'MAT_Gold_Gilt', P({ pos: [cx, bottom + hh - ww / 2, 0.14] }));
  for (const side of [-1, 1]) {
    for (let k = 0; k < 5; k++) {
      b.instance('DrapePleat', () => new CylinderGeometry(0.07, 0.09, 1, 12, 1, true, 0, Math.PI), 'MAT_Fabric_VelvetRed',
        P({ pos: [cx + side * (ww / 2 + 0.05 + k * 0.1), (y1 + 0.02) / 2, 0.24], scale: [1, y1 + 0.02, 1] }), true);
    }
  }
  b.add(meterBox(ww + 1.3, 0.35, 0.12), 'MAT_Fabric_VelvetRed', P({ pos: [cx, y1 - 0.12, 0.3] }));
  b.add(meterBox(ww + 1.34, 0.04, 0.14), 'MAT_Gold_Gilt', P({ pos: [cx, y1 - 0.3, 0.3] }));
}

export function painting(b: RoomBuilder, m: Matrix4, maxW: number, maxH: number, seed: number): void {
  // a real public-domain painting, fitted inside the frame box at its true proportions
  const art = pickArtwork(seed, maxW > maxH ? 'landscape' : 'portrait');
  const aspect = art?.aspect ?? maxW / maxH;
  const w = Math.min(maxW, maxH * aspect), h = w / aspect;
  const tex = art?.texture ?? oilPaintingTexture(seed);
  const mat: Material = new MeshStandardMaterial({ map: tex, roughness: 0.42 });
  mat.name = 'MAT_Canvas_Oil';
  const canvas = new Mesh(new PlaneGeometry(w, h), mat);
  canvas.applyMatrix4(at(m, { pos: [0, 0, 0.01] }));
  canvas.name = `PROP_${b.zone}_Painting_${b.next()}`;
  canvas.receiveShadow = true;
  b.root.add(canvas);
  for (const [sw, sh, x, y] of [[w + 0.3, 0.15, 0, h / 2 + 0.075], [w + 0.3, 0.15, 0, -h / 2 - 0.075], [0.15, h, w / 2 + 0.075, 0], [0.15, h, -w / 2 - 0.075, 0]] as const) {
    b.add(meterBox(sw, sh, 0.08), 'MAT_Gold_Gilt', at(m, { pos: [x, y, 0.04] }));
  }
  frame(b, at(m, { pos: [0, 0, 0.085] }), w + 0.06, h + 0.06, 0.025);
}

/**
 * Standard rectangular room shell, zone-local: entrance wall on z=0 (door opening centred at x=0),
 * room extends to z=-depth. The entrance opening is not lined with jambs (the hallway's wall does that).
 */
export function roomShell(b: RoomBuilder, o: {
  width: number; depth: number; height: number; field: MaterialKey;
  floor: { field: MaterialKey; band: MaterialKey; margin?: MaterialKey; m?: number; bw?: number };
  entrance: { width: number; height: number };
  bays?: { side: number; back: number; front: number };
  windowBays?: { left?: number[]; right?: number[]; back?: number[] };
  paintingBays?: { left?: number[]; right?: number[]; back?: number[] };
  sconces?: boolean;
}): void {
  const { width: W, depth: D, height: H } = o;
  const x0 = -W / 2, x1 = W / 2;
  const bays = o.bays ?? { side: Math.max(2, Math.round(D / 3.2)), back: Math.max(2, Math.round(W / 3.2)), front: 3 };
  const sconces = (n: number) => (o.sconces === false ? [] : Array.from({ length: n - 1 }, (_, i) => i).filter((i) => i % 2 === 0));

  borderedFloor(b, x0, x1, -D, 0, o.floor);
  cofferedCeiling(b, x0, x1, -D, 0, H, 2.4);

  // front (entrance) wall: runs +X along z=0, facing -Z into the room → rotY π, origin at x1
  const frontBay = Math.floor(bays.front / 2);
  wall(b, { pos: [x1, 0, 0], rotY: Math.PI }, W, H, {
    bays: bays.front, jambs: false, field: o.field,
    openings: [{ bay: frontBay, width: o.entrance.width, height: o.entrance.height }],
  });
  // back wall at z=-D facing +Z
  wall(b, { pos: [x0, 0, -D], rotY: 0 }, W, H, { bays: bays.back, field: o.field, windowBays: o.windowBays?.back, paintingBays: o.paintingBays?.back, sconceAfter: sconces(bays.back) });
  // left wall x=x0 facing +X, running toward -Z
  wall(b, { pos: [x0, 0, 0], rotY: Math.PI / 2 }, D, H, { bays: bays.side, field: o.field, windowBays: o.windowBays?.left, paintingBays: o.paintingBays?.left, sconceAfter: sconces(bays.side) });
  // right wall x=x1 facing -X, running toward +Z from the back
  wall(b, { pos: [x1, 0, -D], rotY: -Math.PI / 2 }, D, H, { bays: bays.side, field: o.field, windowBays: o.windowBays?.right, paintingBays: o.paintingBays?.right, sconceAfter: sconces(bays.side) });
}

/** Common floor recipes. */
export const FLOORS = {
  marble: { field: 'MAT_Marble_Calacatta', band: 'MAT_Marble_Nero' },
  crimsonCarpet: { field: 'MAT_Fabric_CarpetCrimson', band: 'MAT_Gold_Gilt', margin: 'MAT_Wood_WalnutPolished', m: 0.55, bw: 0.05 },
  forestCarpet: { field: 'MAT_Fabric_CarpetForest', band: 'MAT_Gold_Gilt', margin: 'MAT_Wood_WalnutPolished', m: 0.55, bw: 0.05 },
} as const satisfies Record<string, { field: MaterialKey; band: MaterialKey; margin?: MaterialKey; m?: number; bw?: number }>;

/** Wraps a finished room builder into a ZoneInstance (bounds, probe at room centre). */
export function roomInstance(b: RoomBuilder, id: string, W: number, D: number, H: number): import('../../world/roomBuilder').ZoneInstance {
  const root = b.build();
  return {
    id, root, colliders: b.colliders, lights: b.lights, doors: b.doors, animate: b.animate, sounds: b.sounds,
    bounds: { id: `TRIGGER_${b.zone}_Bounds`, min: { x: -W / 2, y: -1, z: -D }, max: { x: W / 2, y: H, z: -0.05 } },
    probe: { x: 0, y: 1.7, z: -D / 2 },
  };
}
