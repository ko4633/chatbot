import { describe, expect, it } from 'vitest';
import { balanceData } from '../core/balance';
import { conscriptAction, domesticAction, fortifyAction, marchAction } from '../core/actions';
import { createInitialState } from '../core/state';
import { advanceTurn } from '../core/state';
import type { GameState } from '../core/types';

describe('conscriptAction (징병: 지역 pop등급×1000명, 봄·여름만)', () => {
  it('recruits pop grade × 1000 troops and spends one action point', () => {
    const state = createInitialState('silla', 1);
    const region = state.regions.seorabeol;
    const result = conscriptAction(state, 'silla', 'seorabeol');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.state.regions.seorabeol.garrison).toBe(region.garrison + region.pop * balanceData.turn.conscriptionPopMultiplier);
    expect(result.state.factions.silla.actionPoints).toBe(state.factions.silla.actionPoints - 1);
  });

  it('refuses conscription outside spring/summer', () => {
    let state = createInitialState('silla', 1);
    state = { ...state, season: 'winter' };
    const result = conscriptAction(state, 'silla', 'seorabeol');
    expect(result.ok).toBe(false);
  });

  it('refuses conscription on a region the faction does not own', () => {
    const state = createInitialState('silla', 1);
    const result = conscriptAction(state, 'silla', 'pyeongyang');
    expect(result.ok).toBe(false);
  });

  it('refuses conscription once action points are exhausted', () => {
    let state = createInitialState('silla', 1);
    state = { ...state, factions: { ...state.factions, silla: { ...state.factions.silla, actionPoints: 0 } } };
    const result = conscriptAction(state, 'silla', 'seorabeol');
    expect(result.ok).toBe(false);
  });
});

describe('domesticAction / fortifyAction (내정 2턴, 축성 3턴)', () => {
  it('starts a domestic project that raises pop/food after the configured duration', () => {
    let state = createInitialState('silla', 1);
    const before = state.regions.amnyang;
    const started = domesticAction(state, 'silla', 'amnyang');
    expect(started.ok).toBe(true);
    if (!started.ok) return;
    state = started.state;
    expect(state.regions.amnyang.project?.kind).toBe('domestic');
    expect(state.regions.amnyang.project?.remainingTurns).toBe(balanceData.turn.domesticDurationTurns);

    for (let i = 0; i < balanceData.turn.domesticDurationTurns; i++) state = advanceTurn(state);
    expect(state.regions.amnyang.project).toBeNull();
    expect(state.regions.amnyang.pop).toBe(Math.min(6, before.pop + balanceData.turn.domesticStatBonus));
    expect(state.regions.amnyang.food).toBe(Math.min(6, before.food + balanceData.turn.domesticStatBonus));
  });

  it('starts a fortify project that raises defense after the configured duration', () => {
    let state = createInitialState('silla', 1);
    const before = state.regions.amnyang.defense;
    const started = fortifyAction(state, 'silla', 'amnyang');
    expect(started.ok).toBe(true);
    if (!started.ok) return;
    state = started.state;
    for (let i = 0; i < balanceData.turn.fortifyDurationTurns; i++) state = advanceTurn(state);
    expect(state.regions.amnyang.defense).toBe(before + balanceData.turn.fortifyDefenseBonus);
  });

  it('refuses to start a second project while one is in progress', () => {
    const state = createInitialState('silla', 1);
    const first = domesticAction(state, 'silla', 'amnyang');
    expect(first.ok).toBe(true);
    if (!first.ok) return;
    const second = fortifyAction(first.state, 'silla', 'amnyang');
    expect(second.ok).toBe(false);
  });
});

