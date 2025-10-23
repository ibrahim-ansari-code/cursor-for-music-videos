import { sentryVitePlugin } from "@sentry/vite-plugin";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react(), sentryVitePlugin({
    org: "brikli",
    project: "landlord-frontend"
  })],
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
    // Fix: Ensure only one copy of React is bundled (prevents Radix UI hook errors)
    dedupe: ['react', 'react-dom'],
  },
  server: {
    host: true,
    port: 5173,
    open: true,
    middlewareMode: false,
    allowedHosts: [
      '.ngrok.io',
      '.ngrok-free.app',
      '.ngrok-free.dev',
    ],
    hmr: {
      // Ensure HMR works over HTTPS tunnels like ngrok
      clientPort: 443,
    },
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
    allowedHosts: [
      '.ngrok.io',
      '.ngrok-free.app',
      '.ngrok-free.dev',
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    include: [
      'react', 
      'react-dom', 
      'react-router-dom', 
      'pdfjs-dist', 
      'recharts', 
      '@sentry/react',
      '@radix-ui/react-dropdown-menu',
      '@radix-ui/react-dialog',
    ],
    exclude: [],
    esbuildOptions: {
      target: 'es2022'
    }
  },
  build: {
    sourcemap: 'hidden',
    target: 'es2022',
    minify: 'esbuild',
    esbuildOptions: {
      // Only drop console.log in production, keep error and warn for debugging
      drop: ['debugger'],
      pure: ['console.log'],
      // Prevent variable hoisting issues in production
      keepNames: true,
    },
    rollupOptions: {
      output: {
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
        // Ensure proper chunk loading order
        inlineDynamicImports: false,
        // Ensure React is available globally for all chunks
        globals: {
          'react': 'React',
          'react-dom': 'ReactDOM'
        },
        manualChunks(id) {
          if (id.includes('node_modules')) {
            // Sentry MUST be in the main vendor chunk to avoid initialization issues
            if (id.includes('@sentry/')) {
              return 'vendor';
            }
            
            // React core MUST load first and be in same chunk
            if (id.includes('react-dom') || id.includes('/react/') || id.includes('scheduler') || id.includes('/react/index')) {
              return 'react-core';
            }
            
            // Radix UI components MUST be in react-libs (separate from react-core to avoid circular deps)
            // But AFTER react-core is loaded
            if (id.includes('@radix-ui/')) {
              return 'radix-ui';
            }
            
            // React-dependent libraries 
            if (id.includes('react-router') || id.includes('react-is')) {
              return 'react-libs';
            }
            
            // Keep critical optimizations for largest dependencies
            if (id.includes('recharts')) return 'charts';
            if (id.includes('pdfjs-dist') || id.includes('react-pdf')) return 'pdf-libs';
            
            // Libraries that use React hooks/context (AFTER radix-ui chunk)
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