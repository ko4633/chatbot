import type { GameState } from './types';

/**
 * 저장/불러오기의 순수 직렬화 로직만 코어에 둔다.
 * 실제 localStorage 접근은 브라우저 계층(src/ui)에서 수행한다.
 */

export const SAVE_FORMAT_VERSION = 1;

export interface SaveFile {
  version: number;
  savedAt: number;
  state: GameState;
}

export function serializeState(state: GameState, now: number): string {
  const save: SaveFile = { version: SAVE_FORMAT_VERSION, savedAt: now, state };
  return JSON.stringify(save);
}

export function deserializeState(raw: string): GameState | null {
  try {
    const parsed = JSON.parse(raw) as SaveFile;
    if (parsed.version !== SAVE_FORMAT_VERSION) return null;
    if (!parsed.state) return null;
    return parsed.state;
  } catch {
    return null;
  }
}
