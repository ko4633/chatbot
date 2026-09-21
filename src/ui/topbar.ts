import { factionsData } from '../core/data';
import type { GameState } from '../core/types';
import { SEASON_LABEL } from '../core/types';

export interface TopbarHandle {
  update(state: GameState): void;
}

export function createTopbar(container: HTMLElement, onNextTurn: () => void): TopbarHandle {
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

  const nextTurnBtn = document.createElement('button');
  nextTurnBtn.type = 'button';
  nextTurnBtn.textContent = '다음 계절';
  nextTurnBtn.addEventListener('click', onNextTurn);

  container.append(dateEl, goldEl, foodEl, cohesionEl, spacer, nextTurnBtn);

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
