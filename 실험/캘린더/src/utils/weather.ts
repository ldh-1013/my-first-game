/**
 * 날씨·미세먼지 도메인 로직 (네트워크 호출 없는 순수 함수만).
 *
 * 데이터는 Open-Meteo(api.open-meteo.com, air-quality-api.open-meteo.com)를 쓴다.
 * 회원가입이나 키 발급 없이 HTTPS + CORS로 바로 호출되므로, 백엔드 없이 렌더러에서
 * 직접 fetch하는 이 앱 구조에 그대로 들어맞는다.
 *
 * 참고: 더 공식적인 국내 수치가 필요하면 data.go.kr 에어코리아 API로 교체 가능하다.
 * (다만 서비스키 발급 절차가 있어 1차 구현에서는 쓰지 않았다.)
 */

export interface WeatherLocation {
  name: string;
  lat: number;
  lon: number;
}

export interface HourlyRain {
  /** 그 시각의 0~23 hour (로컬 기준) */
  hour: number;
  /** 강수확률 % */
  probability: number | null;
  /** 강수량 mm */
  amount: number | null;
}

export interface WeatherSnapshot {
  /** 응답을 받은 시각(Date.now). 캐시가 얼마나 오래됐는지 표시하는 데 쓴다 */
  fetchedAt: number;
  location: WeatherLocation;
  temperature: number;
  apparentTemperature: number;
  /** WMO 날씨 코드 */
  weatherCode: number;
  isDay: boolean;
  /** 지상 10m 풍속 (m/s). 응답에서 못 받으면 null */
  windSpeed: number | null;
  /** 오늘 하루 최대 강수확률 (%). 응답에서 못 받으면 null */
  rainChancePercent: number | null;
  /** 오늘 시간대별 강수확률·강수량. 응답에서 못 받으면 null */
  hourlyRain: HourlyRain[] | null;
  /** 미세먼지 ㎍/㎥ — 대기질 응답만 따로 실패할 수 있어 null을 허용한다 */
  pm10: number | null;
  pm25: number | null;
}

/* ---------------------------------------------------------------------------
 * 미세먼지 등급
 *
 * Open-Meteo도 자체 AQI를 주지만 그건 유럽 기준(European AQI)이라 한국에서 보던
 * 수치와 등급이 어긋난다. 그래서 원시 농도(㎍/㎥)만 받아서 환경부 예보등급 4단계로
 * 직접 환산한다. PM10과 PM2.5의 등급이 다르면 더 나쁜 쪽을 최종 등급으로 삼는데,
 * 이것도 실제 미세먼지 예보가 발표되는 방식과 같다.
 * ------------------------------------------------------------------------- */

export type AqiGrade = 'good' | 'moderate' | 'bad' | 'verybad';

export const AQI_LABELS: Record<AqiGrade, string> = {
  good: '좋음',
  moderate: '보통',
  bad: '나쁨',
  verybad: '매우나쁨',
};

const GRADE_ORDER: AqiGrade[] = ['good', 'moderate', 'bad', 'verybad'];

/** [상한값, 등급] — 상한 이하면 그 등급. 어디에도 안 걸리면 매우나쁨 */
const PM25_BANDS: [number, AqiGrade][] = [
  [15, 'good'],
  [35, 'moderate'],
  [75, 'bad'],
];

const PM10_BANDS: [number, AqiGrade][] = [
  [30, 'good'],
  [80, 'moderate'],
  [150, 'bad'],
];

function gradeFromBands(value: number | null, bands: [number, AqiGrade][]): AqiGrade | null {
  if (value === null || !Number.isFinite(value) || value < 0) return null;
  for (const [limit, grade] of bands) {
    if (value <= limit) return grade;
  }
  return 'verybad';
}

export function pm25Grade(value: number | null): AqiGrade | null {
  return gradeFromBands(value, PM25_BANDS);
}

export function pm10Grade(value: number | null): AqiGrade | null {
  return gradeFromBands(value, PM10_BANDS);
}

/** 둘 중 더 나쁜 등급. 한쪽이 없으면 있는 쪽을 그대로 쓴다. */
export function worseGrade(a: AqiGrade | null, b: AqiGrade | null): AqiGrade | null {
  if (a === null) return b;
  if (b === null) return a;
  return GRADE_ORDER.indexOf(a) >= GRADE_ORDER.indexOf(b) ? a : b;
}

