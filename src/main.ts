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
import { createFactionSelect } from './ui/factionSelect';
import { createHeroPanel } from './ui/heroPanel';
import { createHistoryCompare } from './ui/historyCompare';
import { createResultPopup } from './ui/resultPopup';
import { createSound } from './ui/sound';
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
const heroPanelEl = document.createElement('div');
const endingBannerEl = document.createElement('div');
const historyCompareEl = document.createElement('div');
const factionSelectEl = document.createElement('div');

app.append(
  topbarEl,
  mapEl,
  bottomSheetEl,
  popupEl,
  eventPopupEl,
  chroniclePanelEl,
  heroPanelEl,
  endingBannerEl,
  historyCompareEl,
  factionSelectEl
);

const existingSave = loadFromLocalStorage();
let state: GameState = existingSave ?? createInitialState(DEFAULT_PLAYER_FACTION, DEFAULT_RNG_SEED);
let selectedRegion: RegionId | null = null;
let marchFrom: RegionId | null = null;

const factionColors = Object.fromEntries(factionsData.factions.map((f) => [f.id, f.color]));

const resultPopup = createResultPopup(popupEl);
const eventPopup = createEventPopup(eventPopupEl);
const chroniclePanel = createChroniclePanel(chroniclePanelEl);
const heroPanel = createHeroPanel(heroPanelEl);
const historyCompare = createHistoryCompare(historyCompareEl);
const endingBanner = createEndingBanner(endingBannerEl, () => historyCompare.show(state));
const factionSelect = createFactionSelect(factionSelectEl);
const sound = createSound();

function battleKey(lb: GameState['lastBattle']): string | null {
  if (!lb) return null;
  return `${lb.turn}|${lb.region}|${lb.attackerFaction}|${lb.defenderFaction}|${lb.winner}`;
}
let lastSeenBattleKey: string | null = battleKey(state.lastBattle);
let lastSeenEnding: string | null = state.ending;

function playBattleEffectsIfNew() {
  const key = battleKey(state.lastBattle);
  if (key && key !== lastSeenBattleKey && state.lastBattle) {
    const { region, attackerFaction, defenderFaction, winner } = state.lastBattle;
    if (region) {
      mapView.playBattleAnimation(region, factionColors[attackerFaction] ?? '#888888', factionColors[defenderFaction] ?? '#888888', winner);
    }
    sound.playClash();
    if (winner === 'attacker') sound.playVictory();
    else sound.playDefeat();
  }
  lastSeenBattleKey = key;

  if (state.ending && state.ending !== lastSeenEnding) {
    sound.playVictory();
  }
  lastSeenEnding = state.ending;
}

function refresh() {
  topbar.update(state);
  if (selectedRegion) {
    bottomSheet.show(selectedRegion, state, marchFrom);
  } else {
    bottomSheet.clear();
  }
  mapView.update(state, selectedRegion);
  chroniclePanel.update(state);
  heroPanel.update(state);
  endingBanner.update(state.ending);
  playBattleEffectsIfNew();

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
  onMarchTarget(toRegionId, troops, heroIds) {
    if (!marchFrom) return;
    const before = state.chronicle.length;
    const fromRegion = marchFrom;
    marchFrom = null;
    handleResult(
      marchAction(state, { faction: state.playerFaction, fromRegion, toRegion: toRegionId, troops, heroIds }),
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

// 지도 초기 확대 계산이 실제 크기를 읽기 전에 상단바가 먼저 (두 줄로 접힐 수도 있는) 자기 높이를
// 확정 짓도록, 지도보다 먼저 만든다.
const topbar = createTopbar(
  topbarEl,
  () => {
    state = advanceTurn(state);
    persistAndRefresh();
  },
  () => {
    chroniclePanel.toggle();
  },
  () => {
    heroPanel.toggle();
  }
);
// 지도가 상단바의 최종 높이(두 줄로 접힐 수도 있음)를 보고 초기 확대를 계산하도록, 실제 글자를
// 먼저 채워 둔다(마지막 진짜 refresh()가 다시 그려도 무해하다).
topbar.update(state);

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

if (existingSave) {
  refresh();
  saveToLocalStorage(state);
} else {
  factionSelect.show((factionId) => {
    state = createInitialState(factionId, Date.now());
    factionSelect.hide();
    persistAndRefresh();
  });
}
