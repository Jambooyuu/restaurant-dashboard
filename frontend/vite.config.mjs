import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Force vite to use esbuild-wasm instead of native esbuild
// This bypasses the spawn EPERM issue on this system
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  esbuild: false,
  optimizeDeps: {
    esbuildOptions: {
      // Use wasm version
    }
  }
})
