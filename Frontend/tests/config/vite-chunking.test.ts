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
    it('should have React and ReactDOM in the same chunk', () => {
      // Check that the config properly bundles React together
      expect(viteConfig).toContain('react-vendor');
      expect(viteConfig).toContain("id.includes('/react/')");
      expect(viteConfig).toContain("id.includes('react-dom')");
    });

    it('should separate React-dependent libraries from React core', () => {
      // Verify React Router is in a separate chunk
      expect(viteConfig).toContain("id.includes('react-router')");
      expect(viteConfig).toContain('react-libs');
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
    it('should separate large dependencies into dedicated chunks', () => {
      expect(viteConfig).toContain('charts');
      expect(viteConfig).toContain('recharts');
      expect(viteConfig).toContain('pdf-libs');
      expect(viteConfig).toContain('pdfjs-dist');
    });

    it('should have proper chunk naming configuration', () => {
      expect(viteConfig).toContain('chunkFileNames');
      expect(viteConfig).toContain('assets/[name]-[hash].js');
    });

    it('should use manualChunks function for intelligent splitting', () => {
      expect(viteConfig).toContain('manualChunks(id)');
      expect(viteConfig).toContain('node_modules');
    });

    it('should handle vendor dependencies properly', () => {
      expect(viteConfig).toContain("return 'vendor'");
      expect(viteConfig).toContain('supabase');
      expect(viteConfig).toContain('lodash');
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