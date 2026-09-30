// Printed artwork for the games, drawn as SVG and rasterised with sharp (librsvg):
//
//   runtime sets (public/assets/textures + textures.json)   Card_Atlas · Chip_Atlas · Slot_Reel
//   Blender zone textures (blender/textures_src/games/)      felt layouts · roulette wheel ring ·
//                                                            slot marquee + belly glass
//
//   npm run make-game-textures
//
// Coordinates for felts are the tables' plan view in metres (see blender/tools/casino_props.py): the
// felt's UV0 is its bounding box, so a layout drawn here lands exactly where the geometry expects it.

import { mkdir, writeFile, readFile, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import sharp from 'sharp';

const ROOT = path.resolve(import.meta.dirname, '..');
const SRC = path.join(ROOT, 'blender/textures_src/games');
const WEB = path.join(ROOT, 'public/assets/textures');
const SERIF = "Didot, 'Bodoni 72', Georgia, serif";
const INK = '#d9bd7a';       // gold-leaf printing on felt
const RED = '#a8141d';
const BLACK = '#17130f';

// ------------------------------------------------------------------ suits (100 × 100 boxes)
const SUIT = {
  H: 'M50 92 C22 68 2 50 2 30 C2 13 14 2 29 2 C39 2 46 8 50 17 C54 8 61 2 71 2 C86 2 98 13 98 30 C98 50 78 68 50 92 Z',
  D: 'M50 2 L86 50 L50 98 L14 50 Z',
  S: 'M50 2 C58 20 98 38 98 60 C98 77 86 86 72 86 C63 86 56 82 53 76 C55 87 60 94 68 99 L32 99 C40 94 45 87 47 76 C44 82 37 86 28 86 C14 86 2 77 2 60 C2 38 42 20 50 2 Z',
  C: 'M50 4 A21 21 0 1 1 49.9 4 Z M27 36 A21 21 0 1 1 26.9 36 Z M73 36 A21 21 0 1 1 72.9 36 Z M44 50 L56 50 C56 76 61 90 69 99 L31 99 C39 90 44 76 44 50 Z',
};
const suitColour = (s) => (s === 'H' || s === 'D' ? RED : BLACK);
const pip = (s, x, y, size, flip = false) =>
  `<path d="${SUIT[s]}" fill="${suitColour(s)}" transform="translate(${x} ${y}) rotate(${flip ? 180 : 0}) translate(${-size / 2} ${-size / 2}) scale(${size / 100})"/>`;

// ------------------------------------------------------------------ playing cards
const CW = 204, CH = 285, COLS = 10;              // 63 × 88 mm at ~3.2 px/mm
const RANK = (r) => (r <= 10 ? String(r) : 'JQKA'[r - 11]);
const PIPS = {
  2: [[0.5, 0.2], [0.5, 0.8]], 3: [[0.5, 0.2], [0.5, 0.5], [0.5, 0.8]],
  4: [[0.3, 0.2], [0.7, 0.2], [0.3, 0.8], [0.7, 0.8]], 5: [[0.3, 0.2], [0.7, 0.2], [0.5, 0.5], [0.3, 0.8], [0.7, 0.8]],
  6: [[0.3, 0.2], [0.7, 0.2], [0.3, 0.5], [0.7, 0.5], [0.3, 0.8], [0.7, 0.8]],
  7: [[0.3, 0.2], [0.7, 0.2], [0.5, 0.35], [0.3, 0.5], [0.7, 0.5], [0.3, 0.8], [0.7, 0.8]],
  8: [[0.3, 0.2], [0.7, 0.2], [0.5, 0.35], [0.3, 0.5], [0.7, 0.5], [0.5, 0.65], [0.3, 0.8], [0.7, 0.8]],
  9: [[0.3, 0.2], [0.7, 0.2], [0.3, 0.4], [0.7, 0.4], [0.5, 0.5], [0.3, 0.6], [0.7, 0.6], [0.3, 0.8], [0.7, 0.8]],
  10: [[0.3, 0.2], [0.7, 0.2], [0.5, 0.3], [0.3, 0.4], [0.7, 0.4], [0.3, 0.6], [0.7, 0.6], [0.5, 0.7], [0.3, 0.8], [0.7, 0.8]],
};
const CROWN = 'M0 30 L8 6 L22 20 L32 0 L42 20 L56 6 L64 30 Z';

function cardFace(rank, suit) {
  const c = suitColour(suit);
  const idx = (x, y, rot) => `<g transform="translate(${x} ${y}) rotate(${rot})">
      <text x="0" y="0" font-family="${SERIF}" font-size="34" font-weight="bold" fill="${c}" text-anchor="middle">${RANK(rank)}</text>
      ${pip(suit, 0, 20, 22)}</g>`;
  let centre = '';
  if (rank <= 10) {
    const ix0 = 38, iy0 = 34, iw = CW - 76, ih = CH - 68;
    centre = PIPS[rank].map(([u, v]) => pip(suit, ix0 + u * iw, iy0 + v * ih, rank >= 9 ? 34 : 40, v > 0.55)).join('');
  } else if (rank === 14) {
    centre = `<circle cx="${CW / 2}" cy="${CH / 2}" r="46" fill="none" stroke="${c}" stroke-width="1.4" opacity="0.55"/>
      <circle cx="${CW / 2}" cy="${CH / 2}" r="52" fill="none" stroke="#b89448" stroke-width="0.9" opacity="0.8"/>
      ${pip(suit, CW / 2, CH / 2, suit === 'S' ? 78 : 66)}`;
  } else {
    // court cards: an engraved panel with crowned monogram (period playing-card style, not a portrait)
    const x0 = 36, y0 = 36, w = CW - 72, h = CH - 72;
    centre = `<rect x="${x0}" y="${y0}" width="${w}" height="${h}" rx="6" fill="url(#court${suit === 'H' || suit === 'D' ? 'R' : 'B'})" stroke="#b89448" stroke-width="2"/>
      <rect x="${x0 + 5}" y="${y0 + 5}" width="${w - 10}" height="${h - 10}" rx="4" fill="none" stroke="${c}" stroke-width="1"/>
      <line x1="${x0 + 8}" y1="${CH / 2}" x2="${x0 + w - 8}" y2="${CH / 2}" stroke="#b89448" stroke-width="1"/>
      ${[1, -1].map((f) => `<g transform="rotate(${f > 0 ? 0 : 180} ${CW / 2} ${CH / 2})">
        <path d="${CROWN}" fill="#c9a24e" stroke="#7a5a1c" stroke-width="1" transform="translate(${CW / 2 - 24} ${y0 + 12}) scale(0.75)"/>
        <text x="${CW / 2}" y="${y0 + 82}" font-family="${SERIF}" font-size="56" font-weight="bold" fill="${c}" text-anchor="middle">${RANK(rank)}</text>
        ${pip(suit, CW / 2, y0 + 100, 22)}</g>`).join('')}`;
  }
  return `<rect width="${CW}" height="${CH}" fill="url(#stock)"/>
    ${idx(20, 40, 0)}${idx(CW - 20, CH - 40, 180)}${centre}`;
}

function cardBack() {
  return `<rect width="${CW}" height="${CH}" fill="#f4efe3"/>
    <rect x="10" y="10" width="${CW - 20}" height="${CH - 20}" rx="6" fill="#6b0f18"/>
    <rect x="10" y="10" width="${CW - 20}" height="${CH - 20}" rx="6" fill="url(#lattice)"/>
    <rect x="16" y="16" width="${CW - 32}" height="${CH - 32}" rx="4" fill="none" stroke="#c9a24e" stroke-width="1.6"/>
    <ellipse cx="${CW / 2}" cy="${CH / 2}" rx="42" ry="54" fill="#5a0c14" stroke="#c9a24e" stroke-width="2"/>
    <text x="${CW / 2}" y="${CH / 2 + 14}" font-family="${SERIF}" font-size="40" fill="#d9bd7a" text-anchor="middle">GR</text>`;
}

async function cardAtlas() {
  const W = 2048, H = 2048;
  const cells = [];
  for (const s of ['S', 'H', 'D', 'C']) for (let r = 2; r <= 14; r++) cells.push(cardFace(r, s));
  cells.push(cardBack());
  const body = cells.map((svg, k) => `<g transform="translate(${(k % COLS) * CW} ${Math.floor(k / COLS) * CH})">${svg}</g>`).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}">
    <defs>
      <linearGradient id="stock" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fbf8f0"/><stop offset="1" stop-color="#efe8d9"/></linearGradient>
      <linearGradient id="courtR" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f7ecd8"/><stop offset="1" stop-color="#f1dcc4"/></linearGradient>
      <linearGradient id="courtB" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#eef0ea"/><stop offset="1" stop-color="#dfe3dc"/></linearGradient>
      <pattern id="lattice" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="14" height="14" fill="none"/><path d="M0 0 L14 0 M0 0 L0 14" stroke="#c9a24e" stroke-width="0.8" opacity="0.55"/>
        <circle cx="7" cy="7" r="1.3" fill="#c9a24e" opacity="0.5"/></pattern>
    </defs><rect width="${W}" height="${H}" fill="#6b0f18"/>${body}</svg>`;
  return sharp(Buffer.from(svg)).png();
}

// ------------------------------------------------------------------ chips (2 × 2 atlas of 512² faces)
const CHIPS = [
  { v: 10, base: '#1f4f95', insert: '#f1ede4', inlay: '#e9e1cf', ink: '#1f4f95' },
  { v: 25, base: '#1d7a3e', insert: '#f1ede4', inlay: '#e9e1cf', ink: '#1d6a36' },
  { v: 100, base: '#161412', insert: '#e9e3d6', inlay: '#e9e1cf', ink: '#161412' },
  { v: 500, base: '#5a2a86', insert: '#f3d77a', inlay: '#efe6d4', ink: '#4c2272' },
];
function chipFace(ch) {
  const c = 256, r = 250;
  const inserts = Array.from({ length: 8 }, (_, k) => {
    const a = (k / 8) * 360;
    return `<rect x="${c - 22}" y="${c - r + 2}" width="44" height="56" fill="${ch.insert}" transform="rotate(${a} ${c} ${c})"/>`;
  }).join('');
  const ticks = Array.from({ length: 48 }, (_, k) => `<rect x="${c - 1.5}" y="${c - 168}" width="3" height="10" fill="${ch.insert}" opacity="0.8" transform="rotate(${k * 7.5} ${c} ${c})"/>`).join('');
  return `<circle cx="${c}" cy="${c}" r="${r}" fill="${ch.base}"/>
    <circle cx="${c}" cy="${c}" r="${r}" fill="url(#chipShade)"/>${inserts}
    <circle cx="${c}" cy="${c}" r="176" fill="none" stroke="${ch.insert}" stroke-width="3"/>${ticks}
    <circle cx="${c}" cy="${c}" r="150" fill="${ch.inlay}"/>
    <circle cx="${c}" cy="${c}" r="142" fill="none" stroke="#b89448" stroke-width="2.5"/>
    ${arcText((x, y) => [c + x, c - y], 1, 0, 0, 112, Math.PI / 2, 'LE GRAND RIVIERA', 25, { inward: false, track: 0.2 }).replaceAll(`fill="${INK}"`, `fill="${ch.ink}"`)}
    <text x="${c}" y="${c + 44}" font-family="${SERIF}" font-weight="bold" font-size="${ch.v >= 100 ? 104 : 124}" fill="${ch.ink}" text-anchor="middle">${ch.v}</text>
    <text x="${c}" y="${c + 92}" font-family="${SERIF}" font-size="20" letter-spacing="4" fill="${ch.ink}" text-anchor="middle">MONTE-CARLO</text>`;
}
async function chipAtlas() {
  const body = CHIPS.map((ch, k) => `<g transform="translate(${(k % 2) * 512} ${Math.floor(k / 2) * 512})">${chipFace(ch)}</g>`).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1024" height="1024">
    <defs><radialGradient id="chipShade" cx="0.45" cy="0.4" r="0.7"><stop offset="0" stop-color="#fff" stop-opacity="0.08"/><stop offset="1" stop-color="#000" stop-opacity="0.12"/></radialGradient></defs>
    <rect width="1024" height="1024" fill="#222"/>${body}</svg>`;
  return sharp(Buffer.from(svg)).png();
}

