import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ command }) => ({
  // Production builds emit *relative* asset URLs so the same bundle works
  // when GitHub Pages serves it from a nested path
  // (https://<user>.github.io/AgentAudit/ -> /assets/... would 404).
  // The dev server keeps the default "/" so local URLs are unchanged.
  base: command === 'build' ? './' : '/',
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Local dev: /api is proxied to the Python runner on loopback, exactly as
    // before. A production build never uses this block -- it calls VITE_API_URL
    // directly (see src/api.js), so no remote host is contacted in dev.
    proxy: {
      '/api': 'http://127.0.0.1:8765',
    },
  },
}))
