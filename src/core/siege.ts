import type { BalanceData } from './balance';

/**
 * 공성 공식 (CLAUDE.md "공성" 절).
 * 공격 전투력이 방어(성벽 포함)의 4배 이상이면 강습 가능(시도마다 공격측 15% 손실).
 * 아니면 포위: 매 턴 방어 병력 -8%, 성 식량(food등급×2턴분) 소진 시 함락.
 */
export function canAssault(attackerPower: number, defenderPower: number, balance: BalanceData['siege']): boolean {
  return attackerPower >= balance.assaultPowerRatio * defenderPower;
}

export function assaultAttackerCasualties(committedTroops: number, balance: BalanceData['siege']): number {
  return Math.round(committedTroops * balance.assaultAttackerLossPerAttempt);
}

export function siegeInitialFoodTurns(foodGrade: number, balance: BalanceData['siege']): number {
  return foodGrade * balance.siegeFoodTurnsPerFoodGrade;
}

export interface SiegeTickResult {
  defenderGarrisonAfter: number;
  foodTurnsRemainingAfter: number;
  fallsByStarvation: boolean;
}

/** 포위 중인 성이 한 턴을 버틴 결과. */
export function tickSiege(
  defenderGarrison: number,
  foodTurnsRemaining: number,
  balance: BalanceData['siege']
): SiegeTickResult {
  const defenderGarrisonAfter = Math.max(0, Math.round(defenderGarrison * (1 - balance.siegeDefenderAttritionPerTurn)));
  const foodTurnsRemainingAfter = foodTurnsRemaining - 1;
  return {
    defenderGarrisonAfter,
    foodTurnsRemainingAfter,
    fallsByStarvation: foodTurnsRemainingAfter <= 0
  };
}
