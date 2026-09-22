import { balanceData } from './balance';
import { defenderTerrainMultiplier, resolveBattle } from './combat';
import { regionsData } from './data';
import { checkCapitalCollapse } from './factionRules';
import { heroLeadership, NO_COMMANDER_LEADERSHIP } from './heroUtil';
import type {
  FactionId,
  GameState,
  HeroId,
  InvasionRoute,
  InvasionState,
  RegionId
} from './types';

/**
 * 외부 침공 모델 (CLAUDE.md "외부 세력" 절).
 * 요서(육로)·산동해로(해로)에서 목표로 진군하는 외부 군단. supplyTurns 경과 후 매 턴 20% 소모,
 * 보급률 하락. 여름 발동 시 장마·역병 추가 소모. 겨울 진입 시 보급률 0.5 미만이면 철수.
 * 점령지는 중원 소유(도호부). 결과를 defeated/withdrawn/victorious로 기록한다.
 */

/** 인접 그래프에서 출발지→목표까지 최단 경로(지역 id 목록, 출발지 포함)를 BFS로 구한다. */
function shortestPath(fromId: RegionId, toId: RegionId): RegionId[] | null {
  if (fromId === toId) return [fromId];
  const queue: RegionId[] = [fromId];
  const cameFrom: Record<RegionId, RegionId | null> = { [fromId]: null };
  const byId = Object.fromEntries(regionsData.regions.map((r) => [r.id, r]));

  while (queue.length > 0) {
    const current = queue.shift()!;
    if (current === toId) break;
    const region = byId[current];
    if (!region) continue;
    for (const adj of region.adjacent) {
      if (adj.to in cameFrom) continue;
      cameFrom[adj.to] = current;
      queue.push(adj.to);
    }
  }
  if (!(toId in cameFrom)) return null;

  const path: RegionId[] = [toId];
  let cursor: RegionId | null = toId;
  while (cursor !== fromId) {
    cursor = cameFrom[cursor!] ?? null;
    if (cursor === null) return null;
    path.unshift(cursor);
  }
  return path;
}

export interface StartInvasionParams {
  faction: FactionId;
  troops: number;
  route: InvasionRoute;
  target: RegionId;
  hero?: HeroId | null;
  summerExtraAttrition?: boolean;
}

export function createInvasion(state: GameState, params: StartInvasionParams): InvasionState | null {
  const path = shortestPath(params.route, params.target);
  if (!path) return null;
  return {
    id: `invasion-${params.faction}-${params.target}-${state.turnNumber}`,
    faction: params.faction,
    hero: params.hero ?? null,
    route: params.route,
    target: params.target,
    path,
    stepIndex: 0,
    troops: params.troops,
    initialTroops: params.troops,
    supplyRatio: 1,
    turnsElapsed: 0,
    summerExtraAttrition: params.summerExtraAttrition ?? false,
    startedTurn: state.turnNumber
  };
}

