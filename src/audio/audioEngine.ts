import type { PerspectiveCamera } from 'three/webgpu';
import { Vector3 } from 'three/webgpu';
import type { System } from '../core/loop';
import type { Vec3 } from '../physics/types';
import { synthesizeAll, type SoundId } from './synth';

/**
 * A positional sound source (the `AUDIO_` role, §6). Code-built zones declare these in their
 * builder; Blender zones export `AUDIO_<Zone>_<Name>` empties with extras
 * `{ sound, gain, mode, intervalMin, intervalMax }`.
 */
export interface SoundEmitterDef {
  id: string;
  sound: SoundId;
  position: Vec3;
  gain: number;
  /** loop = continuous (fire); random = one-shots at random intervals (chips, roulette ball). */
  mode: 'loop' | 'random';
  interval?: [number, number];
  /** Distance at which the emitter is inaudible and skipped. */
  range?: number;
}

/** Per-zone ambience beds: layers of looping sounds crossfaded as the player moves (§8 Audio). */
const BEDS: Record<string, Partial<Record<SoundId, number>>> = {
  // a house at night: room air, and guests' voices drifting from the reception rooms
  stair_hall: { roomTone: 0.26, murmur: 0.04 },
  grand_salon: { roomTone: 0.22, murmur: 0.12 },   // guests at the baccarat table and round the fire
  library: { roomTone: 0.2, murmur: 0.06 },        // a hushed room: the poker table's murmur, the fire
  ballroom: { roomTone: 0.24, murmur: 0.16 },      // the roulette crowd under the chandeliers
};
const BED_SOUNDS: SoundId[] = ['roomTone', 'murmur', 'slotHall'];
const CROSSFADE = 1.6; // seconds

interface ActiveEmitter {
  def: SoundEmitterDef;
  panner: PannerNode;
  source?: AudioBufferSourceNode;
  nextAt: number;
}

export class AudioEngine implements System {
  readonly name = 'audio';
  private ctx: AudioContext | null = null;
  private master!: GainNode;
  private buffers = new Map<SoundId, AudioBuffer>();
  private beds = new Map<SoundId, GainNode>();
  private emitters = new Map<string, ActiveEmitter>();
  private volume = 0.8;
  private zone = '';
  private muted = false;
  private sinceSync = 0;
  private readonly fwd = new Vector3();

  constructor(
    private readonly camera: PerspectiveCamera,
    /** Emitters of the zones currently visible, in world space. */
    private readonly emitterSource: () => SoundEmitterDef[],
  ) {}

  get started(): boolean { return this.ctx !== null; }

  /** Must run inside a user gesture (browser autoplay policy). */
  start(): void {
    if (this.ctx) { void this.ctx.resume(); return; }
    const ctx = new AudioContext({ latencyHint: 'interactive' });
    this.ctx = ctx;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -14;
    comp.ratio.value = 3;
    this.master = ctx.createGain();
    this.master.gain.value = this.muted ? 0 : this.volume;
    this.master.connect(comp).connect(ctx.destination);
    this.buffers = synthesizeAll(ctx);
    for (const id of BED_SOUNDS) {
      const g = ctx.createGain();
      g.gain.value = 0;
      g.connect(this.master);
      const src = ctx.createBufferSource();
      src.buffer = this.buffers.get(id)!;
      src.loop = true;
      src.connect(g);
      src.start(ctx.currentTime + Math.random() * 0.2);
      this.beds.set(id, g);
    }
    if (this.zone) this.setZone(this.zone);
  }

  setVolume(v: number): void {
    this.volume = v;
    this.applyMaster();
  }

  toggleMute(): boolean {
    this.muted = !this.muted;
    this.applyMaster();
    return this.muted;
  }

  private applyMaster(): void {
    if (this.ctx) this.master.gain.setTargetAtTime(this.muted ? 0 : this.volume, this.ctx.currentTime, 0.1);
  }

