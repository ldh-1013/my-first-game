/**
 * 타이머 완료 알림음.
 *
 * 오디오 파일을 번들에 넣지 않고 Web Audio API로 두 음(A5 → D6)을 짧게 겹쳐 만든다.
 * - 파일이 없으니 로딩 실패나 경로 문제가 생길 여지가 없고, 용량도 0이다.
 * - 사인파 + 지수 감쇠라서 '삑' 하는 자극적인 소리 대신 부드럽게 사라지는 종소리에 가깝다.
 * - AudioContext는 사용자 제스처 안에서 만들어야 자동재생 정책에 막히지 않으므로,
 *   타이머를 '시작'하는 클릭 시점에 ensureAudio()로 미리 깨워 둔다.
 */

type AudioContextCtor = typeof AudioContext;

let context: AudioContext | null = null;

function audioContextCtor(): AudioContextCtor | undefined {
  // window에서 typeof globalThis를 떼면 표준 AudioContext까지 사라지므로 교집합에 남겨 둔다
  const w = window as Window & typeof globalThis & { webkitAudioContext?: AudioContextCtor };
  return w.AudioContext ?? w.webkitAudioContext;
}

/** 오디오 컨텍스트를 만들거나 깨운다. 사용자 클릭 핸들러 안에서 호출할 것. */
export function ensureAudio(): AudioContext | null {
  try {
    if (!context) {
      const Ctor = audioContextCtor();
      if (!Ctor) return null;
      context = new Ctor();
    }
    if (context.state === 'suspended') void context.resume();
    return context;
  } catch {
    // 오디오를 못 쓰는 환경이어도 타이머 자체는 계속 동작해야 한다
    return null;
  }
}

/** 톤 하나를 예약 재생 (offset초 뒤 시작) */
function scheduleTone(ctx: AudioContext, frequency: number, offset: number): void {
  const start = ctx.currentTime + offset;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  osc.type = 'sine';
  osc.frequency.value = frequency;

  // exponentialRamp는 0을 못 받으므로 아주 작은 값에서 시작·종료한다
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(0.22, start + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.45);

  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(start);
  osc.stop(start + 0.5);
}

/** 타이머 완료 알림음을 재생한다. 실패해도 조용히 무시. */
export function playChime(): void {
  const ctx = ensureAudio();
  if (!ctx) return;
  try {
    scheduleTone(ctx, 880, 0); // A5
    scheduleTone(ctx, 1174.66, 0.17); // D6
  } catch {
    /* 무시 */
  }
}
