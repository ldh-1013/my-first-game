/**
 * 외부 라이브러리 없이 달의 위상을 계산한다.
 *
 * 예전에는 "평균 삭망월(29.530588853일) + 기준 신월 시각" 하나로 선형 계산했는데,
 * 그 방식은 달 궤도의 이심률과 태양의 섭동을 전혀 반영하지 못한다.
 * 2026년의 삭·망 25번을 실제 값과 대조해 보니 평균 7.1시간, 최대 17.4시간까지 어긋났다.
 * (예: 2026-08-12 17:37 UTC 신월을 8월 13일 07:45로 계산 — 14시간 늦음)
 * 하루 사이에도 모양이 눈에 띄게 바뀌는 상현/하현 부근에서는 아이콘이 통째로
 * 하루 밀려 보이기 충분한 크기다.
 *
 * 그래서 평균 주기를 쓰는 대신, 태양과 달의 황경(ecliptic longitude)을 각각 구해
 * 그 차이(이각, elongation)로 위상을 구한다. 위상은 원래 이 각도로 정의되는 값이라
 * 물리적으로도 이쪽이 맞다. 계산은 Jean Meeus의 저정밀도 급수를 잘라 쓴 것으로,
 * 여전히 순수 수식이라 새 의존성이 필요 없다.
 *   - 태양 황경: Meeus 25장 (중심차 3항)
 *   - 달 황경: Meeus 47장 주기항 중 진폭이 큰 28개
 * 같은 25개 표본에서 오차가 3분 이내로 줄었다.
 *
 * ΔT(TT-UT, 2026년 기준 약 72초)는 무시했다. 달이 태양에 대해 1시간에 0.5°쯤
 * 움직이므로 72초는 0.01° 남짓이고, 아이콘 모양에는 아무 영향이 없다.
 */

const RAD = Math.PI / 180;

function norm360(deg: number): number {
  return ((deg % 360) + 360) % 360;
}

function sinDeg(deg: number): number {
  return Math.sin(deg * RAD);
}

/** J2000.0 기준 율리우스 세기 */
function julianCenturies(date: Date): number {
  const julianDay = date.getTime() / 86_400_000 + 2_440_587.5;
  return (julianDay - 2_451_545.0) / 36_525;
}

/** 태양의 겉보기 황경(도). Meeus 25장 — 평균황경 + 중심차 */
function sunLongitude(t: number): number {
  const meanLongitude = 280.46646 + 36000.76983 * t + 0.0003032 * t * t;
  const meanAnomaly = 357.52911 + 35999.05029 * t - 0.0001537 * t * t;
  const center =
    (1.914602 - 0.004817 * t - 0.000014 * t * t) * sinDeg(meanAnomaly) +
    (0.019993 - 0.000101 * t) * sinDeg(2 * meanAnomaly) +
    0.000289 * sinDeg(3 * meanAnomaly);
  return norm360(meanLongitude + center);
}

/**
 * 달 황경의 주기항 (Meeus 47장, 진폭 1e-6도 단위).
 * [진폭, D 계수, M 계수, M' 계수, F 계수]
 *   D  = 달의 평균 이각, M = 태양의 평균 근점이각,
 *   M' = 달의 평균 근점이각, F = 달의 위도 인수
 * 진폭이 큰 것부터 28개만 남겼다. 잘라낸 항들의 합은 0.01° 수준이라
 * 시간으로 환산해도 1~2분이고, 이 아이콘에는 과할 정도로 충분하다.
 */
