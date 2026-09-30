import { CanvasTexture, SRGBColorSpace } from 'three/webgpu';

/**
 * Phase 1 placeholders for artwork that will later be authored textures (window backdrops,
 * oil paintings). Generated once at load on a canvas; deterministic via a seeded RNG.
 */
function rng(seed: number): () => number {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function finish(canvas: HTMLCanvasElement): CanvasTexture {
  const t = new CanvasTexture(canvas);
  t.colorSpace = SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

/** Night over the Riviera: indigo sky, stars, dark hills with warm villa lights, moonlit sea. */
export function rivieraNightTexture(seed = 7): CanvasTexture {
  const W = 1024, H = 1536;
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const g = c.getContext('2d')!;
  const r = rng(seed);

  const sky = g.createLinearGradient(0, 0, 0, H * 0.62);
  sky.addColorStop(0, '#05081a');
  sky.addColorStop(0.6, '#0d1636');
  sky.addColorStop(1, '#2a2a4a');
  g.fillStyle = sky;
  g.fillRect(0, 0, W, H);

  for (let i = 0; i < 380; i++) {
    const a = r() * 0.8 + 0.2;
    g.fillStyle = `rgba(255,248,230,${a * a})`;
    const s = r() < 0.05 ? 2.2 : 1.1;
    g.fillRect(r() * W, r() * H * 0.5, s, s);
  }
  // moon
  const mx = W * 0.72, my = H * 0.16;
  const glow = g.createRadialGradient(mx, my, 0, mx, my, 160);
  glow.addColorStop(0, 'rgba(255,245,220,0.35)');
  glow.addColorStop(1, 'rgba(255,245,220,0)');
  g.fillStyle = glow;
  g.fillRect(mx - 160, my - 160, 320, 320);
  g.fillStyle = '#fff6e0';
  g.beginPath(); g.arc(mx, my, 26, 0, Math.PI * 2); g.fill();

  // sea
  const horizon = H * 0.62;
  const sea = g.createLinearGradient(0, horizon, 0, H);
  sea.addColorStop(0, '#0e1530');
  sea.addColorStop(1, '#03050c');
  g.fillStyle = sea;
  g.fillRect(0, horizon, W, H - horizon);
  // moon path on the water
  for (let y = horizon + 4; y < H; y += 3) {
    const k = (y - horizon) / (H - horizon);
    const w = 20 + k * 220 * r();
    g.fillStyle = `rgba(255,236,200,${0.28 * (1 - k) * r()})`;
    g.fillRect(mx - w / 2 + (r() - 0.5) * 40 * k, y, w, 1.5);
  }

  // headland silhouette with villa lights
  g.fillStyle = '#04050a';
  g.beginPath();
  g.moveTo(0, horizon - 40);
  for (let x = 0; x <= W * 0.55; x += 16) {
    const y = horizon - 150 * Math.sin((x / (W * 0.55)) * Math.PI * 0.9) - 40 + (r() - 0.5) * 10;
    g.lineTo(x, y);
  }
  g.lineTo(W * 0.62, horizon + 2);
  g.lineTo(0, horizon + 2);
  g.fill();
  for (let i = 0; i < 90; i++) {
    const x = r() * W * 0.55;
    const top = horizon - 150 * Math.sin((x / (W * 0.55)) * Math.PI * 0.9) - 40;
    const y = top + r() * (horizon - top);
    g.fillStyle = r() < 0.8 ? `rgba(255,190,110,${0.5 + r() * 0.5})` : 'rgba(255,240,210,0.9)';
    g.fillRect(x, y, 2, 2);
    // reflection
    g.fillStyle = 'rgba(255,180,100,0.12)';
    g.fillRect(x, horizon + (horizon - y) * 0.4 + 6, 2, 10);
  }
  // distant yacht lights
  for (let i = 0; i < 6; i++) {
    g.fillStyle = 'rgba(255,230,190,0.9)';
    g.fillRect(W * (0.55 + r() * 0.4), horizon + 10 + r() * 50, 3, 2);
  }
  return finish(c);
}

/** A dark, varnished "old master" style landscape — deliberately soft and low-contrast. */
export function oilPaintingTexture(seed: number): CanvasTexture {
  const W = 768, H = 1024;
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const g = c.getContext('2d')!;
  const r = rng(seed);
  const warm = ['#3a2412', '#5a3a1c', '#2a1a0e', '#6b4a24'];
  const sky = g.createLinearGradient(0, 0, 0, H);
  sky.addColorStop(0, '#1c1610');
  sky.addColorStop(0.35, seed % 2 ? '#7a5a30' : '#5e6a60');
  sky.addColorStop(0.55, '#3a2a18');
  sky.addColorStop(1, '#120c07');
  g.fillStyle = sky;
  g.fillRect(0, 0, W, H);
  g.filter = 'blur(10px)';
  for (let i = 0; i < 70; i++) {
    g.fillStyle = warm[Math.floor(r() * warm.length)];
    g.globalAlpha = 0.25 + r() * 0.4;
    g.beginPath();
    g.ellipse(r() * W, H * (0.45 + r() * 0.55), 40 + r() * 180, 20 + r() * 90, r() * Math.PI, 0, Math.PI * 2);
    g.fill();
  }
  // a tree mass and a pale figure-ish highlight
  g.globalAlpha = 0.85;
  g.fillStyle = '#140e08';
  g.beginPath(); g.ellipse(W * 0.25, H * 0.42, 150, 230, 0.1, 0, Math.PI * 2); g.fill();
  g.globalAlpha = 0.6;
  g.fillStyle = '#c9a26a';
  g.beginPath(); g.ellipse(W * 0.62, H * 0.7, 26, 70, 0, 0, Math.PI * 2); g.fill();
  g.filter = 'none';
  g.globalAlpha = 1;
  // varnish vignette + craquelure speckle
  const v = g.createRadialGradient(W / 2, H / 2, H * 0.2, W / 2, H / 2, H * 0.75);
  v.addColorStop(0, 'rgba(0,0,0,0)');
  v.addColorStop(1, 'rgba(8,5,2,0.8)');
  g.fillStyle = v;
  g.fillRect(0, 0, W, H);
  for (let i = 0; i < 4000; i++) {
    g.fillStyle = `rgba(0,0,0,${r() * 0.18})`;
    g.fillRect(r() * W, r() * H, 1, 1);
  }
  return finish(c);
}

function canvas(w: number, h: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return [c, c.getContext('2d')!];
}

const SERIF = "'Cinzel', 'Trajan Pro', 'Times New Roman', serif";

/** Engraved brass-on-lacquer door plaque. Lines are drawn centred; first line is larger. */
export function plaqueTexture(lines: string[], w = 1024, h = 256): CanvasTexture {
  const [c, g] = canvas(w, h);
  const bg = g.createLinearGradient(0, 0, 0, h);
  bg.addColorStop(0, '#16100a');
  bg.addColorStop(1, '#0a0705');
  g.fillStyle = bg;
  g.fillRect(0, 0, w, h);
  g.strokeStyle = '#b08a48';
  g.lineWidth = 6;
  g.strokeRect(14, 14, w - 28, h - 28);
  g.lineWidth = 2;
  g.strokeRect(28, 28, w - 56, h - 56);
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  const gold = g.createLinearGradient(0, 0, 0, h);
  gold.addColorStop(0, '#f2d79a');
  gold.addColorStop(0.5, '#c9a45c');
  gold.addColorStop(1, '#8a6a2f');
  g.fillStyle = gold;
  const n = lines.length;
  lines.forEach((line, i) => {
    let size = i === 0 ? h * (n > 1 ? 0.3 : 0.4) : h * 0.17;
    const text = line.toUpperCase();
    // shrink long lines to fit inside the inner border
    for (;;) {
      g.font = `500 ${size}px ${SERIF}`;
      g.letterSpacing = `${size * 0.18}px`;
      if (g.measureText(text).width <= w - 110 || size < 12) break;
      size *= 0.92;
    }
    const y = n === 1 ? h / 2 : h * (i === 0 ? 0.42 : 0.72);
    g.fillText(text, w / 2, y);
  });
  return finish(c);
}

/** Felt printing for a cylinder-cap table top (cap UVs are circular: centre = 0.5,0.5). */
export function feltPrintTexture(kind: 'blackjack' | 'baccarat' | 'poker', base: string): CanvasTexture {
  const S = 1024;
  const [c, g] = canvas(S, S);
  g.fillStyle = base;
  g.fillRect(0, 0, S, S);
  // subtle felt mottling
  const r = rng(kind.length * 17);
  for (let i = 0; i < 9000; i++) {
    g.fillStyle = `rgba(0,0,0,${r() * 0.05})`;
    g.fillRect(r() * S, r() * S, 2, 2);
  }
  g.strokeStyle = 'rgba(232,206,140,0.85)';
  g.fillStyle = 'rgba(232,206,140,0.9)';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  const cx = S / 2, cy = S / 2;
  if (kind === 'blackjack') {
    // players sit on +Z → canvas bottom half (v small ↔ z positive after cap mapping flips; draw both arcs)
    g.lineWidth = 5;
    g.beginPath(); g.arc(cx, cy, S * 0.3, 0, Math.PI); g.stroke();
    arcText(g, 'BLACKJACK PAYS 3 TO 2', cx, cy, S * 0.36, Math.PI * 0.2, Math.PI * 0.8, 38);
    arcText(g, 'Dealer must draw to 16 and stand on all 17s', cx, cy, S * 0.25, Math.PI * 0.22, Math.PI * 0.78, 22);
    for (let i = 0; i < 5; i++) {
      const a = Math.PI * (0.1 + (i + 0.5) * 0.16);
      g.save(); g.translate(cx + Math.cos(a) * S * 0.41, cy + Math.sin(a) * S * 0.41); g.rotate(a - Math.PI / 2);
      g.strokeRect(-34, -24, 68, 48); g.restore();
    }
  } else if (kind === 'baccarat') {
    g.lineWidth = 4;
    for (const [rad, label] of [[0.3, 'BANQUE'], [0.38, 'JOUEUR']] as const) {
      g.beginPath(); g.arc(cx, cy, S * rad, Math.PI * 0.05, Math.PI * 0.95); g.stroke();
      arcText(g, label, cx, cy, S * (rad + 0.035), Math.PI * 0.4, Math.PI * 0.6, 30);
      arcText(g, label, cx, cy, S * (rad + 0.035), Math.PI * 1.4, Math.PI * 1.6, 30);
      g.beginPath(); g.arc(cx, cy, S * rad, Math.PI * 1.05, Math.PI * 1.95); g.stroke();
    }
    g.font = `500 44px ${SERIF}`;
    g.fillText('BACCARAT', cx, cy);
  } else {
    g.lineWidth = 4;
    g.beginPath(); g.arc(cx, cy, S * 0.34, 0, Math.PI * 2); g.stroke();
    g.font = `500 40px ${SERIF}`;
    g.fillText('LE GRAND RIVIERA', cx, cy);
  }
  return finish(c);
}

function arcText(g: CanvasRenderingContext2D, text: string, cx: number, cy: number, radius: number, a0: number, a1: number, size: number) {
  g.font = `500 ${size}px ${SERIF}`;
  const chars = [...text];
  chars.forEach((ch, i) => {
    const a = a1 - ((i + 0.5) / chars.length) * (a1 - a0);
    g.save();
    g.translate(cx + Math.cos(a) * radius, cy + Math.sin(a) * radius);
    g.rotate(a - Math.PI / 2);
    g.fillText(ch, 0, 0);
    g.restore();
  });
}

/** Roulette rotor for a cylinder cap: 37 pockets (single zero), numbers in wheel order. */
export function rouletteWheelTexture(): CanvasTexture {
  const S = 1024;
  const [c, g] = canvas(S, S);
  const order = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26];
  const cx = S / 2, cy = S / 2;
  g.fillStyle = '#2a1a0e';
  g.fillRect(0, 0, S, S);
  const n = order.length;
  for (let i = 0; i < n; i++) {
    const a0 = (i / n) * Math.PI * 2, a1 = ((i + 1) / n) * Math.PI * 2;
    const num = order[i];
    g.fillStyle = num === 0 ? '#136b33' : i % 2 ? '#8e1414' : '#141010';
    g.beginPath(); g.moveTo(cx, cy); g.arc(cx, cy, S * 0.49, a0, a1); g.closePath(); g.fill();
    g.strokeStyle = '#c9a45c'; g.lineWidth = 3;
    g.beginPath(); g.moveTo(cx + Math.cos(a0) * S * 0.3, cy + Math.sin(a0) * S * 0.3); g.lineTo(cx + Math.cos(a0) * S * 0.49, cy + Math.sin(a0) * S * 0.49); g.stroke();
    g.save();
    const am = (a0 + a1) / 2;
    g.translate(cx + Math.cos(am) * S * 0.44, cy + Math.sin(am) * S * 0.44);
    g.rotate(am + Math.PI / 2);
    g.fillStyle = '#f3e6c8';
    g.font = `600 30px ${SERIF}`;
    g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(String(num), 0, 0);
    g.restore();
  }
  // inner cone: polished wood with gilt spokes
  const cone = g.createRadialGradient(cx, cy, 0, cx, cy, S * 0.3);
  cone.addColorStop(0, '#6b4424'); cone.addColorStop(1, '#2a1709');
  g.fillStyle = cone;
  g.beginPath(); g.arc(cx, cy, S * 0.3, 0, Math.PI * 2); g.fill();
  g.strokeStyle = '#d8ad5c'; g.lineWidth = 8;
  for (let k = 0; k < 4; k++) {
    const a = (k / 4) * Math.PI * 2;
    g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.cos(a) * S * 0.26, cy + Math.sin(a) * S * 0.26); g.stroke();
  }
  g.beginPath(); g.arc(cx, cy, S * 0.3, 0, Math.PI * 2); g.stroke();
  return finish(c);
}

