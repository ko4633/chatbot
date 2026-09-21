import { describe, expect, it } from 'vitest';
import { balanceData } from '../core/balance';
import {
  attackerSeasonCrossingMultiplier,
  defenderTerrainMultiplier,
  effectiveTroops,
  leadershipMultiplier,
  resolveBattle,
  rollHeroDeath
} from '../core/combat';

const combat = balanceData.combat;

describe('effectiveTroops (대군 감쇠)', () => {
  it('leaves troops unchanged at or below the threshold', () => {
    expect(effectiveTroops(30000, 50000, 0.8)).toBe(30000);
    expect(effectiveTroops(50000, 50000, 0.8)).toBe(50000);
  });

  it('dampens the excess above the threshold by ^0.8', () => {
    const result = effectiveTroops(60000, 50000, 0.8);
    expect(result).toBeCloseTo(50000 + Math.pow(10000, 0.8), 6);
    // 감쇠가 실제로 원 병력보다 작아야 한다.
    expect(result).toBeLessThan(60000);
  });

  it('is monotonically increasing in troops', () => {
    const a = effectiveTroops(80000, 50000, 0.8);
    const b = effectiveTroops(120000, 50000, 0.8);
    expect(b).toBeGreaterThan(a);
  });
});

describe('leadershipMultiplier (0.5 + 통솔/100)', () => {
  it('matches CLAUDE.md 공식 at the stat range boundaries', () => {
    expect(leadershipMultiplier(0, combat)).toBeCloseTo(0.5, 6);
    expect(leadershipMultiplier(50, combat)).toBeCloseTo(1.0, 6);
    expect(leadershipMultiplier(100, combat)).toBeCloseTo(1.5, 6);
  });
});

describe('defenderTerrainMultiplier (성 방어 ×(1+0.25×defense), 고개 ×1.5)', () => {
  it('applies the castle defense bonus per defense grade', () => {
    expect(defenderTerrainMultiplier(0, 'castle', combat)).toBeCloseTo(1, 6);
    expect(defenderTerrainMultiplier(4, 'castle', combat)).toBeCloseTo(2, 6);
    expect(defenderTerrainMultiplier(5, 'capital', combat)).toBeCloseTo(2.25, 6);
  });

  it('stacks an additional 1.5x for mountain passes', () => {
    expect(defenderTerrainMultiplier(4, 'pass', combat)).toBeCloseTo(3, 6);
  });
});

describe('attackerSeasonCrossingMultiplier (도하·도해 ×0.8, 겨울 공격 ×0.8)', () => {
  it('is 1 for a plain land attack in a non-winter season', () => {
    expect(attackerSeasonCrossingMultiplier('spring', 'land', combat)).toBeCloseTo(1, 6);
  });
  it('applies 0.8 for winter attacks', () => {
    expect(attackerSeasonCrossingMultiplier('winter', 'land', combat)).toBeCloseTo(0.8, 6);
  });
  it('applies 0.8 for sea crossings', () => {
    expect(attackerSeasonCrossingMultiplier('spring', 'sea', combat)).toBeCloseTo(0.8, 6);
  });
  it('stacks both penalties for a winter sea crossing', () => {
    expect(attackerSeasonCrossingMultiplier('winter', 'sea', combat)).toBeCloseTo(0.64, 6);
  });
});

describe('resolveBattle (패자 손실 30~50%, 승자 손실 = 패자손실×(패자전투력/승자전투력))', () => {
  const side = (troops: number) => ({ troops, leadership: 70, morale: 1, terrainMultiplier: 1 });

  it('declares the side with overwhelming power the winner regardless of rng', () => {
    const outcome = resolveBattle(side(100000), side(1000), 1234, 0, combat);
    expect(outcome.winner).toBe('attacker');
  });

  it('keeps the loser loss ratio within the configured 30~50% band', () => {
    for (let cursor = 0; cursor < 50; cursor += 3) {
      const outcome = resolveBattle(side(20000), side(18000), 999, cursor, combat);
      expect(outcome.loserLossRatio).toBeGreaterThanOrEqual(combat.loserLossMin);
      expect(outcome.loserLossRatio).toBeLessThanOrEqual(combat.loserLossMax);
    }
  });

  it('gives the winner a smaller loss ratio than the loser when the win is decisive', () => {
    const outcome = resolveBattle(side(50000), side(5000), 42, 0, combat);
    expect(outcome.winnerLossRatio).toBeLessThan(outcome.loserLossRatio);
  });

  it('advances the rng cursor by exactly 3 draws', () => {
    const outcome = resolveBattle(side(10000), side(10000), 7, 10, combat);
    expect(outcome.nextRngCursor).toBe(13);
  });
});

describe('rollHeroDeath (참전 영웅 패배 시 사망 10%, 주장 20%)', () => {
  it('rolls commander deaths near 20% and non-commanders near 10% over many draws', () => {
    let commanderDeaths = 0;
    let soldierDeaths = 0;
    const n = 4000;
    let cursor = 0;
    for (let i = 0; i < n; i++) {
      const c = rollHeroDeath(555, cursor, true, combat);
      cursor = c.nextRngCursor;
      if (c.died) commanderDeaths++;
      const s = rollHeroDeath(555, cursor, false, combat);
      cursor = s.nextRngCursor;
      if (s.died) soldierDeaths++;
    }
    expect(commanderDeaths / n).toBeGreaterThan(0.15);
    expect(commanderDeaths / n).toBeLessThan(0.25);
    expect(soldierDeaths / n).toBeGreaterThan(0.06);
    expect(soldierDeaths / n).toBeLessThan(0.14);
  });
});
