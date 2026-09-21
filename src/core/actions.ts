import { balanceData } from './balance';
import {
  attackerSeasonCrossingMultiplier,
  defenderTerrainMultiplier,
  resolveBattle,
  rollHeroDeath
} from './combat';
import { heroesData, regionsData } from './data';
import { assaultAttackerCasualties, canAssault, siegeInitialFoodTurns } from './siege';
import type { AdjacencyType, FactionId, GameState, HeroId, RegionId, SiegeState } from './types';

/**
 * 행동력을 소모하는 국가 행동: 징병·내정·축성·출진 (CLAUDE.md "턴과 행동" 절).
 * 순수 함수: 성공하면 새 GameState를, 실패하면 사유를 반환한다.
 */

export type ActionResult = { ok: true; state: GameState } | { ok: false; reason: string };

const NO_COMMANDER_LEADERSHIP = 50; // 지휘 영웅이 없는 부대의 기본 통솔(설계 미기재 구간의 중립값).

function consumeActionPoint(state: GameState, faction: FactionId): GameState {
  const fs = state.factions[faction];
  return { ...state, factions: { ...state.factions, [faction]: { ...fs, actionPoints: fs.actionPoints - 1 } } };
}

function withChronicle(state: GameState, text: string): GameState {
  return { ...state, chronicle: [...state.chronicle, { year: state.year, season: state.season, text }] };
}

function findAdjacency(fromId: RegionId, toId: RegionId): AdjacencyType | null {
  const from = regionsData.regions.find((r) => r.id === fromId);
  const edge = from?.adjacent.find((a) => a.to === toId);
  return edge ? edge.type : null;
}

function requireActionPoint(state: GameState, faction: FactionId): string | null {
  if (state.factions[faction].actionPoints <= 0) return '행동력이 남아있지 않다.';
  return null;
}

export function conscriptAction(state: GameState, faction: FactionId, regionId: RegionId): ActionResult {
  const apError = requireActionPoint(state, faction);
  if (apError) return { ok: false, reason: apError };

  const region = state.regions[regionId];
  if (!region || region.owner !== faction) return { ok: false, reason: '아군 지역이 아니다.' };
  if (!balanceData.turn.conscriptionSeasons.includes(state.season)) {
    return { ok: false, reason: '봄과 여름에만 징병할 수 있다.' };
  }

  const recruited = region.pop * balanceData.turn.conscriptionPopMultiplier;
  const name = regionsData.regions.find((r) => r.id === regionId)?.name ?? regionId;

  let next: GameState = {
    ...state,
    regions: { ...state.regions, [regionId]: { ...region, garrison: region.garrison + recruited } }
  };
  next = consumeActionPoint(next, faction);
  next = withChronicle(next, `${name}에서 병 ${recruited.toLocaleString()}을 징집하다.`);
  return { ok: true, state: next };
}

export function domesticAction(state: GameState, faction: FactionId, regionId: RegionId): ActionResult {
  const apError = requireActionPoint(state, faction);
  if (apError) return { ok: false, reason: apError };

  const region = state.regions[regionId];
  if (!region || region.owner !== faction) return { ok: false, reason: '아군 지역이 아니다.' };
  if (region.project) return { ok: false, reason: '이미 진행 중인 공사가 있다.' };

  const name = regionsData.regions.find((r) => r.id === regionId)?.name ?? regionId;
  let next: GameState = {
    ...state,
    regions: {
      ...state.regions,
      [regionId]: {
        ...region,
        project: { kind: 'domestic', faction, remainingTurns: balanceData.turn.domesticDurationTurns }
      }
    }
  };
  next = consumeActionPoint(next, faction);
  next = withChronicle(next, `${name}에 내정을 베풀다.`);
  return { ok: true, state: next };
}

export function fortifyAction(state: GameState, faction: FactionId, regionId: RegionId): ActionResult {
  const apError = requireActionPoint(state, faction);
  if (apError) return { ok: false, reason: apError };

  const region = state.regions[regionId];
  if (!region || region.owner !== faction) return { ok: false, reason: '아군 지역이 아니다.' };
  if (region.project) return { ok: false, reason: '이미 진행 중인 공사가 있다.' };

  const name = regionsData.regions.find((r) => r.id === regionId)?.name ?? regionId;
  let next: GameState = {
    ...state,
    regions: {
      ...state.regions,
      [regionId]: {
        ...region,
        project: { kind: 'fortify', faction, remainingTurns: balanceData.turn.fortifyDurationTurns }
      }
    }
  };
  next = consumeActionPoint(next, faction);
  next = withChronicle(next, `${name}에 성을 쌓다.`);
  return { ok: true, state: next };
}

