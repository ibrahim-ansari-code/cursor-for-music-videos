/**
 * Utility function for retrying API calls with exponential backoff
 */

/**
 * Retry an async function with exponential backoff
 * @param {Function} fn - The async function to retry
 * @param {number} maxRetries - Maximum number of retry attempts
 * @param {number} baseDelay - Base delay in milliseconds
 * @param {Array} retryOn - HTTP status codes or error types to retry on
 * @returns {Promise} - The result of the function or throws the last error
 */
export const retryWithBackoff = async (
  fn,
  maxRetries = 3,
  baseDelay = 1000,
  retryOn = [408, 429, 500, 502, 503, 504]
) => {
  let lastError;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const result = await fn();
      return result;
    } catch (error) {
      lastError = error;
      
      // Don't retry on the last attempt
      if (attempt === maxRetries) {
        break;
      }
      
      // Check if we should retry based on error type/status
      const shouldRetry = 
        error.status && retryOn.includes(error.status) ||
        error.code === 'NETWORK_ERROR' ||
        error.code === 'TIMEOUT' ||
        error.name === 'TypeError'; // Common for network errors
      
      if (!shouldRetry) {
        break;
      }
      
      // Exponential backoff with jitter
      const delay = baseDelay * Math.pow(2, attempt) + Math.random() * 1000;
      console.log(`API call failed (attempt ${attempt + 1}/${maxRetries + 1}), retrying in ${Math.round(delay)}ms...`, error.message);
      
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw lastError;
};

/**
 * Specific retry function for getCurrentUser API call
 * @param {Function} apiCall - The API call function
 * @returns {Promise} - The user data or throws error
 */
export const retryGetCurrentUser = (apiCall) => {
  return retryWithBackoff(
    apiCall,
    2, // Max 2 retries for user data
    500, // 500ms base delay
    [408, 429, 500, 502, 503, 504] // Retry on these HTTP status codes
  );
};

/**
 * Generic API retry wrapper with user-friendly error messages
 * @param {Function} apiCall - The API call function
 * @param {string} operationName - Name of the operation for logging
 * @param {Object} options - Retry options
 * @returns {Promise} - The API result or throws with user-friendly message
 */
export const retryApiCall = async (apiCall, operationName = 'API call', options = {}) => {
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
    const apiError = new Error(userFriendlyMessage);
    apiError.originalError = error;
    apiError.operation = operationName;
    throw apiError;
  }
};