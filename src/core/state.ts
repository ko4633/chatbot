import { balanceData } from './balance';
import { factionsData, heroesData, regionsData } from './data';
import { applyAutumnHarvest, applyGoldIncome, applyUpkeep } from './economy';
import { tickSiege } from './siege';
import {
  type FactionId,
  type FactionState,
  type GameState,
  type HeroState,
  type RegionState,
  SEASON_LABEL,
  SEASON_ORDER,
  type Season,
  type SiegeState
} from './types';

/**
 * 코어 상태 모듈. DOM·브라우저 API를 import하지 않는다.
 * state → action → newState 형태의 순수 함수만 둔다.
 */

function buildInitialRegions(): Record<string, RegionState> {
  const result: Record<string, RegionState> = {};
  for (const r of regionsData.regions) {
    result[r.id] = {
      id: r.id,
      owner: r.owner,
      garrison: r.garrison,
      defense: r.defense,
      pop: r.pop,
      food: r.food,
      project: null
    };
  }
  return result;
}

function buildInitialFactions(): Record<string, FactionState> {
  const result: Record<string, FactionState> = {};
  for (const f of factionsData.factions) {
    result[f.id] = {
      id: f.id,
      gold: f.gold,
      food: f.food,
      cohesion: f.cohesion,
      grudge: f.grudge ?? 0,
      morale: 1,
      actionPoints: balanceData.turn.actionsPerFaction
    };
  }
  return result;
}

function buildInitialHeroes(startYear: number): Record<string, HeroState> {
  const result: Record<string, HeroState> = {};
  const capitalByFaction = Object.fromEntries(factionsData.factions.map((f) => [f.id, f.capital]));
  for (const h of heroesData.heroes) {
    const alive = h.appearYear <= startYear && startYear <= h.exitYear;
    result[h.id] = {
      id: h.id,
      faction: h.faction,
      location: alive ? capitalByFaction[h.faction] ?? null : null,
      alive
    };
  }
  return result;
}

export function createInitialState(playerFaction: FactionId, rngSeed: number): GameState {
  return {
    turnNumber: 0,
    year: regionsData.startYear,
    season: regionsData.startSeason,
    regions: buildInitialRegions(),
    factions: buildInitialFactions(),
    relations: factionsData.initialRelations.map((r) => ({ ...r })),
    heroes: buildInitialHeroes(regionsData.startYear),
    sieges: [],
    playerFaction,
    rngSeed,
    rngCursor: 0,
    flags: {},
    chronicle: [
      {
        year: regionsData.startYear,
        season: regionsData.startSeason,
        text: `${regionsData.startYear}년 ${SEASON_LABEL[regionsData.startSeason]}, 삼한이 다시 어지러워지다.`
      }
    ]
  };
}

function nextSeason(season: Season): { season: Season; yearDelta: number } {
  const idx = SEASON_ORDER.indexOf(season);
  const next = SEASON_ORDER[(idx + 1) % SEASON_ORDER.length];
  const yearDelta = next === 'spring' ? 1 : 0;
  return { season: next, yearDelta };
}

function resetActionPoints(state: GameState): GameState {
  const factions = { ...state.factions };
  for (const id of Object.keys(factions)) {
    factions[id] = { ...factions[id], actionPoints: balanceData.turn.actionsPerFaction };
  }
  return { ...state, factions };
}

/** 내정(2턴)·축성(3턴) 진행 중인 지역의 프로젝트를 한 턴 진행시키고, 완료되면 효과를 적용한다. */
function processProjects(state: GameState): GameState {
  const regions = { ...state.regions };
  const chronicle = [...state.chronicle];
  for (const id of Object.keys(regions)) {
    const region = regions[id];
    if (!region.project) continue;
    const remainingTurns = region.project.remainingTurns - 1;
    if (remainingTurns > 0) {
      regions[id] = { ...region, project: { ...region.project, remainingTurns } };
      continue;
    }
    const staticRegion = regionsData.regions.find((r) => r.id === id);
    const name = staticRegion?.name ?? id;
    if (region.project.kind === 'domestic') {
      regions[id] = {
        ...region,
        project: null,
        pop: Math.min(6, region.pop + balanceData.turn.domesticStatBonus),
        food: Math.min(6, region.food + balanceData.turn.domesticStatBonus)
      };
      chronicle.push({ year: state.year, season: state.season, text: `${name}의 내정이 갖추어지다.` });
    } else {
      regions[id] = {
        ...region,
        project: null,
        defense: region.defense + balanceData.turn.fortifyDefenseBonus
      };
      chronicle.push({ year: state.year, season: state.season, text: `${name}의 성벽을 새로 쌓다.` });
    }
  }
  return { ...state, regions, chronicle };
}

/** 포위 중인 성을 한 턴 진행시킨다. 성 식량이 다하면 함락된다. */
function processSieges(state: GameState): GameState {
  if (state.sieges.length === 0) return state;
  const regions = { ...state.regions };
  const factions = { ...state.factions };
  const chronicle = [...state.chronicle];
  const remainingSieges: SiegeState[] = [];

  for (const siege of state.sieges) {
    const region = regions[siege.region];
    const tick = tickSiege(region.garrison, siege.foodTurnsRemaining, balanceData.siege);
    const staticRegion = regionsData.regions.find((r) => r.id === siege.region);
    const name = staticRegion?.name ?? siege.region;

    if (tick.fallsByStarvation) {
      regions[siege.region] = {
        ...region,
        owner: siege.attacker,
        garrison: siege.attackerTroops,
        project: null
      };
      chronicle.push({
        year: state.year,
        season: state.season,
        text: `${name}이 식량이 다하여 마침내 함락되다.`
      });
      if (staticRegion?.capital) {
        const defender = factions[siege.defender];
        factions[siege.defender] = {
          ...defender,
          cohesion: Math.max(0, defender.cohesion + balanceData.siege.capitalFallCohesionPenalty)
        };
      }
    } else {
      regions[siege.region] = { ...region, garrison: tick.defenderGarrisonAfter };
      remainingSieges.push({ ...siege, foodTurnsRemaining: tick.foodTurnsRemainingAfter });
    }
  }

  return { ...state, regions, factions, chronicle, sieges: remainingSieges };
}

/**
 * 턴 진행: 계절 처리 → (행동력 초기화) → 내정/축성 진행 → 포위 진행 → 경제(금·유지비·가을수확).
 * 이벤트 판정·플레이어/AI 행동·이동/전투는 각 행동 함수(actions.ts)와 이후 단계에서 수행한다.
 */
export function advanceTurn(state: GameState): GameState {
  const { season, yearDelta } = nextSeason(state.season);
  const year = state.year + yearDelta;

  let next: GameState = {
    ...state,
    turnNumber: state.turnNumber + 1,
    year,
    season,
    chronicle: [...state.chronicle, { year, season, text: `${year}년 ${SEASON_LABEL[season]}이 되다.` }]
  };

  next = resetActionPoints(next);
  next = processProjects(next);
  next = processSieges(next);
  next = applyGoldIncome(next, balanceData.economy);
  const upkeep = applyUpkeep(next, balanceData.economy, balanceData.combat.moraleMin);
  next = upkeep.state;
  next = applyAutumnHarvest(next, balanceData.economy);

  return next;
}
