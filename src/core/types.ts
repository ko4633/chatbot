export type Season = 'spring' | 'summer' | 'autumn' | 'winter';

export type FactionId = string;
export type RegionId = string;
export type HeroId = string;

export type AdjacencyType = 'land' | 'sea';

export interface RegionAdjacency {
  to: RegionId;
  type: AdjacencyType;
}

export type Terrain = 'capital' | 'castle' | 'port' | 'pass' | 'external';

export interface RegionData {
  id: RegionId;
  name: string;
  modernName: string;
  owner: FactionId;
  terrain: Terrain;
  capital: boolean;
  garrison: number;
  defense: number;
  pop: number;
  food: number;
  x: number;
  y: number;
  adjacent: RegionAdjacency[];
}

export interface RegionsFile {
  startYear: number;
  startSeason: Season;
  regions: RegionData[];
}

export interface FactionData {
  id: FactionId;
  name: string;
  color: string;
  playable: boolean;
  capital: RegionId | null;
  gold: number;
  food: number;
  cohesion: number;
  grudge?: number;
  traits?: string[];
  notes?: string;
}

export interface FactionRelation {
  a: FactionId;
  b: FactionId;
  value: number;
}

export interface FactionsFile {
  factions: FactionData[];
  initialRelations: FactionRelation[];
}

export interface HeroData {
  id: HeroId;
  name: string;
  faction: FactionId;
  appearYear: number;
  exitYear: number;
  isKing: boolean;
  leadership: number;
  power: number;
  intellect: number;
  politics: number;
  traits: string[];
  historicalDeathYear: number | null;
}

export interface HeroesFile {
  heroes: HeroData[];
}

export type EventsFile = Record<string, unknown>;

export type ProjectKind = 'domestic' | 'fortify';

export interface RegionProject {
  kind: ProjectKind;
  faction: FactionId;
  remainingTurns: number;
}

/** Mutable per-region game state (a copy derived from RegionData). */
export interface RegionState {
  id: RegionId;
  owner: FactionId;
  garrison: number;
  defense: number;
  pop: number;
  food: number;
  project: RegionProject | null;
}

/** Mutable per-faction game state (a copy derived from FactionData). */
export interface FactionState {
  id: FactionId;
  gold: number;
  food: number;
  cohesion: number;
  grudge: number;
  morale: number;
  actionPoints: number;
  destroyed: boolean;
}

export interface RelationState {
  a: FactionId;
  b: FactionId;
  value: number;
}

/** 영웅의 생애 단계: 아직 등장 전 / 활동 중 / 퇴장(사망 등). */
export type HeroStatus = 'unborn' | 'active' | 'dead';

/** 영웅의 가변 상태: 위치와 생애 단계. 능력치·생몰연도 등 불변값은 heroesData에서 읽는다. */
export interface HeroState {
  id: HeroId;
  faction: FactionId;
  location: RegionId | null;
  status: HeroStatus;
  /** 이 판에서 죽은 연도·계절·원인. 자연 퇴장(전역)은 원인을 남기지 않는다("내 역사 vs 실제 역사" 화면용). */
  deathYear: number | null;
  deathSeason: Season | null;
  deathCause: string | null;
}

export interface SiegeState {
  id: string;
  region: RegionId;
  attacker: FactionId;
  defender: FactionId;
  attackerTroops: number;
  attackerHeroes: HeroId[];
  foodTurnsRemaining: number;
  startedTurn: number;
}

export type JungwonPhase = 'namboekjo' | 'sui' | 'tang';

export interface LastBattleInfo {
  region: RegionId | null;
  attackerFaction: FactionId;
  defenderFaction: FactionId;
  winner: 'attacker' | 'defender';
  attackerHeroIds: HeroId[];
  defenderHeroIds: HeroId[];
  turn: number;
}

export interface InvasionOutcome {
  result: string;
  at: RegionId | null;
  supplyRatio: number;
}

export type InvasionRoute = 'yoseo' | 'sandonghaero';

/** 진행 중인 외부 침공(요서·산동해로에서 목표로 진군하는 군단). CLAUDE.md "외부 세력" 절. */
export interface InvasionState {
  id: string;
  faction: FactionId;
  hero: HeroId | null;
  route: InvasionRoute;
  target: RegionId;
  path: RegionId[];
  stepIndex: number;
  troops: number;
  initialTroops: number;
  supplyRatio: number;
  turnsElapsed: number;
  summerExtraAttrition: boolean;
  startedTurn: number;
}

export interface PendingChoiceOption {
  id: string;
  label: string;
}

export interface PendingChoice {
  eventId: string;
  title: string;
  text: string;
  options: PendingChoiceOption[];
}

export interface GameState {
  turnNumber: number;
  year: number;
  season: Season;
  regions: Record<RegionId, RegionState>;
  factions: Record<FactionId, FactionState>;
  relations: RelationState[];
  heroes: Record<HeroId, HeroState>;
  sieges: SiegeState[];
  playerFaction: FactionId;
  rngSeed: number;
  rngCursor: number;
  flags: Record<string, boolean>;
  chronicle: ChronicleEntry[];
  jungwonPhase: JungwonPhase;
  firedEvents: Record<string, boolean>;
  eventCursorIndex: number;
  pendingChoice: PendingChoice | null;
  lastBattle: LastBattleInfo | null;
  invasionOutcomes: Record<FactionId, InvasionOutcome>;
  invasions: InvasionState[];
  ending: string | null;
  /** 직전 턴이 끝났을 때의 지역 소유. captured 조건이 "그 사이 바뀌었는가"를 판정하는 기준이다. */
  previousRegionOwners: Record<RegionId, FactionId>;
}

export interface ChronicleEntry {
  year: number;
  season: Season;
  text: string;
}

export const SEASON_ORDER: Season[] = ['spring', 'summer', 'autumn', 'winter'];

export const SEASON_LABEL: Record<Season, string> = {
  spring: '봄',
  summer: '여름',
  autumn: '가을',
  winter: '겨울'
};
