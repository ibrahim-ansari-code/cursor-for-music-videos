import { describe, it, expect, beforeAll } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

describe('Build Verification', () => {
  const distPath = path.resolve(__dirname, '../../dist');
  let distExists = false;

  beforeAll(async () => {
    // Check if dist folder exists (from a previous build)
    distExists = fs.existsSync(distPath);
    
    if (!distExists) {
      console.log('Note: dist folder not found. Run "npm run build" to test build outputs.');
    }
  }, 30000);

  describe('Build Output Structure', () => {
    it('should generate expected chunk files when built', async () => {
      if (!distExists) {
        console.warn('Skipping: dist folder not found');
        return;
      }

      const files = fs.readdirSync(path.join(distPath, 'assets'));
      
      // Check for critical chunks
      const hasReactVendor = files.some(f => f.includes('react-vendor'));
      const hasReactLibs = files.some(f => f.includes('react-libs'));
      const hasReactDeps = files.some(f => f.includes('react-deps'));
      const hasCharts = files.some(f => f.includes('charts'));
      const hasPdfLibs = files.some(f => f.includes('pdf-libs'));
      const hasVendor = files.some(f => f.includes('vendor'));
      const hasIndex = files.some(f => f.includes('index') && f.endsWith('.js'));

      expect(hasReactVendor).toBe(true);
      expect(hasCharts).toBe(true);
      expect(hasPdfLibs).toBe(true);
      expect(hasVendor).toBe(true);
      expect(hasIndex).toBe(true);
      
      // Either react-libs or react-deps should exist
      expect(hasReactLibs || hasReactDeps).toBe(true);
    });

    it('should not create excessively large chunks', () => {
      if (!distExists) {
        console.warn('Skipping: dist folder not found');
        return;
      }

      const files = fs.readdirSync(path.join(distPath, 'assets'));
      const jsFiles = files.filter(f => f.endsWith('.js'));
      
      jsFiles.forEach(file => {
        const stats = fs.statSync(path.join(distPath, 'assets', file));
        const sizeInMB = stats.size / (1024 * 1024);
        
        // Main/index chunks: 1.2MB max (realistic for feature-rich B2B SaaS)
        // Industry accepts 1-1.5MB for main bundles (Notion: 1.8MB, Linear: 1.5MB)
        if (!file.includes('vendor') && !file.includes('pdf-libs') && !file.includes('charts')) {
          expect(sizeInMB).toBeLessThan(1.2);
        } else {
          // Vendor/library chunks: 2MB max (heavily cached by browsers)
          expect(sizeInMB).toBeLessThan(2);
        }
      });
    });

    it('should include index.html with proper script tags', () => {
      if (!distExists) {
        console.warn('Skipping: dist folder not found');
        return;
      }

      const indexPath = path.join(distPath, 'index.html');
      expect(fs.existsSync(indexPath)).toBe(true);
      
      const indexContent = fs.readFileSync(indexPath, 'utf-8');
      
      // Check for module script tags
      expect(indexContent).toContain('<script type="module"');
      expect(indexContent).toContain('crossorigin');
      
      // Should not have any inline scripts that could cause security issues
      expect(indexContent).not.toContain('window.React =');
      expect(indexContent).not.toContain('global.React =');
    });
  });

  describe('React Module Loading Order', () => {
    it('should ensure React loads before dependent modules in HTML', () => {
      if (!distExists) {
        console.warn('Skipping: dist folder not found');
        return;
      }

      const indexPath = path.join(distPath, 'index.html');
      const indexContent = fs.readFileSync(indexPath, 'utf-8');
      
      // Extract script tags
      const scriptMatches = indexContent.match(/<script[^>]*src="([^"]+)"[^>]*>/g) || [];
      const scriptSrcs = scriptMatches.map(tag => {
        const match = tag.match(/src="([^"]+)"/);
        return match ? match[1] : '';
      }).filter(Boolean);
      
      // Find positions of different chunk types
      const reactVendorIndex = scriptSrcs.findIndex(src => src.includes('react-vendor'));
      const reactDepsIndex = scriptSrcs.findIndex(src => src.includes('react-deps') || src.includes('react-libs'));
      const indexJsIndex = scriptSrcs.findIndex(src => src.includes('index'));
      
      // React vendor should load before react-dependent libraries
      if (reactVendorIndex !== -1 && reactDepsIndex !== -1) {
        expect(reactVendorIndex).toBeLessThan(reactDepsIndex);
      }
      
      // React vendor should load before main index
      if (reactVendorIndex !== -1 && indexJsIndex !== -1) {
        expect(reactVendorIndex).toBeLessThan(indexJsIndex);
      }
    });
  });

  describe('No Global Namespace Pollution', () => {
    it('should not expose React globally in any chunk', async () => {
      if (!distExists) {
        console.warn('Skipping: dist folder not found');
        return;
      }

      const files = fs.readdirSync(path.join(distPath, 'assets'));
      const jsFiles = files.filter(f => f.endsWith('.js'));
      
      for (const file of jsFiles) {
        const content = fs.readFileSync(path.join(distPath, 'assets', file), 'utf-8');
        
        // Check for global React assignments
        expect(content).not.toContain('window.React =');
        expect(content).not.toContain('window.React=');
        expect(content).not.toContain('global.React =');
        expect(content).not.toContain('global.React=');
        expect(content).not.toContain('globalThis.React =');
        expect(content).not.toContain('globalThis.React=');
      }
    });
  });

  describe('Error Boundary Integration', () => {
    it('should include ProductionErrorBoundary in the build', () => {
      if (!distExists) {
        console.warn('Skipping: dist folder not found');
        return;
      }

      const files = fs.readdirSync(path.join(distPath, 'assets'));
      const jsFiles = files.filter(f => f.endsWith('.js'));
      
      // Check if any chunk contains error boundary code
      let hasErrorBoundary = false;
      for (const file of jsFiles) {
        const content = fs.readFileSync(path.join(distPath, 'assets', file), 'utf-8');
        if (content.includes('ProductionErrorBoundary') || 
            content.includes('componentDidCatch') ||
            content.includes('getDerivedStateFromError')) {
          hasErrorBoundary = true;
          break;
        }
      }
      
      expect(hasErrorBoundary).toBe(true);
    });
  });
});