import { balanceData } from '../core/balance';
import { factionsData, heroesData, regionsData } from '../core/data';
import { getRelationValue } from '../core/events';
import type { DiplomacyKind } from '../core/actions';
import type { FactionId, GameState, HeroId, RegionId } from '../core/types';

export interface BottomSheetHandlers {
  onConscript(regionId: RegionId): void;
  onDomestic(regionId: RegionId): void;
  onFortify(regionId: RegionId): void;
  onMarchBegin(fromRegionId: RegionId): void;
  onMarchTarget(toRegionId: RegionId, troops: number, heroIds: HeroId[]): void;
  onMarchCancel(): void;
  onDiplomacy(targetFaction: FactionId, kind: DiplomacyKind): void;
}

const DIPLOMACY_LABEL: Record<DiplomacyKind, string> = {
  envoy: '사신',
  tribute: '조공',
  allianceProposal: '동맹 제안',
  declareWar: '선전포고'
};

export interface BottomSheetHandle {
  show(regionId: RegionId, state: GameState, marchFrom: RegionId | null): void;
  clear(): void;
}

const TERRAIN_LABEL: Record<string, string> = {
  capital: '수도',
  castle: '성',
  port: '항구',
  pass: '고개',
  external: '외부'
};

export function createBottomSheet(container: HTMLElement, handlers: BottomSheetHandlers): BottomSheetHandle {
  container.className = 'bottom-sheet empty';
  container.textContent = '지역을 눌러 정보를 확인한다.';

  const byId = Object.fromEntries(regionsData.regions.map((r) => [r.id, r]));
  const factionById = Object.fromEntries(factionsData.factions.map((f) => [f.id, f]));
  // 출진 중 고른 영웅(최대 3명, 설계 "출진(인접 지역, 영웅 최대 3명)"). 출진 시작 지역이 바뀌면 비운다.
  let selectedMarchHeroIds: HeroId[] = [];
  let selectedMarchFrom: RegionId | null = null;

  function heroesStationedAt(state: GameState, regionId: RegionId) {
    return heroesData.heroes.filter((h) => state.heroes[h.id]?.status === 'active' && state.heroes[h.id]?.location === regionId);
  }

  function show(regionId: RegionId, state: GameState, marchFrom: RegionId | null) {
    if (marchFrom !== selectedMarchFrom) {
      selectedMarchHeroIds = [];
      selectedMarchFrom = marchFrom;
    }
    const staticRegion = byId[regionId];
    const dynamic = state.regions[regionId];
    if (!staticRegion || !dynamic) return;
    container.className = 'bottom-sheet';

    const owner = factionById[dynamic.owner];
    const adjacentNames = staticRegion.adjacent
      .map((a) => `${byId[a.to]?.name ?? a.to}${a.type === 'sea' ? '(해로)' : ''}`)
      .join(', ');

    const isPlayerOwned = dynamic.owner === state.playerFaction;
    const ap = state.factions[state.playerFaction]?.actionPoints ?? 0;
    const isMarching = marchFrom === regionId;
    const isMarchTarget =
      marchFrom !== null &&
      marchFrom !== regionId &&
      byId[marchFrom]?.adjacent.some((a) => a.to === regionId);
    const stationedHeroes = heroesStationedAt(state, regionId);

    container.innerHTML = `
      <h2>${staticRegion.name}${staticRegion.modernName ? `<small> (${staticRegion.modernName})</small>` : ''}</h2>
      <dl>
        <dt>세력</dt><dd>${owner?.name ?? dynamic.owner}</dd>
        <dt>지형</dt><dd>${TERRAIN_LABEL[staticRegion.terrain] ?? staticRegion.terrain}</dd>
        <dt>수비</dt><dd>${dynamic.garrison.toLocaleString()}</dd>
        <dt>성벽</dt><dd>${dynamic.defense}</dd>
        <dt>인구</dt><dd>${dynamic.pop}등급</dd>
        <dt>생산</dt><dd>${dynamic.food}등급</dd>
        ${dynamic.project ? `<dt>공사</dt><dd>${dynamic.project.kind === 'domestic' ? '내정' : '축성'} (${dynamic.project.remainingTurns}턴 남음)</dd>` : ''}
        ${stationedHeroes.length ? `<dt>주둔 영웅</dt><dd>${stationedHeroes.map((h) => h.name).join(', ')}</dd>` : ''}
      </dl>
      <div class="adjacent-list">인접: ${adjacentNames || '없음'}</div>
      ${
        isPlayerOwned || marchFrom || (owner && !isPlayerOwned)
          ? `<div class="action-points">행동력 ${ap} / ${balanceData.turn.actionsPerFaction}</div><div class="action-panel"></div>`
          : ''
      }
    `;

    const panel = container.querySelector('.action-panel');
    if (!panel) return;

    if (marchFrom) {
      if (isMarchTarget) {
        const sourceGarrison = state.regions[marchFrom]?.garrison ?? 0;
        const sourceName = byId[marchFrom]?.name ?? marchFrom;

        const availableNote = document.createElement('div');
        availableNote.className = 'march-available-note';
        availableNote.textContent = `${sourceName}의 가용 병력: ${sourceGarrison.toLocaleString()}`;
        panel.appendChild(availableNote);

        const troopsInput = document.createElement('input');
        troopsInput.type = 'number';
        troopsInput.min = '1';
        troopsInput.max = String(sourceGarrison);
        troopsInput.step = '100';
        troopsInput.value = String(Math.min(1000, sourceGarrison));
        troopsInput.className = 'march-troops-input';
        panel.appendChild(troopsInput);

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = `이곳으로 출진`;
        btn.addEventListener('click', () => {
          const troops = Number(troopsInput.value);
          if (!Number.isFinite(troops) || troops <= 0) return;
          handlers.onMarchTarget(regionId, Math.min(troops, sourceGarrison), selectedMarchHeroIds);
        });
        panel.appendChild(btn);
      }
      const cancelBtn = document.createElement('button');
      cancelBtn.type = 'button';
      cancelBtn.textContent = '출진 취소';
      cancelBtn.addEventListener('click', () => handlers.onMarchCancel());
      panel.appendChild(cancelBtn);
      if (isMarching) {
        const availableHeroes = heroesStationedAt(state, marchFrom).filter((h) => h.faction === state.playerFaction);
        if (availableHeroes.length) {
          const heroPicker = document.createElement('div');
          heroPicker.className = 'march-hero-picker';
          for (const h of availableHeroes) {
            const label = document.createElement('label');
            label.className = 'march-hero-option';
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = selectedMarchHeroIds.includes(h.id);
            checkbox.disabled = !checkbox.checked && selectedMarchHeroIds.length >= balanceData.turn.maxHeroesPerCampaign;
            checkbox.addEventListener('change', () => {
              selectedMarchHeroIds = checkbox.checked
                ? [...selectedMarchHeroIds, h.id]
                : selectedMarchHeroIds.filter((id) => id !== h.id);
              show(regionId, state, marchFrom);
            });
            label.append(checkbox, document.createTextNode(` ${h.name}`));
            heroPicker.appendChild(label);
          }
          panel.appendChild(heroPicker);
        }
        const note = document.createElement('div');
        note.textContent = '인접 지역을 눌러 목표를 고른다.';
        note.style.fontSize = '12px';
        note.style.opacity = '0.7';
        panel.appendChild(note);
      }
      return;
    }

    if (!isPlayerOwned) {
      if (!owner || dynamic.owner === state.playerFaction) return;
      const relation = getRelationValue(state, state.playerFaction, dynamic.owner);
      const relationNote = document.createElement('div');
      relationNote.className = 'action-points';
      relationNote.textContent = `${owner.name} 관계: ${relation}`;
      panel.parentElement?.insertBefore(relationNote, panel);

      (Object.keys(DIPLOMACY_LABEL) as DiplomacyKind[]).forEach((kind) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = DIPLOMACY_LABEL[kind];
        btn.disabled = ap <= 0;
        btn.addEventListener('click', () => handlers.onDiplomacy(dynamic.owner, kind));
        panel.appendChild(btn);
      });
      return;
    }

    const conscriptBtn = document.createElement('button');
    conscriptBtn.type = 'button';
    conscriptBtn.textContent = '징병';
    conscriptBtn.disabled = ap <= 0;
    conscriptBtn.addEventListener('click', () => handlers.onConscript(regionId));

    const domesticBtn = document.createElement('button');
    domesticBtn.type = 'button';
    domesticBtn.textContent = '내정';
    domesticBtn.disabled = ap <= 0 || !!dynamic.project;
    domesticBtn.addEventListener('click', () => handlers.onDomestic(regionId));

    const fortifyBtn = document.createElement('button');
    fortifyBtn.type = 'button';
    fortifyBtn.textContent = '축성';
    fortifyBtn.disabled = ap <= 0 || !!dynamic.project;
    fortifyBtn.addEventListener('click', () => handlers.onFortify(regionId));

    const marchBtn = document.createElement('button');
    marchBtn.type = 'button';
    marchBtn.textContent = '출진';
    marchBtn.disabled = ap <= 0;
    marchBtn.addEventListener('click', () => handlers.onMarchBegin(regionId));

    panel.append(conscriptBtn, domesticBtn, fortifyBtn, marchBtn);
  }

  function clear() {
    container.className = 'bottom-sheet empty';
    container.textContent = '지역을 눌러 정보를 확인한다.';
  }

  return { show, clear };
}
