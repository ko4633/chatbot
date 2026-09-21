import { factionsData, regionsData } from './data';
import {
  type FactionId,
  type FactionState,
  type GameState,
  type RegionState,
  SEASON_LABEL,
  SEASON_ORDER,
  type Season
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
      food: r.food
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
      grudge: f.grudge ?? 0
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

/**
 * 턴 진행의 "계절 처리" 단계만 수행한다(1단계 범위).
 * 이벤트 판정·행동·전투·침공·영웅·엔딩 판정은 이후 단계에서 추가된다.
 */
export function advanceTurn(state: GameState): GameState {
  const { season, yearDelta } = nextSeason(state.season);
  const year = state.year + yearDelta;
  const chronicle = [
    ...state.chronicle,
    { year, season, text: `${year}년 ${SEASON_LABEL[season]}이 되다.` }
  ];
  return {
    ...state,
    turnNumber: state.turnNumber + 1,
    year,
    season,
    chronicle
  };
}
