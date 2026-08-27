import { getLunarAnchors, hasLunarData } from './lunarHolidayTable';

/**
 * 대한민국 공휴일 계산.
 *
 * 먼저 알아둘 것: 공휴일은 몇 년치를 미리 100% 확정할 수 있는 값이 아니다.
 * 다음 해 공휴일이 담긴 공식 월력요항은 주무 부처(우주항공청)가 매년 6월 말에야 발표하고,
 * 임시공휴일처럼 몇 달 전에 갑자기 지정되는 날도 있다. 한국천문연구원의 공식 API조차
 * "수기로 입력한 약 1년치"만 제공한다고 밝히고 있다.
 *
 * 그래서 이 모듈의 목표는 "먼 미래까지 완벽히 맞추기"가 아니라
 * **무엇이 확정이고 무엇이 계산값인지 구분해서 알려주기**다. isProjected가 그 역할을 한다.
 *
 * 다루지 않는 것: 임시공휴일. 정부가 그때그때 지정하므로 예측이 불가능하다.
 * (예: 2025-01-27은 설 연휴에 붙은 임시공휴일이었지만 사전에 알 방법이 없었다.)
 */

export interface Holiday {
  /** 'YYYY-MM-DD' */
  date: string;
  /** '광복절', '설날' 등. 같은 날 겹치면 '어린이날 · 부처님오신날'처럼 이어 붙는다 */
  name: string;
  isSubstitute: boolean;
  /** 대체공휴일이면 원래 공휴일의 날짜 */
  substituteFor?: string;
  /** 공식 월력요항 발표 전이라 계산으로 뽑은 값인지 */
  isProjected: boolean;
}

/**
 * 공식 월력요항이 발표되어 확정된 마지막 연도.
 *
 * 매년 6월 말 새 월력요항이 나오면 이 숫자만 올리면 된다.
 * 2027년분은 2026-06-29 관보 공고 제2026-0078호로 발표되었다.
 */
export const LATEST_CONFIRMED_YEAR = 2027;

/**
 * 대체공휴일 제도가 처음 시행된 해(2014년 설날부터).
 * 이전 연도를 계산할 때 있지도 않았던 대체공휴일을 만들어내지 않기 위한 하한선이다.
 *
 * 한계: 2014~2020년에는 설날·추석·어린이날에만 적용됐고 삼일절 등은 2021년에야 추가됐는데,
 * 그 시기 구분까지는 모델링하지 않았다. 과거 연도를 거슬러 보면 대체공휴일이 실제보다
 * 많게 나올 수 있다. 이 앱은 앞으로의 일정을 위한 것이라 거기까지는 맞추지 않았다.
 */
export const SUBSTITUTE_SINCE_YEAR = 2014;

/**
 * 대체공휴일 규칙.
 *
 * 「관공서의 공휴일에 관한 규정」 제3조. 2021년(삼일절·광복절·개천절·한글날·어린이날),
 * 2023년(부처님오신날·성탄절)에 확대 개정된 이력이 있어 또 바뀔 수 있으므로
 * 여기 한 곳에만 모아 둔다. 법이 바뀌면 이 표만 고치면 된다.
 *
 * 규정상 '일요일'은 그 자체가 공휴일(제2조 제1호)이고 토요일은 공휴일이 아니다.
 * 그래서 조문의 "다른 공휴일과 겹치는 경우"에는 일요일이 자동으로 포함되고,
 * 토요일은 따로 명시된 공휴일에만 적용된다.
 *   - 설날·추석 연휴: 다른 공휴일(=일요일 포함)과 겹칠 때만. 토요일은 제외.
 *   - 어린이날: 토요일 또는 다른 공휴일과 겹칠 때.
 *   - 삼일절·부처님오신날·광복절·개천절·한글날·성탄절: 토요일 또는 일요일과 겹칠 때.
 *   - 신정·현충일: 적용 대상 아님.
 */
interface SubstituteRule {
  /** 토요일과 겹쳐도 대체공휴일이 붙는지 */
  onSaturday: boolean;
  /** 일요일이나 다른 공휴일과 겹칠 때 붙는지 */
  onSundayOrHoliday: boolean;
}

