import { describe, expect, it } from 'vitest';
import { validateExtras } from './schema';

describe('validateExtras', () => {
  it('accepts a door with a target', () => {
    expect(validateExtras({ interactable: true, interactionType: 'door', interactionPrompt: 'Enter Poker Room', target: 'poker' })).toEqual([]);
  });
  it('accepts a locked door without a target', () => {
    expect(validateExtras({ interactable: true, interactionType: 'door', interactionPrompt: 'Salon Privé', locked: true })).toEqual([]);
  });
  it('rejects a door with neither target nor lock', () => {
    expect(validateExtras({ interactable: true, interactionType: 'door', interactionPrompt: 'x' })).toHaveLength(1);
  });
  it('validates casino tables', () => {
    expect(validateExtras({ interactable: true, interactionType: 'casinoTable', interactionPrompt: 'Play', gameType: 'blackjack', tableId: 'bj_01' })).toEqual([]);
    expect(validateExtras({ interactable: true, interactionType: 'casinoTable', interactionPrompt: 'Play', gameType: 'craps', tableId: 'x' })).toHaveLength(1);
  });
  it('rejects unknown types', () => {
    expect(validateExtras({ interactable: true, interactionType: 'teleport', interactionPrompt: 'x' })[0]).toMatch(/unknown/);
  });
});
