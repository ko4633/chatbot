import { SEASON_LABEL } from '../core/types';
import type { GameState } from '../core/types';

export interface ChroniclePanelHandle {
  update(state: GameState): void;
  toggle(): void;
}

/** 연대기 사이드 탭. transform만으로 여닫는다(설계 "화면" 절). */
export function createChroniclePanel(container: HTMLElement): ChroniclePanelHandle {
  container.className = 'chronicle-panel closed';
  const list = document.createElement('ul');
  container.appendChild(list);

  let open = false;

  function update(state: GameState) {
    list.innerHTML = state.chronicle
      .slice()
      .reverse()
      .map((c) => `<li><span class="chronicle-date">${c.year}년 ${SEASON_LABEL[c.season]}</span>${c.text}</li>`)
      .join('');
  }

  function toggle() {
    open = !open;
    container.classList.toggle('closed', !open);
  }

  return { update, toggle };
}