// ------------------------------------------------------------------ slot reel strip (12 stops)
export const REEL_STOPS = ['seven', 'cherry', 'bell', 'lemon', 'bar', 'cherry', 'diamond', 'lemon', 'bell', 'cherry', 'bar', 'lemon'];
function symbol(kind, cx, cy, s) {
  const g = (inner) => `<g transform="translate(${cx} ${cy}) scale(${s / 100})">${inner}</g>`;
  switch (kind) {
    case 'cherry': return g(`<path d="M-4 -44 C8 -60 30 -62 44 -54 C28 -48 14 -44 -4 -44 Z" fill="#2f7a2c" stroke="#1d4d1b" stroke-width="2"/>
      <path d="M-4 -44 C-10 -20 -20 0 -24 14 M-4 -44 C4 -20 14 -2 22 14" stroke="#4a3a14" stroke-width="5" fill="none"/>
      <circle cx="-26" cy="26" r="24" fill="url(#cherryG)" stroke="#5a0808" stroke-width="2"/><circle cx="24" cy="28" r="24" fill="url(#cherryG)" stroke="#5a0808" stroke-width="2"/>
      <ellipse cx="-33" cy="17" rx="7" ry="5" fill="#fff" opacity="0.7"/><ellipse cx="17" cy="19" rx="7" ry="5" fill="#fff" opacity="0.7"/>`);
    case 'lemon': return g(`<path d="M-50 0 C-48 -30 -20 -44 6 -42 C30 -40 46 -26 52 -6 L60 -8 L56 4 C50 30 22 44 -6 42 C-32 40 -50 22 -50 0 Z" fill="url(#lemonG)" stroke="#8a6d05" stroke-width="2.5"/>
      <ellipse cx="-12" cy="-18" rx="18" ry="8" fill="#fff" opacity="0.45"/>`);
    case 'bell': return g(`<path d="M0 -52 C-6 -52 -8 -46 -8 -42 C-30 -36 -36 -12 -38 8 C-40 24 -48 32 -54 38 L54 38 C48 32 40 24 38 8 C36 -12 30 -36 8 -42 C8 -46 6 -52 0 -52 Z" fill="url(#goldG)" stroke="#6b4c0f" stroke-width="2.5"/>
      <circle cx="0" cy="46" r="10" fill="url(#goldG)" stroke="#6b4c0f" stroke-width="2"/><path d="M-22 -18 C-26 -2 -28 14 -32 26" stroke="#fff" stroke-width="5" opacity="0.5" fill="none"/>`);
    case 'bar': return g(`<rect x="-62" y="-24" width="124" height="48" rx="6" fill="#141414" stroke="#c9a24e" stroke-width="4"/>
      <text x="0" y="16" font-family="Georgia" font-weight="bold" font-size="42" fill="#f3efe4" text-anchor="middle" letter-spacing="6">BAR</text>`);
    case 'seven': return g(`<path d="M-40 -46 L44 -46 L44 -30 C18 -4 4 22 -2 50 L-28 50 C-20 20 -4 -8 16 -26 L-40 -26 Z" fill="url(#sevenG)" stroke="#d9bd7a" stroke-width="4" stroke-linejoin="round"/>`);
    case 'diamond': return g(`<path d="M-46 -14 L-26 -38 L26 -38 L46 -14 L0 44 Z" fill="url(#gemG)" stroke="#123a6a" stroke-width="2.5"/>
      <path d="M-46 -14 L46 -14 M-26 -38 L-12 -14 L0 44 L12 -14 L26 -38 M-12 -14 L0 -38 L12 -14" stroke="#e8f2ff" stroke-width="1.6" opacity="0.8" fill="none"/>`);
  }
}
async function reelStrip() {
  const W = 512, H = 2048, cell = H / REEL_STOPS.length;
  const body = REEL_STOPS.map((k, i) => `<rect y="${i * cell}" width="${W}" height="${cell}" fill="url(#paper)"/>
    <line x1="0" y1="${i * cell}" x2="${W}" y2="${i * cell}" stroke="#c9b894" stroke-width="2"/>
    ${symbol(k, W / 2, i * cell + cell / 2, cell * 0.78)}`).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}"><defs>
    <linearGradient id="paper" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#e9e0cc"/><stop offset="0.5" stop-color="#faf6ec"/><stop offset="1" stop-color="#e9e0cc"/></linearGradient>
    <radialGradient id="cherryG" cx="0.35" cy="0.3" r="0.8"><stop offset="0" stop-color="#ff4a4a"/><stop offset="0.6" stop-color="#b3101a"/><stop offset="1" stop-color="#5a0808"/></radialGradient>
    <radialGradient id="lemonG" cx="0.4" cy="0.35" r="0.8"><stop offset="0" stop-color="#fff38a"/><stop offset="0.7" stop-color="#f2c812"/><stop offset="1" stop-color="#b58d05"/></radialGradient>
    <linearGradient id="goldG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fbe7a1"/><stop offset="0.45" stop-color="#d6a633"/><stop offset="1" stop-color="#7a5510"/></linearGradient>
    <linearGradient id="sevenG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff3b3b"/><stop offset="1" stop-color="#8a0a12"/></linearGradient>
    <linearGradient id="gemG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9fd0ff"/><stop offset="0.5" stop-color="#2f7ad8"/><stop offset="1" stop-color="#0f3b7a"/></linearGradient>
    </defs>${body}</svg>`;
  return sharp(Buffer.from(svg)).png();
}

// ------------------------------------------------------------------ felts (plan view, metres → px)
function feltSvg({ w, h, W, H, colour, draw }) {
  const sx = W / w, sy = H / h;
  const P = (x, y) => [(x - (-w / 2)) * sx, (h / 2 - y) * sy];   // plan (x right, y up) → image
  return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${W}" height="${H}"><defs>
    <filter id="fibre" x="0" y="0" width="1" height="1"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed="7"/>
      <feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.10 0"/><feComposite in2="SourceGraphic" operator="in"/></filter>
    <filter id="mottle"><feTurbulence type="fractalNoise" baseFrequency="0.006" numOctaves="2" seed="3"/>
      <feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.10 0"/></filter>
    <filter id="ink"><feTurbulence type="fractalNoise" baseFrequency="1.4" numOctaves="1" seed="11" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="1.4"/></filter></defs>
    <rect width="${W}" height="${H}" fill="${colour}"/>
    <rect width="${W}" height="${H}" filter="url(#mottle)"/>
    <rect width="${W}" height="${H}" fill="#fff" filter="url(#fibre)"/>
    <g filter="url(#ink)" opacity="0.92">${draw(P, sx)}</g></svg>`;
}
/**
 * Text laid along a circular arc, one glyph at a time (librsvg has no <textPath>). Plan coordinates.
 * inward = true: glyph tops face the centre (read by someone outside the arc looking in, e.g. players at
 * a half-moon table); the text then runs counter-clockwise.
 */
