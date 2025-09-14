import * as Sentry from '@sentry/react';

// Error severity levels for better prioritization in Sentry dashboard
export type ErrorSeverity = 'fatal' | 'error' | 'warning' | 'info';

// Interface for error context to ensure consistency
export interface ErrorContext {
  component?: string;
  action?: string;
  userId?: string | number;
  tags?: Record<string, string | number | boolean>;
  extra?: Record<string, any>;
  fingerprint?: string[];
}

// Sensitive field patterns that should be sanitized
const SENSITIVE_FIELD_PATTERNS = [
  /password/i,
  /token/i,
  /secret/i,
  /key/i,
  /ssn/i,
  /social.security/i,
  /credit.card/i,
  /bank.account/i,
  /routing.number/i,
  /api.key/i,
  /private/i,
];

// Fields that should be completely removed from logging
const SENSITIVE_FIELDS_TO_REMOVE = [
  'password',
  'confirmPassword', 
  'token',
  'accessToken',
  'refreshToken',
  'apiKey',
  'privateKey',
  'secretKey',
  'creditCardNumber',
  'ssn',
  'socialSecurityNumber',
  'bankAccountNumber',
  'routingNumber',
];

/**
 * Sanitizes sensitive data before sending to Sentry
 * @param data - The data object to sanitize
 * @returns Sanitized data object
 */
const sanitizeData = (data: any): any => {
  if (!data || typeof data !== 'object') {
    return data;
  }

  if (Array.isArray(data)) {
    return data.map(item => sanitizeData(item));
  }

  const sanitized: any = {};
  
  for (const [key, value] of Object.entries(data)) {
    // Remove completely sensitive fields
    if (SENSITIVE_FIELDS_TO_REMOVE.includes(key)) {
      continue;
    }
    
    // Check if key matches sensitive patterns
    const isSensitive = SENSITIVE_FIELD_PATTERNS.some(pattern => pattern.test(key));
    
    if (isSensitive && typeof value === 'string') {
      // Mask sensitive string values
      sanitized[key] = value.length > 0 ? '[REDACTED]' : '';
    } else if (typeof value === 'object' && value !== null) {
      // Recursively sanitize nested objects
      sanitized[key] = sanitizeData(value);
    } else {
      sanitized[key] = value;
    }
  }
  
  return sanitized;
};

/**
 * Maps our severity levels to Sentry severity levels
 */
const mapSeverityToSentry = (severity: ErrorSeverity): Sentry.SeverityLevel => {
  switch (severity) {
    case 'fatal':
      return 'fatal';
    case 'error':
      return 'error';
    case 'warning':
      return 'warning';
    case 'info':
      return 'info';
    default:
      return 'error';
  }
};

/**
 * Checks if Sentry is properly initialized and available
 * @returns boolean indicating if Sentry is available
 */
const isSentryAvailable = (): boolean => {
  try {
    return !!(Sentry && typeof Sentry.captureException === 'function' && typeof Sentry.getCurrentScope === 'function');
  } catch {
    return false;
  }
};

/**
 * Centralized error reporting utility with defensive programming
 * @param error - The error to report
 * @param context - Additional context and configuration
 * @param severity - Error severity level (defaults to 'error')
 */
export const reportError = (
  error: Error | string | unknown,
  context: ErrorContext = {},
  severity: ErrorSeverity = 'error'
): void => {
  // Normalize error to Error instance
  const errorInstance = error instanceof Error 
    ? error 
    : new Error(typeof error === 'string' ? error : String(error));

  // Sanitize context data to prevent sensitive data exposure
  const sanitizedContext = {
    ...context,
    extra: context.extra ? sanitizeData(context.extra) : undefined,
  };

  // Enhanced error context with consistent structure
  const errorContext = {
    tags: {
      severity,
      timestamp: new Date().toISOString(),
      userAgent: navigator?.userAgent ? 'browser' : 'unknown',
      ...sanitizedContext.tags,
    },
    contexts: {
      application: {
        component: sanitizedContext.component || 'unknown',
        action: sanitizedContext.action || 'unknown',
        errorSeverity: severity,
      },
      ...(sanitizedContext.userId && {
        user: { id: sanitizedContext.userId }
      }),
    },
    level: mapSeverityToSentry(severity),
    ...(sanitizedContext.extra && { extra: sanitizedContext.extra }),
    ...(sanitizedContext.fingerprint && { fingerprint: sanitizedContext.fingerprint }),
  };

  // Defensive Sentry reporting with fallback
  if (isSentryAvailable()) {
    try {
      Sentry.captureException(errorInstance, errorContext);
    } catch (sentryError) {
      // Fallback to console if Sentry fails
      console.error('[Sentry Error]', sentryError);
      console.error('[Original Error]', errorInstance, sanitizedContext);
    }
  } else {
    // Fallback to console logging when Sentry is not available
    console.error('[Error Reporting - Sentry Unavailable]', {
      error: errorInstance,
      context: sanitizedContext,
      severity,
    });
  }
};

/**
 * Convenience method for reporting fatal errors
 */
export const reportFatalError = (
  error: Error | string | unknown,
  context: ErrorContext = {}
): void => {
  reportError(error, context, 'fatal');
};

/**
 * Convenience method for reporting warnings
 */
export const reportWarning = (
  error: Error | string | unknown,
  context: ErrorContext = {}
): void => {
  reportError(error, context, 'warning');
};

/**
 * Convenience method for reporting info-level errors
 */
export const reportInfo = (
  error: Error | string | unknown,
  context: ErrorContext = {}
): void => {
  reportError(error, context, 'info');
};

/**
 * Performance span wrapper with Sentry integration
 * @param operation - The operation name
 * @param description - Description of the span
 * @param callback - Function to execute within the span
 * @returns Result of the callback function
 */
export const withPerformanceSpan = async <T>(
  operation: string,
  description: string,
  callback: () => Promise<T> | T
): Promise<T> => {
  if (isSentryAvailable() && Sentry.startSpan) {
    return Sentry.startSpan(
      {
        op: operation,
        name: description,
      },
      callback
    );
  }
  
  // Fallback execution without performance tracking
  return callback();
};
