import { create } from 'zustand';
import { isThemePreference, type ResolvedTheme, type ThemePreference } from '../types/theme';
import { loadSettings, saveSettings } from '../utils/storage';

/**
 * 테마(라이트/다크/시스템) 스토어.
 *
 * 실제 색은 전부 tokens.css의 CSS 변수에 있고, 여기서는 <html>에 data-theme만 찍는다.
 * 그래서 테마가 바뀌어도 리액트가 다시 그릴 일이 없고, 브라우저가 변수 값만 갈아끼운다.
 *
 * 'system'은 값으로 저장만 하고 화면에는 항상 해석된 결과(light|dark)를 찍는다.
 * matchMedia를 계속 구독하므로 앱이 떠 있는 동안 OS 설정을 바꿔도 즉시 따라간다.
 */

const DARK_QUERY = '(prefers-color-scheme: dark)';

/** 테마 전환 순간에만 짧은 크로스페이드를 켜는 표식 (global.css가 이 속성을 본다) */
const SWITCH_ATTR = 'data-theme-switch';
const SWITCH_MS = 300;

function prefersDark(): boolean {
  return typeof window !== 'undefined' && window.matchMedia(DARK_QUERY).matches;
}

function resolve(preference: ThemePreference): ResolvedTheme {
  if (preference === 'system') return prefersDark() ? 'dark' : 'light';
  return preference;
}

function paint(theme: ResolvedTheme): void {
  document.documentElement.dataset.theme = theme;
  // 네이티브 위젯(스크롤바, input[type=color] 팝업 등)도 같이 어두워지게 한다
  document.documentElement.style.colorScheme = theme;
}

let switchTimer: number | undefined;
let fadeLayer: HTMLDivElement | undefined;
let fadeTimer: number | undefined;

function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * 배경 그라디언트만 따로 크로스페이드한다.
 *
 * 색(background-color)과 달리 그라디언트(background-image)는 브라우저가 보간해 주지 않아
 * transition을 걸어도 한 프레임에 툭 바뀐다(리터럴 그라디언트끼리도 마찬가지였다).
 * 화면에서 가장 넓은 면이라 이것만 하드컷이면 나머지가 아무리 부드러워도 티가 난다.
 * 그래서 바뀌기 직전 배경을 한 장 떠서 위에 덮고, 그 덮개의 opacity만 서서히 지운다.
 * (opacity는 합성만으로 처리되어 프레임을 잡아먹지 않는다.)
 */
function crossfadeBackground(previous: string): void {
  if (previous === 'none' || prefersReducedMotion()) return;
  if (!fadeLayer) {
    fadeLayer = document.createElement('div');
    fadeLayer.className = 'themeFade';
    fadeLayer.setAttribute('aria-hidden', 'true');
  }
  // 연달아 바꿔도 덮개는 하나만 쓴다. 트랜지션을 잠깐 끄고 시작 상태로 되돌린다.
  fadeLayer.style.transition = 'none';
  fadeLayer.style.opacity = '1';
  fadeLayer.style.backgroundImage = previous;
  if (!fadeLayer.isConnected) document.body.appendChild(fadeLayer);
  void fadeLayer.offsetWidth; // 위 상태를 확정시켜야 아래 변화가 트랜지션으로 잡힌다
  fadeLayer.style.transition = '';
  fadeLayer.style.opacity = '0';
  window.clearTimeout(fadeTimer);
  fadeTimer = window.setTimeout(() => fadeLayer?.remove(), SWITCH_MS);
}

/** 사용자가 직접 바꿨을 때만 부드럽게 넘긴다. 첫 렌더에는 트랜지션이 없어야 깜빡이지 않는다. */
function paintWithTransition(theme: ResolvedTheme): void {
  const root = document.documentElement;
  const previousBackground = getComputedStyle(document.body).backgroundImage;
  root.setAttribute(SWITCH_ATTR, '');
  paint(theme);
  crossfadeBackground(previousBackground);
  window.clearTimeout(switchTimer);
  switchTimer = window.setTimeout(() => root.removeAttribute(SWITCH_ATTR), SWITCH_MS);
}

interface ThemeStore {
  preference: ThemePreference;
  resolved: ResolvedTheme;
  setPreference: (preference: ThemePreference) => void;
}

const initialPreference: ThemePreference = (() => {
  const saved = loadSettings().theme;
  return isThemePreference(saved) ? saved : 'system';
})();

const initialResolved = resolve(initialPreference);

// 리액트가 그리기 전에 미리 칠해 둔다 (main.tsx가 이 모듈을 먼저 import한다).
// 이래야 첫 프레임부터 다크로 뜨고 흰 화면이 번쩍이지 않는다.
paint(initialResolved);

export const useThemeStore = create<ThemeStore>((set) => ({
  preference: initialPreference,
  resolved: initialResolved,

  setPreference: (preference) => {
    const resolved = resolve(preference);
    paintWithTransition(resolved);
    saveSettings({ theme: preference });
    set({ preference, resolved });
  },
}));

// OS 테마 변화 구독. 'system'을 고른 동안에만 반응한다.
if (typeof window !== 'undefined') {
  window.matchMedia(DARK_QUERY).addEventListener('change', () => {
    const { preference, resolved } = useThemeStore.getState();
    if (preference !== 'system') return;
    const next = resolve('system');
    if (next === resolved) return;
    paintWithTransition(next);
    useThemeStore.setState({ resolved: next });
  });
}
