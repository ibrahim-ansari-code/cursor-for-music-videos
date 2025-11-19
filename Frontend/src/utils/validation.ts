/**
 * Validation and Formatting Utilities
 * 
 * Centralized utilities for input validation and formatting across the application.
 * Following industry best practices for user input handling.
 */

/**
 * Format a phone number as (xxx) xxx-xxxx
 * Auto-formats as user types, removing non-numeric characters
 * 
 * @param value - Raw phone input string
 * @returns Formatted phone string
 * 
 * @example
 * formatPhoneNumber('5551234567') // Returns: '(555) 123-4567'
 * formatPhoneNumber('555-123-4567') // Returns: '(555) 123-4567'
 */
export const formatPhoneNumber = (value: string): string => {
  if (!value) return '';
  
  // Remove all non-numeric characters
  const numbers = value.replace(/\D/g, '');
  
  // Format as (xxx) xxx-xxxx
  if (numbers.length <= 3) {
    return numbers;
  } else if (numbers.length <= 6) {
    return `(${numbers.slice(0, 3)}) ${numbers.slice(3)}`;
  } else {
    return `(${numbers.slice(0, 3)}) ${numbers.slice(3, 6)}-${numbers.slice(6, 10)}`;
  }
};

/**
 * Validate a US phone number
 * Accepts formatted or unformatted input
 * 
 * @param phone - Phone number string to validate
 * @returns true if valid 10-digit US phone number
 * 
 * @example
 * validatePhone('(555) 123-4567') // Returns: true
 * validatePhone('555-123-4567') // Returns: true
 * validatePhone('5551234567') // Returns: true
 * validatePhone('555') // Returns: false
 */
export const validatePhone = (phone: string): boolean => {
  if (!phone) return true; // Phone is optional
  const numbers = phone.replace(/\D/g, '');
  return numbers.length === 10; // Valid US phone number
};

/**
 * Validate an email address
 * RFC 5322 compliant email validation
 * 
 * @param email - Email address string to validate
 * @returns true if valid email format
 * 
 * @example
 * validateEmail('user@example.com') // Returns: true
 * validateEmail('invalid.email') // Returns: false
 * validateEmail('user+tag@example.co.uk') // Returns: true
 */
export const validateEmail = (email: string): boolean => {
  if (!email) return true; // Email is optional
  
  // RFC 5322 compliant email regex
  // Supports: local-part@domain with various valid characters
  const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
  
  return emailRegex.test(email);
};

/**
 * Validate required field
 * Checks if field is not empty after trimming whitespace
 * 
 * @param value - Field value to validate
 * @returns true if field has content
 */
export const validateRequired = (value: string | null | undefined): boolean => {
  if (value === null || value === undefined) return false;
  return value.trim().length > 0;
};

/**
 * Validate minimum length
 * 
 * @param value - String to validate
 * @param minLength - Minimum required length
 * @returns true if value meets minimum length
 */
export const validateMinLength = (value: string, minLength: number): boolean => {
  if (!value) return false;
  return value.trim().length >= minLength;
};

/**
 * Validate maximum length
 * 
 * @param value - String to validate
 * @param maxLength - Maximum allowed length
 * @returns true if value is within maximum length
 */
export const validateMaxLength = (value: string, maxLength: number): boolean => {
  if (!value) return true;
  return value.length <= maxLength;
};

/**
 * Validate numeric input
 * 
 * @param value - Value to validate
 * @returns true if value is a valid number
 */
export const validateNumeric = (value: string | number): boolean => {
  if (value === '' || value === null || value === undefined) return false;
  return !isNaN(Number(value));
};

/**
 * Validate URL format
 * 
 * @param url - URL string to validate
 * @returns true if valid URL format
 */
export const validateURL = (url: string): boolean => {
  if (!url) return true; // URL is optional
  
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
};

/**
 * Validate postal code (US ZIP code)
 * Accepts 5-digit or 9-digit (ZIP+4) format
 * 
 * @param postalCode - Postal code to validate
 * @returns true if valid US postal code
 * 
 * @example
 * validatePostalCode('12345') // Returns: true
 * validatePostalCode('12345-6789') // Returns: true
 * validatePostalCode('123') // Returns: false
 */
export const validatePostalCode = (postalCode: string): boolean => {
  if (!postalCode) return true; // Optional
  
  // US ZIP code: 5 digits or 5+4 format
  const postalRegex = /^\d{5}(-\d{4})?$/;
  return postalRegex.test(postalCode);
};


