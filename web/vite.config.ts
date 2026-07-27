import {defineConfig} from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8220',
      '/health': 'http://127.0.0.1:8220',
    },
  },
  build: {
    sourcemap: true,
    target: 'es2022',
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      thresholds: {lines: 80, functions: 80, branches: 80, statements: 80},
      exclude: ['src/main.tsx', 'src/test/**', 'src/components/OperationalMap.tsx'],
    },
  },
})
