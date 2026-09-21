import { describe, expect, it } from 'vitest';
import { balanceData } from '../core/balance';
import { regionsData } from '../core/data';
import { applyAutumnHarvest, applyGoldIncome, applyUpkeep } from '../core/economy';
import { createInitialState } from '../core/state';

const economy = balanceData.economy;

function sillaOwnedRegions() {
  return regionsData.regions.filter((r) => r.owner === 'silla' && r.terrain !== 'external');
}

describe('applyGoldIncome (매 턴 금 += Σ(pop등급×40))', () => {
  it('adds gold proportional to the sum of owned pop grades', () => {
    const state = createInitialState('silla', 1);
    const before = state.factions.silla.gold;
    const next = applyGoldIncome(state, economy);
    const expectedIncome = sillaOwnedRegions().reduce((sum, r) => sum + r.pop * economy.goldPerPopGradePerTurn, 0);
    expect(next.factions.silla.gold).toBe(before + expectedIncome);
  });

  it('leaves other factions untouched in their own income calc', () => {
    const state = createInitialState('silla', 1);
    const next = applyGoldIncome(state, economy);
    const baekjeOwned = regionsData.regions.filter((r) => r.owner === 'baekje' && r.terrain !== 'external');
    const expectedIncome = baekjeOwned.reduce((sum, r) => sum + r.pop * economy.goldPerPopGradePerTurn, 0);
    expect(next.factions.baekje.gold).toBe(state.factions.baekje.gold + expectedIncome);
  });
});

describe('applyAutumnHarvest (식량 += Σ(food등급×300)×(0.5+결속/200))', () => {
  it('does nothing outside autumn', () => {
    const state = createInitialState('silla', 1); // starts in spring
    const next = applyAutumnHarvest(state, economy);
    expect(next).toEqual(state);
  });

  it('applies the harvest formula exactly in autumn', () => {
    let state = createInitialState('silla', 1);
    state = { ...state, season: 'autumn' };
    const next = applyAutumnHarvest(state, economy);
    const base = sillaOwnedRegions().reduce((sum, r) => sum + r.food * economy.autumnHarvestFoodPerFoodGrade, 0);
    const expected =
      state.factions.silla.food +
      base * (economy.autumnHarvestCohesionBaseline + state.factions.silla.cohesion / economy.autumnHarvestCohesionDivisor);
    expect(next.factions.silla.food).toBeCloseTo(expected, 6);
  });
});

describe('applyUpkeep (병력 1000당 식량15·금5, 식량 0이면 사기-30%·결속-5)', () => {
  it('charges food and gold proportional to total garrison', () => {
    const state = createInitialState('silla', 1);
    const totalTroops = sillaOwnedRegions().reduce((sum, r) => sum + r.garrison, 0);
    const { state: next } = applyUpkeep(state, economy, balanceData.combat.moraleMin);
    const expectedFoodCost = (totalTroops / 1000) * economy.upkeepFoodPer1000Troops;
    const expectedGoldCost = (totalTroops / 1000) * economy.upkeepGoldPer1000Troops;
    expect(next.factions.silla.food).toBeCloseTo(Math.max(0, state.factions.silla.food - expectedFoodCost), 6);
    expect(next.factions.silla.gold).toBeCloseTo(state.factions.silla.gold - expectedGoldCost, 6);
  });

  it('penalizes cohesion and morale once food hits zero', () => {
    let state = createInitialState('silla', 1);
    state = { ...state, factions: { ...state.factions, silla: { ...state.factions.silla, food: 0 } } };
    const { state: next, zeroFoodFactions } = applyUpkeep(state, economy, balanceData.combat.moraleMin);
    expect(zeroFoodFactions).toContain('silla');
    expect(next.factions.silla.food).toBe(0);
    expect(next.factions.silla.cohesion).toBe(Math.max(0, state.factions.silla.cohesion + economy.zeroFoodCohesionPerTurn));
    expect(next.factions.silla.morale).toBeCloseTo(
      Math.max(balanceData.combat.moraleMin, 1 * (1 + economy.zeroFoodMoraleMultiplier)),
      6
    );
  });
});
