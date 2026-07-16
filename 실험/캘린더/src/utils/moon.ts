// 외부 라이브러리 없이 삭망월(synodic month) 기반으로 달의 위상을 계산한다.
const SYNODIC = 29.530588853; // 삭망월 (일)
// 기준 신월(New Moon): 2000-01-06 18:14 UTC
const REFERENCE_DAYS = Date.UTC(2000, 0, 6, 18, 14) / 86_400_000;

/** 위상 값 0..1 반환 (0 = 신월, 0.5 = 보름) */
export function moonPhase(date: Date): number {
  const days = date.getTime() / 86_400_000;
  const phase = (((days - REFERENCE_DAYS) % SYNODIC) + SYNODIC) % SYNODIC;
  return phase / SYNODIC;
}

const PHASE_NAMES = [
  '신월',
  '초승달',
  '상현달',
  '상현망간의 달',
  '보름달',
  '하현망간의 달',
  '하현달',
  '그믐달',
];

export function moonPhaseName(phase: number): string {
  const index = Math.round(phase * 8) % 8;
  return PHASE_NAMES[index];
}
