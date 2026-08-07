import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Calls to /api go to the Python backend, so the browser sees one origin
    // and there is no CORS to configure.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
