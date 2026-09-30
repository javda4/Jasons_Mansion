/** A tiny time-based animation scheduler driven by a zone's animate hook (seconds). */
export type Ease = (k: number) => number;
export const easeInOut: Ease = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
export const easeOut: Ease = (k) => 1 - Math.pow(1 - k, 3);
export const linear: Ease = (k) => k;

interface Job { start: number; dur: number; fn: (k: number) => void; ease: Ease; done: () => void; begun: boolean; onStart?: () => void }

export class Tweens {
  private jobs: Job[] = [];
  private now = 0;

  /** Run `fn(k)` for k ∈ [0, 1] over `dur` seconds after `delay`; resolves when finished. */
  add(delay: number, dur: number, fn: (k: number) => void, ease: Ease = easeInOut, onStart?: () => void): Promise<void> {
    return new Promise((done) => this.jobs.push({ start: this.now + delay, dur: Math.max(1e-3, dur), fn, ease, done, begun: false, onStart }));
  }

  /** Resolve after `delay` seconds of animation time. */
  wait(delay: number): Promise<void> {
    return this.add(delay, 1e-3, () => {});
  }

  get busy(): boolean { return this.jobs.length > 0; }

  update(time: number): void {
    this.now = time;
    const keep: Job[] = [];
    for (const j of this.jobs) {
      if (time < j.start) { keep.push(j); continue; }
      if (!j.begun) { j.begun = true; j.onStart?.(); }
      const k = Math.min(1, (time - j.start) / j.dur);
      j.fn(j.ease(k));
      if (k < 1) keep.push(j); else j.done();
    }
    this.jobs = keep;
  }

  /** Finish everything immediately (e.g. the zone unloads or the player leaves the table). */
  flush(): void {
    for (const j of this.jobs) { if (!j.begun) j.onStart?.(); j.fn(1); j.done(); }
    this.jobs = [];
  }
}
