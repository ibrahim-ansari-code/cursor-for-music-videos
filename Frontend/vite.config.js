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
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 4173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom', 'pdfjs-dist', 'recharts'],
    exclude: [],
    esbuildOptions: {
      target: 'es2022'
    }
  },
  build: {
    sourcemap: false,
    target: 'es2022',
    minify: 'esbuild',
    esbuildOptions: {
      drop: ['console', 'debugger'],
    },
    rollupOptions: {
      output: {
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
        manualChunks(id) {
          if (id.includes('node_modules')) {
            // Keep critical optimizations for largest dependencies
            if (id.includes('recharts')) return 'charts';
            if (id.includes('pdfjs-dist') || id.includes('react-pdf')) return 'pdf-libs';
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) return 'react-vendor';
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