import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base: './' — dist/를 어떤 정적 호스팅 경로에 올려도 동작하도록 상대 경로 빌드
export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    watch: {
      // electron-builder 산출물은 감시 대상에서 제외 (패키징 중 EBUSY 방지)
      ignored: ['**/release/**'],
    },
  },
});
