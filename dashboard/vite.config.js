import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // The New Audit page talks to the local Python runner; it is bound to
    // 127.0.0.1 only. No remote hosts are ever contacted.
    proxy: {
      '/api': 'http://127.0.0.1:8765',
    },
  },
})
