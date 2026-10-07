import { describe, expect, it } from 'vitest';
import { gameOfTable, validateExtras } from './schema';

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
    expect(validateExtras({ interactable: true, interactionType: 'casinoTable', interactionPrompt: 'Play', gameType: 'blackjack', tableId: 'blackjack_01' })).toEqual([]);
    expect(validateExtras({ interactable: true, interactionType: 'casinoTable', interactionPrompt: 'Play', gameType: 'craps', tableId: 'craps_01' })[0]).toMatch(/gameType/);
  });
  it('requires a tableId of the form <gameType>_<NN> (presenters are picked per table)', () => {
    expect(validateExtras({ interactable: true, interactionType: 'casinoTable', interactionPrompt: 'Play', gameType: 'blackjack', tableId: 'bj_01' })[0]).toMatch(/blackjack_<NN>/);
    expect(gameOfTable('roulette_02')).toBe('roulette');
    expect(gameOfTable('slots_17')).toBe('slots');
    expect(gameOfTable('ballroom_01')).toBeNull();
  });
  it('rejects unknown types', () => {
    expect(validateExtras({ interactable: true, interactionType: 'teleport', interactionPrompt: 'x' })[0]).toMatch(/unknown/);
  });
});
