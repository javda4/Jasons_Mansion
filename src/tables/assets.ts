import {
  BufferAttribute,
  BufferGeometry,
  Color,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  SphereGeometry,
  type Material,
  type Texture,
} from 'three/webgpu';
import type { TextureLibrary } from '../loading/textureLibrary';

/**
 * Shared runtime geometry + materials for game presentation (cards, chips, reels, ball). The artwork is
 * the generated atlases in textures.json (scripts/make-game-textures.mjs); their layout comes from the
 * manifest's `meta`, never from constants duplicated here. Everything is `userData.shared` so zone
 * unloads never dispose it.
 */
export interface Card { rank: number; suit: string }

interface CardMeta { size: number; cell: [number, number]; cols: number; suits: string; ranks: [number, number]; back: number }
interface ChipMeta { denoms: number[]; grid: number; faceRadius: number; rimInner: number }

export const CARD_W = 0.063, CARD_L = 0.088, CARD_T = 0.00035;
export const CHIP_R = 0.0195, CHIP_H = 0.0034;

export interface TableAssets {
  card(card: Card | null): BufferGeometry;     // null → a card whose face is the back (hidden hole card)
  cardMaterial: Material;
  chip(denomIndex: number): BufferGeometry;
  chipMaterial: Material;
  denoms: number[];
  reel(radius: number, width: number): BufferGeometry;
  reelMaterial: Material;
  reelStops: string[];
  ball: BufferGeometry;
  ballMaterial: Material;
}

let assets: TableAssets | null = null;

export function tableAssets(): TableAssets {
  if (!assets) throw new Error('initTableAssets() not called');
  return assets;
}

const shared = <M extends Material>(m: M, name: string): M => { m.name = name; m.userData.shared = true; return m; };

export function initTableAssets(tex: TextureLibrary): TableAssets {
  if (assets) return assets;
  const cm = tex.meta<CardMeta>('Card_Atlas')!;
  const km = tex.meta<ChipMeta>('Chip_Atlas')!;
  const stops = tex.meta<{ stops: string[] }>('Slot_Reel')!.stops;
  const cardTex = tex.get('Card_Atlas').BaseColor as Texture;
  const chipTex = tex.get('Chip_Atlas').BaseColor as Texture;
  const reelTex = tex.get('Slot_Reel').BaseColor as Texture;

  const cardCache = new Map<number, BufferGeometry>();
  const cellIndex = (c: Card | null) => (c === null || c.rank === 0 ? cm.back : cm.suits.indexOf(c.suit) * (cm.ranks[1] - cm.ranks[0] + 1) + (c.rank - cm.ranks[0]));
  const chipCache = new Map<number, BufferGeometry>();
  const reelCache = new Map<string, BufferGeometry>();

  assets = {
    card(c) {
      const k = cellIndex(c);
      let g = cardCache.get(k);
      if (!g) cardCache.set(k, (g = cardGeometry(k, cm)));
      g.userData.shared = true;
      return g;
    },
    // linen-finish card stock: matte, so a lamp overhead never washes the pips out
    cardMaterial: shared(new MeshStandardMaterial({ map: cardTex, color: new Color(0xc8c2b6), roughness: 0.9, metalness: 0, envMapIntensity: 0.15 }), 'MAT_Runtime_Card'),
    chip(k) {
      let g = chipCache.get(k);
      if (!g) chipCache.set(k, (g = chipGeometry(k, km)));
      g.userData.shared = true;
      return g;
    },
    chipMaterial: shared(new MeshPhysicalMaterial({ map: chipTex, roughness: 0.46, clearcoat: 0.35, clearcoatRoughness: 0.3 }), 'MAT_Runtime_Chip'),
    denoms: km.denoms,
    reel(radius, width) {
      const key = `${radius}:${width}`;
      let g = reelCache.get(key);
      if (!g) reelCache.set(key, (g = reelGeometry(radius, width)));
      g.userData.shared = true;
      return g;
    },
    // printed paper strip, faintly back-lit by the lamp in the reel window
    reelMaterial: shared(new MeshStandardMaterial({ map: reelTex, roughness: 0.55, emissive: new Color(0xfff2dc), emissiveMap: reelTex, emissiveIntensity: 0.28 }), 'MAT_Runtime_Reel'),
    reelStops: stops,
    ball: Object.assign(new SphereGeometry(0.0095, 20, 14), { userData: { shared: true } }),
    ballMaterial: shared(new MeshPhysicalMaterial({ color: 0xf4efe4, roughness: 0.18, clearcoat: 1, clearcoatRoughness: 0.05 }), 'MAT_Runtime_Ball'),
  };
  return assets;
}

/**
 * A playing card lying flat: +Y = face normal, −Z = the card's top, +X = its right. The top face shows the
 * card, the bottom face the back (so a face-down card is the same mesh rotated π about Z).
 */
