/**
 * 밸런스 시뮬레이터 (CLAUDE.md 6단계).
 * AI 전원이 자동으로 두는 판을 지정한 횟수만큼 돌려 밸런스 목표치와 비교한다.
 * 브라우저 없이 순수 core 함수만으로 동작한다(설계 원칙 2).
 *
 * 사용법: npm run sim [게임 수] [시작 시드]
 */
import { balanceData } from '../src/core/balance';
import { resolveEventChoice } from '../src/core/events';
import { advanceTurn, createInitialState } from '../src/core/state';
import type { FactionId, GameState } from '../src/core/types';

const NUM_GAMES = Number(process.argv[2] ?? 1000);
const START_SEED = Number(process.argv[3] ?? 1);
const MAX_YEAR = 700;
const MAX_TURNS = (MAX_YEAR - 551) * 4 + 8; // 여유를 좀 둔다.

function autoResolve(state: GameState): GameState {
  let s = state;
  let guard = 0;
  while (s.pendingChoice && guard < 20) {
    s = resolveEventChoice(s, s.pendingChoice.options[0].id);
    guard++;
  }
  return s;
}

interface GameStats {
  hanseongLostByBaekje: boolean;
  seongwangDied: boolean;
  salsuVictory: boolean;
  suiOrTangInvaded: boolean;
  ansiseongHeld: boolean;
  nadangAlliance: boolean;
  baekjeFallen: boolean;
  goguryeoFallen: boolean;
  ending: string | null;
  finalYear: number;
}

/** playerFaction을 영토 세력이 아닌 값으로 두면 고구려·백제·신라·가야 넷 다 AI가 움직인다. */
const NO_PLAYER: FactionId = 'jungwon';

function simulateOne(seed: number): GameStats {
  let state = createInitialState(NO_PLAYER, seed);
  let ansiseongEverLost = false;
  let sawInvasion = false;
  // 성왕은 565년에 자연 퇴장하므로, 그 전(560년 시점)에 이미 죽어 있으면 관산성 매복
  // 전사(e1_04)로 인한 죽음이다. 자연 퇴장과 뒤섞이지 않도록 미리 스냅샷을 찍어 둔다.
  let seongwangDeadBefore560 = false;
  let seongwang560Checked = false;

  for (let i = 0; i < MAX_TURNS; i++) {
    state = advanceTurn(state);
    state = autoResolve(state);
    if (state.regions.ansiseong.owner !== 'goguryeo') ansiseongEverLost = true;
    if (state.invasions.length > 0 || Object.keys(state.invasionOutcomes).length > 0) sawInvasion = true;
    if (!seongwang560Checked && state.year >= 560) {
      seongwangDeadBefore560 = state.heroes.seongwang.status === 'dead';
      seongwang560Checked = true;
    }
    if (state.ending) break;
    if (state.year >= MAX_YEAR) break;
  }

  return {
    hanseongLostByBaekje: !!state.flags.sinjuEstablished,
    seongwangDied: seongwangDeadBefore560,
    salsuVictory: !!state.flags.salsuVictory,
    suiOrTangInvaded: sawInvasion,
    ansiseongHeld: !ansiseongEverLost,
    nadangAlliance: !!state.flags.nadangAlliance,
    baekjeFallen: !!state.flags.baekjeFallen,
    goguryeoFallen: !!state.flags.goguryeoFallen,
    ending: state.ending,
    finalYear: state.year
  };
}

function winningFaction(ending: string | null): FactionId | null {
  if (!ending) return null;
  if (ending === 'samhanUnification') return 'silla';
  if (ending === 'goguryeoUnderHeaven') return 'goguryeo';
  if (ending === 'baekjeSea' || ending === 'baekjeRevival') return 'baekje';
  if (ending === 'tangProvince') return 'jungwon';
  if (ending.startsWith('territorial700:')) return ending.split(':')[1] as FactionId;
  return null;
}

function pct(count: number, total: number): number {
  return total === 0 ? 0 : Math.round((count / total) * 1000) / 10;
}

function inRange(value: number, range: number[]): boolean {
  return value >= range[0] * 100 && value <= range[1] * 100;
}