export interface MarchParams {
  faction: FactionId;
  fromRegion: RegionId;
  toRegion: RegionId;
  troops: number;
  heroIds: HeroId[];
}

function heroLeadership(heroId: HeroId): number {
  return heroesData.heroes.find((h) => h.id === heroId)?.leadership ?? NO_COMMANDER_LEADERSHIP;
}

export function marchAction(state: GameState, params: MarchParams): ActionResult {
  const { faction, fromRegion, toRegion, troops, heroIds } = params;
  const apError = requireActionPoint(state, faction);
  if (apError) return { ok: false, reason: apError };

  const source = state.regions[fromRegion];
  if (!source || source.owner !== faction) return { ok: false, reason: '아군 지역이 아니다.' };
  if (troops <= 0 || troops > source.garrison) return { ok: false, reason: '병력이 부족하다.' };

  const adjacency = findAdjacency(fromRegion, toRegion);
  if (!adjacency) return { ok: false, reason: '인접한 지역이 아니다.' };

  if (heroIds.length > balanceData.turn.maxHeroesPerCampaign) {
    return { ok: false, reason: `영웅은 최대 ${balanceData.turn.maxHeroesPerCampaign}명까지 종군할 수 있다.` };
  }
  for (const heroId of heroIds) {
    const hero = state.heroes[heroId];
    if (!hero || !hero.alive || hero.faction !== faction || hero.location !== fromRegion) {
      return { ok: false, reason: '종군할 수 없는 영웅이다.' };
    }
  }

  const target = state.regions[toRegion];
  const targetStatic = regionsData.regions.find((r) => r.id === toRegion);
  const sourceName = regionsData.regions.find((r) => r.id === fromRegion)?.name ?? fromRegion;
  const targetName = targetStatic?.name ?? toRegion;

  const isWinter = state.season === 'winter';
  const arrivingTroops = isWinter
    ? Math.round(troops * (1 - balanceData.turn.winterCampaignLossRatio))
    : troops;

  // 병력은 출발 즉시 원 지역에서 빠져나간다.
  let next: GameState = {
    ...state,
    regions: { ...state.regions, [fromRegion]: { ...source, garrison: source.garrison - troops } }
  };

  if (target.owner === faction) {
    // 아군 지역으로 이동: 단순 합류.
    const destAfterMove = next.regions[toRegion];
    next = {
      ...next,
      regions: { ...next.regions, [toRegion]: { ...destAfterMove, garrison: destAfterMove.garrison + arrivingTroops } },
      heroes: heroIds.reduce(
        (acc, id) => ({ ...acc, [id]: { ...acc[id], location: toRegion } }),
        next.heroes
      )
    };
    next = consumeActionPoint(next, faction);
    next = withChronicle(next, `${sourceName}에서 ${targetName}으로 병 ${arrivingTroops.toLocaleString()}이 이동하다.`);
    return { ok: true, state: next };
  }

  // 적/무주 지역 공격.
  return resolveAttack(next, {
    faction,
    fromRegion,
    toRegion,
    marchingTroops: arrivingTroops,
    heroIds,
    adjacency,
    sourceName,
    targetName
  });
}

interface AttackContext {
  faction: FactionId;
  fromRegion: RegionId;
  toRegion: RegionId;
  marchingTroops: number;
  heroIds: HeroId[];
  adjacency: AdjacencyType;
  sourceName: string;
  targetName: string;
}