function cardGeometry(cell: number, m: CardMeta): BufferGeometry {
  const r = 0.0035, seg = 4;
  const outline: [number, number][] = [];
  const corners: [number, number, number][] = [[CARD_W / 2 - r, -CARD_L / 2 + r, -Math.PI / 2], [CARD_W / 2 - r, CARD_L / 2 - r, 0], [-CARD_W / 2 + r, CARD_L / 2 - r, Math.PI / 2], [-CARD_W / 2 + r, -CARD_L / 2 + r, Math.PI]];
  for (const [cx, cz, a0] of corners) for (let i = 0; i <= seg; i++) { const a = a0 + (i / seg) * (Math.PI / 2); outline.push([cx + r * Math.cos(a), cz + r * Math.sin(a)]); }
  const cellUv = (k: number, fx: number, fy: number): [number, number] => {
    const col = k % m.cols, row = Math.floor(k / m.cols);
    return [(col * m.cell[0] + fx * m.cell[0]) / m.size, 1 - (row * m.cell[1] + fy * m.cell[1]) / m.size];
  };
  const pos: number[] = [], uv: number[] = [], nrm: number[] = [], idx: number[] = [];
  const face = (y: number, ny: number, k: number, mirror: boolean) => {
    const base = pos.length / 3;
    pos.push(0, y, 0); nrm.push(0, ny, 0); uv.push(...cellUv(k, 0.5, 0.5));
    for (const [x, z] of outline) {
      pos.push(x, y, z); nrm.push(0, ny, 0);
      uv.push(...cellUv(k, mirror ? 0.5 - x / CARD_W : 0.5 + x / CARD_W, 0.5 + z / CARD_L));
    }
    for (let i = 0; i < outline.length; i++) {
      const a = base + 1 + i, b = base + 1 + ((i + 1) % outline.length);
      if (ny > 0) idx.push(base, b, a); else idx.push(base, a, b);
    }
  };
  face(CARD_T / 2, 1, cell, false);
  face(-CARD_T / 2, -1, m.back, true);
  // edge: white card stock (sample a plain margin texel of the back cell)
  const edgeUv = cellUv(m.back, 0.02, 0.5);
  const base = pos.length / 3;
  for (const [x, z] of outline) {
    const l = Math.hypot(x, z) || 1;
    pos.push(x, CARD_T / 2, z, x, -CARD_T / 2, z);
    nrm.push(x / l, 0, z / l, x / l, 0, z / l);
    uv.push(...edgeUv, ...edgeUv);
  }
  for (let i = 0; i < outline.length; i++) {
    const a = base + i * 2, b = base + ((i + 1) % outline.length) * 2;
    idx.push(a, b, a + 1, b, b + 1, a + 1);
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new BufferAttribute(new Float32Array(pos), 3));
  g.setAttribute('normal', new BufferAttribute(new Float32Array(nrm), 3));
  g.setAttribute('uv', new BufferAttribute(new Float32Array(uv), 2));
  g.setIndex(idx);
  return g;
}

/** A chip (axis +Y, resting on y = 0) whose faces and striped edge map into the chip atlas. */
function chipGeometry(k: number, m: ChipMeta): BufferGeometry {
  const seg = 28;
  const cu = (k % m.grid) / m.grid + 0.5 / m.grid, cv = 1 - (Math.floor(k / m.grid) / m.grid + 0.5 / m.grid);
  const R = m.faceRadius;
  const pos: number[] = [], uv: number[] = [], nrm: number[] = [], idx: number[] = [];
  for (const [y, ny] of [[CHIP_H, 1], [0, -1]] as const) {
    const base = pos.length / 3;
    pos.push(0, y, 0); nrm.push(0, ny, 0); uv.push(cu, cv);
    for (let i = 0; i < seg; i++) {
      const a = (i / seg) * Math.PI * 2, c = Math.cos(a), s = Math.sin(a);
      pos.push(CHIP_R * c, y, CHIP_R * s); nrm.push(0, ny, 0); uv.push(cu + R * c, cv + R * s * (ny > 0 ? -1 : 1));
    }
    for (let i = 0; i < seg; i++) {
      const a = base + 1 + i, b = base + 1 + ((i + 1) % seg);
      if (ny > 0) idx.push(base, b, a); else idx.push(base, a, b);
    }
  }
  const base = pos.length / 3;
  for (let i = 0; i <= seg; i++) {
    const a = (i / seg) * Math.PI * 2, c = Math.cos(a), s = Math.sin(a);
    pos.push(CHIP_R * c, CHIP_H, CHIP_R * s, CHIP_R * c, 0, CHIP_R * s);
    nrm.push(c, 0, s, c, 0, s);
    uv.push(cu + R * c, cv - R * s, cu + m.rimInner * c, cv - m.rimInner * s);
  }
  for (let i = 0; i < seg; i++) {
    const a = base + i * 2, b = a + 2;
    idx.push(a, b, a + 1, b, b + 1, a + 1);
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new BufferAttribute(new Float32Array(pos), 3));
  g.setAttribute('normal', new BufferAttribute(new Float32Array(nrm), 3));
  g.setAttribute('uv', new BufferAttribute(new Float32Array(uv), 2));
  g.setIndex(idx);
  return g;
}

/**
 * A reel drum turning about +X: the strip wraps the circumference (v = θ / 2π, θ = 0 at the front, −Z,
 * increasing upward), u runs across the drum. Rotating the mesh by +ρ about X shows strip position −ρ.
 */
function reelGeometry(R: number, W: number): BufferGeometry {
  const seg = 72;
  const pos: number[] = [], uv: number[] = [], nrm: number[] = [], idx: number[] = [];
  for (let j = 0; j <= seg; j++) {
    const t = (j / seg) * Math.PI * 2, s = Math.sin(t), c = Math.cos(t);
    for (const x of [-W / 2, W / 2]) {
      pos.push(x, R * s, -R * c); nrm.push(0, s, -c); uv.push(0.5 - x / W, j / seg);   // viewer's right is −X
    }
  }
  for (let j = 0; j < seg; j++) {
    const a = j * 2, b = a + 2;
    idx.push(a, b, a + 1, b, b + 1, a + 1);   // counter-clockwise seen from outside
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new BufferAttribute(new Float32Array(pos), 3));
  g.setAttribute('normal', new BufferAttribute(new Float32Array(nrm), 3));
  g.setAttribute('uv', new BufferAttribute(new Float32Array(uv), 2));
  g.setIndex(idx);
  return g;
}
