import { AlarmClock, Hourglass, Timer } from 'lucide-react';
import { stopwatchElapsed, useToolStore } from '../store/toolStore';
import { formatCountdown, formatStopwatch } from '../utils/duration';
import styles from './ToolsWidget.module.css';

/**
 * 사이드바에서 스톱워치·타이머로 들어가는 입구.
 *
 * 두 도구는 화면을 나가도 계속 돌아가므로, 캘린더로 돌아왔을 때 "지금 뭔가 돌고 있다"는 걸
 * 알 수 있어야 한다. 그래서 버튼 아래에 현재 상태를 한 줄로 같이 보여준다.
 * 여기서는 흐르는 숫자를 매 프레임 갱신할 필요가 없으므로(사이드바의 요약일 뿐이다)
 * rAF 티커는 구독하지 않고, 스토어가 바뀔 때만 다시 그린다.
 */
export function ToolsWidget() {
  const openTool = useToolStore((s) => s.openTool);
  const stopwatch = useToolStore((s) => s.stopwatch);
  const timer = useToolStore((s) => s.timer);

  const swElapsed = stopwatchElapsed(stopwatch);
  const swLabel = stopwatch.running
    ? '측정 중'
    : swElapsed > 0
      ? formatStopwatch(swElapsed).main
      : '기록 없음';

  const timerLabel = timer.finished
    ? '완료!'
    : timer.running
      ? '카운트다운'
      : formatCountdown(timer.restMs);

  return (
    <section className={styles.widget} aria-label="시간 도구">
      <h2 className={styles.widgetTitle}>
        <Hourglass size={16} aria-hidden /> 시간 도구
      </h2>

      <div className={styles.buttons}>
        <button
          type="button"
          className={`${styles.toolButton} ${stopwatch.running ? styles.toolActive : ''}`}
          onClick={() => openTool('stopwatch')}
        >
          <Timer size={18} aria-hidden />
          <span className={styles.toolName}>스톱워치</span>
          <span className={styles.toolState}>
            {stopwatch.running && <span className={styles.pulse} aria-hidden />}
            {swLabel}
          </span>
        </button>

        <button
          type="button"
          className={`${styles.toolButton} ${
            timer.running || timer.finished ? styles.toolActive : ''
          }`}
          onClick={() => openTool('timer')}
        >
          <AlarmClock size={18} aria-hidden />
          <span className={styles.toolName}>타이머</span>
          <span className={styles.toolState}>
            {timer.running && <span className={styles.pulse} aria-hidden />}
            {timerLabel}
          </span>
        </button>
      </div>
    </section>
  );
}
