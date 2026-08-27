import { toEnglishPlace, toKoreanPlace } from './koreanPlaces';
import type { WeatherLocation, WeatherSnapshot } from './weather';

/**
 * 날씨 관련 외부 호출 모음. 전부 키 없이 HTTPS로 열려 있는 엔드포인트다.
 *
 * 응답은 남의 서버에서 온 값이라 그대로 믿지 않는다. storage.ts의 isValidEvent처럼
 * 필요한 필드가 기대한 타입인지 하나씩 확인한 뒤에만 도메인 타입으로 넘긴다.
 * 형태가 어긋나면 예외를 던져 호출부의 실패 처리(캐시 유지 + 재시도 버튼)로 흘려보낸다.
 */

const REQUEST_TIMEOUT_MS = 8000;

/** 응답이 없거나 느릴 때 무한정 기다리지 않도록 타임아웃을 건다 */
async function getJson(url: string): Promise<unknown> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return (await response.json()) as unknown;
  } finally {
    window.clearTimeout(timer);
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : null;
}

function asFiniteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

/* ---------------------------------------------------------------------------
 * 위치
 * ------------------------------------------------------------------------- */

/**
 * IP 기반 대략적인 위치.
 *
 * navigator.geolocation을 쓰지 않는 이유: Electron 데스크톱에서는 OS에 GPS가 없으면
 * 동작하지 않거나 별도 Google API 키를 요구하는 경우가 있어, 키 없이 바로 켜지는
 * 이 앱의 전제와 맞지 않는다. 도시 단위 정확도면 날씨·미세먼지에는 충분하고,
 * 어긋나면 사용자가 위젯에서 직접 지역을 고를 수 있게 해 두었다.
 */
export async function detectLocationByIp(): Promise<WeatherLocation> {
  const data = asRecord(await getJson('https://ipwho.is/'));
  if (!data || data.success === false) throw new Error('ip lookup failed');

  const lat = asFiniteNumber(data.latitude);
  const lon = asFiniteNumber(data.longitude);
  if (lat === null || lon === null) throw new Error('ip lookup: no coordinates');

  const city = typeof data.city === 'string' && data.city ? data.city : null;
  const region = typeof data.region === 'string' && data.region ? data.region : null;
  const country = typeof data.country === 'string' && data.country ? data.country : null;

  // ipwho.is는 도시명을 영문으로 준다('Asan'). 아는 지명이면 한글로 바꿔 보여준다.
  const raw = city ?? region ?? country ?? '현재 위치';
  return { name: (city && toKoreanPlace(city)) ?? raw, lat, lon };
}

async function geocodeOnce(name: string, preferKorea: boolean): Promise<WeatherLocation[]> {
  const url =
    'https://geocoding-api.open-meteo.com/v1/search' +
    `?name=${encodeURIComponent(name)}&count=6&language=ko&format=json`;
  const data = asRecord(await getJson(url));
  if (!data || !Array.isArray(data.results)) return [];

  const found: { location: WeatherLocation; isKorea: boolean }[] = [];

  for (const item of data.results) {
    const row = asRecord(item);
    if (!row) continue;
    const lat = asFiniteNumber(row.latitude);
    const lon = asFiniteNumber(row.longitude);
    if (lat === null || lon === null || typeof row.name !== 'string') continue;

    // 같은 이름의 도시가 여러 나라에 있으므로 상위 행정구역/국가를 덧붙여 구분한다.
    // 단 '서울특별시 (서울특별시, 대한민국)'처럼 겹쳐 보이는 건 걸러낸다.
    const detail = [row.admin1, row.country]
      .filter((v): v is string => typeof v === 'string' && v.length > 0 && v !== row.name)
      .join(', ');
    const location: WeatherLocation = {
      name: detail ? `${row.name} (${detail})` : row.name,
      lat,
      lon,
    };
    found.push({ location, isKorea: row.country_code === 'KR' });
  }

  // 한글로 검색해 영문명으로 바꿔 조회한 경우엔 국내 지명을 원한 게 확실하므로 KR을 앞으로 끌어올린다.
  // ('Jeju'로 찾으면 에티오피아·브라질의 동명 지역이 제주시보다 위에 잡힌다.)
  // 그 외에는 API가 매긴 관련도 순서를 그대로 존중한다.
  const ordered = preferKorea
    ? [...found.filter((f) => f.isKorea), ...found.filter((f) => !f.isKorea)]
    : found;
  return ordered.map((f) => f.location);
}

