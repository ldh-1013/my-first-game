export type MoodLevel = 1 | 2 | 3 | 4 | 5;

export const MOOD_LEVELS: MoodLevel[] = [1, 2, 3, 4, 5];

interface MoodMeta {
  label: string;
  color: string;
}

// 신호등 빨강/초록을 피한 부드러운 파스텔: 초록 → 노랑 → 주황 → 라이트 퍼플 → 그레이
export const MOOD_META: Record<MoodLevel, MoodMeta> = {
  1: { label: '매우 좋음', color: '#A7E0C0' },
  2: { label: '좋음', color: '#EADFA0' },
  3: { label: '보통', color: '#F3CDA4' },
  4: { label: '흐림', color: '#D5C6EF' },
  5: { label: '매우 흐림', color: '#C4C2D2' },
};

export const MOOD_EMPTY_COLOR = '#ECEBF4';

export function moodColor(level: number | undefined): string {
  if (level && level >= 1 && level <= 5) return MOOD_META[level as MoodLevel].color;
  return MOOD_EMPTY_COLOR;
}

export function moodLabel(level: number | undefined): string {
  if (level && level >= 1 && level <= 5) return MOOD_META[level as MoodLevel].label;
  return '기록 없음';
}
