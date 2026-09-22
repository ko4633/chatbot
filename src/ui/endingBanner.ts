const ENDING_LABEL: Record<string, string> = {
  samhanUnification: '삼한일통',
  goguryeoUnderHeaven: '고구려의 천하',
  baekjeSea: '백제의 바다',
  baekjeRevival: '백제 부활',
  tangProvince: '당의 주현'
};

function labelFor(ending: string): string {
  if (ENDING_LABEL[ending]) return ENDING_LABEL[ending];
  if (ending.startsWith('territorial700:')) {
    const faction = ending.split(':')[1];
    return `700년, ${faction}이(가) 가장 넓은 땅을 차지하다`;
  }
  return ending;
}

export interface EndingBannerHandle {
  update(ending: string | null): void;
}

/** 엔딩 배너: 결과를 알리고, "역사 비교" 버튼으로 7단계 비교 화면을 연다. */
export function createEndingBanner(container: HTMLElement, onCompareHistory: () => void): EndingBannerHandle {
  container.className = 'ending-banner hidden';
  const label = document.createElement('span');
  const compareBtn = document.createElement('button');
  compareBtn.type = 'button';
  compareBtn.textContent = '역사 비교';
  compareBtn.addEventListener('click', onCompareHistory);
  container.append(label, compareBtn);

  function update(ending: string | null) {
    if (!ending) {
      container.className = 'ending-banner hidden';
      return;
    }
    container.className = 'ending-banner';
    label.textContent = `이야기가 끝나다 — ${labelFor(ending)}`;
  }

  return { update };
}
