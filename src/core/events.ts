import { balanceData } from './balance';
import { clamp, defenderTerrainMultiplier, resolveBattle, rollHeroDeath } from './combat';
import { eventsData, factionsData, heroesData, regionsData } from './data';
import { checkCapitalCollapse } from './factionRules';
import { heroLeadership, NO_COMMANDER_LEADERSHIP } from './heroUtil';
import { nextRandom } from './rng';
import type { FactionId, GameState, HeroId, RegionId, Season } from './types';

/**
 * 이벤트 엔진 (CLAUDE.md "이벤트 엔진" 절).
 * 매 턴 모든 이벤트의 연도 범위와 조건을 평가한다. decider가 있으면 해당 국가가 선택한다
 * (플레이어면 팝업, AI면 가중치 추첨). DSL에 없는 키는 여기서 에러를 던진다.
 *
 * 참고: invasion·navalBattle 효과는 여기서는 즉시 전투로 단순화해 처리한다.
 * 요서·산동해로에서 여러 턴에 걸쳐 진군하는 보급 모델(공식 "외부 세력" 절)은 5단계에서 구현한다.
 * act가 "random"인 랜덤 이벤트(가뭄·역병 등)도 5~6단계에서 세력별 순회 로직과 함께 연결한다.
 */

interface EventAllyRef {
  faction?: FactionId;
  hero?: HeroId;
  troops?: number;
}

interface EventChoice {
  id: string;
  label: string;
  text?: string;
  weight?: number;
  effects?: unknown[];
}

interface EventDef {
  id: string;
  act: number | 'random';
  title: string;
  text?: string;
  once?: boolean;
  decider?: FactionId;
  conditions?: Record<string, unknown>;
  effects?: unknown[];
  choices?: EventChoice[];
}

const events = (eventsData as unknown as { events: EventDef[] }).events;

interface RngThread {
  seed: number;
  cursor: number;
}

function drawChance(rng: RngThread): { hit: (chance: number) => boolean; rng: RngThread } {
  const draw = nextRandom(rng.seed, rng.cursor);
  const next = { seed: rng.seed, cursor: draw.nextCursor };
  return { hit: (chance: number) => draw.value < chance, rng: next };
}

interface Thresholds {
  gte?: number;
  lte?: number;
  gt?: number;
  lt?: number;
  eq?: number;
}

function withinThresholds(value: number, t: Thresholds): boolean {
  if (t.gte !== undefined && !(value >= t.gte)) return false;
  if (t.lte !== undefined && !(value <= t.lte)) return false;
  if (t.gt !== undefined && !(value > t.gt)) return false;
  if (t.lt !== undefined && !(value < t.lt)) return false;
  if (t.eq !== undefined && !(value === t.eq)) return false;
  return true;
}

function getRelationValue(state: GameState, a: FactionId, b: FactionId): number {
  const r = state.relations.find((r) => (r.a === a && r.b === b) || (r.a === b && r.b === a));
  return r ? r.value : 0;
}

interface CondCtx {
  state: GameState;
  turnStartRegionOwners: Record<RegionId, FactionId>;
}