function arcText(P, s, cx, cy, r, aMid, text, size, { inward = true, weight = 'normal', track = 0.14 } = {}) {
  const adv = size * (0.66 + track);                        // average cap advance of Didot + tracking
  const span = (adv * text.length) / r;
  let out = '';
  [...text].forEach((ch, i) => {
    const a = inward ? aMid - span / 2 + (i + 0.5) * (adv / r) : aMid + span / 2 - (i + 0.5) * (adv / r);
    if (ch === ' ') return;
    const [x, y] = P(cx + r * Math.cos(a), cy + r * Math.sin(a));
    const rot = (inward ? 270 : 90) - (a * 180) / Math.PI;
    out += `<text x="${x}" y="${y}" font-family="${SERIF}" font-size="${size * s}" font-weight="${weight}" fill="${INK}" text-anchor="middle" dominant-baseline="middle" transform="rotate(${rot} ${x} ${y})">${ch}</text>`;
  });
  return out;
}
const circle = (P, s, x, y, r, sw = 0.006, fill = 'none') => { const [a, b] = P(x, y); return `<circle cx="${a}" cy="${b}" r="${r * s}" fill="${fill}" stroke="${INK}" stroke-width="${sw * s}"/>`; };
const label = (P, s, x, y, text, size, rot = 0, weight = 'normal') => { const [a, b] = P(x, y); return `<text x="${a}" y="${b}" font-family="${SERIF}" font-size="${size * s}" font-weight="${weight}" fill="${INK}" text-anchor="middle" dominant-baseline="middle" transform="rotate(${rot} ${a} ${b})" letter-spacing="${size * s * 0.1}">${text}</text>`; };
const crest = (P, s, x, y, size) => { const [a, b] = P(x, y); const k = size * s / 100;
  return `<g transform="translate(${a} ${b}) scale(${k})" fill="none" stroke="${INK}" stroke-width="2.2">
    <path d="M-40 -18 C-40 20 -20 40 0 48 C20 40 40 20 40 -18 L0 -34 Z"/><path d="M-30 -14 C-30 14 -14 30 0 37 C14 30 30 14 30 -14 L0 -26 Z" stroke-width="1.2"/>
    <text x="0" y="12" font-family="${SERIF}" font-size="30" fill="${INK}" stroke="none" text-anchor="middle">GR</text>
    <path d="${CROWN}" transform="translate(-24 -62) scale(0.75)" fill="${INK}" stroke="none"/></g>`; };

