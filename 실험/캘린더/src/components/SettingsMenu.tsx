import { Download, Moon, Settings, Upload } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useCalendarStore } from '../store/calendarStore';
import type { CalendarEvent } from '../types/event';
import { toDateKey } from '../utils/dateUtils';
import { parseEvents } from '../utils/storage';
import { ConfirmDialog } from './ConfirmDialog';
import styles from './SettingsMenu.module.css';

export function SettingsMenu() {
  const events = useCalendarStore((s) => s.events);
  const replaceAllEvents = useCalendarStore((s) => s.replaceAllEvents);
  const bgEffect = useCalendarStore((s) => s.bgEffect);
  const toggleBgEffect = useCalendarStore((s) => s.toggleBgEffect);
  const [open, setOpen] = useState(false);
  const [pendingImport, setPendingImport] = useState<CalendarEvent[] | null>(null);
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

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(events, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `my-calendar-backup-${toDateKey(new Date())}.json`;
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
