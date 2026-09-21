import { regionsData } from './data';
import type { BalanceData } from './balance';
import type { FactionId, GameState } from './types';

/**
 * 경제·결속 공식 (CLAUDE.md "경제·결속" 절). 순수 함수로 GameState를 갱신한다.
 */

function regionsOwnedBy(state: GameState, faction: FactionId) {
  return regionsData.regions.filter((r) => state.regions[r.id]?.owner === faction && r.terrain !== 'external');
}

/** 매 턴 금 += Σ(pop등급×40). */
export function applyGoldIncome(state: GameState, balance: BalanceData['economy']): GameState {
  const factions = { ...state.factions };
  for (const factionId of Object.keys(factions)) {
    const owned = regionsOwnedBy(state, factionId);
    const income = owned.reduce((sum, r) => sum + state.regions[r.id].pop * balance.goldPerPopGradePerTurn, 0);
    if (income === 0) continue;
    factions[factionId] = { ...factions[factionId], gold: factions[factionId].gold + income };
  }
  return { ...state, factions };
}

/** 가을 수확: 식량 += Σ(food등급×300)×(0.5+결속/200). */
export function applyAutumnHarvest(state: GameState, balance: BalanceData['economy']): GameState {
  if (state.season !== 'autumn') return state;
  const factions = { ...state.factions };
  for (const factionId of Object.keys(factions)) {
    const fs = factions[factionId];
    const owned = regionsOwnedBy(state, factionId);
    const baseFood = owned.reduce((sum, r) => sum + state.regions[r.id].food * balance.autumnHarvestFoodPerFoodGrade, 0);
    const harvest = baseFood * (balance.autumnHarvestCohesionBaseline + fs.cohesion / balance.autumnHarvestCohesionDivisor);
    if (harvest === 0) continue;
    factions[factionId] = { ...fs, food: fs.food + harvest };
  }
  return { ...state, factions };
}

export interface UpkeepResult {
  state: GameState;
  zeroFoodFactions: FactionId[];
}

/** 유지비: 병력 1000당 식량 15, 금 5. 식량 0이면 사기 -30%, 결속 -5/턴. */
export function applyUpkeep(state: GameState, balance: BalanceData['economy'], moraleFloor: number): UpkeepResult {
  const factions = { ...state.factions };
  const zeroFoodFactions: FactionId[] = [];

  for (const factionId of Object.keys(factions)) {
    const fs = factions[factionId];
    const owned = regionsOwnedBy(state, factionId);
    const totalTroops = owned.reduce((sum, r) => sum + state.regions[r.id].garrison, 0);
    const foodCost = (totalTroops / 1000) * balance.upkeepFoodPer1000Troops;
    const goldCost = (totalTroops / 1000) * balance.upkeepGoldPer1000Troops;

    const foodAfter = fs.food - foodCost;
    const nextFood = Math.max(0, foodAfter);
    const nextGold = fs.gold - goldCost;

    let cohesion = fs.cohesion;
    let morale = fs.morale;
    if (foodAfter <= 0) {
      zeroFoodFactions.push(factionId);
      cohesion = Math.max(0, cohesion + balance.zeroFoodCohesionPerTurn);
      morale = Math.max(moraleFloor, morale * (1 + balance.zeroFoodMoraleMultiplier));
    }

    factions[factionId] = { ...fs, food: nextFood, gold: nextGold, cohesion, morale };
  }

  return { state: { ...state, factions }, zeroFoodFactions };
}
