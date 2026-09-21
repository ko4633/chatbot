import { heroesData } from './data';
import type { HeroId } from './types';

/** 지휘 영웅이 없는 부대의 기본 통솔(설계 미기재 구간의 중립값). */
export const NO_COMMANDER_LEADERSHIP = 50;

export function heroLeadership(heroId: HeroId): number {
  return heroesData.heroes.find((h) => h.id === heroId)?.leadership ?? NO_COMMANDER_LEADERSHIP;
}
