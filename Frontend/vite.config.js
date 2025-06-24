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
  },
  build: {
    sourcemap: true, // Enable source maps for production debugging
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // Ensure React is always in its own chunk and loaded first
          if (id.includes('react') && !id.includes('react-') && !id.includes('@')) {
            return 'react-core';
          }
          if (id.includes('react-dom')) {
            return 'react-dom';
          }
          if (id.includes('react-router')) {
            return 'react-router';
          }
          if (id.includes('pdfjs-dist')) {
            return 'pdf-lib';
          }
          if (id.includes('chart.js') || id.includes('react-chartjs')) {
            return 'charts';
          }
          if (id.includes('@supabase')) {
            return 'supabase';
          }
          if (id.includes('node_modules')) {
            return 'vendor';
          }
        },
      },
    },
    chunkSizeWarningLimit: 600, // Increase warning limit slightly
  },
});