/* ---------------------------------------------------------------------------
 * WMO 날씨 코드
 * ------------------------------------------------------------------------- */

export type WeatherIconKey =
  | 'clear'
  | 'partly'
  | 'cloud'
  | 'fog'
  | 'drizzle'
  | 'rain'
  | 'snow'
  | 'thunder';

export interface WeatherLook {
  icon: WeatherIconKey;
  label: string;
}

/** WMO weather code를 아이콘 종류와 한국어 설명으로 옮긴다 */
export function describeWeather(code: number): WeatherLook {
  if (code === 0) return { icon: 'clear', label: '맑음' };
  if (code === 1) return { icon: 'clear', label: '대체로 맑음' };
  if (code === 2) return { icon: 'partly', label: '구름 조금' };
  if (code === 3) return { icon: 'cloud', label: '흐림' };
  if (code === 45 || code === 48) return { icon: 'fog', label: '안개' };
  if (code >= 51 && code <= 57) return { icon: 'drizzle', label: '이슬비' };
  if (code >= 61 && code <= 67) return { icon: 'rain', label: '비' };
  if (code >= 71 && code <= 77) return { icon: 'snow', label: '눈' };
  if (code >= 80 && code <= 82) return { icon: 'rain', label: '소나기' };
  if (code === 85 || code === 86) return { icon: 'snow', label: '소낙눈' };
  // WMO 코드는 99까지다. 범위를 넘는 값은 뇌우로 뭉뚱그리지 않고 미상으로 떨어뜨린다.
  if (code >= 95 && code <= 99) return { icon: 'thunder', label: '뇌우' };
  return { icon: 'cloud', label: '알 수 없음' };
}

/* ---------------------------------------------------------------------------
 * 바람 세기
 *
 * 기준은 기상청 예보용어해설(https://www.kma.go.kr/kma/biz/forecast05.jsp)의
 * 풍속 표현을 그대로 따른다. 단위는 m/s다 — weatherApi가 wind_speed_unit=ms로
 * 받아 오므로 여기서 변환하지 않는다.
 *
 *   약간 강한 바람  4~9 m/s
 *   강한 바람       9~14 m/s
 *   매우 강한 바람  14 m/s 이상(주의보), 21 m/s 이상(경보)
 *
 * 위젯은 3단계만 보여주므로 '강한'과 '매우 강한'을 '강함' 하나로 합쳤다.
 * 미세먼지 등급과 달리 좋고 나쁨의 평가가 아니라 세기의 서술이다.
 * ------------------------------------------------------------------------- */

export type WindGrade = 'weak' | 'medium' | 'strong';

/** '약간 강한 바람'이 시작되는 풍속 */
const WIND_MEDIUM_MS = 4;
/** '강한 바람'이 시작되는 풍속 */
const WIND_STRONG_MS = 9;

export const WIND_GRADE_LABELS: Record<WindGrade, string> = {
  weak: '약함',
  medium: '중간',
  strong: '강함',
};

/**
 * 등급은 '화면에 보이는 숫자' 기준이다.
 *
 * 원본 값으로 등급을 매기면 8.999가 '9.0m/s · 중간'으로 표시되어, 숫자와 라벨이
 * 서로 어긋나 보인다. 호출부는 roundWindSpeed()를 통과시킨 값을 넘긴다.
 */
export function windGrade(speed: number | null): WindGrade | null {
  if (speed === null || !Number.isFinite(speed) || speed < 0) return null;
  if (speed < WIND_MEDIUM_MS) return 'weak';
  if (speed < WIND_STRONG_MS) return 'medium';
  return 'strong';
}

/**
 * 화면에 쓸 정밀도로 줄인 풍속. 10m/s 미만은 소수 한 자리, 그 이상은 정수.
 * (약한 바람일수록 소수점 한 자리가 의미 있고, 센 바람에서는 군더더기다.)
 *
 * 표시와 등급이 같은 값을 보도록 이 함수를 단일 기준점으로 둔다. 이미 줄인 값을
 * 다시 넣어도 결과가 같아서(멱등), 호출 순서를 신경 쓸 필요가 없다.
 */
export function roundWindSpeed(speed: number): number {
  return speed < 10 ? Math.round(speed * 10) / 10 : Math.round(speed);
}