function resolveArrivalBattle(state: GameState, invasion: InvasionState): GameState {
  const target = state.regions[invasion.target];
  const targetStatic = regionsData.regions.find((r) => r.id === invasion.target);
  if (!target || !targetStatic) return state;
  const defenderFaction = target.owner;

  const attackerLeadership = invasion.hero ? heroLeadership(invasion.hero) : NO_COMMANDER_LEADERSHIP;
  const defenderHeroId = Object.values(state.heroes).find(
    (h) => h.faction === defenderFaction && h.status === 'active' && h.location === invasion.target
  )?.id;
  const defenderLeadership = defenderHeroId ? heroLeadership(defenderHeroId) : NO_COMMANDER_LEADERSHIP;
  const defenderTerrain = defenderTerrainMultiplier(target.defense, targetStatic.terrain, balanceData.combat);

  const outcome = resolveBattle(
    { troops: invasion.troops, leadership: attackerLeadership, morale: invasion.supplyRatio, terrainMultiplier: 1 },
    {
      troops: target.garrison,
      leadership: defenderLeadership,
      morale: state.factions[defenderFaction]?.morale ?? 1,
      terrainMultiplier: defenderTerrain
    },
    state.rngSeed,
    state.rngCursor,
    balanceData.combat
  );

  const targetName = targetStatic.name;
  let next: GameState = {
    ...state,
    rngCursor: outcome.nextRngCursor,
    lastBattle: {
      region: invasion.target,
      attackerFaction: invasion.faction,
      defenderFaction,
      winner: outcome.winner,
      attackerHeroIds: invasion.hero ? [invasion.hero] : [],
      defenderHeroIds: defenderHeroId ? [defenderHeroId] : [],
      turn: state.turnNumber
    }
  };

  if (outcome.winner === 'attacker') {
    const survivors = Math.max(0, Math.round(invasion.troops * (1 - outcome.winnerLossRatio)));
    next = {
      ...next,
      regions: { ...next.regions, [invasion.target]: { ...target, owner: invasion.faction, garrison: survivors, project: null } }
    };
    if (targetStatic.capital) next = checkCapitalCollapse(next, defenderFaction, invasion.faction);
    next = {
      ...next,
      invasionOutcomes: {
        ...next.invasionOutcomes,
        [invasion.faction]: { result: 'victorious', at: invasion.target, supplyRatio: invasion.supplyRatio }
      },
      chronicle: [...next.chronicle, { year: next.year, season: next.season, text: `${targetName}이 함락되다.` }]
    };
  } else {
    const survivors = Math.max(0, Math.round(target.garrison * (1 - outcome.winnerLossRatio)));
    next = {
      ...next,
      regions: { ...next.regions, [invasion.target]: { ...target, garrison: survivors } },
      invasionOutcomes: {
        ...next.invasionOutcomes,
        [invasion.faction]: { result: 'defeated', at: invasion.target, supplyRatio: invasion.supplyRatio }
      },
      chronicle: [...next.chronicle, { year: next.year, season: next.season, text: `${targetName} 공략이 격퇴되다.` }]
    };
  }

  return next;
}

/** 진행 중인 모든 침공을 한 턴 진행시킨다: 진군, 보급 소모, 겨울 철수 판정, 도착 시 전투. */
export function processInvasions(state: GameState): GameState {
  if (state.invasions.length === 0) return state;
  let next = state;
  const remaining: InvasionState[] = [];

  for (const invasion0 of state.invasions) {
    let invasion = { ...invasion0, turnsElapsed: invasion0.turnsElapsed + 1 };

    if (invasion.turnsElapsed > balanceData.invasion.supplyTurnsBeforeAttrition) {
      const rate = balanceData.invasion.supplyAttritionAfterSupplyTurnsPerTurn;
      invasion = {
        ...invasion,
        troops: Math.max(0, Math.round(invasion.troops * (1 - rate))),
        supplyRatio: Math.max(0, invasion.supplyRatio * (1 - rate))
      };
    }
    if (invasion.summerExtraAttrition && next.season === 'summer') {
      const rate = balanceData.invasion.summerMonsoonPlagueExtraAttrition;
      invasion = {
        ...invasion,
        troops: Math.max(0, Math.round(invasion.troops * (1 - rate))),
        supplyRatio: Math.max(0, invasion.supplyRatio * (1 - rate))
      };
    }

    const routeName = invasion.route === 'yoseo' ? '요서' : '산동해로';

    if (invasion.troops <= 0) {
      next = {
        ...next,
        invasionOutcomes: { ...next.invasionOutcomes, [invasion.faction]: { result: 'withdrawn', at: null, supplyRatio: 0 } },
        chronicle: [...next.chronicle, { year: next.year, season: next.season, text: `${routeName}의 군세가 보급이 끊겨 물러나다.` }]
      };
      continue;
    }
    if (next.season === 'winter' && invasion.supplyRatio < balanceData.invasion.winterWithdrawSupplyThreshold) {
      next = {
        ...next,
        invasionOutcomes: { ...next.invasionOutcomes, [invasion.faction]: { result: 'withdrawn', at: invasion.target, supplyRatio: invasion.supplyRatio } },
        chronicle: [...next.chronicle, { year: next.year, season: next.season, text: `${routeName}의 군세가 겨울을 맞아 철수하다.` }]
      };
      continue;
    }

    if (invasion.stepIndex < invasion.path.length - 1) {
      invasion = { ...invasion, stepIndex: invasion.stepIndex + 1 };
    }

    if (invasion.stepIndex >= invasion.path.length - 1) {
      next = resolveArrivalBattle(next, invasion);
      continue;
    }

    remaining.push(invasion);
  }

  return { ...next, invasions: remaining };
}
