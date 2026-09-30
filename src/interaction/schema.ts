/**
 * The single schema for interaction metadata (§6). In Blender these are custom properties;
 * they arrive as glTF `extras` → `userData`. Code-built zones set the same shape on userData.
 * The asset validator (Phase 2) checks exported extras against `validateExtras`.
 */
import type { GameType } from '../games/shared/types';
export type { GameType };

export interface DoorExtras {
  interactable: true;
  interactionType: 'door';
  interactionPrompt: string;
  /** Zone id behind the door. Omitted for locked/decorative doors. */
  target?: string;
  locked?: boolean;
}

export interface CasinoTableExtras {
  interactable: true;
  interactionType: 'casinoTable';
  interactionPrompt: string;
  gameType: GameType;
  tableId: string;
}

export type InteractionExtras = DoorExtras | CasinoTableExtras;
export type InteractionType = InteractionExtras['interactionType'];

const GAME_TYPES: readonly GameType[] = ['poker', 'blackjack', 'baccarat', 'roulette', 'slots'];

/** Returns a list of problems (empty = valid). Shared by the runtime and the asset validator. */
export function validateExtras(x: unknown): string[] {
  const e = x as Record<string, unknown>;
  const errs: string[] = [];
  if (!e || e.interactable !== true) return ['interactable must be true'];
  if (typeof e.interactionPrompt !== 'string' || !e.interactionPrompt) errs.push('interactionPrompt required');
  switch (e.interactionType) {
    case 'door':
      if (e.target !== undefined && typeof e.target !== 'string') errs.push('door.target must be a zone id');
      if (e.target === undefined && e.locked !== true) errs.push('door needs a target or locked: true');
      break;
    case 'casinoTable':
      if (!GAME_TYPES.includes(e.gameType as GameType)) errs.push(`casinoTable.gameType must be one of ${GAME_TYPES.join(', ')}`);
      if (typeof e.tableId !== 'string' || !e.tableId) errs.push('casinoTable.tableId required');
      break;
    default:
      errs.push(`unknown interactionType "${String(e.interactionType)}"`);
  }
  return errs;
}
