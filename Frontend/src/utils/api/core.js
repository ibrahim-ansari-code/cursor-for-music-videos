// Core API utility functions for interacting with the backend
import { executeRecaptchaAction } from '../recaptcha';

// Sanitize the base URL: strip any trailing slash to avoid duplicate slashes when concatenating
const API_BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");

if (!API_BASE_URL) {
  throw new Error("CRITICAL: VITE_API_URL environment variable is not defined! Cannot initialize API client.");
}

// Helper function to format query strings with proper URL formatting
export const formatQueryString = (queryString) => {
  // Type check to ensure input is safely convertible to string
  if (queryString == null) return "";

  let processedString = queryString;
  if (typeof processedString !== "string") {
    // Convert to string - String() constructor never throws
    processedString = String(processedString);
  }

  if (!processedString) return "";
  return processedString.startsWith("?")
    ? processedString
    : `?${processedString}`;
};

// Helper function to handle 401 authentication errors
const handle401Error = (response, errorObj) => {
  // For /auth/me calls, don't redirect automatically - let the caller handle it
  if (response.url.toLowerCase().includes("/auth/me")) {
    throw Object.assign(
      new Error("Authentication failed. Session expired."),
      errorObj
    );
  }

  // For other endpoints, clear auth data and redirect to login
  localStorage.removeItem("token");
  localStorage.removeItem("user_type");
  localStorage.removeItem("user");
  window.location.href = "/login";
  throw Object.assign(
    new Error("Authentication failed. Please log in again."),
    errorObj
  );
};

// Helper function to handle API responses
const handleResponse = async (response) => {
  if (!response.ok) {
    // Try to parse error message from response
    let errorObj = {
      status: response.status,
      statusText: response.statusText,
      url: response.url,
    };

    try {
      const errorData = await response.json();
      errorObj.data = errorData;

      // Handle auth errors
      if (response.status === 401) {
        console.error("Authentication error:", errorData);
        handle401Error(response, errorObj);
      }

      // Throw enhanced error with all details
      let errorMessage = `API error: ${response.status}`;
      if (errorData.detail) {
        if (typeof errorData.detail === "string") {
          errorMessage = errorData.detail;
        } else {
          // If detail is an array or object (e.g., Pydantic validation errors), stringify it.
          try {
            errorMessage = JSON.stringify(errorData.detail);
          } catch (e) {
            errorMessage = "Could not stringify error details.";
          }
        }
      }
      throw Object.assign(new Error(errorMessage), errorObj);
    } catch (e) {
      // If response is not JSON or another error occurs
      if (e.data) {
        // This is our enhanced error from above, just rethrow it
        throw e;
      }

      if (response.status === 401) {
        handle401Error(response, errorObj);
      }

      // Try to get text content if JSON parsing failed
      try {
        const textContent = await response.text();
        errorObj.rawResponse = textContent;

        throw Object.assign(
          new Error(
            `API error: ${response.status}. ${
              textContent || response.statusText
            }`
          ),
          errorObj
        );
      } catch (textError) {
        errorObj.rawResponseError = "Couldn't read response text";
        throw Object.assign(
          new Error(`API error: ${response.status}. ${response.statusText}`),
          errorObj
        );
      }
    }
  }

  // For 204 No Content responses, return null instead of trying to parse JSON
  if (response.status === 204) {
    return null;
  }

  // For other successful responses, parse JSON
  return response.json();
};

// Base API request function with authentication
// options.recaptchaAction (string) - when provided, a v3 token is fetched and sent as headers
// Type hint (JSDoc) so TS callers accept the option
/**
 * @typedef {Object} ApiRequestOptions
 * @property {string} [method]
 * @property {any} [body]
 * @property {Record<string,string>} [headers]
 * @property {boolean} [cache]
 * @property {number} [cacheMaxAge]
 * @property {AbortSignal} [signal]
 * @property {string} [recaptchaAction]
 */
