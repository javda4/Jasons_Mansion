import type { ZoneInstance } from '../world/roomBuilder';
import { attachFire } from './fire';

/**
 * Runtime-simulated effects authored as `FX_` markers (CLAUDE.md §6): things glTF can't carry, like a
 * living fire. Each marker's `extras.effect` picks the simulator; its size extras shape it. Adding an
 * effect = a simulator here + the name in conventions.py / validate-assets.mjs (FX_EFFECTS).
 */
const EFFECTS: Record<string, (inst: ZoneInstance, def: NonNullable<ZoneInstance['effects']>[number]) => void> = {
  fire: attachFire,
};

export function attachEffects(inst: ZoneInstance): void {
  for (const def of inst.effects ?? []) {
    const make = EFFECTS[def.effect];
    if (make) make(inst, def);
    else console.warn(`[fx] ${inst.id}: unknown effect "${def.effect}" on ${def.node.name}`);
  }
}
