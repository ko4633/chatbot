import { factionsData } from '../core/data';
import type { GameState } from '../core/types';
import { SEASON_LABEL } from '../core/types';

export interface TopbarHandle {
  update(state: GameState): void;
}

export function createTopbar(
  container: HTMLElement,
  onNextTurn: () => void,
  onToggleChronicle: () => void,
  onToggleHeroes: () => void
): TopbarHandle {
  container.innerHTML = '';
  container.className = 'topbar';

  const dateEl = document.createElement('span');
  dateEl.className = 'date';

  const goldEl = document.createElement('span');
  goldEl.className = 'stat';
  const foodEl = document.createElement('span');
  foodEl.className = 'stat';
  const cohesionEl = document.createElement('span');
  cohesionEl.className = 'stat';

  const spacer = document.createElement('span');
  spacer.className = 'spacer';

  const buttonGroup = document.createElement('div');
  buttonGroup.className = 'topbar-buttons';

  const heroesBtn = document.createElement('button');
  heroesBtn.type = 'button';
  heroesBtn.textContent = '영웅';
  heroesBtn.addEventListener('click', onToggleHeroes);

  const chronicleBtn = document.createElement('button');
  chronicleBtn.type = 'button';
  chronicleBtn.textContent = '연대기';
  chronicleBtn.addEventListener('click', onToggleChronicle);

  const nextTurnBtn = document.createElement('button');
  nextTurnBtn.type = 'button';
  nextTurnBtn.className = 'next-turn';
  nextTurnBtn.textContent = '다음 계절';
  nextTurnBtn.addEventListener('click', onNextTurn);

  buttonGroup.append(heroesBtn, chronicleBtn, nextTurnBtn);
  container.append(dateEl, goldEl, foodEl, cohesionEl, spacer, buttonGroup);

  function update(state: GameState) {
    const faction = factionsData.factions.find((f) => f.id === state.playerFaction);
    const fs = state.factions[state.playerFaction];
    dateEl.textContent = `${state.year}년 ${SEASON_LABEL[state.season]} · ${faction?.name ?? state.playerFaction}`;
    goldEl.innerHTML = `<span class="label">금</span> ${fs?.gold ?? 0}`;
    foodEl.innerHTML = `<span class="label">식량</span> ${fs?.food ?? 0}`;
    cohesionEl.innerHTML = `<span class="label">결속</span> ${fs?.cohesion ?? 0}`;
  }

  return { update };
}
