export interface ResultPopupHandle {
  show(title: string, lines: string[]): void;
}

/** 결과 팝업: transform/opacity만으로 여닫는다(설계 "화면" 절). */
export function createResultPopup(container: HTMLElement): ResultPopupHandle {
  container.className = 'result-popup-backdrop hidden';
  const card = document.createElement('div');
  card.className = 'result-popup-card';
  const h2 = document.createElement('h2');
  const body = document.createElement('div');
  body.className = 'result-popup-body';
  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.textContent = '닫기';
  closeBtn.addEventListener('click', () => {
    container.classList.add('hidden');
  });
  card.append(h2, body, closeBtn);
  container.appendChild(card);
  container.addEventListener('click', (e) => {
    if (e.target === container) container.classList.add('hidden');
  });

  function show(title: string, lines: string[]) {
    h2.textContent = title;
    body.innerHTML = lines.map((l) => `<p>${l}</p>`).join('');
    container.classList.remove('hidden');
  }

  return { show };
}
