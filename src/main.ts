import './style.css';
import { conscriptAction, diplomacyAction, domesticAction, fortifyAction, marchAction } from './core/actions';
import { factionsData, regionsData } from './core/data';
import { resolveEventChoice } from './core/events';
import { advanceTurn, createInitialState } from './core/state';
import type { ActionResult } from './core/actions';
import type { GameState, RegionId } from './core/types';
import { createMapView } from './map/svgMap';
import { createBottomSheet } from './ui/bottomSheet';
import { createChroniclePanel } from './ui/chroniclePanel';
import { createEndingBanner } from './ui/endingBanner';
import { createEventPopup } from './ui/eventPopup';
import { createResultPopup } from './ui/resultPopup';
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
const popupEl = document.createElement('div');
const eventPopupEl = document.createElement('div');
const chroniclePanelEl = document.createElement('div');
const endingBannerEl = document.createElement('div');

app.append(topbarEl, mapEl, bottomSheetEl, popupEl, eventPopupEl, chroniclePanelEl, endingBannerEl);

let state: GameState = loadFromLocalStorage() ?? createInitialState(DEFAULT_PLAYER_FACTION, DEFAULT_RNG_SEED);
let selectedRegion: RegionId | null = null;
let marchFrom: RegionId | null = null;

const factionColors = Object.fromEntries(factionsData.factions.map((f) => [f.id, f.color]));
const regionNameById = Object.fromEntries(regionsData.regions.map((r) => [r.id, r.name]));

const resultPopup = createResultPopup(popupEl);
const eventPopup = createEventPopup(eventPopupEl);
const chroniclePanel = createChroniclePanel(chroniclePanelEl);
const endingBanner = createEndingBanner(endingBannerEl);

function refresh() {
  topbar.update(state);
  if (selectedRegion) {
    bottomSheet.show(selectedRegion, state, marchFrom);
  } else {
    bottomSheet.clear();
  }
  mapView.update(state, selectedRegion);
  chroniclePanel.update(state);
  endingBanner.update(state.ending);

  if (state.pendingChoice) {
    eventPopup.show(state.pendingChoice, (choiceId) => {
      state = resolveEventChoice(state, choiceId);
      persistAndRefresh();
    });
  } else {
    eventPopup.hide();
  }
}

function persistAndRefresh() {
  saveToLocalStorage(state);
  refresh();
}

function handleResult(result: ActionResult, chronicleCountBefore: number) {
  if (!result.ok) {
    resultPopup.show('행할 수 없다', [result.reason]);
    return;
  }
  state = result.state;
  const newLines = state.chronicle.slice(chronicleCountBefore).map((c) => c.text);
  resultPopup.show('결과', newLines.length ? newLines : ['별다른 일이 일어나지 않다.']);
  persistAndRefresh();
}

const bottomSheet = createBottomSheet(bottomSheetEl, {
  onConscript(regionId) {
    const before = state.chronicle.length;
    handleResult(conscriptAction(state, state.playerFaction, regionId), before);
  },
  onDomestic(regionId) {
    const before = state.chronicle.length;
    handleResult(domesticAction(state, state.playerFaction, regionId), before);
  },
  onFortify(regionId) {
    const before = state.chronicle.length;
    handleResult(fortifyAction(state, state.playerFaction, regionId), before);
  },
  onMarchBegin(fromRegionId) {
    marchFrom = fromRegionId;
    refresh();
  },
  onMarchTarget(toRegionId) {
    if (!marchFrom) return;
    const source = state.regions[marchFrom];
    const input = window.prompt(
      `${regionNameById[marchFrom]}에서 ${regionNameById[toRegionId]}(으)로 보낼 병력 수를 입력한다 (최대 ${source.garrison.toLocaleString()}).`,
      String(Math.min(1000, source.garrison))
    );
    if (input === null) return;
    const troops = Number(input);
    if (!Number.isFinite(troops) || troops <= 0) {
      resultPopup.show('행할 수 없다', ['올바른 병력 수가 아니다.']);
      return;
    }
    const before = state.chronicle.length;
    const fromRegion = marchFrom;
    marchFrom = null;
    handleResult(
      marchAction(state, { faction: state.playerFaction, fromRegion, toRegion: toRegionId, troops, heroIds: [] }),
      before
    );
  },
  onMarchCancel() {
    marchFrom = null;
    refresh();
  },
  onDiplomacy(targetFaction, kind) {
    const before = state.chronicle.length;
    handleResult(diplomacyAction(state, state.playerFaction, targetFaction, kind), before);
  }
});

const mapView = createMapView(mapEl, factionColors, (regionId) => {
  if (marchFrom) {
    const isValidTarget = regionsData.regions
      .find((r) => r.id === marchFrom)
      ?.adjacent.some((a) => a.to === regionId);
    if (isValidTarget && regionId !== marchFrom) {
      selectedRegion = regionId;
      refresh();
      return;
    }
  }
  selectedRegion = regionId;
  refresh();
});

const topbar = createTopbar(
  topbarEl,
  () => {
    state = advanceTurn(state);
    persistAndRefresh();
  },
  () => {
    chroniclePanel.toggle();
  }
);

refresh();
saveToLocalStorage(state);