/** 조건 DSL 평가. 반환값과 함께 rng 커서를 실로 꿴다(chance 조건이 소비한다). */
function evalCond(cond: unknown, ctx: CondCtx, rng: RngThread): { result: boolean; rng: RngThread } {
  if (typeof cond !== 'object' || cond === null) {
    throw new Error(`조건은 객체여야 한다: ${JSON.stringify(cond)}`);
  }
  const keys = Object.keys(cond as Record<string, unknown>);
  if (keys.length !== 1) throw new Error(`조건 객체는 키를 하나만 가져야 한다: ${JSON.stringify(cond)}`);
  const key = keys[0];
  const val = (cond as Record<string, unknown>)[key];
  const state = ctx.state;

  switch (key) {
    case 'all': {
      let r = rng;
      for (const c of val as unknown[]) {
        const res = evalCond(c, ctx, r);
        r = res.rng;
        if (!res.result) return { result: false, rng: r };
      }
      return { result: true, rng: r };
    }
    case 'any': {
      let r = rng;
      for (const c of val as unknown[]) {
        const res = evalCond(c, ctx, r);
        r = res.rng;
        if (res.result) return { result: true, rng: r };
      }
      return { result: false, rng: r };
    }
    case 'not': {
      const res = evalCond(val, ctx, rng);
      return { result: !res.result, rng: res.rng };
    }
    case 'year': {
      const v = val as Thresholds;
      return { result: withinThresholds(state.year, v), rng };
    }
    case 'season': {
      return { result: state.season === (val as Season), rng };
    }
    case 'flag': {
      const v = val as { flag: string; value?: boolean };
      const expected = v.value ?? true;
      return { result: (state.flags[v.flag] ?? false) === expected, rng };
    }
    case 'owns': {
      const v = val as { faction: FactionId; region: RegionId };
      return { result: state.regions[v.region]?.owner === v.faction, rng };
    }
    case 'stat': {
      const v = val as Thresholds & { faction: FactionId; key: string };
      const fs = state.factions[v.faction];
      if (!fs) return { result: false, rng };
      const value = (fs as unknown as Record<string, number>)[v.key];
      return { result: withinThresholds(value, v), rng };
    }
    case 'relation': {
      const v = val as Thresholds & { a: FactionId; b: FactionId };
      return { result: withinThresholds(getRelationValue(state, v.a, v.b), v), rng };
    }
    case 'garrison': {
      const v = val as Thresholds & { region: RegionId; faction?: FactionId; present?: boolean };
      const region = state.regions[v.region];
      if (!region) return { result: false, rng };
      if (v.present) {
        const present =
          (v.faction ? region.owner === v.faction : region.garrison > 0) ||
          state.sieges.some((s) => s.region === v.region && s.attacker === v.faction);
        return { result: present, rng };
      }
      if (v.faction && region.owner !== v.faction) return { result: false, rng };
      return { result: withinThresholds(region.garrison, v), rng };
    }
    case 'heroAlive': {
      return { result: state.heroes[val as HeroId]?.status === 'active', rng };
    }
    case 'king': {
      const v = val as { faction: FactionId; hero: HeroId };
      const heroDef = heroesData.heroes.find((h) => h.id === v.hero);
      const hs = state.heroes[v.hero];
      const result = !!heroDef?.isKing && heroDef.faction === v.faction && hs?.status === 'active';
      return { result, rng };
    }
    case 'factionAlive': {
      const fs = state.factions[val as FactionId];
      return { result: !!fs && !fs.destroyed, rng };
    }
    case 'jungwonPhase': {
      return { result: state.jungwonPhase === val, rng };
    }
    case 'regionCount': {
      const v = val as Thresholds & { faction: FactionId };
      const count = regionsData.regions.filter(
        (r) => r.terrain !== 'external' && state.regions[r.id]?.owner === v.faction
      ).length;
      return { result: withinThresholds(count, v), rng };
    }
    case 'chance': {
      const draw = drawChance(rng);
      return { result: draw.hit(val as number), rng: draw.rng };
    }
    case 'captured': {
      const v = val as { region: RegionId; from: FactionId; to?: FactionId };
      const prev = ctx.turnStartRegionOwners[v.region];
      const cur = state.regions[v.region]?.owner;
      const result = prev === v.from && cur !== v.from && (v.to ? cur === v.to : true);
      return { result, rng };
    }
    case 'battleResult': {
      const v = val as { region?: RegionId; hero?: HeroId; result: string };
      const lb = state.lastBattle;
      if (!lb) return { result: false, rng };
      if (v.region && lb.region !== v.region) return { result: false, rng };
      const winnerFaction = lb.winner === 'attacker' ? lb.attackerFaction : lb.defenderFaction;
      const loserFaction = lb.winner === 'attacker' ? lb.defenderFaction : lb.attackerFaction;
      if (v.result === 'attackerVictory') return { result: lb.winner === 'attacker', rng };
      if (v.result === 'defenderVictory') return { result: lb.winner === 'defender', rng };
      if (v.result.endsWith('Victory')) {
        const faction = v.result.slice(0, -'Victory'.length);
        return { result: winnerFaction === faction, rng };
      }
      if (v.result.endsWith('Defeat')) {
        const faction = v.result.slice(0, -'Defeat'.length);
        return { result: loserFaction === faction, rng };
      }
      if (v.hero) {
        const side = lb.attackerHeroIds.includes(v.hero) ? 'attacker' : lb.defenderHeroIds.includes(v.hero) ? 'defender' : null;
        if (!side) return { result: false, rng };
        if (v.result === 'victory') return { result: lb.winner === side, rng };
        if (v.result === 'defeat') return { result: lb.winner !== side, rng };
      }
      return { result: false, rng };
    }
    case 'invasionSupply': {
      const v = val as Thresholds & { faction: FactionId };
      const ratio = state.invasionOutcomes[v.faction]?.supplyRatio ?? 1;
      return { result: withinThresholds(ratio, v), rng };
    }
    case 'invasionResult': {
      const v = val as { faction: FactionId; result: string; at?: RegionId };
      const outcome = state.invasionOutcomes[v.faction];
      const result = !!outcome && outcome.result === v.result && (v.at ? outcome.at === v.at : true);
      return { result, rng };
    }
    default:
      throw new Error(`알 수 없는 조건 키: ${key}`);
  }
}