/** @param {string} endpoint @param {ApiRequestOptions} [options] */
export const apiRequest = async (endpoint, options = {}) => {
  const token = localStorage.getItem("token");

  // Use the validated API_BASE_URL
  if (!API_BASE_URL) {
    console.error("API URL is not configured. Cannot make API requests.");
    throw new Error("API configuration error.");
  }

  if (!token && !endpoint.includes("/auth/")) {
    console.error("No token found for authenticated request");
    window.location.href = "/login";
    throw new Error("Authentication required. Please log in.");
  }

  const requestHeaders = {
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  // Inject reCAPTCHA headers when requested
  if (options.recaptchaAction) {
    try {
      const rcToken = await executeRecaptchaAction(options.recaptchaAction);
      if (rcToken) {
        requestHeaders['X-Recaptcha-Token'] = rcToken;
        requestHeaders['X-Recaptcha-Action'] = options.recaptchaAction;
      }
    } catch (e) {
      // If reCAPTCHA fails to execute, proceed without headers; server will enforce
      console.warn('reCAPTCHA execution failed:', e);
    }
  }

  // Add intelligent Cache-Control header for GET requests
  // Allow caching unless explicitly disabled
  if (!options.method || options.method.toUpperCase() === "GET") {
    if (options.cache === false) {
      // Explicit no-cache when needed
      requestHeaders["Cache-Control"] = "no-cache";
      requestHeaders["Pragma"] = "no-cache";
      requestHeaders["Expires"] = "0";
    } else {
      // Allow reasonable caching for GET requests (5 minutes default)
      const maxAge = options.cacheMaxAge || 300; // 5 minutes default
      requestHeaders["Cache-Control"] = `max-age=${maxAge}, must-revalidate`;
    }
  }

  // Do NOT set Content-Type for FormData; browser handles it.
  if (
    options.method &&
    options.method.toUpperCase() !== "GET" &&
    !(options.body instanceof FormData)
  ) {
    requestHeaders["Content-Type"] = "application/json";
  }

  const requestOptions = {
    ...options, // Spread options first to allow overriding method, body, etc.
    headers: requestHeaders,
  };

  // Debug logging for request data
  if (
    import.meta.env.MODE !== 'production' &&
    endpoint.includes("/accounting/payments") &&
    options.method === "POST" &&
    typeof options.body === "string"
  ) {
    try {
      console.log("Payment request data:", JSON.parse(options.body));
    } catch {
      console.log("Payment request data: <non-JSON body>");
    }
  }

  try {
    // Use the validated API_BASE_URL
    const response = await fetch(
      `${API_BASE_URL}/api${endpoint}`,
      requestOptions
    );

    // For debugging: Log the raw response for payment creation
    if (
      (endpoint.includes("/accounting/payments/parse-receipt") ||
        endpoint.includes("/accounting/payments")) &&
      options.method === "POST"
    ) {
      const responseClone = response.clone();
      const rawText = await responseClone.text();
      console.log(`Raw response for ${endpoint}:`, rawText || "Empty response");

      if (!response.ok) {
        // Use the detailed error message from rawText if available for 422s from this specific path
        if (response.status === 422 && rawText) {
          try {
            const parsedError = JSON.parse(rawText);
            let detailMessage = "Unprocessable Entity";
            if (parsedError.detail) {
              detailMessage =
                typeof parsedError.detail === "string"
                  ? parsedError.detail
                  : JSON.stringify(parsedError.detail);
            }
            throw new Error(detailMessage);
          } catch (jsonError) {
            throw new Error(rawText); // Fallback to raw text if JSON parsing of error fails
          }
        }
        throw new Error(rawText || `HTTP error ${response.status}`);
      }

      // Try to parse as JSON if possible
      try {
        return JSON.parse(rawText);
      } catch (e) {
        console.error("Failed to parse response as JSON:", e);
        throw new Error("Invalid response format from server");
      }
    }

    return handleResponse(response);
  } catch (error) {
    console.error(`API request failed for ${endpoint}:`, error);
    throw error;
  }
};

// Authentication API Functions
export const login = async (email, password) => {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  // Use the validated API_BASE_URL
  if (!API_BASE_URL) {
    console.error("API URL is not configured. Cannot attempt login.");
    throw new Error("API configuration error.");
  }
  const loginUrl = `${API_BASE_URL}/api/auth/token`;
  console.log(`Attempting login to: ${loginUrl}`); // Log the URL before fetch

  const response = await fetch(loginUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData,
  });

  return handleResponse(response);
};

export const register = async (userData) => {
  return apiRequest("/auth/register", {
    method: "POST",
    body: JSON.stringify(userData),
  });
};

export const getCurrentUser = async () => {
  try {
    return await apiRequest("/auth/me");
  } catch (error) {
    // If it's an authentication error, clear local storage and don't redirect
    // Let the App.jsx handle the redirect logic
    if (error.status === 401 || error.status === 403) {
      console.log(
        "Authentication error in getCurrentUser, clearing local storage"
      );
      localStorage.removeItem("token");
      localStorage.removeItem("user_type");
      localStorage.removeItem("user");
      // Don't redirect here, let App.jsx handle it
      throw error;
    }
    // For other errors, just rethrow
    throw error;
  }
};

// File upload helper
export const uploadFile = async (endpoint, fileOrFormData, options = {}) => {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("Authentication required. Please log in.");

  let formData;
  if (fileOrFormData instanceof FormData) {
    formData = fileOrFormData;
  } else {
    formData = new FormData();
    const formKey = options.formKey || "file";
    formData.append(formKey, fileOrFormData);
    // Add any extra fields if provided
    if (options.extraFields) {
      Object.entries(options.extraFields).forEach(([k, v]) =>
        formData.append(k, v)
      );
    }
  }

  const response = await fetch(`${API_BASE_URL}/api${endpoint}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      // Content-Type is set automatically for FormData
    },
    body: formData,
  });

  return handleResponse(response);
}; 