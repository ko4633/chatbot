import type { BalanceData } from './balance';
import { nextRange } from './rng';
import type { AdjacencyType, Season, Terrain } from './types';

/**
 * 전투 공식 (CLAUDE.md "전투" 절).
 * 전투력 = 유효병력 × (0.5+주장통솔/100) × 사기(0.5~1.5) × 지형 × 계절 × rng(0.85~1.15)
 * 유효병력 = 5만 이하면 그대로, 초과분은 (병력-50000)^0.8 (대군 감쇠)
 */
export function effectiveTroops(troops: number, threshold: number, exponent: number): number {
  if (troops <= threshold) return troops;
  return threshold + Math.pow(troops - threshold, exponent);
}

export function leadershipMultiplier(leadership: number, balance: BalanceData['combat']): number {
  return balance.leadershipBase + leadership / balance.leadershipDivisor;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** 성 안 방어 = ×(1+0.25×defense). 고개 방어는 추가로 ×1.5. */
export function defenderTerrainMultiplier(defense: number, terrain: Terrain, balance: BalanceData['combat']): number {
  let mult = 1 + balance.castleDefenseBonusPerDefenseGrade * defense;
  if (terrain === 'pass') mult *= balance.passDefenseMultiplier;
  return mult;
}

/** 도하·도해 공격 ×0.8, 겨울 공격 ×0.8. 둘 다 해당하면 곱해서 적용한다. */
export function attackerSeasonCrossingMultiplier(
  season: Season,
  adjacencyType: AdjacencyType,
  balance: BalanceData['combat']
): number {
  let mult = 1;
  if (adjacencyType === 'sea') mult *= balance.riverOrSeaCrossingAttackMultiplier;
  if (season === 'winter') mult *= balance.winterAttackMultiplier;
  return mult;
}

export function battlePower(
  troops: number,
  leadership: number,
  morale: number,
  terrainMultiplier: number,
  rngValue: number,
  balance: BalanceData['combat']
): number {
  const eff = effectiveTroops(troops, balance.largeArmyThreshold, balance.largeArmyExponent);
  const moraleClamped = clamp(morale, balance.moraleMin, balance.moraleMax);
  const rngClamped = clamp(rngValue, balance.rngMin, balance.rngMax);
  return eff * leadershipMultiplier(leadership, balance) * moraleClamped * terrainMultiplier * rngClamped;
}

export interface BattleSideInput {
  troops: number;
  leadership: number;
  morale: number;
  terrainMultiplier: number;
}

export interface BattleOutcome {
  attackerPower: number;
  defenderPower: number;
  winner: 'attacker' | 'defender';
  loserLossRatio: number;
  winnerLossRatio: number;
  nextRngCursor: number;
}

/**
 * 전투 1회를 해석한다. 패자 손실 30~50%, 승자 손실 = 패자손실×(패자전투력/승자전투력).
 */
export function resolveBattle(
  attacker: BattleSideInput,
  defender: BattleSideInput,
  rngSeed: number,
  rngCursor: number,
  balance: BalanceData['combat']
): BattleOutcome {
  const rngA = nextRange(rngSeed, rngCursor, balance.rngMin, balance.rngMax);
  const attackerPower = battlePower(
    attacker.troops,
    attacker.leadership,
    attacker.morale,
    attacker.terrainMultiplier,
    rngA.value,
    balance
  );

  const rngD = nextRange(rngSeed, rngA.nextCursor, balance.rngMin, balance.rngMax);
  const defenderPower = battlePower(
    defender.troops,
    defender.leadership,
    defender.morale,
    defender.terrainMultiplier,
    rngD.value,
    balance
  );

  const winner: 'attacker' | 'defender' = attackerPower >= defenderPower ? 'attacker' : 'defender';
  const loserPower = winner === 'attacker' ? defenderPower : attackerPower;
  const winnerPower = winner === 'attacker' ? attackerPower : defenderPower;

  const rngLoss = nextRange(rngSeed, rngD.nextCursor, balance.loserLossMin, balance.loserLossMax);
  const loserLossRatio = rngLoss.value;
  const winnerLossRatio = winnerPower > 0 ? loserLossRatio * (loserPower / winnerPower) : 0;

  return {
    attackerPower,
    defenderPower,
    winner,
    loserLossRatio,
    winnerLossRatio,
    nextRngCursor: rngLoss.nextCursor
  };
}

export interface HeroDeathRoll {
  died: boolean;
  nextRngCursor: number;
}

/** 참전 영웅 패배 시 사망 10%, 주장 20%. */
export function rollHeroDeath(
  rngSeed: number,
  rngCursor: number,
  isCommander: boolean,
  balance: BalanceData['combat']
): HeroDeathRoll {
  const chance = isCommander ? balance.commanderDeathChanceOnDefeat : balance.heroDeathChanceOnDefeat;
  const draw = nextRange(rngSeed, rngCursor, 0, 1);
  return { died: draw.value < chance, nextRngCursor: draw.nextCursor };
}