// Blackjack half-moon: R = 1.25, dealer edge on y = 0, players around the arc (+y). Seats at a = π(0.1 + (i + .5)·0.16).
export const BJ = { R: 1.25, spots: [0, 1, 2, 3, 4].map((i) => Math.PI * (0.1 + (i + 0.5) * 0.16)), spotR: 0.98 };
function blackjackFelt() {
  const w = 2.5, h = 1.25;
  return feltSvg({ w, h: h * 2, W: 2048, H: 2048, colour: '#0c2d1d', draw: (P, s) => {
    const cy = 0;
    let out = '';
    out += arcText(P, s, 0, cy, 0.86, Math.PI / 2, 'BLACKJACK PAYS 3 TO 2', 0.066, { weight: 'bold' });
    out += arcText(P, s, 0, cy, 0.6, Math.PI / 2, 'DEALER MUST DRAW TO 16 AND STAND ON ALL 17S', 0.03);
    // insurance band
    for (const r of [0.68, 0.76]) {
      const [x0, y0] = P(r * Math.cos(Math.PI * 0.78), r * Math.sin(Math.PI * 0.78)), [x1, y1] = P(r * Math.cos(Math.PI * 0.22), r * Math.sin(Math.PI * 0.22));
      out += `<path d="M ${x0} ${y0} A ${r * s} ${r * s} 0 0 1 ${x1} ${y1}" fill="none" stroke="${INK}" stroke-width="${0.005 * s}"/>`;
    }
    out += arcText(P, s, 0, cy, 0.72, Math.PI / 2, 'INSURANCE PAYS 2 TO 1', 0.032);
    for (const a of BJ.spots) {
      const x = BJ.spotR * Math.cos(a), y = BJ.spotR * Math.sin(a);
      out += circle(P, s, x, y, 0.09, 0.007) + circle(P, s, x, y, 0.078, 0.003);
    }
    out += `<g transform="rotate(180 ${P(0, 0.26)[0]} ${P(0, 0.26)[1]})">${crest(P, s, 0, 0.26, 0.16)}</g>` + label(P, s, 0, 0.4, 'LE GRAND RIVIERA', 0.035, 180);
    return out;
  } });
}

