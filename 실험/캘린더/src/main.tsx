// 무엇보다 먼저 — 아래 import들이 평가되다 죽어도 그물에 걸리게 한다
import './utils/bootGuard';
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { ErrorBoundary } from './components/ErrorBoundary';
// 렌더보다 먼저 import해서 첫 프레임부터 저장된 테마로 뜨게 한다 (흰 화면 번쩍임 방지)
import './store/themeStore';
import './styles/tokens.css';
import './styles/global.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
