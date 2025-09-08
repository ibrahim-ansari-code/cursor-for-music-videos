import { describe, it, expect, beforeEach } from 'vitest';
import {
  sanitizeString,
  sanitizeFinancialAmount,
  sanitizeTaxRate,
  sanitizeInvoiceNumber,
  sanitizeId,
  sanitizeDate,
  sanitizeCSVField,
  validateFileUpload,
  sanitizeObjectKeys,
  rateLimiter,
  generateSecureId,
} from '../../src/utils/security';

describe('Security Utils', () => {
  describe('sanitizeString', () => {
    it('should sanitize HTML characters', () => {
      expect(sanitizeString('<script>alert("xss")</script>')).toBe('&lt;script&gt;alert(&quot;xss&quot;)&lt;&#x2F;script&gt;');
      expect(sanitizeString('Hello & "World"')).toBe('Hello &amp; &quot;World&quot;');
      expect(sanitizeString("It's a <test> & 'quote'")).toBe('It&#x27;s a &lt;test&gt; &amp; &#x27;quote&#x27;');
    });

    it('should handle non-string inputs', () => {
      expect(sanitizeString(123)).toBe('');
      expect(sanitizeString(null)).toBe('');
      expect(sanitizeString(undefined)).toBe('');
      expect(sanitizeString({})).toBe('');
    });

    it('should trim whitespace', () => {
      expect(sanitizeString('  hello world  ')).toBe('hello world');
    });
  });

  describe('sanitizeFinancialAmount', () => {
    it('should handle valid numeric inputs', () => {
      expect(sanitizeFinancialAmount(123.45)).toBe('123.45');
      expect(sanitizeFinancialAmount(0)).toBe('0.00');
      expect(sanitizeFinancialAmount(1000)).toBe('1000.00');
    });

    it('should handle string inputs', () => {
      expect(sanitizeFinancialAmount('123.45')).toBe('123.45');
      expect(sanitizeFinancialAmount('$123.45')).toBe('123.45');
      expect(sanitizeFinancialAmount('1,234.56')).toBe('1234.56');
      expect(sanitizeFinancialAmount('123.45abc')).toBe('123.45');
    });

    it('should reject negative amounts', () => {
      expect(sanitizeFinancialAmount(-123)).toBe('0.00');
      expect(sanitizeFinancialAmount('-123.45')).toBe('0.00');
    });

    it('should cap at maximum amount', () => {
      expect(sanitizeFinancialAmount('9999999999999')).toBe('999999999.99');
      expect(sanitizeFinancialAmount(Infinity)).toBe('0.00');
    });

    it('should handle invalid inputs', () => {
      expect(sanitizeFinancialAmount(NaN)).toBe('0.00');
      expect(sanitizeFinancialAmount('abc')).toBe('0.00');
      expect(sanitizeFinancialAmount(null)).toBe('0.00');
      expect(sanitizeFinancialAmount(undefined)).toBe('0.00');
    });
  });

  describe('sanitizeTaxRate', () => {
    it('should handle valid tax rates', () => {
      expect(sanitizeTaxRate(13.5)).toBe('13.50');
      expect(sanitizeTaxRate('5.75')).toBe('5.75');
      expect(sanitizeTaxRate(0)).toBe('0.00');
    });

    it('should cap at 100%', () => {
      expect(sanitizeTaxRate(150)).toBe('100.00');
      expect(sanitizeTaxRate('200.5')).toBe('100.00');
    });

    it('should reject negative rates', () => {
      expect(sanitizeTaxRate(-5)).toBe('0.00');
      expect(sanitizeTaxRate('-10.5')).toBe('0.00');
    });

    it('should handle invalid inputs', () => {
      expect(sanitizeTaxRate('abc')).toBe('0.00');
      expect(sanitizeTaxRate(NaN)).toBe('0.00');
      expect(sanitizeTaxRate(null)).toBe('0.00');
    });
  });

  describe('sanitizeInvoiceNumber', () => {
    it('should allow valid invoice numbers', () => {
      expect(sanitizeInvoiceNumber('INV-2023-001')).toBe('INV-2023-001');
      expect(sanitizeInvoiceNumber('INV_001.pdf')).toBe('INV_001.pdf');
      expect(sanitizeInvoiceNumber('ABC123')).toBe('ABC123');
    });

    it('should remove special characters', () => {
      expect(sanitizeInvoiceNumber('INV<>001')).toBe('INV001');
      expect(sanitizeInvoiceNumber('INV&001')).toBe('INV001');
      expect(sanitizeInvoiceNumber('INV"001')).toBe('INV001');
    });

    it('should limit length', () => {
      const longString = 'A'.repeat(100);
      expect(sanitizeInvoiceNumber(longString)).toHaveLength(50);
    });

    it('should handle non-string inputs', () => {
      expect(sanitizeInvoiceNumber(123)).toBe('');
      expect(sanitizeInvoiceNumber(null)).toBe('');
    });
  });

  describe('sanitizeId', () => {
    it('should handle valid IDs', () => {
      expect(sanitizeId(123)).toBe(123);
      expect(sanitizeId('456')).toBe(456);
      expect(sanitizeId(1)).toBe(1);
    });

    it('should reject invalid IDs', () => {
      expect(sanitizeId(0)).toBe(null);
      expect(sanitizeId(-1)).toBe(null);
      expect(sanitizeId('abc')).toBe(null);
      expect(sanitizeId(1.5)).toBe(null);
      expect(sanitizeId(null)).toBe(null);
      expect(sanitizeId(undefined)).toBe(null);
    });
  });

  describe('sanitizeDate', () => {
    it('should handle valid dates', () => {
      expect(sanitizeDate('2023-12-01')).toBe('2023-12-01');
      expect(sanitizeDate('2023-01-01')).toBe('2023-01-01');
    });

    it('should reject invalid date formats', () => {
      expect(sanitizeDate('12/01/2023')).toBe('');
      expect(sanitizeDate('2023-1-1')).toBe('');
      expect(sanitizeDate('not-a-date')).toBe('');
    });

    it('should reject dates outside reasonable range', () => {
      expect(sanitizeDate('1800-01-01')).toBe('');
      expect(sanitizeDate('2200-01-01')).toBe('');
    });

    it('should handle non-string inputs', () => {
      expect(sanitizeDate(123)).toBe('');
      expect(sanitizeDate(null)).toBe('');
    });
  });

  describe('sanitizeCSVField', () => {
    it('should remove CSV injection characters', () => {
      expect(sanitizeCSVField('=cmd')).toBe('cmd');
      expect(sanitizeCSVField('@SUM(1+1)')).toBe('SUM(1+1)'); // Only removes @ at start, preserves + inside
      expect(sanitizeCSVField('+cmd')).toBe('cmd');
      expect(sanitizeCSVField('-cmd')).toBe('cmd');
    });

    it('should preserve content after removing leading injection characters', () => {
      // Verify that formulas are properly sanitized while preserving their mathematical content
      expect(sanitizeCSVField('@sum(1+1)')).toBe('sum(1+1)'); // Preserves lowercase and full expression
      expect(sanitizeCSVField('=A1+B2')).toBe('A1+B2'); // Preserves cell references and operators
      expect(sanitizeCSVField('+1+2+3')).toBe('1+2+3'); // Only removes leading +, preserves the rest
      expect(sanitizeCSVField('-5+10')).toBe('5+10'); // Only removes leading -, preserves the rest
      
      // Test that injection characters in the middle are preserved (they're safe there)
      expect(sanitizeCSVField('normal@text')).toBe('normal@text');
      expect(sanitizeCSVField('value=5')).toBe('value=5');
    });

    it('should sanitize HTML characters', () => {
      expect(sanitizeCSVField('<script>alert(1)</script>')).toBe('&lt;script&gt;alert(1)&lt;&#x2F;script&gt;');
    });

    it('should limit field length', () => {
      const longString = 'A'.repeat(2000);
      expect(sanitizeCSVField(longString)).toHaveLength(1000);
    });
  });

  describe('validateFileUpload', () => {
    it('should accept valid file types', () => {
      const validFile = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
      expect(validateFileUpload(validFile)).toEqual({ valid: true });

      const pdfFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
      expect(validateFileUpload(pdfFile)).toEqual({ valid: true });
    });

    it('should reject large files', () => {
      const largeContent = new Array(11 * 1024 * 1024).fill('a').join(''); // 11MB
      const largeFile = new File([largeContent], 'large.jpg', { type: 'image/jpeg' });
      
      const result = validateFileUpload(largeFile);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('10MB');
    });

    it('should reject dangerous file types', () => {
      const exeFile = new File(['test'], 'virus.exe', { type: 'application/x-executable' });
      const result = validateFileUpload(exeFile);
      expect(result.valid).toBe(false);
    });

    it('should reject suspicious file extensions', () => {
      const jsFile = new File(['test'], 'script.js', { type: 'text/javascript' });
      const result = validateFileUpload(jsFile);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('allowed');
    });
  });

  describe('sanitizeObjectKeys', () => {
    it('should sanitize object properties', () => {
      const input = {
        name: 'John <script>',
        age: 25,
        valid: true,
        items: ['item1', '<script>alert(1)</script>'],
      };

      const result = sanitizeObjectKeys(input);
      expect(result.name).toBe('John &lt;script&gt;');
      expect(result.age).toBe(25);
      expect(result.valid).toBe(true);
      expect(result.items?.[0]).toBe('item1');
      expect(result.items?.[1]).toBe('&lt;script&gt;alert(1)&lt;&#x2F;script&gt;');
    });

    it('should remove dangerous prototype keys', () => {
      const input = {
        name: 'John',
        '__proto__': { admin: true },
        'constructor': 'bad',
        'prototype': 'also bad',
      };

      const result = sanitizeObjectKeys(input);
      expect(result.name).toBe('John');
      expect(result).not.toHaveProperty('__proto__');
      expect(result).not.toHaveProperty('constructor');
      expect(result).not.toHaveProperty('prototype');
    });

    it('should handle non-object inputs', () => {
      expect(sanitizeObjectKeys(null)).toEqual({});
      expect(sanitizeObjectKeys('string')).toEqual({});
      expect(sanitizeObjectKeys(123)).toEqual({});
    });
  });

  describe('rateLimiter', () => {
    beforeEach(() => {
      // Reset rate limiter
      rateLimiter.reset('test-key');
    });

    it('should allow calls within limit', () => {
      for (let i = 0; i < 5; i++) {
        expect(rateLimiter.isAllowed('test-key', 60000, 10)).toBe(true);
      }
    });

    it('should block calls exceeding limit', () => {
      // Make 10 calls (the limit)
      for (let i = 0; i < 10; i++) {
        rateLimiter.isAllowed('test-key', 60000, 10);
      }

      // 11th call should be blocked
      expect(rateLimiter.isAllowed('test-key', 60000, 10)).toBe(false);
    });

    it('should reset after time window', async () => {
      // Make 10 calls
      for (let i = 0; i < 10; i++) {
        rateLimiter.isAllowed('test-key', 100, 10); // 100ms window
      }

      expect(rateLimiter.isAllowed('test-key', 100, 10)).toBe(false);

      // Wait for window to expire
      await new Promise(resolve => setTimeout(resolve, 150));

      // Should be allowed again
      expect(rateLimiter.isAllowed('test-key', 100, 10)).toBe(true);
    });
  });

  describe('generateSecureId', () => {
    it('should generate unique IDs', () => {
      const id1 = generateSecureId();
      const id2 = generateSecureId();
      expect(id1).not.toBe(id2);
      expect(id1).toMatch(/^[0-9a-z_]+$/);
    });

    it('should include prefix when provided', () => {
      const id = generateSecureId('inv_');
      expect(id).toMatch(/^inv_[0-9a-z_]+$/);
    });

    it('should generate reasonable length IDs', () => {
      const id = generateSecureId();
      expect(id.length).toBeGreaterThan(10);
      expect(id.length).toBeLessThan(50);
    });
  });
});