// Poker oval: half-width 1.365, half-depth 0.78
export const PK = { a: 1.365, b: 0.78 };
function pokerFelt() {
  return feltSvg({ w: 2 * PK.a, h: 2 * PK.b, W: 2048, H: 1024, colour: '#0d2e22', draw: (P, s) => {
    const [cx, cy] = P(0, 0);
    return `<ellipse cx="${cx}" cy="${cy}" rx="${(PK.a - 0.2) * s}" ry="${(PK.b - 0.2) * s}" fill="none" stroke="${INK}" stroke-width="${0.007 * s}"/>
      <ellipse cx="${cx}" cy="${cy}" rx="${(PK.a - 0.23) * s}" ry="${(PK.b - 0.23) * s}" fill="none" stroke="${INK}" stroke-width="${0.003 * s}"/>
      ${crest(P, s, 0, 0.1, 0.16)}${label(P, s, 0, -0.1, 'LE GRAND RIVIERA', 0.05)}${label(P, s, 0, -0.18, "TEXAS HOLD'EM", 0.03)}`;
  } });
}

// Baccarat oval: half-width 1.995, half-depth 0.95; croupier at −y
export const BC = { a: 1.995, b: 0.95 };
function baccaratFelt() {
  return feltSvg({ w: 2 * BC.a, h: 2 * BC.b, W: 2048, H: 1024, colour: '#0e2a1f', draw: (P, s) => {
    const [cx, cy] = P(0, 0);
    let out = `<ellipse cx="${cx}" cy="${cy}" rx="${(BC.a - 0.16) * s}" ry="${(BC.b - 0.16) * s}" fill="none" stroke="${INK}" stroke-width="${0.006 * s}"/>
      <ellipse cx="${cx}" cy="${cy}" rx="${(BC.a - 0.46) * s}" ry="${(BC.b - 0.4) * s}" fill="none" stroke="${INK}" stroke-width="${0.005 * s}"/>
      <ellipse cx="${cx}" cy="${cy}" rx="${(BC.a - 0.72) * s}" ry="${(BC.b - 0.6) * s}" fill="none" stroke="${INK}" stroke-width="${0.004 * s}"/>`;
    out += label(P, s, 0, 0.62, 'BANQUE', 0.07, 180, 'bold') + label(P, s, 0, 0.44, 'JOUEUR', 0.06, 180) + label(P, s, 0, 0.3, 'ÉGALITÉ PAIE 8 CONTRE 1', 0.028, 180);
    out += crest(P, s, 0, -0.5, 0.11) + label(P, s, 0, -0.66, 'BACCARAT', 0.045);
    // the croupier lays the coup in the middle of the table, where every seat can read it
    for (const [x, t] of [[-0.3, 'JOUEUR'], [0.3, 'BANQUE']]) {
      const [a, b] = P(x - 0.2, -0.07), [a2, b2] = P(x + 0.2, -0.33);
      out += `<rect x="${a}" y="${b}" width="${a2 - a}" height="${b2 - b}" rx="${0.02 * s}" fill="none" stroke="${INK}" stroke-width="${0.005 * s}"/>` + label(P, s, x, -0.02, t, 0.03, 180);
    }
    // numbered stations around the rim
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * 2 * Math.PI + Math.PI / 12;
      if (Math.sin(a) < -0.9) continue;
      const x = Math.cos(a) * (BC.a - 0.3), y = Math.sin(a) * (BC.b - 0.28);
      out += circle(P, s, x, y, 0.08, 0.005) + label(P, s, x, y, String(i + 1), 0.06, 270 - (a * 180) / Math.PI);  // tops toward the centre
    }
    return out;
  } });
}

