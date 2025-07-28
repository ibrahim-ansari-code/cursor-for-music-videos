import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174, // Different port from main Frontend (5173)
    open: true,
    host: true,
  },
  optimizeDeps: {
    esbuildOptions: {
      target: 'es2022'
    }
  },
  build: {
    target: 'es2022',
    rollupOptions: {
      external: [],
    }
  },
  // Modern browser compatibility
  define: {
    global: 'globalThis',
  },
  // Bypass Node.js crypto compatibility issues
  resolve: {
    alias: {
      crypto: 'crypto-browserify',
      stream: 'stream-browserify',
      util: 'util'
    }
  }
})
