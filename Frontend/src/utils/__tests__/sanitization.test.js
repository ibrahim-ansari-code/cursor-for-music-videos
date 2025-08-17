/**
 * Tests for sanitization utilities
 */
import { 
  sanitizeText, 
  sanitizeAndTruncate, 
  sanitizeCurrency, 
  sanitizePropertyName, 
  sanitizeTenantName 
} from '../sanitization';

describe('sanitization utilities', () => {
  describe('sanitizeText', () => {
    it('should escape HTML characters', () => {
      expect(sanitizeText('<script>alert("xss")</script>')).toBe('&lt;script&gt;alert(&quot;xss&quot;)&lt;&#x2F;script&gt;');
      expect(sanitizeText('John & Jane')).toBe('John &amp; Jane');
      expect(sanitizeText("O'Connor")).toBe('O&#x27;Connor');
    });

    it('should handle non-string input', () => {
      expect(sanitizeText(null)).toBe('');
      expect(sanitizeText(undefined)).toBe('');
      expect(sanitizeText(123)).toBe('123');
    });
  });

  describe('sanitizeAndTruncate', () => {
    it('should sanitize and truncate long text', () => {
      const longText = '<script>alert("xss")</script>' + 'a'.repeat(100);
      const result = sanitizeAndTruncate(longText, 50);
      expect(result).toHaveLength(50);
      expect(result).toContain('&lt;script&gt;');
      expect(result).toEndWith('...');
    });
  });

  describe('sanitizeCurrency', () => {
    it('should format valid currency amounts', () => {
      expect(sanitizeCurrency(1000)).toBe('$1,000.00');
      expect(sanitizeCurrency('1500.50')).toBe('$1,500.50');
      expect(sanitizeCurrency('$2000')).toBe('$2,000.00');
    });

    it('should handle invalid input', () => {
      expect(sanitizeCurrency(null)).toBe('$0.00');
      expect(sanitizeCurrency(undefined)).toBe('$0.00');
      expect(sanitizeCurrency('invalid')).toBe('$0.00');
    });
  });

  describe('sanitizePropertyName', () => {
    it('should sanitize property names', () => {
      expect(sanitizePropertyName('Sunset <script>alert("xss")</script> Apartments')).toBe('Sunset alert("xss") Apartments');
      expect(sanitizePropertyName('Oak & Pine Building')).toBe('Oak & Pine Building');
      expect(sanitizePropertyName('')).toBe('Unknown Property');
      expect(sanitizePropertyName(null)).toBe('Unknown Property');
    });

    it('should remove dangerous patterns', () => {
      expect(sanitizePropertyName('Building onclick=alert("xss")')).toBe('Building ');
      expect(sanitizePropertyName('javascript:alert("xss")')).toBe('alert("xss")');
    });
  });

  describe('sanitizeTenantName', () => {
    it('should sanitize tenant names', () => {
      expect(sanitizeTenantName('John <script>alert("xss")</script> Doe')).toBe('John alert("xss") Doe');
      expect(sanitizeTenantName('Jane & Bob Smith')).toBe('Jane & Bob Smith');
      expect(sanitizeTenantName('')).toBe('Unknown Tenant');
      expect(sanitizeTenantName(null)).toBe('Unknown Tenant');
    });

    it('should remove dangerous patterns', () => {
      expect(sanitizeTenantName('John onclick=alert("xss") Doe')).toBe('John  Doe');
      expect(sanitizeTenantName('javascript:alert("xss")')).toBe('alert("xss")');
    });
  });
});