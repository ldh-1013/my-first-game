import { CalendarHeart, ChevronLeft, ChevronRight } from 'lucide-react';
import { useEffect } from 'react';
import { CalendarGrid } from './components/CalendarGrid';
import { Celebration } from './components/Celebration';
import { ClockWidget } from './components/ClockWidget';
import { ConstellationView } from './components/ConstellationView';
import { DateDetailPanel } from './components/DateDetailPanel';
import { MoodHeatmap } from './components/MoodHeatmap';
import { RhythmInsight } from './components/RhythmInsight';
import { SearchBar } from './components/SearchBar';
import { SettingsMenu } from './components/SettingsMenu';
import { StatsWidget } from './components/StatsWidget';
import { UpcomingEvents } from './components/UpcomingEvents';
import { WeekView } from './components/WeekView';
import { useTimeGrain } from './hooks/useTimeGrain';
import { useCalendarStore, type ViewMode } from './store/calendarStore';
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

  useTimeGrain(bgEffect);

  const showNav = viewMode === 'month' || viewMode === 'week';

  // 전역 단축키: ←/→ 이동, T 오늘로 이동 ('/'는 SearchBar에서 처리)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isTypingTarget(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;
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
  }, []);

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

      <div className={styles.layout}>
        <main className={styles.main}>
          <ClockWidget />
          <RhythmInsight />

          <section className={styles.calendarCard}>
            <div className={styles.toolbar}>
              <h2 className={styles.viewTitle}>{viewTitle(viewMode, viewDate)}</h2>
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
              <div className={styles.toggle} role="tablist" aria-label="보기 전환">
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
              </div>
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
          <UpcomingEvents />
          <StatsWidget />
        </aside>
      </div>

      <DateDetailPanel />
      <Celebration />
    </div>
  );
}
