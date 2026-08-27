export type MoodLevel = 1 | 2 | 3 | 4 | 5;

export const MOOD_LEVELS: MoodLevel[] = [1, 2, 3, 4, 5];

interface MoodMeta {
  label: string;
  color: string;
}

// 신호등 빨강/초록을 피한 부드러운 파스텔: 초록 → 노랑 → 주황 → 라이트 퍼플 → 그레이.
// 실제 색값은 tokens.css에 있다 — 인라인 style로 들어가는 값이라 var()를 그대로 써도 되고,
// 그래야 다크 모드에서 같은 순서·같은 의미를 유지한 어두운 팔레트로 자동으로 바뀐다.
export const MOOD_META: Record<MoodLevel, MoodMeta> = {
  1: { label: '매우 좋음', color: 'var(--color-mood-1)' },
  2: { label: '좋음', color: 'var(--color-mood-2)' },
  3: { label: '보통', color: 'var(--color-mood-3)' },
  4: { label: '흐림', color: 'var(--color-mood-4)' },
  5: { label: '매우 흐림', color: 'var(--color-mood-5)' },
};

export const MOOD_EMPTY_COLOR = 'var(--color-mood-empty)';

export function moodColor(level: number | undefined): string {
  if (level && level >= 1 && level <= 5) return MOOD_META[level as MoodLevel].color;
  return MOOD_EMPTY_COLOR;
}

export function moodLabel(level: number | undefined): string {
  if (level && level >= 1 && level <= 5) return MOOD_META[level as MoodLevel].label;
  return '기록 없음';
}
