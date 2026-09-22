import { regionsData } from './data';
import type { FactionId, GameState } from './types';

/**
 * 엔딩 판정 (CLAUDE.md "엔딩" 절).
 * 삼한일통 | 고구려의 천하 | 백제의 바다 | 백제 부활 | 당의 주현 | 700년 도달 시 영토 비율 판정.
 * 각 턴 한 번씩 평가해 처음 맞는 조건으로 확정한다(이미 확정된 엔딩은 바꾸지 않는다).
 */

const TERRITORIAL_REGION_IDS = regionsData.regions.filter((r) => r.terrain !== 'external').map((r) => r.id);

function owns(state: GameState, faction: FactionId, region: string): boolean {
  return state.regions[region]?.owner === faction;
}

function territorialShare(state: GameState, faction: FactionId): number {
  const owned = TERRITORIAL_REGION_IDS.filter((id) => state.regions[id]?.owner === faction).length;
  return owned / TERRITORIAL_REGION_IDS.length;
}

function mostTerritorialFaction(state: GameState): FactionId {
  const counts = new Map<FactionId, number>();
  for (const id of TERRITORIAL_REGION_IDS) {
    const owner = state.regions[id]?.owner;
    if (!owner) continue;
    counts.set(owner, (counts.get(owner) ?? 0) + 1);
  }
  let best: FactionId = 'jungwon';
  let bestCount = -1;
  for (const [faction, count] of counts) {
    if (count > bestCount) {
      best = faction;
      bestCount = count;
    }
  }
  return best;
}

export function checkEndings(state: GameState): GameState {
  if (state.ending) return state;

  if (state.flags.tangWithdrawn && owns(state, 'silla', 'hanseong') && owns(state, 'silla', 'sabi')) {
    return { ...state, ending: 'samhanUnification' };
  }
  if (owns(state, 'goguryeo', 'pyeongyang') && owns(state, 'goguryeo', 'sabi') && owns(state, 'goguryeo', 'seorabeol')) {
    return { ...state, ending: 'goguryeoUnderHeaven' };
  }
  if (owns(state, 'baekje', 'sabi') && owns(state, 'baekje', 'seorabeol') && owns(state, 'baekje', 'pyeongyang')) {
    return { ...state, ending: 'baekjeSea' };
  }
  if (owns(state, 'baekjeRevival', 'sabi')) {
    return { ...state, ending: 'baekjeRevival' };
  }
  if (territorialShare(state, 'jungwon') >= 0.6) {
    return { ...state, ending: 'tangProvince' };
  }
  if (state.year >= 700) {
    return { ...state, ending: `territorial700:${mostTerritorialFaction(state)}` };
  }
  return state;
}
