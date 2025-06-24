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
    include: ['pdfjs-dist'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // Split vendor chunks
          if (id.includes('node_modules')) {
            // Create a separate chunk for pdfjs-dist
            if (id.includes('pdfjs-dist')) {
              return 'pdf-lib';
            }
            // Create a separate chunk for React and related libraries
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
              return 'react-vendor';
            }
            // Create a separate chunk for chart.js
            if (id.includes('chart.js')) {
              return 'charts';
            }
            // Create a separate chunk for Supabase
            if (id.includes('@supabase')) {
              return 'supabase';
            }
            // Other vendor libraries
            return 'vendor';
          }
        },
      },
    },
    chunkSizeWarningLimit: 600, // Increase warning limit slightly
  },
});
