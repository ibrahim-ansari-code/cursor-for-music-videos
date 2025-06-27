import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
    middlewareMode: false,
    watch: {
      usePolling: true,
    },
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom', 'pdfjs-dist', 'recharts'],
    exclude: [],
    esbuildOptions: {
      target: 'es2020'
    }
  },
  build: {
    sourcemap: true,
    target: 'es2020',
    minify: 'esbuild',
    rollupOptions: {
      output: {
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
        // ✅ Strategic chunking for largest libraries only
        manualChunks: {
          // Core React ecosystem
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          // Large PDF library (500KB+)
          'pdfjs': ['pdfjs-dist'],
          // Database client
          'supabase': ['@supabase/supabase-js'],
          // Charts library (400KB+)
          'charts': ['recharts'],
          // Animations
          'animation': ['framer-motion'],
          // Monitoring
          'monitoring': ['@sentry/react'],
        }
      },
    },
    chunkSizeWarningLimit: 600,
  },
});