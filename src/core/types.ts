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

export type BalanceFile = Record<string, unknown>;
export type EventsFile = Record<string, unknown>;

/** Mutable per-region game state (a copy derived from RegionData). */
export interface RegionState {
  id: RegionId;
  owner: FactionId;
  garrison: number;
  defense: number;
  pop: number;
  food: number;
}

/** Mutable per-faction game state (a copy derived from FactionData). */
export interface FactionState {
  id: FactionId;
  gold: number;
  food: number;
  cohesion: number;
  grudge: number;
}

export interface RelationState {
  a: FactionId;
  b: FactionId;
  value: number;
}

export interface GameState {
  turnNumber: number;
  year: number;
  season: Season;
  regions: Record<RegionId, RegionState>;
  factions: Record<FactionId, FactionState>;
  relations: RelationState[];
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