  /** Crossfade ambience beds to the zone the player is in. */
  setZone(zoneId: string): void {
    this.zone = zoneId;
    if (!this.ctx) return;
    const bed = BEDS[zoneId] ?? { roomTone: 0.2 };
    for (const [id, g] of this.beds) g.gain.setTargetAtTime(bed[id] ?? 0, this.ctx.currentTime, CROSSFADE / 3);
  }

  /** Fire-and-forget sound, optionally positioned in the world. */
  play(sound: SoundId, position?: Vec3, gain = 1, rate = 1): void {
    const ctx = this.ctx;
    if (!ctx) return;
    const src = ctx.createBufferSource();
    src.buffer = this.buffers.get(sound)!;
    src.playbackRate.value = rate * (0.94 + Math.random() * 0.12);
    const g = ctx.createGain();
    g.gain.value = gain;
    src.connect(g);
    if (position) g.connect(this.panner(position)).connect(this.master);
    else g.connect(this.master);
    src.start();
  }

  private panner(p: Vec3, range = 18): PannerNode {
    const pn = this.ctx!.createPanner();
    pn.panningModel = 'HRTF';
    pn.distanceModel = 'inverse';
    pn.refDistance = 1.5;
    pn.maxDistance = range;
    pn.rolloffFactor = 1.2;
    pn.positionX.value = p.x; pn.positionY.value = p.y; pn.positionZ.value = p.z;
    return pn;
  }

  update(dt: number, time: number): void {
    const ctx = this.ctx;
    if (!ctx) return;
    // listener follows the camera
    const l = ctx.listener;
    const c = this.camera;
    this.camera.getWorldDirection(this.fwd);
    const t = ctx.currentTime;
    if (l.positionX) {
      l.positionX.setTargetAtTime(c.position.x, t, 0.03);
      l.positionY.setTargetAtTime(c.position.y, t, 0.03);
      l.positionZ.setTargetAtTime(c.position.z, t, 0.03);
      l.forwardX.setTargetAtTime(this.fwd.x, t, 0.03);
      l.forwardY.setTargetAtTime(this.fwd.y, t, 0.03);
      l.forwardZ.setTargetAtTime(this.fwd.z, t, 0.03);
    }

    // sync emitters with visible zones twice a second
    this.sinceSync += dt;
    if (this.sinceSync > 0.5) {
      this.sinceSync = 0;
      this.syncEmitters(time);
    }
    // random one-shots
    for (const e of this.emitters.values()) {
      if (e.def.mode !== 'random' || time < e.nextAt) continue;
      const [a, b] = e.def.interval ?? [6, 14];
      e.nextAt = time + a + Math.random() * (b - a);
      const src = ctx.createBufferSource();
      src.buffer = this.buffers.get(e.def.sound)!;
      src.playbackRate.value = 0.92 + Math.random() * 0.16;
      const g = ctx.createGain();
      g.gain.value = e.def.gain * (0.7 + Math.random() * 0.3);
      src.connect(g).connect(e.panner);
      src.start();
    }
  }

  private syncEmitters(time: number): void {
    const ctx = this.ctx!;
    const wanted = new Map(this.emitterSource().map((d) => [d.id, d]));
    for (const [id, e] of this.emitters) {
      if (wanted.has(id)) continue;
      e.source?.stop();
      e.panner.disconnect();
      this.emitters.delete(id);
    }
    for (const [id, def] of wanted) {
      if (this.emitters.has(id)) continue;
      const panner = this.panner(def.position, def.range ?? 18);
      panner.connect(this.master);
      const e: ActiveEmitter = { def, panner, nextAt: time + Math.random() * (def.interval?.[0] ?? 4) };
      if (def.mode === 'loop') {
        const src = ctx.createBufferSource();
        src.buffer = this.buffers.get(def.sound)!;
        src.loop = true;
        const g = ctx.createGain();
        g.gain.value = def.gain;
        src.connect(g).connect(panner);
        src.start(ctx.currentTime, Math.random() * src.buffer.duration);
        e.source = src;
      }
      this.emitters.set(id, e);
    }
  }
}
