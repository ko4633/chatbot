import { describe, expect, it } from 'vitest';
import { checkEndings } from '../core/endings';
import { createInitialState } from '../core/state';

describe('엔딩 판정', () => {
  it('삼한일통: 당이 철수했고 신라가 한성·사비를 보유하면', () => {
    let state = createInitialState('silla', 1);
    state = {
      ...state,
      flags: { ...state.flags, tangWithdrawn: true },
      regions: {
        ...state.regions,
        hanseong: { ...state.regions.hanseong, owner: 'silla' },
        sabi: { ...state.regions.sabi, owner: 'silla' }
      }
    };
    expect(checkEndings(state).ending).toBe('samhanUnification');
  });

  it('고구려의 천하: 평양·사비·서라벌을 모두 보유하면', () => {
    let state = createInitialState('goguryeo', 1);
    state = {
      ...state,
      regions: {
        ...state.regions,
        sabi: { ...state.regions.sabi, owner: 'goguryeo' },
        seorabeol: { ...state.regions.seorabeol, owner: 'goguryeo' }
      }
    };
    expect(checkEndings(state).ending).toBe('goguryeoUnderHeaven');
  });

  it('당의 주현: 중원이 영토 지역의 60% 이상을 보유하면', () => {
    let state = createInitialState('silla', 1);
    const regions = { ...state.regions };
    let i = 0;
    for (const id of Object.keys(regions)) {
      if (regions[id].garrison === undefined) continue;
      // 외부 지역(요서 등)은 이미 jungwon/wa 소유이므로 건드리지 않아도 되지만, 골고루 넘긴다.
      if (i % 10 !== 0) regions[id] = { ...regions[id], owner: 'jungwon' };
      i++;
    }
    state = { ...state, regions };
    expect(checkEndings(state).ending).toBe('tangProvince');
  });

  it('700년에 도달하면 영토 비율로 승자를 판정한다', () => {
    let state = createInitialState('silla', 1);
    state = { ...state, year: 700 };
    const result = checkEndings(state);
    expect(result.ending).toMatch(/^territorial700:/);
  });

  it('한 번 확정된 엔딩은 바뀌지 않는다', () => {
    let state = createInitialState('silla', 1);
    state = { ...state, ending: 'samhanUnification', year: 700 };
    expect(checkEndings(state).ending).toBe('samhanUnification');
  });
});
