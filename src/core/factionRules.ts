import { factionsData, regionsData } from './data';
import type { FactionId, GameState } from './types';

/**
 * 가야(AI 전용) 등 "수도 함락 시 전 지역 항복" 트레잇(capitalCollapse)을 가진 세력이
 * 수도를 잃으면 남은 모든 지역이 정복자에게 넘어가고 그 세력은 소멸한다.
 */
export function checkCapitalCollapse(state: GameState, fallenFaction: FactionId, conqueror: FactionId): GameState {
  const fd = factionsData.factions.find((f) => f.id === fallenFaction);
  if (!fd || !fd.traits?.includes('capitalCollapse')) return state;

  const regions = { ...state.regions };
  for (const r of regionsData.regions) {
    if (regions[r.id].owner === fallenFaction) {
      regions[r.id] = { ...regions[r.id], owner: conqueror };
    }
  }
  const fs = state.factions[fallenFaction];
  const factions = fs ? { ...state.factions, [fallenFaction]: { ...fs, destroyed: true } } : state.factions;
  return { ...state, regions, factions };
}
