/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev the SPA runs on :5173 and proxies API calls to the backend on :8000,
// so the client always uses same-origin relative paths (matching the all-in-one
// production deploy where FastAPI serves the built SPA).
const apiPrefixes = [
  '/works',
  '/manifestations',
  '/patrons',
  '/loans',
  '/holds',
  '/items',
  '/catalog',
]

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(
      apiPrefixes.map((p) => [
        p,
        { target: 'http://localhost:8000', changeOrigin: true },
      ]),
    ),
  },
  // Unit + component tests (Vitest). The Playwright e2e suite under `e2e/` is a
  // separate runner and is excluded here so the two don't collide.
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    css: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'text-summary', 'json-summary', 'lcov'],
      reportsDirectory: './coverage',
      // Scope: the logic and interactive components under *unit* test. The big
      // staff screens and the app/shell wiring are covered by the Playwright E2E
      // suite instead, so they're excluded here to keep this number an honest
      // measure of unit coverage rather than double-counting the E2E surface.
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/**/*.stories.tsx',
        'src/stories/**',
        'src/test/**',
        'src/main.tsx', // bootstrap
        'src/types.ts', // type-only
        'src/App.tsx', // router bootstrap — E2E
        'src/StaffShell.tsx', // staff shell — E2E
        'src/screens/**', // Catalog, CirculationDesk — E2E
        'src/opac/OpacShell.tsx', // OPAC shell — E2E
      ],
    },
  },
})
