import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import { fileURLToPath, URL } from 'url';

export default defineConfig({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify('http://localhost:8000'),
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.jsx'],
    globals: true,
    css: true,
    // Include files to test
    include: ['src/**/*.{test,spec}.{js,jsx,ts,tsx}'],
    // Exclude files from testing
    exclude: [
      'node_modules/**',
      'dist/**',
      '.eslintrc.cjs',
      'vite.config.js'
    ],
    // Test reporting for CI
    reporters: ['default', 'junit'],
    outputFile: {
      junit: './test-results.xml'
    },
    // Coverage configuration
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/**',
        'src/test/**',
        'src/**/*.{test,spec}.{js,jsx,ts,tsx}',
        'src/main.jsx',
        'vite.config.js',
        'vitest.config.js'
      ]
    }
  },
  resolve: {
    alias: {
      '@': resolve(fileURLToPath(new URL('.', import.meta.url)), 'src')
    }
  }
});