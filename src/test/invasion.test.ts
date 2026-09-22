import { describe, expect, it } from 'vitest';
import { balanceData } from '../core/balance';
import { createInvasion, processInvasions } from '../core/invasion';
import { createInitialState } from '../core/state';
import type { GameState } from '../core/types';

describe('외부 침공 모델 (요서·산동해로 진군, 보급 소모, 철수/함락)', () => {
  it('요서에서 목표까지 인접 그래프를 따라 경로를 찾는다', () => {
    const state = createInitialState('silla', 1);
    const invasion = createInvasion(state, { faction: 'jungwon', troops: 300000, route: 'yoseo', target: 'yodongseong' });
    expect(invasion).not.toBeNull();
    expect(invasion?.path[0]).toBe('yoseo');
    expect(invasion?.path[invasion.path.length - 1]).toBe('yodongseong');
  });

  it('여러 턴 진군하며 보급 임계 턴을 넘기면 병력과 보급률이 줄어든다', () => {
    let state = createInitialState('silla', 1);
    // 목표를 멀리 잡아(요서→서라벌) 소모 임계 턴 전에 도착해 버리지 않게 한다.
    const invasion = createInvasion(state, { faction: 'jungwon', troops: 100000, route: 'yoseo', target: 'seorabeol' });
    expect(invasion).not.toBeNull();
    expect((invasion?.path.length ?? 0) - 1).toBeGreaterThan(balanceData.invasion.supplyTurnsBeforeAttrition);
    if (!invasion) return;
    state = { ...state, invasions: [invasion] };

    for (let i = 0; i < balanceData.invasion.supplyTurnsBeforeAttrition; i++) {
      state = processInvasions(state);
    }
    const beforeAttrition = state.invasions[0]?.troops ?? 0;
    expect(beforeAttrition).toBe(100000); // 아직 소모 임계 턴 전.

    state = processInvasions(state);
    const afterAttrition = state.invasions.find((inv) => inv.faction === 'jungwon');
    if (afterAttrition) {
      expect(afterAttrition.troops).toBeLessThan(beforeAttrition);
      expect(afterAttrition.supplyRatio).toBeLessThan(1);
    }
  });

  it('겨울에 보급률이 0.5 미만이면 철수하고 결과가 withdrawn으로 기록된다', () => {
    let state = createInitialState('silla', 1);
    const invasion = createInvasion(state, { faction: 'jungwon', troops: 100000, route: 'yoseo', target: 'pyeongyang' });
    expect(invasion).not.toBeNull();
    if (!invasion) return;
    state = { ...state, season: 'winter', invasions: [{ ...invasion, supplyRatio: 0.3 }] };
    state = processInvasions(state);
    expect(state.invasions).toHaveLength(0);
    expect(state.invasionOutcomes.jungwon.result).toBe('withdrawn');
  });

  it('목표에 도착하면 전투가 벌어지고, 공격측이 압도적이면 지역을 점령한다', () => {
    let state: GameState = createInitialState('silla', 1);
    // 안시성을 극단적으로 약화시켜 도착 즉시 함락되도록 한다.
    state = { ...state, regions: { ...state.regions, ansiseong: { ...state.regions.ansiseong, garrison: 10, defense: 0 } } };
    const invasion = createInvasion(state, { faction: 'jungwon', troops: 50000, route: 'yoseo', target: 'ansiseong' });
    expect(invasion).not.toBeNull();
    if (!invasion) return;
    // 이미 목표 바로 앞 칸까지 진군한 상태로 만들어 다음 한 턴에 도착하게 한다.
    state = { ...state, invasions: [{ ...invasion, stepIndex: invasion.path.length - 2 }] };
    state = processInvasions(state);
    expect(state.regions.ansiseong.owner).toBe('jungwon');
    expect(state.invasionOutcomes.jungwon.result).toBe('victorious');
    expect(state.invasions).toHaveLength(0);
  });
});
