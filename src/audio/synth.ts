/**
 * Procedural sound library. There are no recorded assets yet, so every sound is synthesised once
 * into an AudioBuffer at start-up (a few hundred ms of CPU). Each recipe can later be replaced by
 * a streamed recording (public/assets/audio/…) behind the same `SoundId` without touching callers.
 */
export type SoundId =
  | 'roomTone' | 'murmur' | 'fireCrackle' | 'slotHall'           // loops
  | 'chips' | 'cardFlick' | 'rouletteBall' | 'slotChime' | 'slotWin'
  | 'doorOpen' | 'doorClose' | 'crystal' | 'uiClick';           // one-shots

type Gen = (ctx: BaseAudioContext) => AudioBuffer;

function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function buffer(ctx: BaseAudioContext, seconds: number, channels = 1): AudioBuffer {
  return ctx.createBuffer(channels, Math.round(seconds * ctx.sampleRate), ctx.sampleRate);
}

/** One-pole low-pass in place. */
function lowpass(d: Float32Array, sr: number, hz: number): void {
  const a = Math.exp((-2 * Math.PI * hz) / sr);
  let y = 0;
  for (let i = 0; i < d.length; i++) d[i] = y = (1 - a) * d[i] + a * y;
}
function highpass(d: Float32Array, sr: number, hz: number): void {
  const a = Math.exp((-2 * Math.PI * hz) / sr);
  let y = 0, xPrev = 0;
  for (let i = 0; i < d.length; i++) { const x = d[i]; y = a * (y + x - xPrev); xPrev = x; d[i] = y; }
}
/** Two-pole resonant band-pass (RBJ) in place. */
function bandpass(d: Float32Array, sr: number, hz: number, q: number): void {
  const w = (2 * Math.PI * hz) / sr, alpha = Math.sin(w) / (2 * q), cos = Math.cos(w);
  const b0 = alpha, b2 = -alpha, a0 = 1 + alpha, a1 = -2 * cos, a2 = 1 - alpha;
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  for (let i = 0; i < d.length; i++) {
    const x = d[i];
    const y = (b0 * x + b2 * x2 - a1 * y1 - a2 * y2) / a0;
    x2 = x1; x1 = x; y2 = y1; y1 = y; d[i] = y;
  }
}
function normalise(d: Float32Array, peak: number): void {
  let m = 0;
  for (const v of d) m = Math.max(m, Math.abs(v));
  if (m > 0) for (let i = 0; i < d.length; i++) d[i] *= peak / m;
}
/** Crossfade the tail into the head so a buffer loops without a click. */
function makeLoopable(d: Float32Array, sr: number, fade = 0.5): void {
  const n = Math.round(fade * sr);
  for (let i = 0; i < n; i++) {
    const t = i / n;
    d[i] = d[i] * t + d[d.length - n + i] * (1 - t);
  }
}

