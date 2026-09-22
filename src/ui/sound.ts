export interface SoundHandle {
  playClash(): void;
  playVictory(): void;
  playDefeat(): void;
}

/**
 * 효과음(설계 7단계). 외부 오디오 에셋 없이 Web Audio API로 그 자리에서 합성한다
 * (설계의 "에셋 복제 금지"와 무관하게 애초에 복제할 에셋이 없다).
 * 모바일은 사용자 동작 전까지 AudioContext가 막히므로, 첫 재생 시점에 지연 생성한다.
 */
export function createSound(): SoundHandle {
  let ctx: AudioContext | null = null;

  function ensureContext(): AudioContext | null {
    if (ctx) return ctx;
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return null;
    try {
      ctx = new Ctor();
    } catch {
      ctx = null;
    }
    return ctx;
  }

  function tone(freqStart: number, freqEnd: number, duration: number, startAt: number, gainPeak: number, type: OscillatorType) {
    const audio = ensureContext();
    if (!audio) return;
    const osc = audio.createOscillator();
    const gain = audio.createGain();
    osc.type = type;
    const t0 = audio.currentTime + startAt;
    osc.frequency.setValueAtTime(freqStart, t0);
    osc.frequency.exponentialRampToValueAtTime(Math.max(1, freqEnd), t0 + duration);
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.exponentialRampToValueAtTime(gainPeak, t0 + duration * 0.15);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + duration);
    osc.connect(gain);
    gain.connect(audio.destination);
    osc.start(t0);
    osc.stop(t0 + duration + 0.02);
  }

  function playClash() {
    // 병장기가 부딪히는 짧고 낮은 충격음.
    tone(180, 60, 0.18, 0, 0.2, 'sawtooth');
  }

  function playVictory() {
    // 오르는 짧은 가락.
    tone(440, 440, 0.1, 0, 0.15, 'triangle');
    tone(660, 660, 0.12, 0.1, 0.15, 'triangle');
    tone(880, 880, 0.18, 0.2, 0.18, 'triangle');
  }

  function playDefeat() {
    // 내려가는 낮은 가락.
    tone(300, 150, 0.35, 0, 0.15, 'sine');
  }

  return { playClash, playVictory, playDefeat };
}
