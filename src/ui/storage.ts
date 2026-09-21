import { deserializeState, serializeState } from '../core/save';
import type { GameState } from '../core/types';

const STORAGE_KEY = 'samhan-jaengpae:save';

export function saveToLocalStorage(state: GameState): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, serializeState(state, Date.now()));
  } catch {
    // localStorage를 쓸 수 없는 환경(사생활 보호 모드 등)에서는 조용히 무시한다.
  }
}

export function loadFromLocalStorage(): GameState | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return deserializeState(raw);
  } catch {
    return null;
  }
}

export function clearLocalStorage(): void {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // 무시
  }
}