/** French roulette betting layout (for a box top whose UVs span 0..1). Landscape: numbers run along U. */
export function rouletteLayoutTexture(): CanvasTexture {
  const W = 2048, H = 768;
  const [c, g] = canvas(W, H);
  g.fillStyle = '#1b5a32';
  g.fillRect(0, 0, W, H);
  const reds = new Set([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]);
  const x0 = 220, cw = 128, ch = 150, y0 = 90;
  g.strokeStyle = '#e8ce8c'; g.lineWidth = 4;
  g.textAlign = 'center'; g.textBaseline = 'middle';
  // zero
  g.fillStyle = '#136b33';
  g.fillRect(x0 - 150, y0, 150, ch * 3); g.strokeRect(x0 - 150, y0, 150, ch * 3);
  g.fillStyle = '#f3e6c8'; g.font = `600 64px ${SERIF}`; g.fillText('0', x0 - 75, y0 + ch * 1.5);
  for (let col = 0; col < 12; col++) {
    for (let row = 0; row < 3; row++) {
      const n = col * 3 + (3 - row);
      const x = x0 + col * cw, y = y0 + row * ch;
      g.strokeRect(x, y, cw, ch);
      g.fillStyle = reds.has(n) ? '#9a1818' : '#151111';
      g.beginPath(); g.ellipse(x + cw / 2, y + ch / 2, 44, 52, 0, 0, Math.PI * 2); g.fill();
      g.fillStyle = '#f3e6c8'; g.font = `600 52px ${SERIF}`;
      g.fillText(String(n), x + cw / 2, y + ch / 2 + 2);
    }
  }
  const labels = ['1ère DOUZAINE', '2ème DOUZAINE', '3ème DOUZAINE'];
  g.font = `500 40px ${SERIF}`;
  labels.forEach((l, i) => {
    const x = x0 + i * cw * 4;
    g.strokeRect(x, y0 + ch * 3, cw * 4, 110);
    g.fillStyle = '#e8ce8c'; g.fillText(l, x + cw * 2, y0 + ch * 3 + 55);
  });
  const evens = ['MANQUE', 'PAIR', '◆', '◆', 'IMPAIR', 'PASSE'];
  evens.forEach((l, i) => {
    const x = x0 + i * cw * 2;
    g.strokeRect(x, y0 + ch * 3 + 110, cw * 2, 110);
    g.fillStyle = l === '◆' ? (i === 2 ? '#9a1818' : '#151111') : '#e8ce8c';
    g.font = l === '◆' ? '90px serif' : `500 38px ${SERIF}`;
    g.fillText(l, x + cw, y0 + ch * 3 + 165);
  });
  return finish(c);
}

