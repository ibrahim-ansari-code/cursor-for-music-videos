import type { RetryOptions, ApiError } from '@/types';

/**
 * Retry an async function with exponential backoff
 * @param fn - The async function to retry
 * @param maxRetries - Maximum number of retry attempts
 * @param baseDelay - Base delay in milliseconds
 * @param retryOn - HTTP status codes or error types to retry on
 * @returns The result of the function or throws the last error
 */
export const retryWithBackoff = async <T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000,
  retryOn: number[] = [408, 429, 500, 502, 503, 504]
): Promise<T> => {
  let lastError: Error | ApiError;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const result = await fn();
      return result;
    } catch (error) {
      lastError = error as Error | ApiError;
      
      // Don't retry on the last attempt
      if (attempt === maxRetries) {
        break;
      }
      
      // Check if we should retry based on error type/status
      const apiError = error as ApiError;
      const shouldRetry = 
        (apiError.status && retryOn.includes(apiError.status)) ||
        (error as { code?: string }).code === 'NETWORK_ERROR' ||
        (error as { code?: string }).code === 'TIMEOUT' ||
        (error as Error).name === 'TypeError'; // Common for network errors
      
      if (!shouldRetry) {
        break;
      }
      
      // Exponential backoff with jitter
      const delay = baseDelay * Math.pow(2, attempt) + Math.random() * 1000;
      console.log(`API call failed (attempt ${attempt + 1}/${maxRetries + 1}), retrying in ${Math.round(delay)}ms...`, (error as Error).message);
      
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw lastError!;
};

/**
 * Specific retry function for getCurrentUser API call
 * @param apiCall - The API call function
 * @returns The user data or throws error
 */
export const retryGetCurrentUser = <T>(apiCall: () => Promise<T>): Promise<T> => {
  return retryWithBackoff(
    apiCall,
    2, // Max 2 retries for user data
    500, // 500ms base delay
    [408, 429, 500, 502, 503, 504] // Retry on these HTTP status codes
  );
};

/**
 * Generic API retry wrapper with user-friendly error messages
 * @param apiCall - The API call function
 * @param operationName - Name of the operation for logging
 * @param options - Retry options
 * @returns The API result or throws with user-friendly message
 */
export const retryApiCall = async <T>(
  apiCall: () => Promise<T>,
  operationName: string = 'API call',
  options: RetryOptions = {}
): Promise<T> => {
  const {
    maxRetries = 3,
    baseDelay = 1000,
    retryOn = [408, 429, 500, 502, 503, 504],
    userFriendlyMessage = `Failed to ${operationName.toLowerCase()}. Please try again.`
  } = options;

  try {
    return await retryWithBackoff(apiCall, maxRetries, baseDelay, retryOn);
  } catch (error) {
    console.error(`${operationName} failed after ${maxRetries + 1} attempts:`, error);
    
    // Return user-friendly error message
    const apiError = new Error(userFriendlyMessage) as ApiError & { 
      originalError: Error; 
      operation: string;
    };
    apiError.originalError = error as Error;
    apiError.operation = operationName;
    throw apiError;
  }
};

