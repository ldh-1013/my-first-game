import { CalendarHeart, ChevronLeft, ChevronRight } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { CalendarGrid } from './components/CalendarGrid';
import { Celebration } from './components/Celebration';
import { ClockWidget } from './components/ClockWidget';
import { ConstellationView } from './components/ConstellationView';
import { DateDetailPanel } from './components/DateDetailPanel';
import { MonthJumpPopover } from './components/MonthJumpPopover';
import { MoodHeatmap } from './components/MoodHeatmap';
import { OnThisDay } from './components/OnThisDay';
import { RainForecastScreen } from './components/RainForecastScreen';
import { RecapScreen } from './components/RecapScreen';
import { RhythmInsight } from './components/RhythmInsight';
import { SearchBar } from './components/SearchBar';
import { SegmentedControl } from './components/SegmentedControl';
import { SettingsMenu } from './components/SettingsMenu';
import { StatsWidget } from './components/StatsWidget';
import { StopwatchScreen } from './components/StopwatchScreen';
import { TimerScreen } from './components/TimerScreen';
import { TodoWidget } from './components/TodoWidget';
import { ToolsWidget } from './components/ToolsWidget';
import { UpcomingEvents } from './components/UpcomingEvents';
import { WeatherWidget } from './components/WeatherWidget';
import { WeekView } from './components/WeekView';
import { useAutoBackup } from './hooks/useAutoBackup';
import { useTimeGrain } from './hooks/useTimeGrain';
import { useCalendarStore, type ViewMode } from './store/calendarStore';
import { useToolStore } from './store/toolStore';
import { formatMonthTitle, formatWeekRange } from './utils/dateUtils';
import { isTypingTarget } from './utils/keyboard';
import styles from './App.module.css';

const VIEW_TABS: { mode: ViewMode; label: string }[] = [
  { mode: 'month', label: '월간' },
  { mode: 'week', label: '주간' },
  { mode: 'constellation', label: '성좌' },
  { mode: 'mood', label: '감정' },
];

function viewTitle(mode: ViewMode, viewDate: Date): string {
  switch (mode) {
    case 'month':
      return formatMonthTitle(viewDate);
    case 'week':
      return formatWeekRange(viewDate);
    case 'constellation':
      return '일정 성좌';
    case 'mood':
      return '감정 기록';
  }
}