interface StagedArmy {
  faction: FactionId;
  troops: number;
  heroIds: HeroId[];
}

interface FoldCtx {
  state: GameState;
  rng: RngThread;
  staged: StagedArmy | null;
  turnStartRegionOwners: Record<RegionId, FactionId>;
}

function withChronicleLine(state: GameState, text: string): GameState {
  return { ...state, chronicle: [...state.chronicle, { year: state.year, season: state.season, text }] };
}

function applyStatEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { faction, key, delta, set, multiply } = payload as {
    faction: FactionId;
    key: string;
    delta?: number;
    set?: number;
    multiply?: number;
  };
  const fs = ctx.state.factions[faction];
  if (!fs) return ctx;
  let value = (fs as unknown as Record<string, number>)[key];
  if (delta !== undefined) value += delta;
  if (set !== undefined) value = set;
  if (multiply !== undefined) value *= multiply;
  if (key === 'cohesion') value = clamp(value, balanceData.cohesion.min, balanceData.cohesion.max);
  if (key === 'grudge') value = clamp(value, balanceData.grudge.min, balanceData.grudge.max);
  if (key === 'morale') value = clamp(value, balanceData.combat.moraleMin, balanceData.combat.moraleMax);
  const factions = { ...ctx.state.factions, [faction]: { ...fs, [key]: value } };
  return { ...ctx, state: { ...ctx.state, factions } };
}

function applyRelationEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { a, b, delta, set } = payload as { a: FactionId; b: FactionId; delta?: number; set?: number };
  const relations = [...ctx.state.relations];
  const idx = relations.findIndex((r) => (r.a === a && r.b === b) || (r.a === b && r.b === a));
  let value = set !== undefined ? set : (idx >= 0 ? relations[idx].value : 0) + (delta ?? 0);
  value = clamp(value, balanceData.diplomacy.min, balanceData.diplomacy.max);
  if (idx >= 0) relations[idx] = { ...relations[idx], value };
  else relations.push({ a, b, value });
  return { ...ctx, state: { ...ctx.state, relations } };
}

function applySetOwnerEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { region, regions, faction } = payload as { region?: RegionId; regions?: RegionId[]; faction: FactionId };
  const ids = regions ?? (region ? [region] : []);
  let state = ctx.state;
  for (const id of ids) {
    const r = state.regions[id];
    if (!r) continue;
    const prevOwner = r.owner;
    const staticRegion = regionsData.regions.find((sr) => sr.id === id);
    state = { ...state, regions: { ...state.regions, [id]: { ...r, owner: faction } } };
    if (staticRegion?.capital && prevOwner !== faction) {
      state = checkCapitalCollapse(state, prevOwner, faction);
    }
  }
  return { ...ctx, state };
}

function applyGarrisonEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { region, regions, delta, multiply } = payload as {
    region?: RegionId;
    regions?: RegionId[];
    delta?: number;
    multiply?: number;
  };
  const ids = regions ?? (region ? [region] : []);
  let stateRegions = ctx.state.regions;
  for (const id of ids) {
    const r = stateRegions[id];
    if (!r) continue;
    let g = r.garrison;
    if (delta !== undefined) g += delta;
    if (multiply !== undefined) g *= multiply;
    stateRegions = { ...stateRegions, [id]: { ...r, garrison: Math.max(0, Math.round(g)) } };
  }
  return { ...ctx, state: { ...ctx.state, regions: stateRegions } };
}

function applyDefenseEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { region, regions, delta } = payload as { region?: RegionId; regions?: RegionId[]; delta?: number };
  const ids = regions ?? (region ? [region] : []);
  let stateRegions = ctx.state.regions;
  for (const id of ids) {
    const r = stateRegions[id];
    if (!r) continue;
    stateRegions = { ...stateRegions, [id]: { ...r, defense: r.defense + (delta ?? 0) } };
  }
  return { ...ctx, state: { ...ctx.state, regions: stateRegions } };
}

function applyKillHeroEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { hero } = payload as { hero: HeroId };
  const hs = ctx.state.heroes[hero];
  if (!hs) return ctx;
  return { ...ctx, state: { ...ctx.state, heroes: { ...ctx.state.heroes, [hero]: { ...hs, status: 'dead', location: null } } } };
}

function applySetKingEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { faction, hero } = payload as { faction: FactionId; hero: HeroId };
  const hs = ctx.state.heroes[hero];
  if (!hs) return ctx;
  const capital = factionsData.factions.find((f) => f.id === faction)?.capital ?? null;
  return { ...ctx, state: { ...ctx.state, heroes: { ...ctx.state.heroes, [hero]: { ...hs, status: 'active', location: capital } } } };
}

function applyTransferHeroEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { hero, to } = payload as { hero: HeroId; to: FactionId };
  const hs = ctx.state.heroes[hero];
  if (!hs) return ctx;
  const capital = factionsData.factions.find((f) => f.id === to)?.capital ?? null;
  return {
    ...ctx,
    state: { ...ctx.state, heroes: { ...ctx.state.heroes, [hero]: { ...hs, faction: to, status: 'active', location: capital } } }
  };
}

function applyArmyEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { hero, heroes: heroList, faction, troops, to, allies } = payload as {
    hero?: HeroId;
    heroes?: HeroId[];
    faction?: FactionId;
    troops?: number;
    to: RegionId;
    allies?: EventAllyRef[];
  };
  const heroIds: HeroId[] = [];
  if (hero) heroIds.push(hero);
  if (heroList) heroIds.push(...heroList);
  let totalTroops = troops ?? 0;
  let resolvedFaction = faction ?? (hero ? heroesData.heroes.find((h) => h.id === hero)?.faction : undefined);
  if (allies) {
    for (const ally of allies) {
      if (ally.hero) heroIds.push(ally.hero);
      if (ally.troops) totalTroops += ally.troops;
    }
  }
  let stateHeroes = ctx.state.heroes;
  for (const id of heroIds) {
    const hs = stateHeroes[id];
    if (hs) stateHeroes = { ...stateHeroes, [id]: { ...hs, status: 'active', location: to } };
  }
  let regions = ctx.state.regions;
  const targetRegion = regions[to];
  // 목표가 아군 땅이면 즉시 그 지역의 수비 병력으로 합류한다(증원·소환). 적지면 뒤따르는 battle 효과가 쓸 부대로만 대기시킨다.
  if (targetRegion && resolvedFaction && targetRegion.owner === resolvedFaction && totalTroops > 0) {
    regions = { ...regions, [to]: { ...targetRegion, garrison: targetRegion.garrison + totalTroops } };
  }
  const state = { ...ctx.state, heroes: stateHeroes, regions };
  const staged = totalTroops > 0 && resolvedFaction ? { faction: resolvedFaction, troops: totalTroops, heroIds } : null;
  return { ...ctx, state, staged };
}

function applyHeroDeathRolls(
  heroIds: HeroId[],
  lost: boolean,
  state: GameState,
  rng: RngThread
): { state: GameState; rng: RngThread } {
  if (!lost || heroIds.length === 0) return { state, rng };
  let heroes = state.heroes;
  let r = rng;
  heroIds.forEach((id, idx) => {
    const roll = rollHeroDeath(r.seed, r.cursor, idx === 0, balanceData.combat);
    r = { seed: r.seed, cursor: roll.nextRngCursor };
    if (roll.died && heroes[id]) heroes = { ...heroes, [id]: { ...heroes[id], status: 'dead', location: null } };
  });
  return { state: { ...state, heroes }, rng: r };
}

function applyBattleEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { attacker, defender, region, hero, special, enemyTroops, enemySurvivors } = payload as {
    attacker: FactionId;
    defender: FactionId;
    region?: RegionId;
    hero?: HeroId;
    special?: string;
    enemyTroops?: number;
    enemySurvivors?: number;
  };

  if (special === 'salsu') {
    // 역사 기록의 결과(별동대 궤멸)를 그대로 반영한다. 다회 진군·보급 모델은 5단계에서 구현한다.
    const supplyRatio = enemyTroops ? (enemySurvivors ?? 0) / enemyTroops : 0;
    const state: GameState = {
      ...ctx.state,
      invasionOutcomes: { ...ctx.state.invasionOutcomes, [defender]: { result: 'defeated', at: null, supplyRatio } },
      lastBattle: {
        region: null,
        attackerFaction: attacker,
        defenderFaction: defender,
        winner: 'attacker',
        attackerHeroIds: hero ? [hero] : [],
        defenderHeroIds: [],
        turn: ctx.state.turnNumber
      }
    };
    return { ...ctx, state };
  }

  const attackerHeroIds = ctx.staged && ctx.staged.faction === attacker ? ctx.staged.heroIds : hero ? [hero] : [];
  const attackerTroops = ctx.staged && ctx.staged.faction === attacker ? ctx.staged.troops : 0;
  const targetRegion = region ? ctx.state.regions[region] : null;
  const targetStatic = region ? regionsData.regions.find((r) => r.id === region) : null;
  const defenderHeroId =
    region &&
    Object.values(ctx.state.heroes).find((h) => h.faction === defender && h.status === 'active' && h.location === region)?.id;

  const attackerLeadership = attackerHeroIds.length ? Math.max(...attackerHeroIds.map(heroLeadership)) : NO_COMMANDER_LEADERSHIP;
  const defenderLeadership = defenderHeroId ? heroLeadership(defenderHeroId) : NO_COMMANDER_LEADERSHIP;
  const defenderTerrain =
    targetRegion && targetStatic ? defenderTerrainMultiplier(targetRegion.defense, targetStatic.terrain, balanceData.combat) : 1;

  const outcome = resolveBattle(
    { troops: attackerTroops, leadership: attackerLeadership, morale: ctx.state.factions[attacker]?.morale ?? 1, terrainMultiplier: 1 },
    {
      troops: targetRegion?.garrison ?? 0,
      leadership: defenderLeadership,
      morale: ctx.state.factions[defender]?.morale ?? 1,
      terrainMultiplier: defenderTerrain
    },
    ctx.rng.seed,
    ctx.rng.cursor,
    balanceData.combat
  );
  const rng: RngThread = { seed: ctx.rng.seed, cursor: outcome.nextRngCursor };

  let regions = ctx.state.regions;
  if (targetRegion && region) {
    const defenderLossRatio = outcome.winner === 'attacker' ? outcome.loserLossRatio : outcome.winnerLossRatio;
    const survivors = Math.max(0, Math.round(targetRegion.garrison * (1 - defenderLossRatio)));
    regions = { ...regions, [region]: { ...targetRegion, garrison: survivors } };
  }

  const factions = { ...ctx.state.factions };
  const winnerFaction = outcome.winner === 'attacker' ? attacker : defender;
  const loserFaction = outcome.winner === 'attacker' ? defender : attacker;
  if (factions[winnerFaction]) {
    factions[winnerFaction] = {
      ...factions[winnerFaction],
      cohesion: clamp(factions[winnerFaction].cohesion + balanceData.cohesion.onVictory, balanceData.cohesion.min, balanceData.cohesion.max)
    };
  }
  if (factions[loserFaction]) {
    factions[loserFaction] = {
      ...factions[loserFaction],
      cohesion: clamp(factions[loserFaction].cohesion + balanceData.cohesion.onDefeat, balanceData.cohesion.min, balanceData.cohesion.max)
    };
  }

  const defenderHeroIds = defenderHeroId ? [defenderHeroId] : [];
  const attackerLost = outcome.winner === 'defender';
  const defenderLost = outcome.winner === 'attacker';
  const afterAttackerDeaths = applyHeroDeathRolls(attackerHeroIds, attackerLost, { ...ctx.state, regions, factions }, rng);
  const afterDefenderDeaths = applyHeroDeathRolls(defenderHeroIds, defenderLost, afterAttackerDeaths.state, afterAttackerDeaths.rng);

  const state: GameState = {
    ...afterDefenderDeaths.state,
    rngCursor: afterDefenderDeaths.rng.cursor,
    lastBattle: {
      region: region ?? null,
      attackerFaction: attacker,
      defenderFaction: defender,
      winner: outcome.winner,
      attackerHeroIds,
      defenderHeroIds,
      turn: ctx.state.turnNumber
    }
  };

  return { ...ctx, state, rng: afterDefenderDeaths.rng, staged: null };
}

function applyNavalBattleEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { attacker, defender, region, attackerTroops, defenderTroops } = payload as {
    attacker: FactionId;
    defender: FactionId;
    region: RegionId;
    attackerTroops?: number;
    defenderTroops?: number;
  };
  const outcome = resolveBattle(
    { troops: attackerTroops ?? 0, leadership: NO_COMMANDER_LEADERSHIP, morale: ctx.state.factions[attacker]?.morale ?? 1, terrainMultiplier: 1 },
    {
      troops: defenderTroops ?? attackerTroops ?? 0,
      leadership: NO_COMMANDER_LEADERSHIP,
      morale: ctx.state.factions[defender]?.morale ?? 1,
      terrainMultiplier: 1
    },
    ctx.rng.seed,
    ctx.rng.cursor,
    balanceData.combat
  );
  const rng: RngThread = { seed: ctx.rng.seed, cursor: outcome.nextRngCursor };
  const state: GameState = {
    ...ctx.state,
    rngCursor: outcome.nextRngCursor,
    lastBattle: {
      region,
      attackerFaction: attacker,
      defenderFaction: defender,
      winner: outcome.winner,
      attackerHeroIds: [],
      defenderHeroIds: [],
      turn: ctx.state.turnNumber
    }
  };
  return { ...ctx, state, rng };
}

