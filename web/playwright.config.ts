import {defineConfig, devices} from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: {timeout: 8_000},
  fullyParallel: true,
  forbidOnly: true,
  retries: 1,
  reporter: [['list'], ['html', {open: 'never'}]],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    serviceWorkers: 'block',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'desktop-1920',
      use: {...devices['Desktop Chrome'], viewport: {width: 1920, height: 1080}},
    },
    {
      name: 'laptop-1366',
      use: {...devices['Desktop Chrome'], viewport: {width: 1366, height: 768}},
    },
    {
      name: 'tablet-landscape',
      use: {
        ...devices['iPad Pro 11 landscape'],
      },
    },
    {
      name: 'mobile-390',
      use: {
        ...devices['Pixel 7'],
        viewport: {width: 390, height: 844},
      },
    },
    {
      name: 'webkit-1440',
      use: {
        ...devices['Desktop Safari'],
        viewport: {width: 1440, height: 900},
      },
    },
    {
      name: 'reduced-motion',
      use: {
        ...devices['Desktop Chrome'],
        viewport: {width: 1920, height: 1080},
        contextOptions: {reducedMotion: 'reduce'},
      },
    },
  ],
  webServer: {
    command: 'npm run build && npx vite preview --host 127.0.0.1 --port 4173',
    url: 'http://127.0.0.1:4173/',
    reuseExistingServer: false,
    timeout: 120_000,
  },
})
