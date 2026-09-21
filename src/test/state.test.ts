import { describe, expect, it } from 'vitest';
import { advanceTurn, createInitialState } from '../core/state';

describe('turn/season progression', () => {
  it('starts at 551년 봄 with historical ownership', () => {
    const state = createInitialState('silla', 1);
    expect(state.year).toBe(551);
    expect(state.season).toBe('spring');
    expect(state.regions.pyeongyang.owner).toBe('goguryeo');
    expect(state.regions.hanseong.owner).toBe('baekje');
    expect(state.regions.seorabeol.owner).toBe('silla');
  });

  it('advances season within the same year for spring->summer->autumn->winter', () => {
    let state = createInitialState('silla', 1);
    state = advanceTurn(state);
    expect(state.season).toBe('summer');
    expect(state.year).toBe(551);
    state = advanceTurn(state);
    expect(state.season).toBe('autumn');
    expect(state.year).toBe(551);
    state = advanceTurn(state);
    expect(state.season).toBe('winter');
    expect(state.year).toBe(551);
  });

  it('rolls over to the next year in spring after winter', () => {
    let state = createInitialState('silla', 1);
    for (let i = 0; i < 4; i++) state = advanceTurn(state);
    expect(state.season).toBe('spring');
    expect(state.year).toBe(552);
  });

  it('is pure and deterministic: same input produces same output', () => {
    const state = createInitialState('silla', 42);
    const a = advanceTurn(state);
    const b = advanceTurn(state);
    expect(a).toEqual(b);
    expect(state.turnNumber).toBe(0);
  });
});