const NO_SUBSTITUTE: SubstituteRule = { onSaturday: false, onSundayOrHoliday: false };
const WEEKEND: SubstituteRule = { onSaturday: true, onSundayOrHoliday: true };
const SUNDAY_ONLY: SubstituteRule = { onSaturday: false, onSundayOrHoliday: true };

const SUBSTITUTE_RULES: Record<string, SubstituteRule> = {
  신정: NO_SUBSTITUTE,
  삼일절: WEEKEND,
  근로자의날: NO_SUBSTITUTE, // 2026년 관공서 공휴일이 되었으나 대체공휴일 적용은 확인되지 않음
  어린이날: WEEKEND,
  부처님오신날: WEEKEND,
  현충일: NO_SUBSTITUTE,
  제헌절: WEEKEND, // 2026년 공휴일 재지정과 함께 대체공휴일 대상
  광복절: WEEKEND,
  개천절: WEEKEND,
  한글날: WEEKEND,
  성탄절: WEEKEND,
  설날: SUNDAY_ONLY,
  추석: SUNDAY_ONLY,
};

/**
 * 양력 고정 공휴일. 날짜가 절대 안 바뀌므로 몇 년이 지나도 안전하다.
 * from을 둔 이유: 근로자의 날과 제헌절은 2026년부터 관공서 공휴일이 되었다.
 * (제헌절은 2008년 제외 후 18년 만의 복귀)
 */
const FIXED_HOLIDAYS: { monthDay: string; name: string; from?: number }[] = [
  { monthDay: '01-01', name: '신정' },
  { monthDay: '03-01', name: '삼일절' },
  { monthDay: '05-01', name: '근로자의날', from: 2026 },
  { monthDay: '05-05', name: '어린이날' },
  { monthDay: '06-06', name: '현충일' },
  { monthDay: '07-17', name: '제헌절', from: 2026 },
  { monthDay: '08-15', name: '광복절' },
  { monthDay: '10-03', name: '개천절' },
  { monthDay: '10-09', name: '한글날' },
  { monthDay: '12-25', name: '성탄절' },
];

/* ---------------------------------------------------------------------------
 * 날짜 도우미 — date-fns를 쓰지 않고 UTC 기준으로 다룬다.
 * 공휴일은 '달력상의 날짜'라 시간대가 개입하면 안 되기 때문이다.
 * ------------------------------------------------------------------------- */

function toKey(utc: Date): string {
  return utc.toISOString().slice(0, 10);
}

function parseKey(key: string): Date {
  return new Date(`${key}T00:00:00Z`);
}

function addDaysKey(key: string, days: number): string {
  const d = parseKey(key);
  d.setUTCDate(d.getUTCDate() + days);
  return toKey(d);
}

/** 0=일 … 6=토 */
function weekdayOf(key: string): number {
  return parseKey(key).getUTCDay();
}

interface Draft {
  date: string;
  name: string;
  rule: SubstituteRule;
}

/** 같은 날짜에 두 공휴일이 겹치면(2025년 어린이날=부처님오신날) 하나로 합친다 */
function mergeSameDay(drafts: Draft[]): Draft[] {
  const byDate = new Map<string, Draft>();
  for (const draft of drafts) {
    const existing = byDate.get(draft.date);
    if (!existing) {
      byDate.set(draft.date, { ...draft });
      continue;
    }
    existing.name = `${existing.name} · ${draft.name}`;
    // 규칙은 둘 중 넓은 쪽을 따른다 (어린이날+부처님오신날 → 토요일에도 대체)
    existing.rule = {
      onSaturday: existing.rule.onSaturday || draft.rule.onSaturday,
      onSundayOrHoliday: existing.rule.onSundayOrHoliday || draft.rule.onSundayOrHoliday,
    };
  }
  return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
}

/**
 * 그 해의 공휴일 전체.
 *
 * 음력 표 범위(1900~2050) 밖이면 음력 기반 공휴일(설날·추석·부처님오신날)은 빼고
 * 양력 고정 공휴일만 돌려준다. 틀린 날짜를 조용히 내놓지 않기 위해서다.
 * 호출부에서 그 사실을 알아야 하면 hasLunarData(year)로 확인할 수 있다.
 */
