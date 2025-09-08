/**
 * @file security.ts
 * @description Security utilities for input validation and sanitization
 */

import Decimal from 'decimal.js';

// XSS Protection - Sanitize strings that might be displayed in UI
export const sanitizeString = (input: unknown): string => {
  if (typeof input !== 'string') {
    return '';
  }

  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;')
    .trim();
};

// Sanitize and validate financial amounts
export const sanitizeFinancialAmount = (input: unknown): string => {
  if (typeof input === 'number') {
    if (!isFinite(input) || input < 0) {
      return '0.00';
    }
    return input.toFixed(2);
  }

  if (typeof input !== 'string') {
    return '0.00';
  }

  // Remove any non-digit, non-decimal point characters
  const cleaned = input.replace(/[^\d.-]/g, '');
  
  // Parse as decimal for precision
  try {
    const decimal = new Decimal(cleaned);
    if (decimal.isNaN() || decimal.isNegative()) {
      return '0.00';
    }
    
    // Cap at reasonable maximum (adjust as needed)
    const MAX_AMOUNT = new Decimal('999999999.99');
    if (decimal.greaterThan(MAX_AMOUNT)) {
      return MAX_AMOUNT.toFixed(2);
    }
    
    return decimal.toFixed(2);
  } catch {
    return '0.00';
  }
};

// Validate and sanitize tax rates
export const sanitizeTaxRate = (input: unknown): string => {
  if (typeof input === 'number') {
    if (!isFinite(input)) {
      return '0.00';
    }
    if (input < 0) {
      return '0.00';
    }
    if (input > 100) {
      return '100.00';
    }
    return input.toFixed(2);
  }

  if (typeof input !== 'string') {
    return '0.00';
  }

  const cleaned = input.replace(/[^\d.-]/g, '');
  
  try {
    const decimal = new Decimal(cleaned);
    if (decimal.isNaN() || decimal.isNegative()) {
      return '0.00';
    }
    
    // Tax rates should be between 0% and 100%
    if (decimal.greaterThan(100)) {
      return '100.00';
    }
    
    return decimal.toFixed(2);
  } catch {
    return '0.00';
  }
};

// Validate invoice numbers (prevent injection attacks)
export const sanitizeInvoiceNumber = (input: unknown): string => {
  if (typeof input !== 'string') {
    return '';
  }

  // Allow alphanumeric, dashes, underscores, and dots only
  return input
    .replace(/[^a-zA-Z0-9\-_.]/g, '')
    .trim()
    .substring(0, 50); // Reasonable length limit
};

// Validate and sanitize property/tenant IDs
export const sanitizeId = (input: unknown): number | null => {
  if (typeof input === 'number') {
    return Number.isInteger(input) && input > 0 ? input : null;
  }

  if (typeof input === 'string') {
    const parsed = parseInt(input, 10);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
  }

  return null;
};

// Validate dates and prevent invalid date injection
export const sanitizeDate = (input: unknown): string => {
  if (typeof input !== 'string') {
    return '';
  }

  // Basic ISO date format validation
  const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
  if (!dateRegex.test(input)) {
    return '';
  }

  const date = new Date(input);
  if (isNaN(date.getTime())) {
    return '';
  }

  // Reasonable date range validation (adjust as needed)
  const minDate = new Date('1900-01-01');
  const maxDate = new Date('2100-12-31');
  
  if (date < minDate || date > maxDate) {
    return '';
  }

  return input;
};

// Rate limiting for API calls (simple client-side implementation)
class RateLimiter {
  private calls: Map<string, number[]> = new Map();
  
  public isAllowed(key: string, windowMs: number = 60000, maxCalls: number = 10): boolean {
    const now = Date.now();
    const windowStart = now - windowMs;
    
    if (!this.calls.has(key)) {
      this.calls.set(key, []);
    }
    
    const callTimes = this.calls.get(key)!;
    
    // Remove old calls outside the window
    while (callTimes.length > 0 && callTimes[0] < windowStart) {
      callTimes.shift();
    }
    
    // Check if we've exceeded the limit
    if (callTimes.length >= maxCalls) {
      return false;
    }
    
    // Add this call
    callTimes.push(now);
    return true;
  }
  
