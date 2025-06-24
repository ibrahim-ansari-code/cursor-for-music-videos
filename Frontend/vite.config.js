import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true,

    // ⚠️ This part is critical
    middlewareMode: false,
    watch: {
      usePolling: true,
    },
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom', 'pdfjs-dist'],
    exclude: [],
    esbuildOptions: {
      target: 'es2020'
    }
  },
  build: {
    sourcemap: true, // Enable source maps for production debugging
    target: 'es2020',
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks: {
          // Bundle all React-related packages together to avoid loading order issues
          'react-vendor': [
            'react',
            'react/jsx-runtime',
            'react/jsx-dev-runtime',
            'react-dom',
            'react-dom/client',
            'react-router-dom'
          ],
          'pdf-lib': ['pdfjs-dist'],
          'charts': ['chart.js', 'react-chartjs-2'],
          'supabase': ['@supabase/supabase-js']
        },
      },
    },
    chunkSizeWarningLimit: 600, // Increase warning limit slightly
  },
});