describe('marchAction: 아군 지역 이동', () => {
  it('moves troops between two adjacent friendly regions', () => {
    const state = createInitialState('silla', 1);
    const result = marchAction(state, {
      faction: 'silla',
      fromRegion: 'seorabeol',
      toRegion: 'amnyang',
      troops: 1000,
      heroIds: []
    });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.state.regions.seorabeol.garrison).toBe(state.regions.seorabeol.garrison - 1000);
    expect(result.state.regions.amnyang.garrison).toBe(state.regions.amnyang.garrison + 1000);
  });

  it('applies the 10% winter campaign loss to arriving troops', () => {
    let state = createInitialState('silla', 1);
    state = { ...state, season: 'winter' };
    const result = marchAction(state, {
      faction: 'silla',
      fromRegion: 'seorabeol',
      toRegion: 'amnyang',
      troops: 1000,
      heroIds: []
    });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    const expectedArrival = Math.round(1000 * (1 - balanceData.turn.winterCampaignLossRatio));
    expect(result.state.regions.amnyang.garrison).toBe(state.regions.amnyang.garrison + expectedArrival);
    expect(result.state.regions.seorabeol.garrison).toBe(state.regions.seorabeol.garrison - 1000);
  });

  it('refuses to march to a non-adjacent region', () => {
    const state = createInitialState('silla', 1);
    const result = marchAction(state, {
      faction: 'silla',
      fromRegion: 'seorabeol',
      toRegion: 'pyeongyang',
      troops: 1000,
      heroIds: []
    });
    expect(result.ok).toBe(false);
  });

  it('refuses to march more troops than are garrisoned', () => {
    const state = createInitialState('silla', 1);
    const result = marchAction(state, {
      faction: 'silla',
      fromRegion: 'seorabeol',
      toRegion: 'amnyang',
      troops: 999999,
      heroIds: []
    });
    expect(result.ok).toBe(false);
  });
});

describe('marchAction: 적 지역 공격 - 병력 열세면 포위, 압도적이면 강습', () => {
  function withWeakDefender(state: GameState): GameState {
    return {
      ...state,
      regions: { ...state.regions, daegaya: { ...state.regions.daegaya, garrison: 50, defense: 0 } }
    };
  }

  it('starts a siege when the attacker cannot reach the 4x assault threshold', () => {
    const state = createInitialState('silla', 1);
    // 압량(3500) 대 대가야(5000, defense 3): 4배에 크게 못 미친다.
    const result = marchAction(state, {
      faction: 'silla',
      fromRegion: 'amnyang',
      toRegion: 'daegaya',
      troops: 3000,
      heroIds: []
    });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.state.sieges).toHaveLength(1);
    expect(result.state.sieges[0].region).toBe('daegaya');
    expect(result.state.sieges[0].attacker).toBe('silla');
    expect(result.state.regions.daegaya.owner).toBe('gaya');
    expect(result.state.regions.amnyang.garrison).toBe(state.regions.amnyang.garrison - 3000);
  });

  it('captures the region immediately via assault when attacker power vastly exceeds defender power', () => {
    const state = withWeakDefender(createInitialState('silla', 1));
    const result = marchAction(state, {
      faction: 'silla',
      fromRegion: 'amnyang',
      toRegion: 'daegaya',
      troops: 3500,
      heroIds: []
    });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.state.sieges).toHaveLength(0);
    expect(result.state.regions.daegaya.owner).toBe('silla');
    expect(result.state.factions.silla.cohesion).toBeGreaterThanOrEqual(state.factions.silla.cohesion);
  });

  it('lets an ongoing siege starve out the defender over several turns', () => {
    let state = createInitialState('silla', 1);
    const started = marchAction(state, {
      faction: 'silla',
      fromRegion: 'amnyang',
      toRegion: 'daegaya',
      troops: 3000,
      heroIds: []
    });
    expect(started.ok).toBe(true);
    if (!started.ok) return;
    state = started.state;
    const foodTurns = state.sieges[0].foodTurnsRemaining;
    for (let i = 0; i < foodTurns; i++) state = advanceTurn(state);
    // 4단계부터는 다른 세력의 AI도 자체적으로 포위를 벌일 수 있으므로, 이 시도의 포위만 사라졌는지 확인한다.
    expect(state.sieges.some((s) => s.region === 'daegaya' && s.attacker === 'silla')).toBe(false);
    expect(state.regions.daegaya.owner).toBe('silla');
  });
});