/** Slot-machine reel window (Art-Deco style), drawn once and shared by every machine in a room. */
export function slotScreenTexture(seed: number): CanvasTexture {
  const W = 512, H = 640;
  const [c, g] = canvas(W, H);
  const r = rng(seed);
  const bg = g.createLinearGradient(0, 0, 0, H);
  bg.addColorStop(0, '#2a0d3a'); bg.addColorStop(1, '#0a0418');
  g.fillStyle = bg; g.fillRect(0, 0, W, H);
  g.textAlign = 'center'; g.textBaseline = 'middle';
  // title
  g.fillStyle = '#ffd36a';
  g.font = `700 54px ${SERIF}`;
  g.fillText('JACKPOT', W / 2, 70);
  g.font = `500 26px ${SERIF}`;
  g.fillStyle = '#ffb04a';
  g.fillText('★ RIVIERA ★', W / 2, 118);
  // reels
  const symbols = ['7', '♦', '♣', 'BAR', '♥', '★', '♠'];
  const colors = ['#ff3a3a', '#ffcf4a', '#7ae07a', '#f3e6c8', '#ff5a8a', '#ffd36a', '#8ab8ff'];
  for (let k = 0; k < 3; k++) {
    const x = 40 + k * 150;
    const reel = g.createLinearGradient(0, 170, 0, 530);
    reel.addColorStop(0, '#8a8070'); reel.addColorStop(0.5, '#fbf4e4'); reel.addColorStop(1, '#8a8070');
    g.fillStyle = reel; g.fillRect(x, 170, 132, 360);
    for (let j = 0; j < 3; j++) {
      const s = Math.floor(r() * symbols.length);
      g.fillStyle = colors[s];
      g.font = symbols[s] === 'BAR' ? `800 40px ${SERIF}` : `800 76px ${SERIF}`;
      g.fillText(symbols[s], x + 66, 230 + j * 120);
    }
  }
  g.strokeStyle = '#ff3a3a'; g.lineWidth = 4;
  g.beginPath(); g.moveTo(24, 350); g.lineTo(W - 24, 350); g.stroke();
  g.fillStyle = '#ffd36a'; g.font = `600 30px ${SERIF}`;
  g.fillText('CRÉDITS  1 000', W / 2, 590);
  return finish(c);
}
