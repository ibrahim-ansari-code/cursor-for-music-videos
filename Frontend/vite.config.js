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
        // ✅ Production-safe chunking strategy
        manualChunks: (id) => {
          // Core React ecosystem - always keep together for optimal loading
          if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
            return 'react-vendor';
          }
          
          // Large, stable dependencies - explicit chunking for better cache control
          if (id.includes('recharts')) return 'charts';
          if (id.includes('pdfjs-dist') || id.includes('react-pdf')) return 'pdf-libs';
          if (id.includes('@supabase/supabase-js')) return 'supabase';
          if (id.includes('framer-motion')) return 'animation';
          if (id.includes('@sentry/react')) return 'monitoring';
          
          // Icon libraries (can be very large)
          if (id.includes('react-icons') || id.includes('lucide-react')) return 'icons';
          
          // UI/UX libraries
          if (id.includes('react-toastify') || id.includes('react-countup')) return 'ui-libs';
          
          // Utility libraries
          if (id.includes('lodash') || id.includes('clsx') || id.includes('uuid') || id.includes('decimal.js')) {
            return 'utils';
          }
          
          // Catch-all for other node_modules dependencies
          // This ensures we don't miss any dependencies and they get proper caching
          if (id.includes('node_modules')) {
            return 'vendor';
          }
        }
      },
    },
    chunkSizeWarningLimit: 600,
  },
  // ✅ Fix for Vite 7.x browser compatibility
  define: {
    global: 'globalThis',
  },
});