function main() {
  const results: GameStats[] = [];
  const t0 = Date.now();
  for (let i = 0; i < NUM_GAMES; i++) {
    results.push(simulateOne(START_SEED + i));
    if ((i + 1) % Math.max(1, Math.floor(NUM_GAMES / 20)) === 0) {
      const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
      process.stderr.write(`... ${i + 1}/${NUM_GAMES} (${elapsed}s)\n`);
    }
  }

  const n = results.length;
  const hanseongFallRate = pct(results.filter((r) => r.hanseongLostByBaekje).length, n);
  const seongwangDeathRate = pct(results.filter((r) => r.seongwangDied).length, n);
  const salsuVictoryRate = pct(results.filter((r) => r.salsuVictory).length, n);
  const ansiseongDefenseRate = pct(results.filter((r) => r.ansiseongHeld).length, n);

  const nadangGames = results.filter((r) => r.nadangAlliance);
  const baekjeFallGivenNadangRate = pct(nadangGames.filter((r) => r.baekjeFallen).length, nadangGames.length);

  const goguryeoFallRate = pct(results.filter((r) => r.goguryeoFallen).length, n);
  const samhanUnificationRate = pct(results.filter((r) => r.ending === 'samhanUnification').length, n);

  const winCounts: Record<string, number> = {};
  for (const r of results) {
    const winner = winningFaction(r.ending);
    if (winner) winCounts[winner] = (winCounts[winner] ?? 0) + 1;
  }
  const winRates = Object.fromEntries(
    Object.entries(winCounts).map(([f, c]) => [f, pct(c, n)])
  );

  const targets = balanceData.endingTargets as Record<string, unknown>;

  const rows: [string, number, string, boolean][] = [
    ['한성 함락', hanseongFallRate, `${(targets.hanseongFallRate as number[])[0] * 100}~${(targets.hanseongFallRate as number[])[1] * 100}%`, inRange(hanseongFallRate, targets.hanseongFallRate as number[])],
    ['성왕 전사', seongwangDeathRate, `${(targets.seongwangDeathRate as number[])[0] * 100}~${(targets.seongwangDeathRate as number[])[1] * 100}%`, inRange(seongwangDeathRate, targets.seongwangDeathRate as number[])],
    ['살수 승리', salsuVictoryRate, `${(targets.salsuVictoryRate as number[])[0] * 100}%+`, salsuVictoryRate >= (targets.salsuVictoryRate as number[])[0] * 100],
    ['안시성 방어', ansiseongDefenseRate, `${(targets.ansiseongDefenseRate as number[])[0] * 100}%+`, ansiseongDefenseRate >= (targets.ansiseongDefenseRate as number[])[0] * 100],
    ['나당동맹 시 백제 멸망', baekjeFallGivenNadangRate, `${(targets.baekjeFallGivenNadangAllianceRate as number[])[0] * 100}~${(targets.baekjeFallGivenNadangAllianceRate as number[])[1] * 100}% (n=${nadangGames.length})`, inRange(baekjeFallGivenNadangRate, targets.baekjeFallGivenNadangAllianceRate as number[])],
    ['고구려 멸망', goguryeoFallRate, `${(targets.goguryeoFallRate as number[])[0] * 100}~${(targets.goguryeoFallRate as number[])[1] * 100}%`, inRange(goguryeoFallRate, targets.goguryeoFallRate as number[])],
    ['삼한일통 엔딩', samhanUnificationRate, `${(targets.samhanUnificationEndingRate as number[])[0] * 100}~${(targets.samhanUnificationEndingRate as number[])[1] * 100}%`, inRange(samhanUnificationRate, targets.samhanUnificationEndingRate as number[])]
  ];

  console.log(`\n=== 밸런스 시뮬레이터: ${n}판 (시드 ${START_SEED}~${START_SEED + n - 1}) ===\n`);
  for (const [label, value, target, ok] of rows) {
    console.log(`${ok ? '✅' : '❌'} ${label}: ${value}% (목표 ${target})`);
  }

  console.log('\n세력별 엔딩 승률 (목표: 어느 세력도 70% 초과 금지):');
  const maxWinRateAllowed = (targets.maxAnyFactionWinRate as number) * 100;
  let anyExceeded = false;
  for (const [faction, rate] of Object.entries(winRates)) {
    const exceeded = rate > maxWinRateAllowed;
    if (exceeded) anyExceeded = true;
    console.log(`  ${exceeded ? '❌' : '✅'} ${faction}: ${rate}%`);
  }
  console.log(`  ${anyExceeded ? '❌ 70% 초과 세력 있음' : '✅ 모두 70% 이하'}`);

  const endingCounts: Record<string, number> = {};
  for (const r of results) {
    const key = r.ending ?? `미종결(${r.finalYear}년)`;
    endingCounts[key] = (endingCounts[key] ?? 0) + 1;
  }
  console.log('\n엔딩 분포:');
  for (const [ending, count] of Object.entries(endingCounts).sort((a, b) => b[1] - a[1])) {
    console.log(`  ${ending}: ${count} (${pct(count, n)}%)`);
  }

  console.log(`\n총 소요 시간: ${((Date.now() - t0) / 1000).toFixed(1)}초`);
}

main();
