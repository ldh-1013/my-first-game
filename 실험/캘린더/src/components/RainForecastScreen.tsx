import { CloudRain } from 'lucide-react';
import { useMemo } from 'react';
import { useNow } from '../store/clock';
import { useWeather } from '../hooks/useWeather';
import {
  RAIN_CHANCE_THRESHOLD,
  describeRainWindows,
  findRainWindows,
  formatHourLabel,
} from '../utils/weather';
import { ToolScreen } from './ToolScreen';
import styles from './RainForecastScreen.module.css';

/** 0~23시를 빠짐없이 그린다 — 응답에 빠진 시간이 있어도 축이 어긋나지 않게 */
const HOURS = Array.from({ length: 24 }, (_, i) => i);

/**
 * 오늘 비가 언제 오는지 시간대별로 보여주는 전체 화면.
 *
 * 위젯의 "오늘 비 소식이 있어요" 한 줄로는 우산을 언제 챙길지 알 수 없다.
 * 스톱워치·타이머와 같은 ToolScreen 껍데기를 써서 캘린더 밖으로 나갔다가
 * 뒤로가기나 Esc로 돌아온다.
 *
 * 색은 파랑 한 가지 색조 안에서 진하기만 다르게 쓴다. 비는 좋고 나쁨을 매길 일이
 * 아니라서 미세먼지 배지 같은 빨강/초록 등급색을 여기에 들이지 않는다.
 */
export function RainForecastScreen() {
  const { snapshot } = useWeather();
  // 지금 시각 표시선과 '지난 시간대' 판정에만 쓰므로 분 단위면 충분하다
  const now = useNow('minute');
  const nowHour = now.getHours() + now.getMinutes() / 60;

  const hourly = snapshot?.hourlyRain ?? null;

  const byHour = useMemo(() => {
    const map = new Map<number, { probability: number | null; amount: number | null }>();
    for (const row of hourly ?? []) {
      map.set(row.hour, { probability: row.probability, amount: row.amount });
    }
    return map;
  }, [hourly]);

  const windows = useMemo(
    () => findRainWindows(hourly, Math.floor(nowHour)),
    [hourly, nowHour],
  );
  const summary = describeRainWindows(windows);

  const totalAmount = (hourly ?? []).reduce((sum, row) => sum + (row.amount ?? 0), 0);

  return (
    <ToolScreen title="오늘 비 예보" icon={<CloudRain size={18} aria-hidden />}>
      <div className={styles.wrap}>
        {hourly === null ? (
          <p className={styles.summary}>시간대별 정보를 받아오지 못했어요</p>
        ) : (
          <>
            <p className={styles.summary}>
              {summary ?? '남은 시간에는 비 소식이 없어요'}
            </p>
            <p className={styles.sub}>
              {`강수확률 ${RAIN_CHANCE_THRESHOLD}% 이상인 시간을 이어서 묶었어요`}
              {totalAmount > 0 && ` · 오늘 예상 강수량 ${totalAmount.toFixed(1)}mm`}
            </p>

            <div className={styles.chart}>
              {HOURS.map((hour) => {
                const row = byHour.get(hour);
                const probability = row?.probability ?? null;
                const past = hour + 1 <= nowHour;
                const label =
                  probability === null
                    ? `${formatHourLabel(hour)} 정보 없음`
                    : `${formatHourLabel(hour)} 강수확률 ${Math.round(probability)}%` +
                      (row?.amount ? ` · ${row.amount.toFixed(1)}mm` : '');
                return (
                  <div key={hour} className={styles.column} title={label}>
                    <div className={styles.track}>
                      <div
                        className={`${styles.bar} ${past ? styles.barPast : ''}`}
                        style={{
                          // 높이와 진하기를 같은 값에서 뽑아, 눈으로 본 크기와 수치가 어긋나지 않게 한다
                          height: `${probability === null ? 0 : Math.max(probability, 2)}%`,
                          opacity: probability === null ? 0 : 0.3 + (probability / 100) * 0.7,
                        }}
                        aria-hidden
                      />
                    </div>
                    <span className={styles.hourLabel}>{hour % 3 === 0 ? hour : ''}</span>
                    <span className={styles.srOnly}>{label}</span>
                  </div>
                );
              })}

              {/* 지금 시각 — WeekView의 nowLine과 같은 표식, 방향만 세로 */}
              <div
                className={styles.nowLine}
                style={{ left: `${(nowHour / 24) * 100}%` }}
                aria-hidden
              />
            </div>

            <div className={styles.legend}>
              <span>0%</span>
              <div className={styles.legendBar} aria-hidden />
              <span>100%</span>
            </div>
          </>
        )}
      </div>
    </ToolScreen>
  );
}