/** 4.24 → '4.2m/s', 12.4 → '12m/s' */
export function formatWindSpeed(speed: number): string {
  const rounded = roundWindSpeed(speed);
  return `${rounded < 10 ? rounded.toFixed(1) : rounded}m/s`;
}

/* ---------------------------------------------------------------------------
 * 오늘 비 예보
 * ------------------------------------------------------------------------- */

/** 이 확률부터 '비 소식이 있다'고 본다 */
export const RAIN_CHANCE_THRESHOLD = 30;

/**
 * 오늘 강수확률을 한 문장으로. 값이 없으면 null을 돌려주고, 위젯은 그 줄을 통째로 뺀다.
 * (insight.ts처럼 재촉하거나 겁주지 않고 담백하게 알려 주는 톤을 따른다.)
 */
export function describeRainChance(percent: number | null): string | null {
  if (percent === null || !Number.isFinite(percent)) return null;
  if (percent >= RAIN_CHANCE_THRESHOLD) return `오늘 비 소식이 있어요 (강수확률 ${Math.round(percent)}%)`;
  return '오늘은 비 걱정 없어요';
}

/* ---------------------------------------------------------------------------
 * 시간대별 비 구간
 * ------------------------------------------------------------------------- */

export interface RainWindow {
  /** 비가 시작되는 시(0~23) */
  startHour: number;
  /** 비가 그치는 시(1~24). 마지막 시간대의 다음 시각이라 24가 될 수 있다 */
  endHour: number;
  /** 구간 안 최고 강수확률 % */
  peak: number;
  /** 이미 시작된 구간이라 시작 시각을 '지금'으로 당겨 잡았는지 */
  ongoing: boolean;
}

/**
 * 확률이 기준치 이상으로 이어지는 구간들을 찾는다.
 *
 * 이미 지나간 구간은 안내할 값어치가 없으니 버리고, 지금 내리는 중인 구간은
 * 시작을 현재 시각으로 당겨 잡는다("오전 3시부터"가 아니라 "지금부터").
 * hourly의 한 칸은 그 시각부터 한 시간을 뜻하므로 끝 시각은 마지막 칸 + 1이다.
 */
export function findRainWindows(
  hourly: HourlyRain[] | null,
  fromHour: number,
): RainWindow[] {
  if (!hourly || hourly.length === 0) return [];

  const windows: RainWindow[] = [];
  let start: number | null = null;
  let peak = 0;

  const close = (endHour: number) => {
    if (start === null) return;
    // 이미 끝난 구간은 버린다
    if (endHour > fromHour) {
      windows.push({
        startHour: Math.max(start, fromHour),
        endHour,
        peak,
        ongoing: start < fromHour,
      });
    }
    start = null;
    peak = 0;
  };

  for (const row of [...hourly].sort((a, b) => a.hour - b.hour)) {
    const wet = row.probability !== null && row.probability >= RAIN_CHANCE_THRESHOLD;
    if (wet) {
      if (start === null) start = row.hour;
      peak = Math.max(peak, row.probability ?? 0);
    } else {
      close(row.hour);
    }
  }
  close(24);

  return windows;
}

/** 14 → '오후 2시'. 0시와 12시는 숫자보다 말이 자연스럽다. */
export function formatHourLabel(hour: number): string {
  const h = ((hour % 24) + 24) % 24;
  if (h === 0) return '자정';
  if (h === 12) return '정오';
  return h < 12 ? `오전 ${h}시` : `오후 ${h - 12}시`;
}

/**
 * 구간들을 한 문장으로. insight.ts처럼 재촉하거나 겁주지 않는 톤을 따른다.
 * 구간이 없으면 null — 화면이 그 자리를 다른 문구로 채운다.
 */
export function describeRainWindows(windows: RainWindow[]): string | null {
  if (windows.length === 0) return null;
  const parts = windows.map((w) => {
    const from = w.ongoing ? '지금' : formatHourLabel(w.startHour);
    return `${from}부터 ${formatHourLabel(w.endHour)}까지`;
  });
  return `${parts.join(', ')} 비가 올 것으로 보여요`;
}

/** 소수점 한 자리 없이 보여줄 기온 문자열 (-0 방지) */
export function formatTemp(value: number): string {
  const rounded = Math.round(value);
  return `${rounded === 0 ? 0 : rounded}°`;
}
