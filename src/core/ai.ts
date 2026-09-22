import { conscriptAction, domesticAction, fortifyAction, marchAction } from './actions';
import { balanceData } from './balance';
import { factionsData, regionsData } from './data';
import { getRelationValue } from './events';
import type { ActionResult } from './actions';
import type { FactionId, GameState, HeroId, RegionData, RegionId } from './types';

/**
 * 규칙 기반 AI (CLAUDE.md 4단계): 방어 우선 → 약한 인접 적 공격 → 내정.
 * 플레이어와 같은 actions.ts 함수만 사용한다(보정 금지 원칙).
 */

function defenderEffectivePower(garrison: number, defense: number): number {
  return garrison * (1 + balanceData.combat.castleDefenseBonusPerDefenseGrade * defense);
}

function ownedRegions(state: GameState, faction: FactionId): RegionData[] {
  return regionsData.regions.filter((r) => r.terrain !== 'external' && state.regions[r.id]?.owner === faction);
}

function heroesAt(state: GameState, faction: FactionId, region: RegionId): HeroId[] {
  return Object.values(state.heroes)
    .filter((h) => h.faction === faction && h.status === 'active' && h.location === region)
    .slice(0, balanceData.turn.maxHeroesPerCampaign)
    .map((h) => h.id);
}

/** 이 지역을 노리는 적의 위협도(인접한 비동맹 적 지역의 유효 방어력 합)를 어림한다. */
function threatScore(state: GameState, faction: FactionId, region: RegionData): number {
  let threat = 0;
  for (const adj of region.adjacent) {
    if (adj.type !== 'land') continue;
    const target = state.regions[adj.to];
    const targetStatic = regionsData.regions.find((r) => r.id === adj.to);
    if (!target || !targetStatic || targetStatic.terrain === 'external') continue;
    if (target.owner === faction) continue;
    if (getRelationValue(state, faction, target.owner) >= balanceData.diplomacy.allianceThreshold) continue;
    threat += defenderEffectivePower(target.garrison, target.defense);
  }
  return threat;
}

/** 방어 우선: 포위당했거나 위협받는 지역을 징병 또는 축성으로 보강한다. */
function tryDefend(state: GameState, faction: FactionId, owned: RegionData[]): ActionResult | null {
  const besiegedIds = state.sieges
    .filter((s) => s.defender === faction)
    .sort((a, b) => b.attackerTroops - a.attackerTroops)
    .map((s) => s.region);

  const threatened = owned
    .map((r) => ({ r, threat: threatScore(state, faction, r) }))
    .filter(({ r, threat }) => threat > defenderEffectivePower(state.regions[r.id].garrison, state.regions[r.id].defense) * balanceData.ai.defenseThreatMarginRatio)
    .sort((a, b) => b.threat - a.threat)
    .map(({ r }) => r.id);

  for (const regionId of [...besiegedIds, ...threatened]) {
    const region = state.regions[regionId];
    if (!region || region.project) continue;
    if (balanceData.turn.conscriptionSeasons.includes(state.season)) {
      const result = conscriptAction(state, faction, regionId);
      if (result.ok) return result;
    }
    const result = fortifyAction(state, faction, regionId);
    if (result.ok) return result;
  }
  return null;
}

/** 약한 인접 적 공격: 아군 병력이 목표의 유효 방어력을 넉넉히 웃돌 때만 출진한다. */
function tryAttack(state: GameState, faction: FactionId, owned: RegionData[]): ActionResult | null {
  for (const region of owned) {
    const source = state.regions[region.id];
    if (source.garrison <= balanceData.ai.minGarrisonReserve) continue;

    for (const adj of region.adjacent) {
      if (adj.type !== 'land') continue;
      const targetStatic = regionsData.regions.find((r) => r.id === adj.to);
      const target = state.regions[adj.to];
      if (!targetStatic || !target || targetStatic.terrain === 'external') continue;
      if (target.owner === faction) continue;
      if (getRelationValue(state, faction, target.owner) >= balanceData.diplomacy.allianceThreshold) continue;

      const targetEffective = defenderEffectivePower(target.garrison, target.defense);
      if (source.garrison <= targetEffective * balanceData.ai.attackPowerMarginRatio) continue;

      const troops = Math.round(source.garrison * balanceData.ai.attackTroopCommitRatio);
      if (troops <= 0) continue;
      const heroIds = heroesAt(state, faction, region.id);
      const result = marchAction(state, { faction, fromRegion: region.id, toRegion: adj.to, troops, heroIds });
      if (result.ok) return result;
    }
  }
  return null;
}

/** 내정: 아직 여지가 있고(공사 중이 아니고) pop·food가 상한 미만인 지역을 개발한다. */
function tryDevelop(state: GameState, faction: FactionId, owned: RegionData[]): ActionResult | null {
  const candidate = owned.find((r) => {
    const region = state.regions[r.id];
    return !region.project && (region.pop < 6 || region.food < 6);
  });
  if (!candidate) return null;
  const result = domesticAction(state, faction, candidate.id);
  return result.ok ? result : null;
}

function aiTakeOneAction(state: GameState, faction: FactionId): ActionResult | null {
  const owned = ownedRegions(state, faction);
  if (owned.length === 0) return null;
  return tryDefend(state, faction, owned) ?? tryAttack(state, faction, owned) ?? tryDevelop(state, faction, owned);
}

function aiTakeFactionTurn(state: GameState, faction: FactionId): GameState {
  let current = state;
  let guard = current.factions[faction]?.actionPoints ?? 0;
  while (guard > 0 && (current.factions[faction]?.actionPoints ?? 0) > 0) {
    const result = aiTakeOneAction(current, faction);
    if (!result || !result.ok) break;
    current = result.state;
    guard--;
  }
  return current;
}

/** 요서·산동해로·왜는 영토 확장 AI가 없다(설계 "외부 세력" 절). 그 외 비플레이어 세력만 행동한다. */
function aiControlledFactionIds(state: GameState): FactionId[] {
  return factionsData.factions
    .filter((f) => f.id !== 'jungwon' && f.id !== 'wa')
    .map((f) => f.id)
    .filter((id) => id !== state.playerFaction && !state.factions[id]?.destroyed);
}

export function aiTakeAllTurns(state: GameState): GameState {
  let current = state;
  for (const faction of aiControlledFactionIds(current)) {
    current = aiTakeFactionTurn(current, faction);
  }
  return current;
}
