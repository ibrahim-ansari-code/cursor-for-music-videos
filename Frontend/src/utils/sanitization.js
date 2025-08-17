/**
 * Utility functions for sanitizing user input to prevent XSS attacks
 */

/**
 * Sanitize text content to prevent XSS by escaping HTML characters
 * @param {string} text - The text to sanitize
 * @returns {string} - The sanitized text
 */
export const sanitizeText = (text) => {
  if (typeof text !== 'string') {
    return String(text || '');
  }
  
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
};

/**
 * Sanitize and truncate text for safe display
 * @param {string} text - The text to sanitize and truncate
 * @param {number} maxLength - Maximum length before truncation
 * @returns {string} - The sanitized and truncated text
 */
export const sanitizeAndTruncate = (text, maxLength = 100) => {
  const sanitized = sanitizeText(text);
  if (sanitized.length <= maxLength) {
    return sanitized;
  }
  return sanitized.substring(0, maxLength - 3) + '...';
};

/**
 * Sanitize currency amounts to ensure they're safe for display
 * @param {string|number} amount - The amount to sanitize
 * @returns {string} - The sanitized amount
 */
export const sanitizeCurrency = (amount) => {
  if (amount === null || amount === undefined) {
    return '$0.00';
  }
  
  // Convert to string and remove any non-numeric characters except decimal point
  const cleanAmount = String(amount).replace(/[^\d.-]/g, '');
  const numericAmount = parseFloat(cleanAmount);
  
  if (isNaN(numericAmount)) {
    return '$0.00';
  }
  
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(numericAmount);
};

/**
 * Get sanitized HTML for safe innerHTML usage
 * @param {string} text - The text to sanitize
 * @returns {string} - The sanitized HTML content
 */
export const getSafeHTML = (text) => {
  return sanitizeText(text);
};

/**
 * Validate and sanitize property names
 * @param {string} propertyName - The property name to sanitize
 * @returns {string} - The sanitized property name
 */
export const sanitizePropertyName = (propertyName) => {
  if (!propertyName || typeof propertyName !== 'string') {
    return 'Unknown Property';
  }
  
  // Remove any potentially dangerous characters while preserving normal text
  const sanitized = propertyName
    .replace(/[<>]/g, '') // Remove angle brackets
    .replace(/javascript:/gi, '') // Remove javascript: protocol
    .replace(/on\w+=/gi, '') // Remove event handlers
    .trim();
  
  return sanitized || 'Unknown Property';
};

/**
 * Validate and sanitize tenant names
 * @param {string} tenantName - The tenant name to sanitize
 * @returns {string} - The sanitized tenant name
 */
export const sanitizeTenantName = (tenantName) => {
  if (!tenantName || typeof tenantName !== 'string') {
    return 'Unknown Tenant';
  }
  
  // Remove any potentially dangerous characters while preserving normal text
  const sanitized = tenantName
    .replace(/[<>]/g, '') // Remove angle brackets
    .replace(/javascript:/gi, '') // Remove javascript: protocol
    .replace(/on\w+=/gi, '') // Remove event handlers
    .trim();
  
  return sanitized || 'Unknown Tenant';
};