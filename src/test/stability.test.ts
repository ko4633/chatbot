import { describe, expect, it } from 'vitest';
import { regionsData } from '../core/data';
import { resolveEventChoice } from '../core/events';
import { advanceTurn, createInitialState } from '../core/state';
import type { GameState } from '../core/types';

const TERRITORIAL_REGION_IDS = regionsData.regions.filter((r) => r.terrain !== 'external').map((r) => r.id);

function isFiniteNumber(n: number): boolean {
  return typeof n === 'number' && Number.isFinite(n);
}

function assertInvariants(state: GameState, atTurn: number) {
  for (const id of TERRITORIAL_REGION_IDS) {
    const region = state.regions[id];
    expect(region, `지역 ${id}이 turn ${atTurn}에 사라졌다`).toBeDefined();
    expect(isFiniteNumber(region.garrison), `${id} garrison이 유한하지 않다`).toBe(true);
    expect(region.garrison).toBeGreaterThanOrEqual(0);
    expect(isFiniteNumber(region.defense)).toBe(true);
    expect(isFiniteNumber(region.pop)).toBe(true);
    expect(isFiniteNumber(region.food)).toBe(true);
  }
  for (const [id, fs] of Object.entries(state.factions)) {
    expect(isFiniteNumber(fs.gold), `${id} gold가 유한하지 않다`).toBe(true);
    expect(isFiniteNumber(fs.food), `${id} food가 유한하지 않다`).toBe(true);
    expect(isFiniteNumber(fs.cohesion), `${id} cohesion이 유한하지 않다`).toBe(true);
    expect(fs.cohesion).toBeGreaterThanOrEqual(0);
    expect(fs.cohesion).toBeLessThanOrEqual(100);
    expect(isFiniteNumber(fs.morale)).toBe(true);
    expect(fs.morale).toBeGreaterThanOrEqual(0.5);
    expect(fs.morale).toBeLessThanOrEqual(1.5);
  }
}

/** pendingChoice가 뜨면 첫 번째 선택지로 자동 응답한다(완전 자동 진행용). */
function respondToAnyPendingChoice(state: GameState): GameState {
  let s = state;
  let guard = 0;
  while (s.pendingChoice && guard < 20) {
    s = resolveEventChoice(s, s.pendingChoice.options[0].id);
    guard++;
  }
  return s;
}

describe('완료 기준: 플레이어 무행동으로도 125년이 굴러간다', () => {
  const TURNS_FOR_125_YEARS = 125 * 4; // 1턴 = 1계절

  for (const seed of [1, 7, 20240101]) {
    it(`시드 ${seed}: 플레이어(신라)가 한 번도 행동하지 않아도 551년 봄부터 676년 봄까지 500턴이 에러 없이 진행된다`, () => {
      let state = createInitialState('silla', seed);
      expect(() => {
        for (let i = 0; i < TURNS_FOR_125_YEARS; i++) {
          // 플레이어는 아무 행동도 하지 않는다: conscriptAction 등을 절대 호출하지 않는다.
          state = advanceTurn(state);
          state = respondToAnyPendingChoice(state);
          assertInvariants(state, i);
        }
      }).not.toThrow();

      expect(state.year).toBe(551 + 125);
      expect(state.season).toBe('spring');
      expect(state.turnNumber).toBe(TURNS_FOR_125_YEARS);

      // 세계가 여전히 일관적인지: 모든 영토 지역이 어느 한 세력 소유로 남아 있다(증발/중복 없음).
      const ownedCount = TERRITORIAL_REGION_IDS.filter((id) => !!state.regions[id]?.owner).length;
      expect(ownedCount).toBe(TERRITORIAL_REGION_IDS.length);
    });
  }

  it('AI가 실제로 행동한다: 125년 동안 최소 1회 이상 징병·내정·출진에 해당하는 연대기 기록이 남는다', () => {
    let state = createInitialState('silla', 42);
    for (let i = 0; i < TURNS_FOR_125_YEARS; i++) {
      state = advanceTurn(state);
      state = respondToAnyPendingChoice(state);
    }
    const aiActed = state.chronicle.some(
      (c) => c.text.includes('징집하다') || c.text.includes('내정을 베풀다') || c.text.includes('성을 쌓다') || c.text.includes('이동하다') || c.text.includes('포위') || c.text.includes('강습')
    );
    expect(aiActed).toBe(true);
  });
});