/**
 * 침공 효과: 지금은 목표 지역에 대한 즉시 전투로 단순화한다.
 * 요서·산동해로 진군, 보급률 감소, 계절별 소모 등 실제 침공 모델은 5단계에서 구현한다.
 */
function applyInvasionEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { faction, troops, target, hero } = payload as { faction: FactionId; troops: number; target: RegionId; hero?: HeroId };
  const targetRegion = ctx.state.regions[target];
  const targetStatic = regionsData.regions.find((r) => r.id === target);
  if (!targetRegion || !targetStatic) return ctx;
  const defenderFaction = targetRegion.owner;
  const leadership = hero ? heroLeadership(hero) : NO_COMMANDER_LEADERSHIP;
  const defenderHeroId = Object.values(ctx.state.heroes).find(
    (h) => h.faction === defenderFaction && h.status === 'active' && h.location === target
  )?.id;
  const defenderLeadership = defenderHeroId ? heroLeadership(defenderHeroId) : NO_COMMANDER_LEADERSHIP;
  const defenderTerrain = defenderTerrainMultiplier(targetRegion.defense, targetStatic.terrain, balanceData.combat);

  const outcome = resolveBattle(
    { troops, leadership, morale: 1, terrainMultiplier: 1 },
    {
      troops: targetRegion.garrison,
      leadership: defenderLeadership,
      morale: ctx.state.factions[defenderFaction]?.morale ?? 1,
      terrainMultiplier: defenderTerrain
    },
    ctx.rng.seed,
    ctx.rng.cursor,
    balanceData.combat
  );
  const rng: RngThread = { seed: ctx.rng.seed, cursor: outcome.nextRngCursor };
  const result = outcome.winner === 'attacker' ? 'victorious' : 'defeated';

  let state: GameState = {
    ...ctx.state,
    rngCursor: outcome.nextRngCursor,
    invasionOutcomes: { ...ctx.state.invasionOutcomes, [faction]: { result, at: target, supplyRatio: 1 } },
    lastBattle: {
      region: target,
      attackerFaction: faction,
      defenderFaction,
      winner: outcome.winner,
      attackerHeroIds: hero ? [hero] : [],
      defenderHeroIds: defenderHeroId ? [defenderHeroId] : [],
      turn: ctx.state.turnNumber
    }
  };

  if (outcome.winner === 'attacker') {
    const survivors = Math.max(0, Math.round(troops * (1 - outcome.winnerLossRatio)));
    state = { ...state, regions: { ...state.regions, [target]: { ...targetRegion, owner: faction, garrison: survivors, project: null } } };
    if (targetStatic.capital) state = checkCapitalCollapse(state, defenderFaction, faction);
  } else {
    const survivors = Math.max(0, Math.round(targetRegion.garrison * (1 - outcome.winnerLossRatio)));
    state = { ...state, regions: { ...state.regions, [target]: { ...targetRegion, garrison: survivors } } };
  }

  return { ...ctx, state, rng };
}

function applyInvasionResultEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { faction, result, at } = payload as { faction: FactionId; result: string; at?: RegionId };
  const prev = ctx.state.invasionOutcomes[faction];
  const invasionOutcomes = {
    ...ctx.state.invasionOutcomes,
    [faction]: { result, at: at ?? prev?.at ?? null, supplyRatio: prev?.supplyRatio ?? 0 }
  };
  return { ...ctx, state: { ...ctx.state, invasionOutcomes } };
}

function applyCivilWarEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { faction, regions } = payload as { faction: FactionId; regions: RegionId[] | string };
  if (!Array.isArray(regions)) return ctx; // "random1" 등 무작위 대상은 5단계에서 구현한다.
  let stateRegions = ctx.state.regions;
  for (const id of regions) {
    const r = stateRegions[id];
    if (r && r.owner === faction) stateRegions = { ...stateRegions, [id]: { ...r, owner: 'rebels', project: null } };
  }
  return { ...ctx, state: { ...ctx.state, regions: stateRegions } };
}

function applyDestroyFactionEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { faction } = payload as { faction: FactionId };
  const fs = ctx.state.factions[faction];
  if (!fs) return ctx;
  return { ...ctx, state: { ...ctx.state, factions: { ...ctx.state.factions, [faction]: { ...fs, destroyed: true } } } };
}

function applySpawnFactionEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { type, faction, region, troops } = payload as { type?: string; faction?: FactionId; region?: RegionId; troops?: number };
  if (type === 'hero' || !faction || !region) return ctx; // 무명 장수 등장(랜덤 이벤트)은 5~6단계에서 구현한다.
  const factions = {
    ...ctx.state.factions,
    [faction]: {
      id: faction,
      gold: 0,
      food: 0,
      cohesion: 50,
      grudge: 0,
      morale: 1,
      actionPoints: balanceData.turn.actionsPerFaction,
      destroyed: false
    }
  };
  const r = ctx.state.regions[region];
  const regions = r ? { ...ctx.state.regions, [region]: { ...r, owner: faction, garrison: troops ?? r.garrison } } : ctx.state.regions;
  return { ...ctx, state: { ...ctx.state, factions, regions } };
}

function applySetJungwonPhaseEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { phase } = payload as { phase: GameState['jungwonPhase'] };
  return { ...ctx, state: { ...ctx.state, jungwonPhase: phase } };
}

function applyRollEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { chance, onSuccess, onFail } = payload as { chance: number; onSuccess?: unknown[]; onFail?: unknown[] };
  const draw = drawChance(ctx.rng);
  const branch = draw.hit(chance) ? onSuccess : onFail;
  const next = { ...ctx, rng: draw.rng };
  return branch ? applyEffects(branch, next) : next;
}

function applyBranchEffect(payload: Record<string, unknown>, ctx: FoldCtx): FoldCtx {
  const { condition, onTrue, onFalse } = payload as { condition: unknown; onTrue?: unknown[]; onFalse?: unknown[] };
  const condCtx: CondCtx = { state: ctx.state, turnStartRegionOwners: ctx.turnStartRegionOwners };
  const res = evalCond(condition, condCtx, ctx.rng);
  const next = { ...ctx, rng: res.rng };
  const branch = res.result ? onTrue : onFalse;
  return branch ? applyEffects(branch, next) : next;
}

function applyEffect(effect: unknown, ctx: FoldCtx): FoldCtx {
  if (typeof effect !== 'object' || effect === null) throw new Error(`효과는 객체여야 한다: ${JSON.stringify(effect)}`);
  const keys = Object.keys(effect as Record<string, unknown>);
  if (keys.length !== 1) throw new Error(`효과 객체는 키를 하나만 가져야 한다: ${JSON.stringify(effect)}`);
  const key = keys[0];
  const payload = (effect as Record<string, unknown>)[key] as Record<string, unknown>;

  switch (key) {
    case 'setFlag': {
      const { flag, value } = payload as { flag: string; value: boolean };
      return { ...ctx, state: { ...ctx.state, flags: { ...ctx.state.flags, [flag]: value } } };
    }
    case 'stat':
      return applyStatEffect(payload, ctx);
    case 'relation':
      return applyRelationEffect(payload, ctx);
    case 'setOwner':
      return applySetOwnerEffect(payload, ctx);
    case 'garrison':
      return applyGarrisonEffect(payload, ctx);
    case 'defense':
      return applyDefenseEffect(payload, ctx);
    case 'killHero':
      return applyKillHeroEffect(payload, ctx);
    case 'setKing':
      return applySetKingEffect(payload, ctx);
    case 'transferHero':
      return applyTransferHeroEffect(payload, ctx);
    case 'army':
      return applyArmyEffect(payload, ctx);
    case 'battle':
      return applyBattleEffect(payload, ctx);
    case 'navalBattle':
      return applyNavalBattleEffect(payload, ctx);
    case 'invasion':
      return applyInvasionEffect(payload, ctx);
    case 'invasionResult':
      return applyInvasionResultEffect(payload, ctx);
    case 'roll':
      return applyRollEffect(payload, ctx);
    case 'branch':
      return applyBranchEffect(payload, ctx);
    case 'requestFrom':
      return ctx; // 외교 요청 AI는 4단계에서 구현한다.
    case 'civilWar':
      return applyCivilWarEffect(payload, ctx);
    case 'destroyFaction':
      return applyDestroyFactionEffect(payload, ctx);
    case 'spawnFaction':
      return applySpawnFactionEffect(payload, ctx);
    case 'setJungwonPhase':
      return applySetJungwonPhaseEffect(payload, ctx);
    default:
      throw new Error(`알 수 없는 효과 키: ${key}`);
  }
}

function applyEffects(effects: unknown[], ctx: FoldCtx): FoldCtx {
  let c = ctx;
  for (const eff of effects) c = applyEffect(eff, c);
  return c;
}