export function getHolidays(year: number): Holiday[] {
  const projected = year > LATEST_CONFIRMED_YEAR;
  const drafts: Draft[] = [];

  const ruleOf = (name: string) => SUBSTITUTE_RULES[name] ?? NO_SUBSTITUTE;

  for (const fixed of FIXED_HOLIDAYS) {
    if (fixed.from !== undefined && year < fixed.from) continue;
    drafts.push({ date: `${year}-${fixed.monthDay}`, name: fixed.name, rule: ruleOf(fixed.name) });
  }

  const lunar = getLunarAnchors(year);
  if (lunar) {
    // 설날·추석 연휴는 음력으로 연속된 사흘이라 양력으로도 연속 사흘이다
    const seollal = `${year}-${lunar.seollal}`;
    const chuseok = `${year}-${lunar.chuseok}`;
    for (const offset of [-1, 0, 1]) {
      drafts.push({ date: addDaysKey(seollal, offset), name: '설날', rule: ruleOf('설날') });
      drafts.push({ date: addDaysKey(chuseok, offset), name: '추석', rule: ruleOf('추석') });
    }
    drafts.push({
      date: `${year}-${lunar.buddha}`,
      name: '부처님오신날',
      rule: ruleOf('부처님오신날'),
    });
  }

  const merged = mergeSameDay(drafts);
  const holidays: Holiday[] = merged.map((d) => ({
    date: d.date,
    name: d.name,
    isSubstitute: false,
    // 양력 고정 공휴일은 날짜 자체가 늘 확실하다. 음력 기반만 계산값으로 표시한다.
    isProjected: projected && isLunarName(d.name),
  }));

  // 날짜만 빠르게 확인하기 위한 집합. 대체공휴일을 붙이는 동안 계속 자란다.
  const taken = new Set(holidays.map((h) => h.date));

  if (year < SUBSTITUTE_SINCE_YEAR) return holidays.sort((a, b) => a.date.localeCompare(b.date));

  for (const draft of merged) {
    const weekday = weekdayOf(draft.date);
    const collides =
      (weekday === 6 && draft.rule.onSaturday) ||
      (weekday === 0 && draft.rule.onSundayOrHoliday) ||
      // 같은 날 두 공휴일이 겹쳐 하나로 합쳐진 경우도 '다른 공휴일과 겹침'이다
      (draft.name.includes(' · ') && draft.rule.onSundayOrHoliday);
    if (!collides) continue;

    // "그 공휴일 다음의 첫 번째 비공휴일". 일요일은 그 자체가 공휴일이라 건너뛴다.
    let cursor = addDaysKey(draft.date, 1);
    while (taken.has(cursor) || weekdayOf(cursor) === 0) cursor = addDaysKey(cursor, 1);

    taken.add(cursor);
    holidays.push({
      date: cursor,
      name: `${draft.name} 대체`,
      isSubstitute: true,
      substituteFor: draft.date,
      // 대체공휴일은 붙는지 여부 자체가 규정 해석에 달려 있어, 미발표 연도면 계산값이다
      isProjected: projected,
    });
  }

  return holidays.sort((a, b) => a.date.localeCompare(b.date));
}

/** 음력으로 날짜가 정해지는 공휴일인지 (양력 고정 공휴일과 구분) */
function isLunarName(name: string): boolean {
  return name.includes('설날') || name.includes('추석') || name.includes('부처님오신날');
}

// 달력은 한 달을 그리며 같은 해를 수십 번 물어보므로 연도 단위로 캐시한다
const cache = new Map<number, Map<string, Holiday>>();

/** 'YYYY-MM-DD' -> Holiday 조회용 맵 */
export function getHolidayMap(year: number): Map<string, Holiday> {
  const hit = cache.get(year);
  if (hit) return hit;
  const map = new Map(getHolidays(year).map((h) => [h.date, h]));
  cache.set(year, map);
  return map;
}

/** 특정 날짜가 공휴일이면 그 정보를, 아니면 null */
export function getHoliday(dateKey: string): Holiday | null {
  const year = Number(dateKey.slice(0, 4));
  if (!Number.isFinite(year)) return null;
  return getHolidayMap(year).get(dateKey) ?? null;
}

export { hasLunarData };
