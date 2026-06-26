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
})
