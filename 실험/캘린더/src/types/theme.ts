/** 사용자가 고르는 테마. 'system'은 OS 설정을 따라간다. */
export type ThemePreference = 'light' | 'dark' | 'system';

/** 실제로 화면에 적용되는 테마 ('system'이 해석된 결과) */
export type ResolvedTheme = 'light' | 'dark';

export const THEME_PREFERENCES: ThemePreference[] = ['light', 'dark', 'system'];

export function isThemePreference(value: unknown): value is ThemePreference {
  return value === 'light' || value === 'dark' || value === 'system';
}
