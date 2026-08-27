import { addMonths, addWeeks } from 'date-fns';
import { v4 as uuid } from 'uuid';
import { create } from 'zustand';
import type { CalendarEvent, EventInput } from '../types/event';
import { fromDateKey } from '../utils/dateUtils';
import { getNow } from './clock';
import {
  loadEvents,
  loadMoods,
  loadSettings,
  saveEventsDebounced,
  saveMoodsDebounced,
  saveSettings,
} from '../utils/storage';

export type ViewMode = 'month' | 'week' | 'constellation' | 'mood';

interface CalendarStore {
  events: CalendarEvent[];
  moods: Record<string, number>;
  bgEffect: boolean;
  viewMode: ViewMode;
  viewDate: Date;
  selectedDate: string | null;
  addEvent: (input: EventInput) => void;
  updateEvent: (id: string, patch: Partial<EventInput>) => void;
  deleteEvent: (id: string) => void;
  toggleComplete: (id: string) => void;
  replaceAllEvents: (events: CalendarEvent[]) => void;
  setMood: (date: string, level: number) => void;
  toggleBgEffect: () => void;
  setViewMode: (mode: ViewMode) => void;
  goPrev: () => void;
  goNext: () => void;
  /** 특정 연/월로 바로 이동 (month는 0-based, Date와 동일) */
  goToMonth: (year: number, month: number) => void;
  goToday: () => void;
  selectDate: (date: string | null) => void;
  openDate: (date: string) => void;
}

export const useCalendarStore = create<CalendarStore>((set) => ({
  events: loadEvents(),
  moods: loadMoods(),
  bgEffect: loadSettings().bgEffect,
  viewMode: 'month',
  viewDate: getNow(),
  selectedDate: null,

  addEvent: (input) =>
    set((state) => {
      const now = getNow().toISOString();
      const event: CalendarEvent = { ...input, id: uuid(), createdAt: now, updatedAt: now };
      return { events: [...state.events, event] };
    }),

  updateEvent: (id, patch) =>
    set((state) => ({
      events: state.events.map((event) =>
        event.id === id ? { ...event, ...patch, updatedAt: getNow().toISOString() } : event,
      ),
    })),

  deleteEvent: (id) =>
    set((state) => ({ events: state.events.filter((event) => event.id !== id) })),

  // setMood와 같은 결: 같은 걸 다시 누르면 해제된다
  toggleComplete: (id) =>
    set((state) => ({
      events: state.events.map((event) =>
        event.id === id
          ? { ...event, completed: !event.completed, updatedAt: getNow().toISOString() }
          : event,
      ),
    })),

  replaceAllEvents: (events) => set({ events }),

  setMood: (date, level) =>
    set((state) => {
      const moods = { ...state.moods };
      if (moods[date] === level) delete moods[date]; // 같은 기분 다시 누르면 해제
      else moods[date] = level;
      return { moods };
    }),

  toggleBgEffect: () => set((state) => ({ bgEffect: !state.bgEffect })),

  setViewMode: (viewMode) => set({ viewMode }),

  goPrev: () =>
    set((state) => ({
      viewDate:
        state.viewMode === 'week' ? addWeeks(state.viewDate, -1) : addMonths(state.viewDate, -1),
    })),

  goNext: () =>
    set((state) => ({
      viewDate:
        state.viewMode === 'week' ? addWeeks(state.viewDate, 1) : addMonths(state.viewDate, 1),
    })),

  // 해당 달의 1일로 맞춘다. 주간 뷰에서도 getWeekDays가 그 1일이 속한 주를 잡아 준다.
  goToMonth: (year, month) => set({ viewDate: new Date(year, month, 1) }),

  goToday: () => set({ viewDate: getNow() }),

  selectDate: (selectedDate) => set({ selectedDate }),

  openDate: (date) => set({ viewDate: fromDateKey(date), selectedDate: date }),
}));

// 상태가 바뀔 때마다 해당 슬라이스만 디바운스 저장
useCalendarStore.subscribe((state, prevState) => {
  if (state.events !== prevState.events) saveEventsDebounced(state.events);
  if (state.moods !== prevState.moods) saveMoodsDebounced(state.moods);
  if (state.bgEffect !== prevState.bgEffect) saveSettings({ bgEffect: state.bgEffect });
});
