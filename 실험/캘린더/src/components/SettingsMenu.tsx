import { Download, FolderOpen, Monitor, Moon, ScrollText, Settings, Sun, Upload } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { getTodayKey } from '../store/clock';
import { useCalendarStore } from '../store/calendarStore';
import type { CalendarEvent } from '../types/event';
import { useThemeStore } from '../store/themeStore';
import { THEME_PREFERENCES, type ThemePreference } from '../types/theme';
import {
  getBackupStatus,
  isBackupAvailable,
  openBackupFolder,
  type BackupStatus,
} from '../utils/backup';
import { isDiagnosticsAvailable, openLogFolder } from '../utils/diagnostics';
import { parseEvents } from '../utils/storage';
import { ConfirmDialog } from './ConfirmDialog';
import { SegmentedControl } from './SegmentedControl';
import styles from './SettingsMenu.module.css';

/** '방금', '12분 전', '3일 전' — 자동 백업 시각을 짧게 */
function formatAgo(timestamp: number): string {
  const minutes = Math.floor((Date.now() - timestamp) / 60_000);
  if (minutes < 1) return '방금';
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  return `${Math.floor(hours / 24)}일 전`;
}

const THEME_OPTIONS: Record<ThemePreference, { label: string; Icon: typeof Sun }> = {
  light: { label: '라이트', Icon: Sun },
  dark: { label: '다크', Icon: Moon },
  system: { label: '시스템', Icon: Monitor },
};

export function SettingsMenu() {
  const events = useCalendarStore((s) => s.events);
  const replaceAllEvents = useCalendarStore((s) => s.replaceAllEvents);
  const bgEffect = useCalendarStore((s) => s.bgEffect);
  const toggleBgEffect = useCalendarStore((s) => s.toggleBgEffect);
  const themePreference = useThemeStore((s) => s.preference);
  const setThemePreference = useThemeStore((s) => s.setPreference);
  const [open, setOpen] = useState(false);
  const [pendingImport, setPendingImport] = useState<CalendarEvent[] | null>(null);
  const [backup, setBackup] = useState<BackupStatus | null>(null);
  const [importError, setImportError] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  // 메뉴를 열 때만 백업 상태를 물어본다 (자주 여는 화면이 아니라 이 정도면 충분하다)
  useEffect(() => {
    if (!open || !isBackupAvailable()) return;
    let cancelled = false;
    void getBackupStatus().then((status) => {
      if (!cancelled) setBackup(status);
    });
    return () => {
      cancelled = true;
    };
  }, [open]);

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(events, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `my-calendar-backup-${getTodayKey()}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    setOpen(false);
  };

  const handleFile = async (file: File) => {
    const text = await file.text();
    const parsed = parseEvents(text);
    if (!parsed) {
      setImportError(true);
      return;
    }
    setPendingImport(parsed);
  };

  return (
    <div ref={rootRef} className={styles.root}>
      <button
        type="button"
        className={styles.trigger}
        aria-label="설정"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <Settings size={18} />
      </button>

      {open && (
        <div className={styles.menu} role="menu">
          <div className={styles.sectionLabel} id="theme-label">
            화면 테마
          </div>
          <SegmentedControl
            className={styles.segment}
            count={THEME_PREFERENCES.length}
            activeIndex={Math.max(0, THEME_PREFERENCES.indexOf(themePreference))}
            role="radiogroup"
            ariaLabelledBy="theme-label"
          >
            {THEME_PREFERENCES.map((option) => {
              const { label, Icon } = THEME_OPTIONS[option];
              const active = themePreference === option;
              return (
                <button
                  type="button"
                  key={option}
                  role="radio"
                  aria-checked={active}
                  className={`${styles.segmentButton} ${active ? styles.segmentActive : ''}`}
                  onClick={() => setThemePreference(option)}
                >
                  <Icon size={14} aria-hidden />
                  {label}
                </button>
              );
            })}
          </SegmentedControl>
          <div className={styles.divider} />
          <label className={styles.toggleRow}>
            <span className={styles.toggleText}>
              <Moon size={15} aria-hidden /> 배경 시간 흐름 효과
            </span>
            <input
              type="checkbox"
              className={styles.switch}
              checked={bgEffect}
              onChange={toggleBgEffect}
            />
          </label>
          <div className={styles.divider} />
          <button type="button" role="menuitem" className={styles.menuItem} onClick={handleExport}>
            <Download size={15} aria-hidden /> JSON으로 내보내기
          </button>
          <button
            type="button"
            role="menuitem"
            className={styles.menuItem}
            onClick={() => fileRef.current?.click()}
          >
            <Upload size={15} aria-hidden /> JSON 불러오기
          </button>

          {/* 자동 백업은 Electron 앱에서만 동작한다. 브라우저에서는 이 구역이 통째로 빠진다. */}
          {isBackupAvailable() && (
            <>
              <div className={styles.divider} />
              <button
                type="button"
                role="menuitem"
                className={styles.menuItem}
                onClick={openBackupFolder}
              >
                <FolderOpen size={15} aria-hidden /> 백업 폴더 열기
              </button>
              <p className={styles.backupNote}>
                {backup?.lastBackupAt
                  ? `마지막 자동 백업: ${formatAgo(backup.lastBackupAt)} · ${backup.count}개 보관`
                  : '아직 자동 백업이 없어요'}
              </p>
            </>
          )}

          {/* 화면이 비거나 이상하게 뜰 때 보낼 파일이 어디 있는지 알려 주는 조용한 창구 */}
          {isDiagnosticsAvailable() && (
            <>
              <div className={styles.divider} />
              <button
                type="button"
                role="menuitem"
                className={styles.menuItem}
                onClick={() => void openLogFolder()}
              >
                <ScrollText size={15} aria-hidden /> 오류 로그 폴더 열기
              </button>
              <p className={styles.backupNote}>
                화면이 비어 보이면 이 폴더의 render-errors.log를 보내 주세요
              </p>
            </>
          )}
        </div>
      )}

      <input
        ref={fileRef}
        type="file"
        accept=".json,application/json"
        className={styles.fileInput}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleFile(file);
          e.target.value = '';
        }}
      />

      <ConfirmDialog
        open={pendingImport !== null}
        title="백업 불러오기"
        message={`백업 파일의 일정 ${pendingImport?.length ?? 0}개로 현재 일정 ${events.length}개를 교체할까요? 기존 일정은 사라져요.`}
        confirmLabel="불러오기"
        onCancel={() => setPendingImport(null)}
        onConfirm={() => {
          if (pendingImport) replaceAllEvents(pendingImport);
          setPendingImport(null);
          setOpen(false);
        }}
      />

      <ConfirmDialog
        open={importError}
        title="불러오기 실패"
        message="올바른 캘린더 백업 파일이 아니에요. '내보내기'로 만든 JSON 파일인지 확인해 주세요."
        confirmLabel="확인"
        hideCancel
        onCancel={() => setImportError(false)}
        onConfirm={() => setImportError(false)}
      />
    </div>
  );
}
