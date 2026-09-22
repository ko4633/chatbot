import balanceJson from '../../data/balance.json';

/**
 * balance.json의 타입이 부여된 뷰. 튜닝 수치는 전부 이 파일에서만 읽는다(하드코딩 금지).
 */
export interface BalanceData {
  turn: {
    actionsPerFaction: number;
    conscriptionSeasons: string[];
    conscriptionPopMultiplier: number;
    domesticStatBonus: number;
    domesticDurationTurns: number;
    fortifyDefenseBonus: number;
    fortifyDurationTurns: number;
    maxHeroesPerCampaign: number;
    winterCampaignLossRatio: number;
  };
  economy: {
    autumnHarvestFoodPerFoodGrade: number;
    autumnHarvestCohesionBaseline: number;
    autumnHarvestCohesionDivisor: number;
    goldPerPopGradePerTurn: number;
    upkeepFoodPer1000Troops: number;
    upkeepGoldPer1000Troops: number;
    zeroFoodMoraleMultiplier: number;
    zeroFoodCohesionPerTurn: number;
  };
  cohesion: {
    min: number;
    max: number;
    onVictory: number;
    onDefeat: number;
    onCapitalFall: number;
    onKingDeath: number;
    onTerritoryLost: number;
    revoltThreshold: number;
    civilWarThreshold: number;
  };
  grudge: {
    min: number;
    max: number;
    highThreshold: number;
    highMoraleBonusVsSilla: number;
    highBlocksPeaceWithSilla: boolean;
    highJungwonRelationPerTurn: number;
  };
  combat: {
    leadershipBase: number;
    leadershipDivisor: number;
    moraleMin: number;
    moraleMax: number;
    rngMin: number;
    rngMax: number;
    largeArmyThreshold: number;
    largeArmyExponent: number;
    castleDefenseBonusPerDefenseGrade: number;
    passDefenseMultiplier: number;
    riverOrSeaCrossingAttackMultiplier: number;
    winterAttackMultiplier: number;
    loserLossMin: number;
    loserLossMax: number;
    heroDeathChanceOnDefeat: number;
    commanderDeathChanceOnDefeat: number;
  };
  siege: {
    assaultPowerRatio: number;
    assaultAttackerLossPerAttempt: number;
    siegeDefenderAttritionPerTurn: number;
    siegeFoodTurnsPerFoodGrade: number;
    capitalFallCohesionPenalty: number;
  };
  diplomacy: {
    min: number;
    max: number;
    allianceThreshold: number;
    warThreshold: number;
    brokenAllianceRelationPenaltyAll: number;
    hanRiverRouteJungwonDiplomacyCostMultiplier: number;
    envoyRelationDelta: number;
    tributeGoldCost: number;
    tributeRelationDelta: number;
    allianceProposalReceptivenessMargin: number;
  };
  ai: {
    defenseThreatMarginRatio: number;
    attackPowerMarginRatio: number;
    attackTroopCommitRatio: number;
    minGarrisonReserve: number;
  };
  invasion: Record<string, number>;
  randomEvents: Record<string, unknown>;
  endingTargets: Record<string, unknown>;
}

export const balanceData = balanceJson as unknown as BalanceData;