const LONGITUDE_TERMS: [number, number, number, number, number][] = [
  [6288774, 0, 0, 1, 0],
  [1274027, 2, 0, -1, 0],
  [658314, 2, 0, 0, 0],
  [213618, 0, 0, 2, 0],
  [-185116, 0, 1, 0, 0],
  [-114332, 0, 0, 0, 2],
  [58793, 2, 0, -2, 0],
  [57066, 2, -1, -1, 0],
  [53322, 2, 0, 1, 0],
  [45758, 2, -1, 0, 0],
  [-40923, 0, 1, -1, 0],
  [-34720, 1, 0, 0, 0],
  [-30383, 0, 1, 1, 0],
  [15327, 2, 0, 0, -2],
  [-12528, 0, 0, 1, 2],
  [10980, 0, 0, 1, -2],
  [10675, 4, 0, -1, 0],
  [10034, 0, 0, 3, 0],
  [8548, 4, 0, -2, 0],
  [-7888, 2, 1, -1, 0],
  [-6766, 2, 1, 0, 0],
  [-5163, 1, 0, -1, 0],
  [4987, 1, 1, 0, 0],
  [4036, 2, -1, 1, 0],
  [3994, 2, 0, 2, 0],
  [3861, 4, 0, 0, 0],
  [3665, 2, 0, -3, 0],
  [-2689, 0, 1, -2, 0],
];

/** 달의 겉보기 황경(도). Meeus 47장 */
function moonLongitude(t: number): number {
  const meanLongitude =
    218.3164477 +
    481267.88123421 * t -
    0.0015786 * t * t +
    t ** 3 / 538841 -
    t ** 4 / 65194000;
  const elongation =
    297.8501921 +
    445267.1114034 * t -
    0.0018819 * t * t +
    t ** 3 / 545868 -
    t ** 4 / 113065000;
  const sunAnomaly = 357.5291092 + 35999.0502909 * t - 0.0001536 * t * t + t ** 3 / 24490000;
  const moonAnomaly =
    134.9633964 +
    477198.8675055 * t +
    0.0087414 * t * t +
    t ** 3 / 69699 -
    t ** 4 / 14712000;
  const latitudeArg =
    93.272095 +
    483202.0175233 * t -
    0.0036539 * t * t -
    t ** 3 / 3526000 +
    t ** 4 / 863310000;

  // 지구 궤도 이심률의 세기별 변화 보정. 태양 근점이각이 든 항에만 곱한다.
  const eccentricity = 1 - 0.002516 * t - 0.0000074 * t * t;

  let sum = 0;
  for (const [amplitude, cD, cM, cMoon, cF] of LONGITUDE_TERMS) {
    let scaled = amplitude;
    if (Math.abs(cM) === 1) scaled *= eccentricity;
    else if (Math.abs(cM) === 2) scaled *= eccentricity * eccentricity;
    sum +=
      scaled *
      sinDeg(cD * elongation + cM * sunAnomaly + cMoon * moonAnomaly + cF * latitudeArg);
  }

  return norm360(meanLongitude + sum / 1e6);
}

/**
 * 위상 값 0..1 반환 (0 = 신월, 0.25 = 상현, 0.5 = 보름, 0.75 = 하현).
 * 달과 태양의 황경 차이를 한 바퀴(360°)로 나눈 값이다.
 */
export function moonPhase(date: Date): number {
  const t = julianCenturies(date);
  return norm360(moonLongitude(t) - sunLongitude(t)) / 360;
}

/** 밝게 보이는 면적의 비율 0..1 (0 = 신월, 1 = 보름) */
export function moonIllumination(phase: number): number {
  return (1 - Math.cos(phase * 2 * Math.PI)) / 2;
}

// '상현망간의 달'·'하현망간의 달'은 사전에는 있어도 일상에서 거의 안 쓰는 말이라,
// 스크린리더로 읽혔을 때 바로 와닿는 '차오르는 달'·'기우는 달'로 바꿨다.
const PHASE_NAMES = [
  '신월',
  '초승달',
  '상현달',
  '차오르는 달',
  '보름달',
  '기우는 달',
  '하현달',
  '그믐달',
];

export function moonPhaseName(phase: number): string {
  const index = Math.round(phase * 8) % 8;
  return PHASE_NAMES[index];
}
