export interface CheatPanelHandlers {
  onAddGold(amount: number): void;
  onAddFood(amount: number): void;
  onMaxCohesion(): void;
  onRestoreActionPoints(): void;
  onAddGarrisonToSelected(amount: number): void;
}

export interface CheatPanelHandle {
  toggle(): void;
}

/**
 * 치트 패널(사용자 요청으로 추가한 디버그 도구, 설계 밖 기능이라 여기 UI 계층에만 둔다).
 * `(백틱) 키로 열고 닫는다. AI와 같은 공식을 쓰는 게임 로직(원칙 5)과는 별개로,
 * 상태를 곧바로 조작하는 개발용 지름길일 뿐이다.
 */
export function createCheatPanel(container: HTMLElement, handlers: CheatPanelHandlers): CheatPanelHandle {
  container.className = 'cheat-panel hidden';
  const title = document.createElement('h3');
  title.textContent = '치트';
  const hint = document.createElement('p');
  hint.textContent = '개발용 지름길. ` 키로 다시 닫는다.';

  const list = document.createElement('div');
  list.className = 'cheat-panel-buttons';

  function addButton(label: string, onClick: () => void) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = label;
    btn.addEventListener('click', onClick);
    list.appendChild(btn);
  }

  addButton('금 +1000', () => handlers.onAddGold(1000));
  addButton('식량 +1000', () => handlers.onAddFood(1000));
  addButton('결속 100', () => handlers.onMaxCohesion());
  addButton('행동력 회복', () => handlers.onRestoreActionPoints());
  addButton('선택 지역 병력 +5000', () => handlers.onAddGarrisonToSelected(5000));

  container.append(title, hint, list);

  let open = false;
  function toggle() {
    open = !open;
    container.classList.toggle('hidden', !open);
  }

  window.addEventListener('keydown', (e) => {
    if (e.key !== '`') return;
    const target = e.target as HTMLElement | null;
    if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) return;
    e.preventDefault();
    toggle();
  });

  return { toggle };
}
