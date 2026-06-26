import { defineConfig, devices } from '@playwright/test'

// Drives the *all-in-one* deploy: build the SPA, then have FastAPI serve it +
// the API on one origin. The webServer command builds `dist/` and boots uvicorn
// from the backend project (uv); Playwright waits for the URL before testing.
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // the backend shares one SQLite file across the run
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:8000',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command:
      'npm run build && (cd ../backend && rm -f library.db && uv run --no-sync uvicorn app.main:create_app --factory --port 8000)',
    url: 'http://127.0.0.1:8000/',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
