import { describe, expect, it } from 'vitest';
import { diplomacyAction, marchAction } from '../core/actions';
import { balanceData } from '../core/balance';
import { getRelationValue } from '../core/events';
import { createInitialState } from '../core/state';

describe('외교: 사신·조공·동맹 제안·선전포고', () => {
  it('사신은 관계를 소폭 개선하고 행동력을 소모한다', () => {
    const state = createInitialState('silla', 1);
    const before = getRelationValue(state, 'silla', 'baekje');
    const result = diplomacyAction(state, 'silla', 'baekje', 'envoy');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(getRelationValue(result.state, 'silla', 'baekje')).toBe(before + balanceData.diplomacy.envoyRelationDelta);
    expect(result.state.factions.silla.actionPoints).toBe(state.factions.silla.actionPoints - 1);
  });

  it('조공은 금을 쓰고 관계를 더 크게 개선하며, 금이 부족하면 실패한다', () => {
    let state = createInitialState('silla', 1);
    const before = getRelationValue(state, 'silla', 'baekje');
    const goldBefore = state.factions.silla.gold;
    const result = diplomacyAction(state, 'silla', 'baekje', 'tribute');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(getRelationValue(result.state, 'silla', 'baekje')).toBe(before + balanceData.diplomacy.tributeRelationDelta);
    expect(result.state.factions.silla.gold).toBe(goldBefore - balanceData.diplomacy.tributeGoldCost);

    state = { ...state, factions: { ...state.factions, silla: { ...state.factions.silla, gold: 0 } } };
    const poor = diplomacyAction(state, 'silla', 'baekje', 'tribute');
    expect(poor.ok).toBe(false);
  });

  it('동맹 제안은 관계가 충분히 우호적일 때만 성사된다', () => {
    // 백제-신라 초기 관계 60(이미 동맹 임계값). 가야-왜(40)는 임계값에 근접해 있어 성사되어야 한다.
    const state = createInitialState('baekje', 1);
    const result = diplomacyAction(state, 'baekje', 'silla', 'allianceProposal');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(getRelationValue(result.state, 'baekje', 'silla')).toBe(balanceData.diplomacy.allianceThreshold);

    // 고구려-백제 초기 관계 -50: 우호도가 한참 모자라 동맹이 성사되지 않는다(관계 불변).
    const distant = diplomacyAction(state, 'goguryeo', 'baekje', 'allianceProposal');
    expect(distant.ok).toBe(true);
    if (!distant.ok) return;
    expect(getRelationValue(distant.state, 'goguryeo', 'baekje')).toBe(getRelationValue(state, 'goguryeo', 'baekje'));
  });

  it('선전포고는 관계를 즉시 전쟁 수준으로 낮춘다', () => {
    const state = createInitialState('baekje', 1);
    const result = diplomacyAction(state, 'baekje', 'silla', 'declareWar');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(getRelationValue(result.state, 'baekje', 'silla')).toBe(balanceData.diplomacy.warThreshold);
  });

  it('동맹을 깨고 공격하면 전 세력과의 관계가 -15 된다', () => {
    // 백제-신라는 초기 관계 60(동맹). 백제가 신라의 인접 지역을 공격하면 위약 페널티가 전 세력에 적용된다.
    const state = createInitialState('baekje', 1);
    const relationsBefore = Object.fromEntries(
      Object.keys(state.factions)
        .filter((id) => id !== 'baekje')
        .map((id) => [id, getRelationValue(state, 'baekje', id)])
    );

    const attack = marchAction(state, {
      faction: 'baekje',
      fromRegion: 'hanseong',
      toRegion: 'hangangsangnyu',
      troops: 5000,
      heroIds: []
    });
    expect(attack.ok).toBe(true);
    if (!attack.ok) return;

    for (const [id, before] of Object.entries(relationsBefore)) {
      if (id === 'silla') continue; // 신라와의 관계는 공격 자체의 결과와 뒤섞이므로 별도로 확인하지 않는다.
      expect(getRelationValue(attack.state, 'baekje', id)).toBe(
        Math.max(balanceData.diplomacy.min, before + balanceData.diplomacy.brokenAllianceRelationPenaltyAll)
      );
    }
  });
});
