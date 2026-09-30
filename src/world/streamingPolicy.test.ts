import { describe, expect, it } from 'vitest';
import { decide, hopsFrom, type ZoneGraph } from './streamingPolicy';

const graph: ZoneGraph = {
  lobby: ['hall_west', 'hall_east'],
  hall_west: ['lobby', 'poker', 'blackjack', 'baccarat'],
  hall_east: ['lobby', 'roulette', 'slots'],
  poker: ['hall_west'], blackjack: ['hall_west'], baccarat: ['hall_west'],
  roulette: ['hall_east'], slots: ['hall_east'],
};

describe('streaming policy', () => {
  it('computes portal hops', () => {
    const h = hopsFrom(graph, 'poker');
    expect(h.get('hall_west')).toBe(1);
    expect(h.get('lobby')).toBe(2);
    expect(h.get('slots')).toBe(4);
  });

  it('loads neighbours before two-hop zones, and two-hop only when idle', () => {
    const busy = decide(graph, 'lobby', new Set(['lobby']), new Map(), 0, { idle: false, unloadAfter: 20 });
    expect(busy.load.map((l) => l.id).sort()).toEqual(['hall_east', 'hall_west']);
    const idle = decide(graph, 'lobby', new Set(['lobby', 'hall_west', 'hall_east']), new Map(), 0, { idle: true, unloadAfter: 20 });
    expect(idle.load.every((l) => l.priority === 3)).toBe(true);
    expect(idle.load).toHaveLength(5);
  });

  it('unloads far zones only after the hysteresis delay', () => {
    const since = new Map<string, number>();
    const loaded = new Set(['poker', 'hall_west', 'lobby', 'hall_east', 'slots']);
    expect(decide(graph, 'poker', loaded, since, 0, { idle: true, unloadAfter: 20 }).unload).toEqual([]);
    expect(decide(graph, 'poker', loaded, since, 10, { idle: true, unloadAfter: 20 }).unload).toEqual([]);
    expect(decide(graph, 'poker', loaded, since, 21, { idle: true, unloadAfter: 20 }).unload.sort()).toEqual(['hall_east', 'slots']);
  });

  it('cancels a pending unload when the player comes back in range', () => {
    const since = new Map<string, number>();
    const loaded = new Set(['hall_east', 'lobby', 'poker', 'hall_west']);
    decide(graph, 'poker', loaded, since, 0, { idle: true, unloadAfter: 20 });
    expect(since.has('hall_east')).toBe(true);
    decide(graph, 'lobby', loaded, since, 5, { idle: true, unloadAfter: 20 });
    expect(since.has('hall_east')).toBe(false);
  });
});
