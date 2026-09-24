/**
 * 세력을 나타내는 작은 깃발 배지. 실존 국기를 흉내내지 않고, 세력 색 바탕에
 * 이름 첫 글자를 넣은 완전히 새로 그린 문장(紋章)이다(설계의 "고지도" 톤에 맞춘다).
 */
export function flagIconHtml(color: string, initial: string): string {
  return `
    <svg class="flag-icon" viewBox="0 0 20 16" width="20" height="16" aria-hidden="true">
      <path d="M1 1 L18 1 L14 5 L18 9 L1 9 Z" fill="${color}" stroke="#2A2622" stroke-width="1" />
      <line x1="1" y1="1" x2="1" y2="15" stroke="#6F6250" stroke-width="1.5" />
      <text x="8" y="7" font-size="7" text-anchor="middle" fill="#F2E8CF" font-family="'Gowun Dodum', sans-serif">${initial}</text>
    </svg>
  `;
}