// Roulette layout: 12 × 3 grid, cell 0.13 × 0.22 m, plus zero, dozens and even-money boxes (plan metres)
export const RL = { w: 1.9, h: 1.15, cw: 0.13, ch: 0.22, x0: -0.78, rowY0: 0.33, dozenY: -0.28, dozenH: 0.1, evenY: -0.4, evenH: 0.12 };
/** Bet-box centres in the layout's plan (metres, felt centre = origin) — exported so chips land on the print. */
export function rouletteBoxes() {
  const { cw, ch, x0, rowY0, dozenY, evenY } = RL;
  const numbers = {};
  for (let col = 0; col < 12; col++) for (let row = 0; row < 3; row++) numbers[col * 3 + (3 - row)] = [+(x0 + 0.18 + col * cw).toFixed(4), +(rowY0 - row * ch).toFixed(4)];
  numbers[0] = [+(x0 + 0.18 - cw / 2 - 0.07).toFixed(4), +(rowY0 - ch).toFixed(4)];
  const dozens = [0, 1, 2].map((i) => [+(x0 + 0.18 + (i * 4 + 1.5) * cw).toFixed(4), dozenY]);
  const outside = {};
  ['low', 'even', 'red', 'black', 'odd', 'high'].forEach((k, i) => { outside[k] = [+(x0 + 0.18 + (i * 2 + 0.5) * cw).toFixed(4), evenY]; });
  return { numbers, dozens, outside };
}
const RED_N = new Set([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]);
function rouletteFelt() {
  return feltSvg({ w: RL.w, h: RL.h, W: 2048, H: 1024, colour: '#0c2e1e', draw: (P, s) => {
    const { cw, ch, x0 } = RL;
    const top = RL.rowY0 + ch / 2;
    const rect = (x, y, w, h, fill = 'none', sw = 0.004) => { const [a, b] = P(x - w / 2, y + h / 2); return `<rect x="${a}" y="${b}" width="${w * s}" height="${h * s}" fill="${fill}" stroke="${INK}" stroke-width="${sw * s}"/>`; };
    let out = '';
    for (let col = 0; col < 12; col++) for (let row = 0; row < 3; row++) {
      const n = col * 3 + (3 - row), cx = x0 + 0.18 + col * cw, cy = 0.33 - row * ch;
      out += rect(cx, cy, cw, ch);
      const [a, b] = P(cx, cy);
      out += `<ellipse cx="${a}" cy="${b}" rx="${0.042 * s}" ry="${0.06 * s}" fill="${RED_N.has(n) ? '#9e1a1c' : '#121212'}" opacity="0.92"/>`;
      out += label(P, s, cx, cy, String(n), 0.05, 180, 'bold').replace(`fill="${INK}"`, 'fill="#f1e8d2"');
    }
    const zx = x0 + 0.18 - cw / 2 - 0.07;
    const [za, zb] = P(zx + 0.07, top), [, zd] = P(zx - 0.07, 0.33 - 2 * ch - ch / 2), [ze, zf] = P(zx - 0.07, 0.33 - ch);
    out += `<path d="M ${za} ${zb} L ${ze + 0.0 * s} ${zb} L ${ze - 0.05 * s} ${zf} L ${ze} ${zd} L ${za} ${zd} Z" fill="#11552e" stroke="${INK}" stroke-width="${0.004 * s}"/>`;
    out += label(P, s, zx, 0.33 - ch, '0', 0.07, 180, 'bold').replace(`fill="${INK}"`, 'fill="#f1e8d2"');
    ['1ʳᵉ 12', '2ᵉ 12', '3ᵉ 12'].forEach((t, i) => { const cx = x0 + 0.18 + (i * 4 + 1.5) * cw; out += rect(cx, RL.dozenY, 4 * cw, RL.dozenH) + label(P, s, cx, RL.dozenY, t, 0.04, 180); });
    ['MANQUE', 'PAIR', 'ROUGE', 'NOIR', 'IMPAIR', 'PASSE'].forEach((t, i) => {
      const cx = x0 + 0.18 + (i * 2 + 0.5) * cw;
      out += rect(cx, RL.evenY, 2 * cw, RL.evenH);
      if (t === 'ROUGE' || t === 'NOIR') { const [a, b] = P(cx, RL.evenY); out += `<path d="M ${a - 0.07 * s} ${b} L ${a} ${b - 0.04 * s} L ${a + 0.07 * s} ${b} L ${a} ${b + 0.04 * s} Z" fill="${t === 'ROUGE' ? '#9e1a1c' : '#121212'}" stroke="${INK}" stroke-width="${0.003 * s}"/>`; }
      else out += label(P, s, cx, RL.evenY, t, 0.03, 180);
    });
    out += `<g transform="rotate(180 ${P(0.78, -0.47)[0]} ${P(0.78, -0.47)[1]})">${crest(P, s, 0.78, -0.47, 0.08)}</g>`;
    return out;
  } });
}

