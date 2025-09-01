import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  // Configure esbuild (applies to dev and build). Use this (not build.esbuildOptions).
  esbuild: {
    drop: ['debugger'], // Keep console.error and console.warn for production debugging
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@components": path.resolve(__dirname, "./src/components"),
      "@utils": path.resolve(__dirname, "./src/utils"),
      "@hooks": path.resolve(__dirname, "./src/hooks"),
      "@contexts": path.resolve(__dirname, "./src/contexts"),
      "@types": path.resolve(__dirname, "./src/types"),
    },
  },
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
      // Only drop console.log in production, keep error and warn for debugging
      drop: ['debugger'],
      pure: ['console.log'],
    },
    rollupOptions: {
      output: {
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
        manualChunks(id) {
          if (id.includes('node_modules')) {
            // React MUST be bundled together and load first
            if (id.includes('react-dom') || id.includes('/react/') || id.includes('scheduler')) {
              return 'react-vendor';
            }
            // React-dependent libraries in separate chunk
            if (id.includes('react-router') || id.includes('react-is')) {
              return 'react-libs';
            }
            // Keep critical optimizations for largest dependencies
            if (id.includes('recharts')) return 'charts';
            if (id.includes('pdfjs-dist') || id.includes('react-pdf')) return 'pdf-libs';
            
            // Libraries that use React hooks/context
            if (id.includes('@tanstack/react-query') || 
                id.includes('react-toastify') || 
                id.includes('framer-motion') ||
                id.includes('@supabase/auth-ui')) {
              return 'react-deps';
            }
            
            // Non-React vendors
            if (id.includes('@supabase') && !id.includes('auth-ui')) return 'supabase';
            if (id.includes('lodash')) return 'lodash';
            
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
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'production'),
  },
});