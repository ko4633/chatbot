import { describe, expect, it } from 'vitest';
import { balanceData } from '../core/balance';
import { assaultAttackerCasualties, canAssault, siegeInitialFoodTurns, tickSiege } from '../core/siege';

const siege = balanceData.siege;

describe('canAssault (공격 전투력이 방어의 4배 이상이면 강습 가능)', () => {
  it('allows assault at exactly 4x', () => {
    expect(canAssault(400, 100, siege)).toBe(true);
  });
  it('forbids assault just under 4x', () => {
    expect(canAssault(399, 100, siege)).toBe(false);
  });
  it('allows assault well above 4x', () => {
    expect(canAssault(1000, 100, siege)).toBe(true);
  });
});

describe('assaultAttackerCasualties (강습 시도마다 공격측 15% 손실)', () => {
  it('applies exactly the configured ratio', () => {
    expect(assaultAttackerCasualties(10000, siege)).toBe(1500);
    expect(assaultAttackerCasualties(1000, siege)).toBe(150);
  });
});

describe('siegeInitialFoodTurns (성 식량 = food등급 × 2턴분)', () => {
  it('scales with the region food grade', () => {
    expect(siegeInitialFoodTurns(4, siege)).toBe(8);
    expect(siegeInitialFoodTurns(1, siege)).toBe(2);
    expect(siegeInitialFoodTurns(6, siege)).toBe(12);
  });
});

describe('tickSiege (매 턴 방어 병력 -8%, 식량 소진 시 함락)', () => {
  it('reduces defender garrison by 8% per turn and decrements food', () => {
    const result = tickSiege(10000, 3, siege);
    expect(result.defenderGarrisonAfter).toBe(9200);
    expect(result.foodTurnsRemainingAfter).toBe(2);
    expect(result.fallsByStarvation).toBe(false);
  });

  it('falls when food turns run out', () => {
    const result = tickSiege(10000, 1, siege);
    expect(result.foodTurnsRemainingAfter).toBe(0);
    expect(result.fallsByStarvation).toBe(true);
  });

  it('never lets defender garrison go negative', () => {
    const result = tickSiege(1, 5, siege);
    expect(result.defenderGarrisonAfter).toBeGreaterThanOrEqual(0);
  });
});