// Roulette wheel top (rotor ring + pockets), plan disc radius 0.45 m → 1024²
const WHEEL_ORDER = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26];
function wheelTop() {
  const S = 1024, c = S / 2, k = S / 0.9;
  const seg = (r0, r1, a0, a1, fill) => {
    const p = (r, a) => `${c + r * k * Math.cos(a)} ${c - r * k * Math.sin(a)}`;
    return `<path d="M ${p(r0, a0)} L ${p(r1, a0)} A ${r1 * k} ${r1 * k} 0 0 0 ${p(r1, a1)} L ${p(r0, a1)} A ${r0 * k} ${r0 * k} 0 0 1 ${p(r0, a0)} Z" fill="${fill}"/>`;
  };
  let out = `<rect width="${S}" height="${S}" fill="#3a2414"/><circle cx="${c}" cy="${c}" r="${0.45 * k}" fill="#2a1a10"/>`;
  WHEEL_ORDER.forEach((n, i) => {
    const a0 = (2 * Math.PI * i) / 37, a1 = (2 * Math.PI * (i + 1)) / 37, am = (a0 + a1) / 2;
    const col = n === 0 ? '#12622f' : RED_N.has(n) ? '#a3161d' : '#141210';
    out += seg(0.3, 0.4, a0, a1, col) + seg(0.4, 0.45, a0, a1, col);
    const x = c + 0.425 * k * Math.cos(am), y = c - 0.425 * k * Math.sin(am);
    out += `<text x="${x}" y="${y}" font-family="${SERIF}" font-weight="bold" font-size="${0.03 * k}" fill="#f2e6c8" text-anchor="middle" dominant-baseline="middle" transform="rotate(${90 - (am * 180) / Math.PI} ${x} ${y})">${n}</text>`;
  });
  out += `<circle cx="${c}" cy="${c}" r="${0.4 * k}" fill="none" stroke="#c9a24e" stroke-width="3"/><circle cx="${c}" cy="${c}" r="${0.45 * k - 2}" fill="none" stroke="#c9a24e" stroke-width="4"/>
    <circle cx="${c}" cy="${c}" r="${0.3 * k}" fill="url(#cone)"/>`;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><defs><radialGradient id="cone"><stop offset="0" stop-color="#6a4426"/><stop offset="1" stop-color="#3a2414"/></radialGradient></defs>${out}</svg>`;
  return sharp(Buffer.from(svg)).png();
}

// Slot marquee (emissive back-lit glass) and belly glass pay table
function marquee() {
  const W = 1024, H = 512;
  const rays = Array.from({ length: 24 }, (_, i) => { const a = Math.PI * (i / 23); return `<path d="M ${W / 2} ${H * 0.95} L ${W / 2 + Math.cos(a) * 700} ${H * 0.95 - Math.sin(a) * 700} L ${W / 2 + Math.cos(a + 0.05) * 700} ${H * 0.95 - Math.sin(a + 0.05) * 700} Z" fill="#ffd89a" opacity="${i % 2 ? 0.1 : 0.2}"/>`; }).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}"><defs>
    <radialGradient id="bg" cx="0.5" cy="0.95" r="0.9"><stop offset="0" stop-color="#b3212a"/><stop offset="0.6" stop-color="#5e0b14"/><stop offset="1" stop-color="#2a0409"/></radialGradient>
    <linearGradient id="gold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff1b8"/><stop offset="0.5" stop-color="#e2b547"/><stop offset="1" stop-color="#9a6b18"/></linearGradient></defs>
    <rect width="${W}" height="${H}" fill="url(#bg)"/>${rays}
    <text x="${W / 2}" y="${H * 0.46}" font-family="Didot" font-size="62" letter-spacing="10" fill="url(#gold)" text-anchor="middle">LE GRAND RIVIERA</text>
    <text x="${W / 2}" y="${H * 0.78}" font-family="Georgia" font-weight="bold" font-size="130" letter-spacing="14" fill="url(#gold)" stroke="#5a3a08" stroke-width="3" text-anchor="middle">JACKPOT</text>
    <rect x="10" y="10" width="${W - 20}" height="${H - 20}" fill="none" stroke="url(#gold)" stroke-width="10"/></svg>`;
  return sharp(Buffer.from(svg)).png();
}
function payGlass() {
  const W = 1024, H = 512;
  const rows = [['diamond', 150], ['seven', 80], ['bar', 40], ['bell', 20], ['lemon', 15], ['cherry', 10]];
  const body = rows.map(([k, v], i) => {
    const y = 110 + i * 62;
    return [0, 1, 2].map((j) => symbol(k, 250 + j * 90, y, 52)).join('') +
      `<text x="560" y="${y + 14}" font-family="Didot" font-size="40" fill="#f3e2b0">………</text><text x="820" y="${y + 16}" font-family="Georgia" font-weight="bold" font-size="44" fill="#ffe7a6" text-anchor="end">× ${v}</text>`;
  }).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}"><defs>
    <radialGradient id="cherryG" cx="0.35" cy="0.3" r="0.8"><stop offset="0" stop-color="#ff4a4a"/><stop offset="0.6" stop-color="#b3101a"/><stop offset="1" stop-color="#5a0808"/></radialGradient>
    <radialGradient id="lemonG" cx="0.4" cy="0.35" r="0.8"><stop offset="0" stop-color="#fff38a"/><stop offset="0.7" stop-color="#f2c812"/><stop offset="1" stop-color="#b58d05"/></radialGradient>
    <linearGradient id="goldG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fbe7a1"/><stop offset="0.45" stop-color="#d6a633"/><stop offset="1" stop-color="#7a5510"/></linearGradient>
    <linearGradient id="sevenG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff3b3b"/><stop offset="1" stop-color="#8a0a12"/></linearGradient>
    <linearGradient id="gemG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9fd0ff"/><stop offset="0.5" stop-color="#2f7ad8"/><stop offset="1" stop-color="#0f3b7a"/></linearGradient></defs>
    <rect width="${W}" height="${H}" fill="#1a0d08"/><rect x="14" y="14" width="${W - 28}" height="${H - 28}" fill="none" stroke="#c9a24e" stroke-width="6"/>
    <text x="${W / 2}" y="62" font-family="Didot" font-size="38" letter-spacing="8" fill="#e8c878" text-anchor="middle">TROIS IDENTIQUES PAIENT</text>${body}</svg>`;
  return sharp(Buffer.from(svg)).png();
}

// ------------------------------------------------------------------ write
await mkdir(SRC, { recursive: true });
const blenderOut = {
  T_FeltBlackjack_BaseColor: blackjackFelt(), T_FeltPoker_BaseColor: pokerFelt(), T_FeltBaccarat_BaseColor: baccaratFelt(),
  T_FeltRoulette_BaseColor: rouletteFelt(), T_WheelTop_BaseColor: wheelTop(), T_SlotMarquee_Emissive: marquee(), T_SlotPayGlass_Emissive: payGlass(),
};
for (const [name, svg] of Object.entries(blenderOut)) {
  const img = typeof svg === 'string' ? sharp(Buffer.from(svg)).png() : svg;
  await img.toFile(path.join(SRC, `${name}.png`));
  console.log(`  ✓ ${name}.png`);
}
const runtime = { Card_Atlas: await cardAtlas(), Chip_Atlas: await chipAtlas(), Slot_Reel: await reelStrip() };
/** Layout of each runtime atlas — the presenters (src/tables) read it instead of hard-coding pixel maths. */
const META = {
  Card_Atlas: { size: 2048, cell: [CW, CH], cols: COLS, suits: 'SHDC', ranks: [2, 14], back: 52 },
  Chip_Atlas: { denoms: CHIPS.map((c) => c.v), grid: 2, faceRadius: 250 / 1024, rimInner: 0.235 },
  Slot_Reel: { stops: REEL_STOPS },
};
const tj = path.join(WEB, 'textures.json');
const manifest = JSON.parse(await readFile(tj, 'utf8'));
for (const [name, img] of Object.entries(runtime)) {
  const file = path.join(WEB, `T_${name}_BaseColor.png`);
  await img.toFile(file);
  await sharp(file).toFile(path.join(SRC, `T_${name}_BaseColor.png`));   // Blender uses the same art (chip trays, shoe)
  const buf = await readFile(file);
  manifest.materials[name] = { source: 'generated:make-game-textures', meta: META[name], maps: { BaseColor: { url: `/assets/textures/${path.basename(file)}`, bytes: (await stat(file)).size, hash: createHash('sha256').update(buf).digest('hex').slice(0, 16) } } };
  console.log(`  ✓ ${name} → textures.json`);
}
await writeFile(tj, JSON.stringify(manifest, null, 2));
await writeFile(path.join(SRC, 'layout.json'), JSON.stringify({ BJ, PK, BC, RL, rouletteBoxes: rouletteBoxes(), REEL_STOPS, WHEEL_ORDER, CARD: { cw: CW, ch: CH, cols: COLS, atlas: 2048 } }, null, 2));