function resolveAttack(state: GameState, ctx: AttackContext): ActionResult {
  const { faction, toRegion, marchingTroops, heroIds, adjacency, targetName } = ctx;
  const balance = balanceData.combat;
  const target = state.regions[toRegion];
  const targetStatic = regionsData.regions.find((r) => r.id === toRegion);
  if (!targetStatic) return { ok: false, reason: '알 수 없는 지역이다.' };
  const defenderFaction = target.owner;

  const commanderId = heroIds[0] ?? null;
  const attackerLeadership = commanderId ? heroLeadership(commanderId) : NO_COMMANDER_LEADERSHIP;
  const defenderHeroId =
    Object.values(state.heroes).find((h) => h.faction === defenderFaction && h.alive && h.location === toRegion)
      ?.id ?? null;
  const defenderLeadership = defenderHeroId ? heroLeadership(defenderHeroId) : NO_COMMANDER_LEADERSHIP;

  const attackerFactionState = state.factions[faction];
  const defenderFactionState = state.factions[defenderFaction];

  const attackerTerrain = attackerSeasonCrossingMultiplier(state.season, adjacency, balance);
  const defenderTerrain = defenderTerrainMultiplier(target.defense, targetStatic.terrain, balance);

  const battle = resolveBattle(
    {
      troops: marchingTroops,
      leadership: attackerLeadership,
      morale: attackerFactionState?.morale ?? 1,
      terrainMultiplier: attackerTerrain
    },
    {
      troops: target.garrison,
      leadership: defenderLeadership,
      morale: defenderFactionState?.morale ?? 1,
      terrainMultiplier: defenderTerrain
    },
    state.rngSeed,
    state.rngCursor,
    balance
  );

  let next: GameState = { ...state, rngCursor: battle.nextRngCursor };
  next = consumeActionPoint(next, faction);

  const assaultPossible = canAssault(battle.attackerPower, battle.defenderPower, balanceData.siege);

  if (!assaultPossible) {
    // 포위 시작(또는 합류): 매 턴 포위 공식(siege.ts)이 진행한다.
    const existing = next.sieges.find((s) => s.region === toRegion && s.attacker === faction);
    const sieges: SiegeState[] = existing
      ? next.sieges.map((s) =>
          s === existing ? { ...s, attackerTroops: s.attackerTroops + marchingTroops } : s
        )
      : [
          ...next.sieges,
          {
            id: `${toRegion}-${faction}-${state.turnNumber}`,
            region: toRegion,
            attacker: faction,
            defender: defenderFaction,
            attackerTroops: marchingTroops,
            attackerHeroes: heroIds,
            foodTurnsRemaining: siegeInitialFoodTurns(target.food, balanceData.siege),
            startedTurn: state.turnNumber
          }
        ];
    next = {
      ...next,
      sieges,
      heroes: heroIds.reduce((acc, id) => ({ ...acc, [id]: { ...acc[id], location: toRegion } }), next.heroes)
    };
    next = withChronicle(next, `${targetName}을(를) 에워싸고 포위하다.`);
    return { ok: true, state: next };
  }

  // 강습: 시도마다 공격측 15% 손실이 항상 발생한다.
  const flatCasualties = assaultAttackerCasualties(marchingTroops, balanceData.siege);
  const attackerAfterFlat = Math.max(0, marchingTroops - flatCasualties);

  let heroDeathCursor = next.rngCursor;
  const heroesAfter = { ...next.heroes };
  const isAttackerLoser = battle.winner === 'defender';
  const isDefenderLoser = battle.winner === 'attacker';

  function applyDeathRolls(ids: HeroId[], lost: boolean) {
    if (!lost) return;
    ids.forEach((id, idx) => {
      const roll = rollHeroDeath(next.rngSeed, heroDeathCursor, idx === 0, balance);
      heroDeathCursor = roll.nextRngCursor;
      if (roll.died) heroesAfter[id] = { ...heroesAfter[id], alive: false, location: null };
    });
  }
  applyDeathRolls(heroIds, isAttackerLoser);
  if (defenderHeroId) applyDeathRolls([defenderHeroId], isDefenderLoser);

  const factions = { ...next.factions };
  let regions = next.regions;
  let chronicle = next.chronicle;

  if (battle.winner === 'attacker') {
    const survivors = Math.max(0, Math.round(attackerAfterFlat * (1 - battle.winnerLossRatio)));
    regions = { ...regions, [toRegion]: { ...target, owner: faction, garrison: survivors, project: null } };
    const cohesionDelta = targetStatic.capital ? balanceData.siege.capitalFallCohesionPenalty : balanceData.cohesion.onTerritoryLost;
    factions[defenderFaction] = {
      ...factions[defenderFaction],
      cohesion: Math.max(0, factions[defenderFaction].cohesion + cohesionDelta)
    };
    factions[faction] = { ...factions[faction], cohesion: Math.min(100, factions[faction].cohesion + balanceData.cohesion.onVictory) };
    chronicle = [...chronicle, { year: state.year, season: state.season, text: `${targetName}을(를) 강습하여 함락시키다.` }];
  } else {
    const survivors = Math.max(0, Math.round(target.garrison * (1 - battle.winnerLossRatio)));
    regions = { ...regions, [toRegion]: { ...target, garrison: survivors } };
    factions[faction] = { ...factions[faction], cohesion: Math.max(0, factions[faction].cohesion + balanceData.cohesion.onDefeat) };
    factions[defenderFaction] = {
      ...factions[defenderFaction],
      cohesion: Math.min(100, factions[defenderFaction].cohesion + balanceData.cohesion.onVictory)
    };
    chronicle = [...chronicle, { year: state.year, season: state.season, text: `${targetName}에 대한 강습이 실패로 돌아가다.` }];
  }

  next = { ...next, regions, factions, chronicle, heroes: heroesAfter, rngCursor: heroDeathCursor };
  return { ok: true, state: next };
}
