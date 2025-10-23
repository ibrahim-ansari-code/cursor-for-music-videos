import { sentryVitePlugin } from "@sentry/vite-plugin";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig(({ command }) => {
  const isBuild = command === 'build';
  return {
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
      // Ensure a single copy of core React modules (prevents hook/context errors)
      dedupe: ['react', 'react-dom', 'react-is', 'scheduler'],
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
        '@radix-ui/react-dialog',
        '@radix-ui/react-dropdown-menu',
        'scheduler',
        'react-is',
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
          inlineDynamicImports: false,
        },
      },
      chunkSizeWarningLimit: 600,
    },
    // ✅ Fix for Vite 7.x browser compatibility
    define: {
      // Only set global shim during dev to avoid breaking UMD/CJS detection in build
      ...(isBuild ? {} : { global: 'globalThis' }),
      'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'production'),
    },
  };
});