import { describe, it, expect, beforeAll } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

describe('Vite Chunking Strategy', () => {
  let viteConfig: string;

  beforeAll(() => {
    const configPath = path.resolve(__dirname, '../../vite.config.js');
    viteConfig = fs.readFileSync(configPath, 'utf-8');
  });

  describe('Critical React Configuration', () => {
    it('should deduplicate React to prevent multiple instances', () => {
      // Using resolve.dedupe instead of manual chunking to avoid Radix UI bundling conflicts
      expect(viteConfig).toContain('dedupe');
      expect(viteConfig).toContain('react');
      expect(viteConfig).toContain('react-dom');
    });

    it('should use automatic code splitting via lazy loading', () => {
      // We use React.lazy() for route-based splitting instead of manualChunks
      // This avoids React context/hook conflicts with Radix UI
      expect(viteConfig).toContain('inlineDynamicImports: false');
    });

    it('should have global defined as globalThis for browser compatibility', () => {
      expect(viteConfig).toContain("global: 'globalThis'");
    });

    it('should include React in optimizeDeps', () => {
      expect(viteConfig).toContain('optimizeDeps');
      expect(viteConfig).toContain("'react'");
      expect(viteConfig).toContain("'react-dom'");
      expect(viteConfig).toContain("'react-router-dom'");
    });
  });

  describe('Chunk Optimization', () => {
    it('should use automatic chunking for dependencies', () => {
      // Vite automatically splits large dependencies when using lazy loading
      // No manual chunking needed (prevents React bundling conflicts)
      expect(viteConfig).toContain('chunkFileNames');
      expect(viteConfig).toContain('assets/[name]-[hash].js');
    });

    it('should have proper chunk naming configuration', () => {
      expect(viteConfig).toContain('chunkFileNames');
      expect(viteConfig).toContain('assets/[name]-[hash].js');
    });

    it('should not use manualChunks to avoid React bundling conflicts', () => {
      // We intentionally removed manualChunks because it was causing
      // "Cannot read properties of undefined (reading 'createContext')" errors
      // with Radix UI in production builds
      expect(viteConfig).not.toContain('manualChunks(id)');
    });

    it('should include Radix UI in optimizeDeps', () => {
      expect(viteConfig).toContain('@radix-ui/react-dialog');
      expect(viteConfig).toContain('@radix-ui/react-dropdown-menu');
    });
  });

  describe('Build Configuration', () => {
    it('should target ES2022 for modern browser support', () => {
      expect(viteConfig).toContain("target: 'es2022'");
    });

    it('should use esbuild for minification', () => {
      expect(viteConfig).toContain("minify: 'esbuild'");
    });

    it('should drop console.log and debugger in production', () => {
      expect(viteConfig).toContain("drop: ['debugger']");
      expect(viteConfig).toContain("pure: ['console.log']");
    });

    it('should set appropriate chunk size warning limit', () => {
      expect(viteConfig).toContain('chunkSizeWarningLimit: 600');
    });
  });

  describe('Module Resolution', () => {
    it('should have proper path alias configuration', () => {
      expect(viteConfig).toContain('"@": path.resolve');
      expect(viteConfig).toContain('./src');
    });

    it('should define process.env.NODE_ENV', () => {
      expect(viteConfig).toContain("'process.env.NODE_ENV'");
    });
  });
});