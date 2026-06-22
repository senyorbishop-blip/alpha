import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';

const dataDir = process.env.DND_E2E_DATA_DIR || path.join(process.cwd(), '.tmp', 'playwright-data');

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: [['html', { outputFolder: 'playwright-report', open: 'never' }], ['list']],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:8765',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER ? undefined : {
    command: 'python -m uvicorn main:app --host 127.0.0.1 --port 8765',
    url: 'http://127.0.0.1:8765/health',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      ...process.env,
      DND_DATA_DIR: dataDir,
      DND_DB_PATH: path.join(dataDir, 'campaigns.db'),
      PYTHONUNBUFFERED: '1',
    },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
