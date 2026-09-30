/**
 * Pure streaming policy (§8 Zone streaming) — no three.js, unit-tested.
 * Priority 1 = current zone, 2 = one portal away, 3 = two away (only when idle), beyond = unload.
 * Unloading uses hysteresis: a zone must be out of range for `unloadAfter` seconds.
 */
export interface ZoneGraph {
  [id: string]: readonly string[];
}

export function hopsFrom(graph: ZoneGraph, start: string): Map<string, number> {
  const hops = new Map<string, number>([[start, 0]]);
  const queue = [start];
  while (queue.length) {
    const id = queue.shift()!;
    for (const n of graph[id] ?? []) {
      if (!hops.has(n)) {
        hops.set(n, hops.get(id)! + 1);
        queue.push(n);
      }
    }
  }
  return hops;
}

export interface StreamingDecision {
  /** Zones to load, highest priority first (priority 1 first). */
  load: { id: string; priority: number }[];
  /** Zones to unload now. */
  unload: string[];
}

export function decide(
  graph: ZoneGraph,
  current: string,
  loaded: ReadonlySet<string>,
  outOfRangeSince: Map<string, number>,
  now: number,
  opts: { idle: boolean; unloadAfter: number; maxHops?: number; pinned?: ReadonlySet<string> },
): StreamingDecision {
  const hops = hopsFrom(graph, current);
  const load: { id: string; priority: number }[] = [];
  const unload: string[] = [];
  const maxHops = opts.maxHops ?? 2;

  for (const id of Object.keys(graph)) {
    const h = hops.get(id) ?? Infinity;
    const inRange = h <= maxHops || opts.pinned?.has(id);
    if (inRange) {
      outOfRangeSince.delete(id);
      if (!loaded.has(id)) {
        const priority = Math.min(h, 2) + 1;
        if (priority < 3 || opts.idle) load.push({ id, priority });
      }
    } else if (loaded.has(id)) {
      const since = outOfRangeSince.get(id);
      if (since === undefined) outOfRangeSince.set(id, now);
      else if (now - since >= opts.unloadAfter) unload.push(id);
    }
  }
  load.sort((a, b) => a.priority - b.priority);
  return { load, unload };
}
