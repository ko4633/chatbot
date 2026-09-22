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

/** 엔딩 배너: 화면 위에 결과만 알린다(역사 비교 화면은 7단계에서 만든다). */
export function createEndingBanner(container: HTMLElement): EndingBannerHandle {
  container.className = 'ending-banner hidden';

  function update(ending: string | null) {
    if (!ending) {
      container.className = 'ending-banner hidden';
      container.textContent = '';
      return;
    }
    container.className = 'ending-banner';
    container.textContent = `이야기가 끝나다 — ${labelFor(ending)}`;
  }

  return { update };
}
