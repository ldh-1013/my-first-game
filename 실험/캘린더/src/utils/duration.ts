/** 스톱워치·타이머 표시용 시간 포맷 유틸 */

function pad(value: number, length = 2): string {
  return String(Math.floor(value)).padStart(length, '0');
}

/**
 * 스톱워치 표기: 크게 보여줄 시:분:초와 작게 덧붙일 1/100초를 나눠서 돌려준다.
 * 두 조각을 따로 주는 이유는 ClockWidget의 시:분 + 초처럼 글자 크기를 달리 주기 위해서다.
 * 한 시간을 넘기기 전에는 시(hour) 자리를 숨겨 숫자가 불필요하게 길어지지 않게 한다.
 */
export function formatStopwatch(ms: number): { main: string; centi: string } {
  const safe = Math.max(ms, 0);
  const centi = Math.floor(safe / 10) % 100;
  const totalSeconds = Math.floor(safe / 1000);
  const seconds = totalSeconds % 60;
  const minutes = Math.floor(totalSeconds / 60) % 60;
  const hours = Math.floor(totalSeconds / 3600);
  const main =
    hours > 0 ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${pad(minutes)}:${pad(seconds)}`;
  return { main, centi: pad(centi) };
}

/** 랩 구간처럼 짧은 시간을 한 줄로 표기 (mm:ss.cc) */
export function formatLap(ms: number): string {
  const { main, centi } = formatStopwatch(ms);
  return `${main}.${centi}`;
}

/**
 * 카운트다운 표기. 남은 시간을 올림(ceil)해서 다룬다 —
 * 5분을 설정하고 시작한 직후에 4:59가 보이면 어색하고, 0:00은 실제로 끝나는 순간에만 나와야 한다.
 */
export function formatCountdown(ms: number): string {
  const totalSeconds = Math.ceil(Math.max(ms, 0) / 1000);
  const seconds = totalSeconds % 60;
  const minutes = Math.floor(totalSeconds / 60) % 60;
  const hours = Math.floor(totalSeconds / 3600);
  return hours > 0
    ? `${hours}:${pad(minutes)}:${pad(seconds)}`
    : `${pad(minutes)}:${pad(seconds)}`;
}
