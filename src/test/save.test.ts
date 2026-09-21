import { describe, expect, it } from 'vitest';
import { deserializeState, serializeState } from '../core/save';
import { advanceTurn, createInitialState } from '../core/state';

describe('save/load', () => {
  it('round-trips state through serialize/deserialize', () => {
    let state = createInitialState('baekje', 7);
    state = advanceTurn(state);
    state = advanceTurn(state);
    const raw = serializeState(state, 1710000000000);
    const restored = deserializeState(raw);
    expect(restored).toEqual(state);
  });

  it('rejects garbage input', () => {
    expect(deserializeState('not json')).toBeNull();
    expect(deserializeState('{}')).toBeNull();
  });
});
