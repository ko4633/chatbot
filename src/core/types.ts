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
}

export interface RelationState {
  a: FactionId;
  b: FactionId;
  value: number;
}

/** 영웅의 가변 상태: 위치와 생존 여부. 능력치·생몰연도 등 불변값은 heroesData에서 읽는다. */
export interface HeroState {
  id: HeroId;
  faction: FactionId;
  location: RegionId | null;
  alive: boolean;
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
