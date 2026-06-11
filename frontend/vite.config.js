import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    hmr: {
      overlay: false,
    },
    watch: {
      usePolling: false,
    }
  },
  build: {
    target: 'esnext',
    minify: 'esbuild',
  }
})
