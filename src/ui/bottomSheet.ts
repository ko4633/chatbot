import { factionsData, regionsData } from '../core/data';
import type { GameState, RegionId } from '../core/types';

export interface BottomSheetHandle {
  show(regionId: RegionId, state: GameState): void;
  clear(): void;
}

const TERRAIN_LABEL: Record<string, string> = {
  capital: '수도',
  castle: '성',
  port: '항구',
  pass: '고개',
  external: '외부'
};

export function createBottomSheet(container: HTMLElement): BottomSheetHandle {
  container.className = 'bottom-sheet empty';
  container.textContent = '지역을 눌러 정보를 확인한다.';

  const byId = Object.fromEntries(regionsData.regions.map((r) => [r.id, r]));
  const factionById = Object.fromEntries(factionsData.factions.map((f) => [f.id, f]));

  function show(regionId: RegionId, state: GameState) {
    const staticRegion = byId[regionId];
    const dynamic = state.regions[regionId];
    if (!staticRegion || !dynamic) return;
    container.className = 'bottom-sheet';

    const owner = factionById[dynamic.owner];
    const adjacentNames = staticRegion.adjacent
      .map((a) => `${byId[a.to]?.name ?? a.to}${a.type === 'sea' ? '(해로)' : ''}`)
      .join(', ');

    container.innerHTML = `
      <h2>${staticRegion.name}${staticRegion.modernName ? `<small> (${staticRegion.modernName})</small>` : ''}</h2>
      <dl>
        <dt>세력</dt><dd>${owner?.name ?? dynamic.owner}</dd>
        <dt>지형</dt><dd>${TERRAIN_LABEL[staticRegion.terrain] ?? staticRegion.terrain}</dd>
        <dt>수비</dt><dd>${dynamic.garrison.toLocaleString()}</dd>
        <dt>성벽</dt><dd>${dynamic.defense}</dd>
        <dt>인구</dt><dd>${dynamic.pop}등급</dd>
        <dt>생산</dt><dd>${dynamic.food}등급</dd>
      </dl>
      <div class="adjacent-list">인접: ${adjacentNames || '없음'}</div>
    `;
  }

  function clear() {
    container.className = 'bottom-sheet empty';
    container.textContent = '지역을 눌러 정보를 확인한다.';
  }

  return { show, clear };
}