  public reset(key: string): void {
    this.calls.delete(key);
  }
}

export const rateLimiter = new RateLimiter();

// Validate CSV input to prevent CSV injection
export const sanitizeCSVField = (input: unknown): string => {
  if (typeof input !== 'string') {
    return '';
  }

  // Remove potential CSV injection characters only at the start of the string
  // This preserves legitimate negative amounts while preventing injection attacks
  let sanitized = input.replace(/^[=@+\-]/g, ''); // Only remove if at start
  
  // Basic sanitization
  sanitized = sanitizeString(sanitized);
  
  // Limit length to prevent abuse
  return sanitized.substring(0, 1000);
};

// Validate file uploads (for receipts)
export const validateFileUpload = (file: File): { valid: boolean; error?: string } => {
  // Check file size (max 10MB)
  const MAX_SIZE = 10 * 1024 * 1024;
  if (file.size > MAX_SIZE) {
    return { valid: false, error: 'File size must be less than 10MB' };
  }

  // Check file type
  const allowedTypes = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'application/pdf'
  ];
  
  if (!allowedTypes.includes(file.type)) {
    return { valid: false, error: 'Only JPEG, PNG, GIF, and PDF files are allowed' };
  }

  // Check file name for suspicious patterns
  const suspiciousPatterns = [
    /\.exe$/i,
    /\.bat$/i,
    /\.cmd$/i,
    /\.scr$/i,
    /\.js$/i,
    /\.vbs$/i,
    /\.php$/i,
  ];

  const hasSuspiciousExtension = suspiciousPatterns.some(pattern => 
    pattern.test(file.name)
  );

  if (hasSuspiciousExtension) {
    return { valid: false, error: 'File type not allowed for security reasons' };
  }

  return { valid: true };
};

// Prevent prototype pollution in object properties
export const sanitizeObjectKeys = (obj: any): any => {
  if (!obj || typeof obj !== 'object') {
    return {};
  }

  const sanitized: any = {};
  const allowedKeys = Object.keys(obj).filter(key => 
    !key.includes('__proto__') && 
    !key.includes('constructor') && 
    !key.includes('prototype')
  );

  for (const key of allowedKeys) {
    const value = obj[key];
    if (typeof value === 'string') {
      sanitized[key] = sanitizeString(value);
    } else if (typeof value === 'number' && isFinite(value)) {
      sanitized[key] = value;
    } else if (typeof value === 'boolean') {
      sanitized[key] = value;
    } else if (Array.isArray(value)) {
      // Basic array sanitization (shallow)
      sanitized[key] = value.map(item => 
        typeof item === 'string' ? sanitizeString(item) : item
      );
    }
  }

  return sanitized;
};

// Content Security Policy helpers
export const createNonce = (): string => {
  const array = new Uint8Array(16);
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    crypto.getRandomValues(array);
  } else {
    console.warn('Web Crypto unavailable. Falling back to Math.random for nonce generation.');
    for (let i = 0; i < array.length; i++) {
      array[i] = Math.floor(Math.random() * 256);
    }
  }
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
};

// Secure random ID generation
export const generateSecureId = (prefix: string = ''): string => {
  const timestamp = Date.now().toString(36);
  const length = 16; // 16 bytes -> 32 hex chars
  let randomHex = '';
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    const bytes = new Uint8Array(length);
    crypto.getRandomValues(bytes);
    randomHex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
  } else {
    console.warn('Web Crypto unavailable. Falling back to Math.random for ID generation.');
    for (let i = 0; i < length; i++) {
      randomHex += Math.floor(Math.random() * 256).toString(16).padStart(2, '0');
    }
  }
  return `${prefix}${timestamp}_${randomHex}`;
};

export default {
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
  createNonce,
  generateSecureId,
};