const GENERATORS: Record<SoundId, Gen> = {
  // warm, low room air — the "size" of a big interior
  roomTone(ctx) {
    const b = buffer(ctx, 8), d = b.getChannelData(0), r = rng(1);
    for (let i = 0; i < d.length; i++) d[i] = r() * 2 - 1;
    lowpass(d, ctx.sampleRate, 220); lowpass(d, ctx.sampleRate, 400);
    makeLoopable(d, ctx.sampleRate); normalise(d, 0.5);
    return b;
  },
  // distant conversation: formant-filtered noise "voices" with syllable-rate envelopes
  murmur(ctx) {
    const sr = ctx.sampleRate, b = buffer(ctx, 12), d = b.getChannelData(0), r = rng(2);
    const voice = new Float32Array(d.length);
    for (let v = 0; v < 9; v++) {
      for (let i = 0; i < voice.length; i++) voice[i] = r() * 2 - 1;
      bandpass(voice, sr, 350 + r() * 500, 3);
      bandpass(voice, sr, 900 + r() * 1200, 2);
      let env = 0, target = 0, next = 0;
      for (let i = 0; i < voice.length; i++) {
        if (i >= next) { target = r() < 0.6 ? 0.4 + r() * 0.6 : 0; next = i + Math.round(sr * (0.08 + r() * 0.22)); }
        env += (target - env) * 0.0015;
        d[i] += voice[i] * env;
      }
    }
    lowpass(d, sr, 2200);
    makeLoopable(d, sr, 1); normalise(d, 0.6);
    return b;
  },
  // wood fire: random crackles over a soft rumble
  fireCrackle(ctx) {
    const sr = ctx.sampleRate, b = buffer(ctx, 10), d = b.getChannelData(0), r = rng(3);
    for (let i = 0; i < d.length; i++) d[i] = (r() * 2 - 1) * 0.15;
    lowpass(d, sr, 300);
    for (let k = 0; k < 260; k++) {
      const at = Math.floor(r() * (d.length - sr * 0.05)), len = Math.floor(sr * (0.002 + r() * 0.02)), amp = 0.3 + r() * 0.9;
      for (let i = 0; i < len; i++) d[at + i] += (r() * 2 - 1) * amp * Math.exp(-i / (len * 0.25));
    }
    highpass(d, sr, 60);
    makeLoopable(d, sr); normalise(d, 0.7);
    return b;
  },
  // slot hall bed: soft detuned electronic chimes far away
  slotHall(ctx) {
    const sr = ctx.sampleRate, b = buffer(ctx, 9), d = b.getChannelData(0), r = rng(4);
    const notes = [523.25, 659.25, 783.99, 1046.5, 880, 698.46];
    for (let k = 0; k < 40; k++) {
      const at = Math.floor(r() * (d.length - sr)), f = notes[Math.floor(r() * notes.length)] * (r() < 0.5 ? 1 : 2);
      for (let i = 0; i < sr * 0.6; i++) d[at + i] += Math.sin((2 * Math.PI * f * i) / sr) * Math.exp(-i / (sr * 0.12)) * 0.25;
    }
    lowpass(d, sr, 3000);
    makeLoopable(d, sr); normalise(d, 0.5);
    return b;
  },
  chips(ctx) { // a small stack of clay chips set down
    const sr = ctx.sampleRate, b = buffer(ctx, 0.35), d = b.getChannelData(0), r = rng(5);
    for (let k = 0; k < 5; k++) {
      const at = Math.floor(sr * (0.02 + k * 0.035 + r() * 0.01));
      for (let i = 0; i < sr * 0.03 && at + i < d.length; i++) d[at + i] += (r() * 2 - 1) * Math.exp(-i / (sr * 0.004));
    }
    bandpass(d, sr, 3800, 1.4); normalise(d, 0.8);
    return b;
  },
  cardFlick(ctx) {
    const sr = ctx.sampleRate, b = buffer(ctx, 0.12), d = b.getChannelData(0), r = rng(6);
    for (let i = 0; i < d.length; i++) d[i] = (r() * 2 - 1) * Math.exp(-i / (sr * 0.02));
    highpass(d, sr, 1800); normalise(d, 0.6);
    return b;
  },
  rouletteBall(ctx) { // ball skipping around the rotor, slowing, then dropping into a pocket
    const sr = ctx.sampleRate, b = buffer(ctx, 4.5), d = b.getChannelData(0), r = rng(7);
    let t = 0.05, gap = 0.06;
    while (t < 4.1) {
      const at = Math.floor(t * sr);
      for (let i = 0; i < sr * 0.012 && at + i < d.length; i++) d[at + i] += (r() * 2 - 1) * Math.exp(-i / (sr * 0.002)) * (0.4 + 0.6 * Math.min(1, t / 3));
      t += gap; gap *= 1.045 + r() * 0.03;
    }
    for (let i = 0; i < d.length; i++) d[i] += Math.sin(i * 0.002) * 0.02 * Math.max(0, 1 - i / (sr * 3)); // rotor rumble
    bandpass(d, sr, 2600, 1.2); normalise(d, 0.7);
    return b;
  },
  slotChime(ctx) {
    const sr = ctx.sampleRate, b = buffer(ctx, 0.5), d = b.getChannelData(0);
    [1046.5, 1318.5].forEach((f, k) => {
      const at = Math.floor(k * sr * 0.08);
      for (let i = 0; at + i < d.length; i++) d[at + i] += Math.sin((2 * Math.PI * f * i) / sr) * Math.exp(-i / (sr * 0.1));
    });
    normalise(d, 0.5);
    return b;
  },
  slotWin(ctx) {
    const sr = ctx.sampleRate, b = buffer(ctx, 1.4), d = b.getChannelData(0);
    [523.25, 659.25, 783.99, 1046.5, 1318.5, 1568].forEach((f, k) => {
      const at = Math.floor(k * sr * 0.1);
      for (let i = 0; at + i < d.length; i++) d[at + i] += (Math.sin((2 * Math.PI * f * i) / sr) + 0.3 * Math.sin((4 * Math.PI * f * i) / sr)) * Math.exp(-i / (sr * 0.25));
    });
    normalise(d, 0.6);
    return b;
  },
  doorOpen(ctx) { // heavy latch click and a low wooden groan
    const sr = ctx.sampleRate, b = buffer(ctx, 1.3), d = b.getChannelData(0), r = rng(8);
    for (let i = 0; i < sr * 0.02; i++) d[i] += (r() * 2 - 1) * Math.exp(-i / (sr * 0.003));
    const groan = new Float32Array(d.length);
    for (let i = 0; i < groan.length; i++) groan[i] = r() * 2 - 1;
    bandpass(groan, sr, 180, 6);
    for (let i = 0; i < d.length; i++) {
      const t = i / sr;
      d[i] += groan[i] * 0.5 * Math.sin(Math.min(1, t / 1.2) * Math.PI) * (t > 0.1 ? 1 : 0);
    }
    normalise(d, 0.6);
    return b;
  },
  doorClose(ctx) { // soft thud as the leaves meet
    const sr = ctx.sampleRate, b = buffer(ctx, 0.6), d = b.getChannelData(0), r = rng(9);
    for (let i = 0; i < d.length; i++) d[i] = ((r() * 2 - 1) * 0.3 + Math.sin(i * 0.012)) * Math.exp(-i / (sr * 0.07));
    lowpass(d, sr, 250); normalise(d, 0.7);
    return b;
  },
  crystal(ctx) { // a chandelier drop stirred by the air
    const sr = ctx.sampleRate, b = buffer(ctx, 1.2), d = b.getChannelData(0), r = rng(10);
    for (let k = 0; k < 3; k++) {
      const f = 2800 + r() * 2400, at = Math.floor(k * sr * 0.05);
      for (let i = 0; at + i < d.length; i++) d[at + i] += Math.sin((2 * Math.PI * f * i) / sr) * Math.exp(-i / (sr * 0.25)) * 0.4;
    }
    normalise(d, 0.35);
    return b;
  },
  uiClick(ctx) {
    const sr = ctx.sampleRate, b = buffer(ctx, 0.05), d = b.getChannelData(0), r = rng(11);
    for (let i = 0; i < d.length; i++) d[i] = (r() * 2 - 1) * Math.exp(-i / (sr * 0.004));
    bandpass(d, sr, 2400, 2); normalise(d, 0.3);
    return b;
  },
};

export function synthesizeAll(ctx: BaseAudioContext): Map<SoundId, AudioBuffer> {
  const out = new Map<SoundId, AudioBuffer>();
  for (const [id, gen] of Object.entries(GENERATORS) as [SoundId, Gen][]) out.set(id, gen(ctx));
  return out;
}
