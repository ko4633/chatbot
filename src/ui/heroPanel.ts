import { heroesData, regionsData } from '../core/data';
import type { GameState } from '../core/types';
import { HERO_TRAIT_LABEL } from './heroTraitLabels';

export interface HeroPanelHandle {
  update(state: GameState): void;
  toggle(): void;
}

/** 영웅 명단 사이드 탭. transform만으로 여닫는다(설계 "화면" 절). */
export function createHeroPanel(container: HTMLElement): HeroPanelHandle {
  container.className = 'hero-panel closed';
  const list = document.createElement('ul');
  container.appendChild(list);

  const regionNameById = Object.fromEntries(regionsData.regions.map((r) => [r.id, r.name]));
  let open = false;

  function update(state: GameState) {
    const heroes = heroesData.heroes
      .filter((h) => h.faction === state.playerFaction && state.heroes[h.id]?.status === 'active')
      .sort((a, b) => (b.isKing ? 1 : 0) - (a.isKing ? 1 : 0) || b.leadership - a.leadership);

    list.innerHTML = heroes.length
      ? heroes
          .map((h) => {
            const hs = state.heroes[h.id];
            const location = hs?.location ? regionNameById[hs.location] ?? hs.location : '미배치';
            const traits = h.traits.map((t) => HERO_TRAIT_LABEL[t] ?? t).join(' · ');
            return `
              <li>
                <div class="hero-name">${h.name}${h.isKing ? ' <span class="hero-king">왕</span>' : ''}</div>
                <div class="hero-stats">통솔 ${h.leadership} · 무력 ${h.power} · 지력 ${h.intellect} · 정치 ${h.politics}</div>
                <div class="hero-location">위치: ${location}</div>
                ${traits ? `<div class="hero-traits">${traits}</div>` : ''}
              </li>
            `;
          })
          .join('')
      : '<li class="hero-empty">활동 중인 영웅이 없다.</li>';
  }

  function toggle() {
    open = !open;
    container.classList.toggle('closed', !open);
  }

  return { update, toggle };
}
