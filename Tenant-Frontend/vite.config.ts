import { sentryVitePlugin } from '@sentry/vite-plugin';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vite.dev/config/
export default defineConfig(({ command }) => {
  const isBuild = command === 'build';
  
  return {
    plugins: [
      react(),
      sentryVitePlugin({
        org: 'brikli',
        project: 'tenant-frontend',
      }),
    ],
    server: {
      port: 5174, // Different port from main Frontend (5173)
      open: true,
      host: true,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@components': path.resolve(__dirname, './src/components'),
        '@utils': path.resolve(__dirname, './src/utils'),
        '@hooks': path.resolve(__dirname, './src/hooks'),
        '@contexts': path.resolve(__dirname, './src/contexts'),
        '@types': path.resolve(__dirname, './src/types'),
        '@pages': path.resolve(__dirname, './src/pages'),
        // Browser polyfills
        crypto: 'crypto-browserify',
        stream: 'stream-browserify',
        util: 'util',
      },
      // Ensure a single copy of core React modules (prevents hook/context errors)
      dedupe: ['react', 'react-dom', 'react-is', 'scheduler'],
    },
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        '@sentry/react',
      ],
      esbuildOptions: {
        target: 'es2022',
      },
    },
    build: {
      target: 'es2022',
      sourcemap: 'hidden',
      minify: 'esbuild',
      rollupOptions: {
        output: {
          chunkFileNames: 'assets/[name]-[hash].js',
          entryFileNames: 'assets/[name]-[hash].js',
          assetFileNames: 'assets/[name]-[hash].[ext]',
        },
      },
    },
    // Modern browser compatibility
    define: {
      // Only set global shim during dev to avoid breaking UMD/CJS detection in build
      ...(isBuild ? {} : { global: 'globalThis' }),
      'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'production'),
    },
  };
});
