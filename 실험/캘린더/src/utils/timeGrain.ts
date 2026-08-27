export type TimeBand = 'dawn' | 'morning' | 'day' | 'dusk' | 'night';

export function getTimeBand(hour: number): TimeBand {
  if (hour >= 4 && hour < 7) return 'dawn';
  if (hour >= 7 && hour < 11) return 'morning';
  if (hour >= 11 && hour < 16) return 'day';
  if (hour >= 16 && hour < 19) return 'dusk';
  return 'night';
}

// 시간대별 전체 배경 그라디언트.
// 실제 색은 tokens.css의 --gradient-* 에 있다. 여기서 var()만 넘기는 이유:
// 이 값은 --bg-gradient 커스텀 속성으로 :root에 직접 꽂히는데, var()를 넘겨두면
// 테마가 바뀌는 순간 별도 처리 없이 다크 팔레트로 따라 바뀐다.
// (hex를 그대로 두면 다크 모드에서 밝은 그라디언트가 배경을 통째로 덮어버린다.)
export const TIME_GRADIENTS: Record<TimeBand, string> = {
  dawn: 'var(--gradient-dawn)', // 새벽: 옅은 라벤더-그레이
  morning: 'var(--gradient-morning)', // 아침: 밝은 하늘빛
  day: 'var(--gradient-day)', // 낮: 선명한 파스텔 블루
  dusk: 'var(--gradient-dusk)', // 노을: 라이트 퍼플 + 옅은 복숭아
  night: 'var(--gradient-night)', // 밤: 깊은 인디고-퍼플
};

export const DEFAULT_GRADIENT = 'var(--gradient-default)';

export const TIME_BAND_LABELS: Record<TimeBand, string> = {
  dawn: '새벽',
  morning: '아침',
  day: '낮',
  dusk: '노을',
  night: '밤',
};
