export type TimeBand = 'dawn' | 'morning' | 'day' | 'dusk' | 'night';

export function getTimeBand(hour: number): TimeBand {
  if (hour >= 4 && hour < 7) return 'dawn';
  if (hour >= 7 && hour < 11) return 'morning';
  if (hour >= 11 && hour < 16) return 'day';
  if (hour >= 16 && hour < 19) return 'dusk';
  return 'night';
}

// 시간대별 전체 배경 그라디언트 — 파스텔 블루/라이트 퍼플 범위 안에서만 이동
export const TIME_GRADIENTS: Record<TimeBand, string> = {
  dawn: 'linear-gradient(180deg, #ECEAF6 0%, #E6E8FA 100%)', // 새벽: 옅은 라벤더-그레이
  morning: 'linear-gradient(180deg, #E8F1FF 0%, #F1F0FF 100%)', // 아침: 밝은 하늘빛
  day: 'linear-gradient(180deg, #DFEAFF 0%, #ECEFFE 100%)', // 낮: 선명한 파스텔 블루
  dusk: 'linear-gradient(180deg, #EDE7F8 0%, #FBEEF1 100%)', // 노을: 라이트 퍼플 + 옅은 복숭아
  night: 'linear-gradient(180deg, #D7D8EC 0%, #CECDE4 100%)', // 밤: 깊은 인디고-퍼플
};

export const DEFAULT_GRADIENT = 'linear-gradient(180deg, #F5F6FE 0%, #EFF0FD 100%)';

export const TIME_BAND_LABELS: Record<TimeBand, string> = {
  dawn: '새벽',
  morning: '아침',
  day: '낮',
  dusk: '노을',
  night: '밤',
};
