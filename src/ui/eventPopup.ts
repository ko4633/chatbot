import type { PendingChoice } from '../core/types';

export interface EventPopupHandle {
  show(choice: PendingChoice, onSelect: (choiceId: string) => void): void;
  hide(): void;
}

/** 이벤트 선택 팝업: 전체화면 두루마리. transform/opacity만으로 여닫는다(설계 "화면" 절). */
export function createEventPopup(container: HTMLElement): EventPopupHandle {
  container.className = 'event-popup-backdrop hidden';
  const scroll = document.createElement('div');
  scroll.className = 'event-popup-scroll';
  const h2 = document.createElement('h2');
  const body = document.createElement('p');
  const choiceList = document.createElement('div');
  choiceList.className = 'event-popup-choices';
  scroll.append(h2, body, choiceList);
  container.appendChild(scroll);

  function show(choice: PendingChoice, onSelect: (choiceId: string) => void) {
    h2.textContent = choice.title;
    body.textContent = choice.text;
    choiceList.innerHTML = '';
    for (const option of choice.options) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = option.label;
      btn.addEventListener('click', () => onSelect(option.id));
      choiceList.appendChild(btn);
    }
    container.classList.remove('hidden');
  }

  function hide() {
    container.classList.add('hidden');
  }

  return { show, hide };
}