export default function App() {
  const viewMode = useCalendarStore((s) => s.viewMode);
  const viewDate = useCalendarStore((s) => s.viewDate);
  const bgEffect = useCalendarStore((s) => s.bgEffect);
  const setViewMode = useCalendarStore((s) => s.setViewMode);
  const goPrev = useCalendarStore((s) => s.goPrev);
  const goNext = useCalendarStore((s) => s.goNext);
  const goToday = useCalendarStore((s) => s.goToday);
  const screen = useToolStore((s) => s.screen);
  // 미니 달력이 열려 있는 동안은 전역 ←/→가 뒤에서 같이 달을 넘기면 안 된다
  const [jumpOpen, setJumpOpen] = useState(false);

  const handleJumpOpenChange = useCallback((open: boolean) => setJumpOpen(open), []);

  useTimeGrain(bgEffect);
  useAutoBackup();

  const showNav = viewMode === 'month' || viewMode === 'week';

  // 전역 단축키: ←/→ 이동, T 오늘로 이동 ('/'는 SearchBar에서 처리)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isTypingTarget(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;
      // 스톱워치·타이머를 보는 동안 뒤에서 몰래 날짜가 넘어가 있으면 안 된다
      if (useToolStore.getState().screen !== 'calendar') return;
      if (jumpOpen) return;
      const { goPrev, goNext, goToday, selectedDate, viewMode } = useCalendarStore.getState();
      if (viewMode !== 'month' && viewMode !== 'week') return;
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        goPrev();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        goNext();
      } else if ((e.key === 't' || e.key === 'T' || e.key === 'ㅅ') && !selectedDate) {
        goToday();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [jumpOpen]);

  // Esc로 도구 화면에서 캘린더로 복귀 — 도구 화면일 때만 등록해 다른 Esc 처리와 겹치지 않게 한다
  useEffect(() => {
    if (screen === 'calendar') return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') useToolStore.getState().closeTool();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [screen]);

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <h1 className={styles.brand}>
          <CalendarHeart size={24} className={styles.brandIcon} aria-hidden />
          나의 캘린더
        </h1>
        <div className={styles.headerCenter}>
          <SearchBar />
        </div>
        <SettingsMenu />
      </header>

      {/*
        세 화면을 같은 그리드 칸에 겹쳐 두고 opacity/transform만 바꿔 갈아 끼운다.
        - 모달이나 옆에서 나오는 패널이 아니라 화면 자체가 교체되는 인상을 주면서,
          크로스페이드라 전환이 끊겨 보이지 않는다.
        - 셋 다 마운트된 채로 두므로 도구 화면을 나갔다 와도 입력값이 그대로 남는다.
          (흐르는 시간 자체는 toolStore가 들고 있어 마운트 여부와 애초에 무관하다.)
        - 칸 높이가 가장 큰 화면(보통 캘린더)에 맞춰지므로 전환 중 레이아웃이 튀지 않는다.
      */}
      <div className={styles.screens}>
        <div
          className={`${styles.screen} ${screen === 'calendar' ? styles.screenActive : ''}`}
          aria-hidden={screen !== 'calendar'}
        >
          <div className={styles.layout}>
            <main className={styles.main}>
              <ClockWidget />
              <RhythmInsight />

              <section className={styles.calendarCard}>
                <div className={styles.toolbar}>
                  {showNav ? (
                    <MonthJumpPopover
                      title={viewTitle(viewMode, viewDate)}
                      onOpenChange={handleJumpOpenChange}
                    />
                  ) : (
                    <h2 className={styles.viewTitle}>{viewTitle(viewMode, viewDate)}</h2>
                  )}
                  {showNav && (
                    <div className={styles.navGroup}>
                      <button
                        type="button"
                        className={styles.navButton}
                        aria-label={viewMode === 'month' ? '이전 달' : '이전 주'}
                        onClick={goPrev}
                      >
                        <ChevronLeft size={18} />
                      </button>
                      <button type="button" className={styles.todayButton} onClick={goToday}>
                        오늘
                      </button>
                      <button
                        type="button"
                        className={styles.navButton}
                        aria-label={viewMode === 'month' ? '다음 달' : '다음 주'}
                        onClick={goNext}
                      >
                        <ChevronRight size={18} />
                      </button>
                    </div>
                  )}
                  <SegmentedControl
                    className={styles.toggle}
                    count={VIEW_TABS.length}
                    activeIndex={Math.max(0, VIEW_TABS.findIndex((tab) => tab.mode === viewMode))}
                    role="tablist"
                    ariaLabel="보기 전환"
                  >
                    {VIEW_TABS.map((tab) => (
                      <button
                        type="button"
                        key={tab.mode}
                        role="tab"
                        aria-selected={viewMode === tab.mode}
                        className={`${styles.toggleButton} ${
                          viewMode === tab.mode ? styles.toggleActive : ''
                        }`}
                        onClick={() => setViewMode(tab.mode)}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </SegmentedControl>
                </div>

                {viewMode === 'month' && <CalendarGrid />}
                {viewMode === 'week' && <WeekView />}
                {viewMode === 'constellation' && <ConstellationView />}
                {viewMode === 'mood' && <MoodHeatmap />}

                {showNav && (
                  <p className={styles.shortcutHint}>
                    <kbd>←</kbd> <kbd>→</kbd> 이동 · <kbd>T</kbd> 오늘 · <kbd>/</kbd> 검색
                  </p>
                )}
              </section>
            </main>

            <aside className={styles.sidebar}>
              {/* 날씨는 사이드바에서 가장 자주 바뀌고 매일 첫눈에 확인하는 정보라 맨 위 */}
              <WeatherWidget />
              <UpcomingEvents />
              {/* 오늘 처리해야 하는 행동 항목이라 정보성 위젯들보다 위 */}
              <TodoWidget />
              {/* 가까운 미래(다가오는 일정) 다음에 지난 기록을 둔다 */}
              <OnThisDay />
              <StatsWidget />
              <ToolsWidget />
            </aside>
          </div>
        </div>

        <div
          className={`${styles.screen} ${screen === 'stopwatch' ? styles.screenActive : ''}`}
          aria-hidden={screen !== 'stopwatch'}
        >
          <StopwatchScreen />
        </div>

        <div
          className={`${styles.screen} ${screen === 'timer' ? styles.screenActive : ''}`}
          aria-hidden={screen !== 'timer'}
        >
          <TimerScreen />
        </div>

        <div
          className={`${styles.screen} ${screen === 'rain' ? styles.screenActive : ''}`}
          aria-hidden={screen !== 'rain'}
        >
          <RainForecastScreen />
        </div>

        <div
          className={`${styles.screen} ${screen === 'recap' ? styles.screenActive : ''}`}
          aria-hidden={screen !== 'recap'}
        >
          <RecapScreen />
        </div>
      </div>

      <DateDetailPanel />
      <Celebration />
    </div>
  );
}
