import { Flag, Pause, Play, RotateCcw, Timer } from 'lucide-react';
import { useMemo } from 'react';
import { useAnimationTick } from '../store/ticker';
import { stopwatchElapsed, useToolStore } from '../store/toolStore';
import { formatLap, formatStopwatch } from '../utils/duration';
import { ToolScreen } from './ToolScreen';
import styles from './StopwatchScreen.module.css';

interface LapRow {
  index: number;
  total: number;
  split: number;
}

export function StopwatchScreen() {
  const screen = useToolStore((s) => s.screen);
  const stopwatch = useToolStore((s) => s.stopwatch);
  const toggleStopwatch = useToolStore((s) => s.toggleStopwatch);
  const resetStopwatch = useToolStore((s) => s.resetStopwatch);
  const addLap = useToolStore((s) => s.addLap);

  // 이 화면이 보이면서 실제로 흐르고 있을 때만 매 프레임 다시 그린다.
  // 캘린더로 나가 있으면 구독을 끊어 rAF가 아예 돌지 않는다(시간은 그래도 흐른다).
  useAnimationTick(screen === 'stopwatch' && stopwatch.running);

  const elapsed = stopwatchElapsed(stopwatch);
  const { main, centi } = formatStopwatch(elapsed);

  // 저장된 랩은 '그 순간의 총 경과'라서, 구간(split)은 직전 랩과의 차이로 만든다
  const laps = useMemo<LapRow[]>(
    () =>
      stopwatch.laps.map((total, i) => ({
        index: i + 1,
        total,
        split: total - (i > 0 ? stopwatch.laps[i - 1] : 0),
      })),
    [stopwatch.laps],
  );

  const splits = laps.map((lap) => lap.split);
  const fastest = laps.length > 1 ? Math.min(...splits) : -1;
  const slowest = laps.length > 1 ? Math.max(...splits) : -1;

  const started = elapsed > 0 || stopwatch.running;
  const mainLabel = stopwatch.running ? '일시정지' : started ? '재개' : '시작';

  return (
    <ToolScreen title="스톱워치" icon={<Timer size={22} aria-hidden />}>
      <div className={styles.panel}>
        <p
          className={`${styles.display} ${stopwatch.running ? styles.displayRunning : ''}`}
          role="timer"
          aria-live="off"
        >
          <span className={styles.main}>{main}</span>
          <span className={styles.centi}>.{centi}</span>
        </p>

        <p className={styles.caption}>
          {stopwatch.running ? '측정 중' : started ? '일시정지됨' : '준비 완료'}
        </p>

        <div className={styles.controls}>
          <button
            type="button"
            className={styles.subButton}
            onClick={resetStopwatch}
            disabled={!started && laps.length === 0}
          >
            <RotateCcw size={16} aria-hidden /> 리셋
          </button>

          <button
            type="button"
            className={`${styles.mainButton} ${stopwatch.running ? styles.mainButtonPause : ''}`}
            onClick={toggleStopwatch}
          >
            {stopwatch.running ? <Pause size={18} aria-hidden /> : <Play size={18} aria-hidden />}
            {mainLabel}
          </button>

          <button
            type="button"
            className={styles.subButton}
            onClick={addLap}
            disabled={!stopwatch.running}
          >
            <Flag size={16} aria-hidden /> 랩
          </button>
        </div>

        {laps.length > 0 && (
          <div className={styles.laps}>
            <div className={`${styles.lapRow} ${styles.lapHead}`}>
              <span>랩</span>
              <span>구간</span>
              <span>누적</span>
            </div>
            <div className={styles.lapList}>
              {/* 방금 찍은 랩이 위로 오도록 뒤집어 보여준다 */}
              {[...laps].reverse().map((lap) => (
                <div key={lap.index} className={styles.lapRow}>
                  <span className={styles.lapIndex}>
                    {lap.index}
                    {lap.split === fastest && <em className={styles.badgeFast}>최고</em>}
                    {lap.split === slowest && <em className={styles.badgeSlow}>최저</em>}
                  </span>
                  <span className={styles.lapSplit}>{formatLap(lap.split)}</span>
                  <span className={styles.lapTotal}>{formatLap(lap.total)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </ToolScreen>
  );
}