/**
 * 도시명 → 좌표. Open-Meteo Geocoding API (키 불필요).
 *
 * 한글 검색어는 이 API가 제대로 못 찾거나 동명의 작은 마을을 집어주기 때문에
 * (koreanPlaces.ts 주석 참고) 영문명을 먼저 시도하고, 없을 때만 입력값 그대로 찾는다.
 */
export async function searchLocations(query: string): Promise<WeatherLocation[]> {
  const trimmed = query.trim();
  if (!trimmed) return [];

  const english = toEnglishPlace(trimmed);
  if (english) {
    const byEnglish = await geocodeOnce(english, true);
    if (byEnglish.length > 0) return byEnglish;
  }
  return geocodeOnce(trimmed, false);
}

/* ---------------------------------------------------------------------------
 * 날씨 + 대기질
 * ------------------------------------------------------------------------- */

interface CurrentWeather {
  temperature: number;
  apparentTemperature: number;
  weatherCode: number;
  isDay: boolean;
  /** 지상 10m 풍속 (m/s — wind_speed_unit=ms로 받는다) */
  windSpeed: number | null;
  /** 오늘 하루 최대 강수확률 (%) */
  rainChancePercent: number | null;
}

async function fetchCurrentWeather(location: WeatherLocation): Promise<CurrentWeather> {
  const url =
    'https://api.open-meteo.com/v1/forecast' +
    `?latitude=${location.lat}&longitude=${location.lon}` +
    '&current=temperature_2m,apparent_temperature,weather_code,is_day,wind_speed_10m' +
    '&daily=precipitation_probability_max' +
    // 기본 단위는 km/h지만 풍속 등급 기준(기상청)이 m/s라, 변환을 거치지 않도록 여기서 맞춰 받는다
    '&wind_speed_unit=ms' +
    '&forecast_days=1' +
    '&timezone=auto';
  const data = asRecord(await getJson(url));
  const current = asRecord(data?.current);
  if (!current) throw new Error('weather: no current block');

  const temperature = asFiniteNumber(current.temperature_2m);
  const weatherCode = asFiniteNumber(current.weather_code);
  if (temperature === null || weatherCode === null) throw new Error('weather: missing fields');

  return {
    temperature,
    // 체감온도는 빠질 수 있으니 없으면 실제 기온으로 대체한다
    apparentTemperature: asFiniteNumber(current.apparent_temperature) ?? temperature,
    weatherCode,
    isDay: asFiniteNumber(current.is_day) !== 0,
    windSpeed: asFiniteNumber(current.wind_speed_10m),
    rainChancePercent: readTodayRainChance(data?.daily),
  };
}

/**
 * daily.precipitation_probability_max는 날짜별 배열이고, forecast_days=1이라 첫 칸이 오늘이다.
 * 확률이므로 0~100을 벗어난 값은 응답이 이상한 것이니 없는 값으로 떨어뜨린다.
 */
function readTodayRainChance(daily: unknown): number | null {
  const block = asRecord(daily);
  const list = block?.precipitation_probability_max;
  if (!Array.isArray(list)) return null;
  const today = asFiniteNumber(list[0]);
  if (today === null || today < 0 || today > 100) return null;
  return today;
}

/** 대기질은 실패해도 날씨는 보여줘야 하므로, 못 받으면 null을 돌려준다 */
async function fetchAirQuality(
  location: WeatherLocation,
): Promise<{ pm10: number | null; pm25: number | null }> {
  try {
    const url =
      'https://air-quality-api.open-meteo.com/v1/air-quality' +
      `?latitude=${location.lat}&longitude=${location.lon}` +
      '&current=pm10,pm2_5&timezone=auto';
    const data = asRecord(await getJson(url));
    const current = asRecord(data?.current);
    if (!current) return { pm10: null, pm25: null };
    return { pm10: asFiniteNumber(current.pm10), pm25: asFiniteNumber(current.pm2_5) };
  } catch {
    return { pm10: null, pm25: null };
  }
}

/** 날씨와 대기질을 함께 받아 한 덩어리로 만든다 */
export async function fetchWeatherSnapshot(location: WeatherLocation): Promise<WeatherSnapshot> {
  const [weather, air] = await Promise.all([
    fetchCurrentWeather(location),
    fetchAirQuality(location),
  ]);
  return {
    fetchedAt: Date.now(),
    location,
    temperature: weather.temperature,
    apparentTemperature: weather.apparentTemperature,
    weatherCode: weather.weatherCode,
    isDay: weather.isDay,
    windSpeed: weather.windSpeed,
    rainChancePercent: weather.rainChancePercent,
    pm10: air.pm10,
    pm25: air.pm25,
  };
}
