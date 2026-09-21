/**
 * 결정론적 시드 RNG (mulberry32). Math.random 대신 게임 전역에서 이 RNG 하나만 사용한다.
 * 순수 함수: 시드/커서를 입력받아 다음 값과 다음 커서를 함께 반환한다.
 */

export interface RngDraw {
  value: number;
  nextCursor: number;
}

function mulberry32(seed: number): number {
  let t = (seed += 0x6d2b79f5);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}

/** seed와 cursor로부터 [0,1) 난수와 다음 cursor를 결정론적으로 계산한다. */
export function nextRandom(seed: number, cursor: number): RngDraw {
  const value = mulberry32((seed ^ (cursor * 0x9e3779b1)) >>> 0);
  return { value, nextCursor: cursor + 1 };
}

/** [min, max) 범위의 난수. */
export function nextRange(seed: number, cursor: number, min: number, max: number): { value: number; nextCursor: number } {
  const draw = nextRandom(seed, cursor);
  return { value: min + draw.value * (max - min), nextCursor: draw.nextCursor };
}