function pickWeightedChoice(
  choices: EventChoice[],
  rngSeed: number,
  rngCursor: number
): { choice: EventChoice; nextRngCursor: number } {
  const specified = choices.map((c) => c.weight).filter((w): w is number => w !== undefined);
  const specifiedSum = specified.reduce((a, b) => a + b, 0);
  const unspecifiedCount = choices.length - specified.length;
  const remaining = Math.max(0, 1 - specifiedSum);
  const perUnspecified = unspecifiedCount > 0 ? remaining / unspecifiedCount : 0;
  const weights = choices.map((c) => c.weight ?? perUnspecified);
  const total = weights.reduce((a, b) => a + b, 0) || 1;

  const draw = nextRandom(rngSeed, rngCursor);
  let acc = 0;
  let chosen = choices[choices.length - 1];
  for (let i = 0; i < choices.length; i++) {
    acc += weights[i] / total;
    if (draw.value < acc) {
      chosen = choices[i];
      break;
    }
  }
  return { choice: chosen, nextRngCursor: draw.nextCursor };
}

function snapshotOwners(state: GameState): Record<RegionId, FactionId> {
  return Object.fromEntries(Object.entries(state.regions).map(([id, r]) => [id, r.owner]));
}

/**
 * 한 턴의 이벤트 한 패스를 진행한다. 플레이어가 결정할 선택지를 만나면 그 자리에서 멈추고
 * pendingChoice를 세워 반환한다(전체화면 팝업으로 이어진다). resolveEventChoice가 이어서 진행한다.
 */
export function processEvents(state: GameState): GameState {
  const turnStartRegionOwners = snapshotOwners(state);
  let current = state;
  let rng: RngThread = { seed: state.rngSeed, cursor: state.rngCursor };
  let index = state.eventCursorIndex;

  while (index < events.length) {
    const ev = events[index];
    if (typeof ev.act !== 'number') {
      index++;
      continue;
    }
    const alreadyFired = ev.once !== false && current.firedEvents[ev.id];
    if (alreadyFired) {
      index++;
      continue;
    }

    const condCtx: CondCtx = { state: current, turnStartRegionOwners };
    const condResult = ev.conditions ? evalCond(ev.conditions, condCtx, rng) : { result: true, rng };
    rng = condResult.rng;
    if (!condResult.result) {
      index++;
      continue;
    }

    if (ev.choices && ev.choices.length > 0) {
      if (ev.decider === current.playerFaction) {
        current = {
          ...current,
          rngSeed: rng.seed,
          rngCursor: rng.cursor,
          eventCursorIndex: index,
          pendingChoice: {
            eventId: ev.id,
            title: ev.title,
            text: ev.text ?? '',
            options: ev.choices.map((c) => ({ id: c.id, label: c.label }))
          }
        };
        return current;
      }
      const pick = pickWeightedChoice(ev.choices, rng.seed, rng.cursor);
      rng = { seed: rng.seed, cursor: pick.nextRngCursor };
      const folded = applyEffects(pick.choice.effects ?? [], { state: current, rng, staged: null, turnStartRegionOwners });
      current = { ...folded.state, firedEvents: { ...folded.state.firedEvents, [ev.id]: true } };
      if (pick.choice.text) current = withChronicleLine(current, pick.choice.text);
      rng = folded.rng;
      index++;
      continue;
    }

    const folded = applyEffects(ev.effects ?? [], { state: current, rng, staged: null, turnStartRegionOwners });
    current = { ...folded.state, firedEvents: { ...folded.state.firedEvents, [ev.id]: true } };
    if (ev.text) current = withChronicleLine(current, ev.text);
    rng = folded.rng;
    index++;
  }

  return { ...current, rngSeed: rng.seed, rngCursor: rng.cursor, eventCursorIndex: index };
}

/** 플레이어가 이벤트 팝업에서 선택지를 고르면 호출한다. 같은 턴의 남은 이벤트를 이어서 처리한다. */
export function resolveEventChoice(state: GameState, choiceId: string): GameState {
  if (!state.pendingChoice) return state;
  const ev = events.find((e) => e.id === state.pendingChoice!.eventId);
  const eventId = state.pendingChoice.eventId;
  let next: GameState = { ...state, pendingChoice: null };

  if (ev?.choices) {
    const choice = ev.choices.find((c) => c.id === choiceId);
    if (choice) {
      const turnStartRegionOwners = snapshotOwners(next);
      const rng: RngThread = { seed: next.rngSeed, cursor: next.rngCursor };
      const folded = applyEffects(choice.effects ?? [], { state: next, rng, staged: null, turnStartRegionOwners });
      next = { ...folded.state, rngSeed: folded.rng.seed, rngCursor: folded.rng.cursor };
      if (choice.text) next = withChronicleLine(next, choice.text);
    }
  }

  next = { ...next, firedEvents: { ...next.firedEvents, [eventId]: true }, eventCursorIndex: state.eventCursorIndex + 1 };
  return processEvents(next);
}
