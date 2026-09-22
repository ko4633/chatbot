import { factionsData, heroesData } from '../core/data';
import type { GameState } from '../core/types';

const SEASON_LABEL_KO: Record<string, string> = { spring: '봄', summer: '여름', autumn: '가을', winter: '겨울' };

const CAUSE_LABEL: Record<string, string> = {
  ambush: '매복',
  arrow: '화살',
  singleCharge: '단신 돌격',
  battle: '전투'
};

export interface HistoryCompareHandle {
  show(state: GameState): void;
  hide(): void;
}

/**
 * "내 역사 vs 실제 역사" 비교 화면(설계 7단계). 엔딩 후에만 연다.
 * 왕·역사에 사망 연도가 남은 인물의 이 판 결과를 실제 역사 기록과 나란히 보여준다.
 * 서술은 상태값을 조립한 고정 템플릿 문장만 쓴다(원칙 4 — 즉흥 문장 생성 금지).
 */
export function createHistoryCompare(container: HTMLElement): HistoryCompareHandle {
  container.className = 'history-compare-backdrop hidden';
  const scroll = document.createElement('div');
  scroll.className = 'history-compare-scroll';
  const h2 = document.createElement('h2');
  h2.textContent = '내 역사 vs 실제 역사';
  const list = document.createElement('div');
  list.className = 'history-compare-list';
  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.textContent = '닫기';
  closeBtn.addEventListener('click', () => container.classList.add('hidden'));
  scroll.append(h2, list, closeBtn);
  container.appendChild(scroll);
  container.addEventListener('click', (e) => {
    if (e.target === container) container.classList.add('hidden');
  });

  function factionName(id: string): string {
    return factionsData.factions.find((f) => f.id === id)?.name ?? id;
  }

  function show(state: GameState) {
    const rows = heroesData.heroes.filter((h) => h.isKing || h.historicalDeathYear !== null);
    list.innerHTML = '';
    for (const h of rows) {
      const hs = state.heroes[h.id];
      const row = document.createElement('div');
      row.className = 'history-compare-row';

      const nameEl = document.createElement('div');
      nameEl.className = 'history-compare-name';
      nameEl.textContent = `${h.name} (${factionName(h.faction)})`;

      const mineEl = document.createElement('div');
      mineEl.className = 'history-compare-mine';
      if (!hs || hs.status !== 'dead') {
        mineEl.textContent = `이 판: 700년까지 생존하다.`;
      } else if (hs.deathCause) {
        const causeLabel = CAUSE_LABEL[hs.deathCause] ?? hs.deathCause;
        mineEl.textContent = `이 판: ${hs.deathYear}년 ${SEASON_LABEL_KO[hs.deathSeason ?? 'spring']}, ${causeLabel}(으)로 목숨을 잃다.`;
      } else {
        mineEl.textContent = `이 판: ${hs.deathYear}년 ${SEASON_LABEL_KO[hs.deathSeason ?? 'spring']}, 그 소임을 마치고 물러나다.`;
      }

      const realEl = document.createElement('div');
      realEl.className = 'history-compare-real';
      realEl.textContent =
        h.historicalDeathYear !== null ? `실제 역사: ${h.historicalDeathYear}년 사망.` : '실제 역사: 기록된 사망 연도 없음.';

      row.append(nameEl, mineEl, realEl);
      list.appendChild(row);
    }
    container.classList.remove('hidden');
  }

  function hide() {
    container.classList.add('hidden');
  }

  return { show, hide };
}
