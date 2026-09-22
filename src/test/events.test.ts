import { describe, expect, it } from 'vitest';
import { resolveEventChoice } from '../core/events';
import { advanceTurn, createInitialState } from '../core/state';
import type { GameState } from '../core/types';

function advanceTo(state: GameState, times: number): GameState {
  let s = state;
  for (let i = 0; i < times; i++) s = advanceTurn(s);
  return s;
}

/** pendingChoice가 뜨면 첫 번째 선택지로 자동 응답하며 n턴을 진행한다(엔진 회귀 검증용). */
function autoAdvance(state: GameState, times: number): GameState {
  let s = state;
  for (let i = 0; i < times; i++) {
    s = advanceTurn(s);
    let guard = 0;
    while (s.pendingChoice && guard < 20) {
      s = resolveEventChoice(s, s.pendingChoice.options[0].id);
      guard++;
    }
  }
  return s;
}

describe('이벤트 엔진: 1막 배신의 한강', () => {
  it('e1_01 한강 탈환이 시작 시점에 바로 발동해 나제동맹 플래그를 세운다', () => {
    const state = createInitialState('silla', 1);
    expect(state.flags.najeAlliance).toBe(true);
    expect(state.firedEvents.e1_01_hangang_recapture).toBe(true);
  });

  it('e1_02 돌궐의 신성 공격: 고구려가 플레이어면 선택 팝업이 뜨고, 고흘 파견 시 신성 수비가 늘어난다', () => {
    let state = createInitialState('goguryeo', 1);
    state = advanceTo(state, 2); // 551년 봄 → 여름 → 가을
    expect(state.pendingChoice?.eventId).toBe('e1_02_gokturk_attack_sinseong');
    expect(state.pendingChoice?.options.map((o) => o.id)).toEqual(['send_goheul', 'hold']);

    const before = state.regions.sinseong.garrison;
    state = resolveEventChoice(state, 'send_goheul');
    expect(state.pendingChoice).toBeNull();
    expect(state.firedEvents.e1_02_gokturk_attack_sinseong).toBe(true);
    expect(state.regions.sinseong.garrison).toBe(before + 10000);
    expect(state.heroes.goheul.location).toBe('sinseong');
  });

  it('e1_02 농성을 택하면 병력 변화 없이 결속만 낮아진다', () => {
    let state = createInitialState('goguryeo', 1);
    state = advanceTo(state, 2);
    const before = state.regions.sinseong.garrison;
    const cohesionBefore = state.factions.goguryeo.cohesion;
    state = resolveEventChoice(state, 'hold');
    expect(state.regions.sinseong.garrison).toBe(before);
    expect(state.factions.goguryeo.cohesion).toBe(cohesionBefore - 5);
  });

  it('e1_03 신라의 선택: 한성 수비 5000 미만이면 기습이 성공해 한성이 신라로 넘어간다', () => {
    let state = createInitialState('silla', 1);
    state = advanceTo(state, 7); // 551년 봄 → 552년 겨울(아직 553년 전이라 이벤트가 발동하지 않는다)
    // 마지막 턴 직전에 수비를 낮춘다: 이벤트 판정은 그 턴의 AI 행동보다 먼저 일어나므로
    // 백제 AI가 미리 증원할 시간이 없다(4단계에서 AI가 지역을 스스로 보강하기 시작했다).
    state = { ...state, regions: { ...state.regions, hanseong: { ...state.regions.hanseong, garrison: 4000 } } };
    state = advanceTurn(state); // 553년 봄
    expect(state.pendingChoice?.eventId).toBe('e1_03_silla_choice');

    const baekjeCohesionBefore = state.factions.baekje.cohesion;
    state = resolveEventChoice(state, 'raid');

    expect(state.regions.hanseong.owner).toBe('silla');
    expect(state.flags.sinjuEstablished).toBe(true);
    expect(state.factions.baekje.grudge).toBe(40);
    expect(state.factions.baekje.cohesion).toBe(baekjeCohesionBefore - 10);
    const relation = state.relations.find(
      (r) => (r.a === 'baekje' && r.b === 'silla') || (r.a === 'silla' && r.b === 'baekje')
    );
    expect(relation?.value).toBe(-80);
  });

  it('완료 기준: 한성 수비가 5000 이상이면 기습이 실패로 분기한다', () => {
    let state = createInitialState('silla', 1);
    // 한성 수비는 초기값 6000으로, 이미 5000 이상이다.
    expect(state.regions.hanseong.garrison).toBeGreaterThanOrEqual(5000);
    state = advanceTo(state, 8);
    expect(state.pendingChoice?.eventId).toBe('e1_03_silla_choice');

    const sillaCohesionBefore = state.factions.silla.cohesion;
    const hangangsangnyuBefore = state.regions.hangangsangnyu.garrison;
    state = resolveEventChoice(state, 'raid');

    expect(state.regions.hanseong.owner).toBe('baekje'); // 기습 실패, 한성은 그대로 백제 소유.
    expect(state.flags.sinjuEstablished).toBeUndefined();
    expect(state.factions.silla.cohesion).toBe(sillaCohesionBefore - 10);
    expect(state.regions.hangangsangnyu.garrison).toBe(Math.round(hangangsangnyuBefore * 0.7));
  });

  it('e1_03 동맹 유지를 택하면 관계가 개선되고 한성 소유는 바뀌지 않는다', () => {
    let state = createInitialState('silla', 1);
    state = advanceTo(state, 8);
    state = resolveEventChoice(state, 'keep_alliance');
    expect(state.regions.hanseong.owner).toBe('baekje');
    const relation = state.relations.find(
      (r) => (r.a === 'baekje' && r.b === 'silla') || (r.a === 'silla' && r.b === 'baekje')
    );
    expect(relation?.value).toBe(75); // 초기 60 + 15
  });

  it('한 번 발동한 once 이벤트는 다시 발동하지 않는다', () => {
    let state = createInitialState('silla', 1);
    const najeAllianceFires = state.chronicle.filter((c) => c.text.includes('나누어 취하다')).length;
    state = advanceTo(state, 8);
    const stillOnce = state.chronicle.filter((c) => c.text.includes('나누어 취하다')).length;
    expect(stillOnce).toBe(najeAllianceFires);
  });

  it('가야를 보호하면 대가야 멸망 "각본" 이벤트(e1_06)는 조건이 막혀 발동하지 않는다', () => {
    let state = createInitialState('baekje', 1);
    // 558~562 구원 요청에서 원군을 보내기로 하면 gayaProtected 플래그가 서고, 대가야 멸망(560~565)의
    // 조건(가야 보호 아님)이 막힌다. (단, 4단계부터는 신라 AI가 이 각본과 무관하게 순수 전력으로
    // 대가야를 정복할 수도 있다 — 이 테스트는 "각본 이벤트가 막히는지"만 검증한다.)
    state = autoAdvance(state, 7 * 4); // 551 → 558년 부근까지
    if (state.pendingChoice?.eventId === 'e1_05_gaya_rescue_request') {
      state = resolveEventChoice(state, 'send_reinforcements');
    }
    state = autoAdvance(state, 7 * 4); // 565년 부근까지 계속 진행
    expect(state.flags.gayaProtected).toBe(true);
    expect(state.firedEvents.e1_06_daegaya_fall).toBeUndefined();
  });

  it('연대 조건 없는 이벤트가 시작 시점에 잘못 발동하지 않는다(형제의 분열 회귀 테스트)', () => {
    // yeongaesomun은 630년에야 등장하므로 551년에는 "아직 태어나지 않음"이지 "죽음"이 아니다.
    const state = createInitialState('goguryeo', 1);
    expect(state.firedEvents.e4_10_brothers_split).toBeUndefined();
    expect(state.flags.goguryeoSplit).toBeUndefined();
    expect(state.regions.gungnaeseong.owner).toBe('goguryeo');
  });

  it('1막 전체를 여러 시드로 자동 진행해도 엔진이 죽지 않는다(DSL 회귀 스모크 테스트)', () => {
    for (const seed of [1, 2, 3, 42, 12345]) {
      for (const playerFaction of ['goguryeo', 'baekje', 'silla']) {
        let state = createInitialState(playerFaction, seed);
        expect(() => {
          state = autoAdvance(state, 4 * 46); // 551 → 약 597년까지(1막 전체 + 2막 진입부)
        }).not.toThrow();
      }
    }
  });
});
