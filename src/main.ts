import './style.css';
import { factionsData } from './core/data';
import { advanceTurn, createInitialState } from './core/state';
import type { GameState, RegionId } from './core/types';
import { createMapView } from './map/svgMap';
import { createBottomSheet } from './ui/bottomSheet';
import { createTopbar } from './ui/topbar';
import { loadFromLocalStorage, saveToLocalStorage } from './ui/storage';

const DEFAULT_PLAYER_FACTION = 'silla';
const DEFAULT_RNG_SEED = 20240101;

const app = document.getElementById('app');
if (!app) throw new Error('#app root element not found');

const topbarEl = document.createElement('div');
const mapEl = document.createElement('div');
mapEl.className = 'map-container';
const bottomSheetEl = document.createElement('div');

app.append(topbarEl, mapEl, bottomSheetEl);

let state: GameState = loadFromLocalStorage() ?? createInitialState(DEFAULT_PLAYER_FACTION, DEFAULT_RNG_SEED);
let selectedRegion: RegionId | null = null;

const factionColors = Object.fromEntries(factionsData.factions.map((f) => [f.id, f.color]));

const bottomSheet = createBottomSheet(bottomSheetEl);

const mapView = createMapView(mapEl, factionColors, (regionId) => {
  selectedRegion = regionId;
  bottomSheet.show(regionId, state);
  mapView.update(state, selectedRegion);
});

const topbar = createTopbar(topbarEl, () => {
  state = advanceTurn(state);
  saveToLocalStorage(state);
  topbar.update(state);
  mapView.update(state, selectedRegion);
});

topbar.update(state);
mapView.update(state, selectedRegion);
saveToLocalStorage(state);
