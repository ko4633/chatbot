import { factionsData } from '../core/data';
import type { FactionId } from '../core/types';

export interface FactionSelectHandle {
  show(onSelect: (factionId: FactionId) => void): void;
  hide(): void;
}

/**
 * 시작 화면: 플레이할 나라를 고른다(설계 "싱글 플레이, 나머지 나라는 AI").
 * playable 세력(고구려·백제·신라)만 고를 수 있다.
 */
export function createFactionSelect(container: HTMLElement): FactionSelectHandle {
  container.className = 'faction-select-backdrop hidden';
  const card = document.createElement('div');
  card.className = 'faction-select-card';
  const h1 = document.createElement('h1');
  h1.textContent = '삼한쟁패 551–676';
  const sub = document.createElement('p');
  sub.textContent = '어느 나라로 이 시대를 살아가겠는가.';
  const choices = document.createElement('div');
  choices.className = 'faction-select-choices';
  card.append(h1, sub, choices);
  container.appendChild(card);

  const playable = factionsData.factions.filter((f) => f.playable);

  function show(onSelect: (factionId: FactionId) => void) {
    choices.innerHTML = '';
    for (const f of playable) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'faction-select-option';
      btn.style.setProperty('--faction-color', f.color);
      btn.innerHTML = `
        <span class="faction-select-swatch"></span>
        <span class="faction-select-name">${f.name}</span>
        <span class="faction-select-notes">${f.notes ?? ''}</span>
      `;
      btn.addEventListener('click', () => onSelect(f.id));
      choices.appendChild(btn);
    }
    container.classList.remove('hidden');
  }

  function hide() {
    container.classList.add('hidden');
  }

  return { show, hide };
}
