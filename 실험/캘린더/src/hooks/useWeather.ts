import { useCallback, useEffect, useRef, useState } from 'react';
import { subscribeMinute } from '../store/clock';
import { loadSettings, loadWeatherCache, saveSettings, saveWeatherCache } from '../utils/storage';
import type { WeatherLocation, WeatherSnapshot } from '../utils/weather';
import { detectLocationByIp, fetchWeatherSnapshot } from '../utils/weatherApi';

/**
 * 날씨/미세먼지 조회·캐싱·자동 갱신을 담당하는 훅.
 *
 * 갱신 주기를 10분으로 둔 이유: 날씨와 미세먼지는 초 단위로 변하는 값이 아니라
 * 자주 찔러 봐야 같은 값만 돌아온다. 게다가 키 없이 쓰는 공개 API라 예의상으로도
 * 폴링을 아껴야 한다. 그보다 최신 값이 필요하면 위젯의 새로고침 버튼이 있다.
 *
 * 타이머를 새로 만들지 않고 store/clock.ts의 subscribeMinute을 쓰는 이유:
 * 이 앱은 이미 분 단위 공유 시계를 갖고 있고, 그 시계는 창이 가려지면 멈췄다가
 * 돌아올 때 재동기화된다. 독립적인 setInterval을 하나 더 띄우는 것보다
 * 이 관례를 따르는 편이 동작도 예측 가능하고 코드베이스와도 일관된다.
 */

const REFRESH_MINUTES = 10;

export interface UseWeatherResult {
  snapshot: WeatherSnapshot | null;
  /** 지금 보고 있는 지역 (좌표를 아직 못 잡았으면 null) */
  location: WeatherLocation | null;
  loading: boolean;
  /** 갱신에 실패한 상태. 캐시된 snapshot이 있으면 그건 계속 보여준다 */
  failed: boolean;
  refresh: () => void;
  changeLocation: (next: WeatherLocation) => void;
}

/** 같은 대상에 대한 중복 요청인지 판별하기 위한 키 */
function targetKey(location: WeatherLocation | null): string {
  return location ? `${location.lat},${location.lon}` : 'auto';
}

export function useWeather(): UseWeatherResult {
  const initialLocation = loadSettings().weatherLocation ?? null;

  const [location, setLocation] = useState<WeatherLocation | null>(initialLocation);
  const [snapshot, setSnapshot] = useState<WeatherSnapshot | null>(() => loadWeatherCache());
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  // load를 useCallback([])으로 고정해야 마운트 효과가 한 번만 도는데,
  // 그러면 콜백이 최신 지역을 못 보므로 ref로도 들고 있는다.
  const locationRef = useRef<WeatherLocation | null>(initialLocation);
  const inFlightKeyRef = useRef<string | null>(null);
  const seqRef = useRef(0);
  const aliveRef = useRef(true);

  useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
    };
  }, []);

  const load = useCallback(async () => {
    const key = targetKey(locationRef.current);
    // 같은 대상 요청이 이미 날아가 있으면 겹쳐 쏘지 않는다.
    // (StrictMode의 이중 마운트, 자동 갱신과 새로고침 버튼이 겹치는 경우 등)
    if (inFlightKeyRef.current === key) return;
    inFlightKeyRef.current = key;

    // 지역을 바꾸면 이전 요청이 아직 살아 있을 수 있다. 항상 마지막 요청이 이긴다.
    const seq = ++seqRef.current;
    const isLatest = () => seqRef.current === seq;

    setLoading(true);
    try {
      let target = locationRef.current;
      if (!target) {
        // 저장해 둔 지역이 없을 때만 IP로 자동 감지한다
        target = await detectLocationByIp();
        if (!aliveRef.current || !isLatest()) return;
        locationRef.current = target;
        setLocation(target);
      }

      const next = await fetchWeatherSnapshot(target);
      if (!aliveRef.current || !isLatest()) return;
      setSnapshot(next);
      saveWeatherCache(next);
      setFailed(false);
    } catch {
      // 오프라인 등 — 캐시된 값은 그대로 두고 실패 표시만 올린다
      if (aliveRef.current && isLatest()) setFailed(true);
    } finally {
      if (inFlightKeyRef.current === key) inFlightKeyRef.current = null;
      if (aliveRef.current && isLatest()) setLoading(false);
    }
  }, []);

  // 첫 진입: 캐시를 이미 보여준 채로 백그라운드에서 최신값을 받아온다
  useEffect(() => {
    void load();
  }, [load]);

  // 공유 시계의 분 변화를 세다가 REFRESH_MINUTES마다 한 번 갱신
  useEffect(() => {
    let elapsed = 0;
    return subscribeMinute(() => {
      elapsed += 1;
      if (elapsed < REFRESH_MINUTES) return;
      elapsed = 0;
      void load();
    });
  }, [load]);

  const changeLocation = useCallback(
    (next: WeatherLocation) => {
      locationRef.current = next;
      setLocation(next);
      // 직접 고른 지역은 다음 실행부터 IP 감지보다 우선한다
      saveSettings({ weatherLocation: next });
      void load();
    },
    [load],
  );

  return { snapshot, location, loading, failed, refresh: load, changeLocation };
}
