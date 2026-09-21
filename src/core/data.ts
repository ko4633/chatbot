import regionsJson from '../../data/regions.json';
import factionsJson from '../../data/factions.json';
import heroesJson from '../../data/heroes.json';
import eventsJson from '../../data/events.json';
import type { EventsFile, FactionsFile, HeroesFile, RegionsFile } from './types';

/**
 * 모든 수치·지역·영웅·이벤트는 data/*.json에서만 읽는다 (하드코딩 금지).
 * 이 모듈은 JSON을 타입이 부여된 형태로 다시 내보내기만 한다. DOM·브라우저 API를 쓰지 않는다.
 * 튜닝 수치(balance.json)는 core/balance.ts에서 읽는다.
 */
export const regionsData = regionsJson as unknown as RegionsFile;
export const factionsData = factionsJson as unknown as FactionsFile;
export const heroesData = heroesJson as unknown as HeroesFile;
export const eventsData = eventsJson as unknown as EventsFile;
export { balanceData } from './balance';
