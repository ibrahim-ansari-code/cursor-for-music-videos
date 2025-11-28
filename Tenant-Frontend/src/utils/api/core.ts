import type { ApiError, User } from '@/types';

// Sanitize the base URL: strip any trailing slash to avoid duplicate slashes when concatenating
// Use a test fallback URL when in test mode
const API_BASE_URL = (import.meta.env.VITE_API_URL || 
  (import.meta.env.MODE === 'test' ? 'http://localhost:8000' : "")
).replace(/\/+$/, "");

if (!API_BASE_URL) {
  throw new Error("CRITICAL: VITE_API_URL environment variable is not defined! Cannot initialize API client.");
}

// Helper function to handle 401 authentication errors
const handle401Error = (response: Response, errorObj: Partial<ApiError>): never => {
  // For /auth/me calls, don't redirect automatically - let the caller handle it
  if (response.url.toLowerCase().includes("/auth/me")) {
    const error = new Error("Authentication failed. Session expired.") as ApiError;
    Object.assign(error, errorObj);
    throw error;
  }

  // For other endpoints, clear auth data and redirect to login
  localStorage.removeItem("token");
  localStorage.removeItem("user_type");
  localStorage.removeItem("user");
  window.location.href = "/login";
  
  const error = new Error("Authentication failed. Please log in again.") as ApiError;
  Object.assign(error, errorObj);
  throw error;
};

// Helper function to handle API responses
const handleResponse = async <T>(response: Response): Promise<T | null> => {
  if (!response.ok) {
    // Try to parse error message from response
    const errorObj: Partial<ApiError> = {
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
          } catch {
            errorMessage = "Could not stringify error details.";
          }
        }
      }
      const error = new Error(errorMessage) as ApiError;
      Object.assign(error, errorObj);
      throw error;
    } catch (e) {
      // If response is not JSON or another error occurs
      if ((e as ApiError).data) {
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

        const error = new Error(
          `API error: ${response.status}. ${textContent || response.statusText}`
        ) as ApiError;
        Object.assign(error, errorObj);
        throw error;
      } catch {
        errorObj.rawResponseError = "Couldn't read response text";
        const error = new Error(
          `API error: ${response.status}. ${response.statusText}`
        ) as ApiError;
        Object.assign(error, errorObj);
        throw error;
      }
    }
  }

  // For 204 No Content responses, return null instead of trying to parse JSON
  if (response.status === 204) {
    return null;
  }

  // For other successful responses, parse JSON
  return response.json() as Promise<T>;
};

interface ApiRequestOptions extends RequestInit {
  headers?: Record<string, string>;
}

// Base API request function with authentication
export const apiRequest = async <T>(endpoint: string, options: ApiRequestOptions = {}): Promise<T | null> => {
  const token = localStorage.getItem("token");

  if (!token && !endpoint.includes("/auth/")) {
    console.error("No token found for authenticated request");
    window.location.href = "/login";
    throw new Error("Authentication required. Please log in.");
  }

  const requestHeaders: Record<string, string> = {
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  // Add Cache-Control header for GET requests to prevent unwanted caching
  if (!options.method || options.method.toUpperCase() === "GET") {
    requestHeaders["Cache-Control"] = "no-cache";
    requestHeaders["Pragma"] = "no-cache"; // For older HTTP/1.0 caches
    requestHeaders["Expires"] = "0"; // For proxies
  }

  // Do NOT set Content-Type for FormData; browser handles it.
  if (
    options.method &&
    options.method.toUpperCase() !== "GET" &&
    !(options.body instanceof FormData)
  ) {
    requestHeaders["Content-Type"] = "application/json";
  }

  const requestOptions: RequestInit = {
    ...options,
    headers: requestHeaders,
  };

  try {
    const response = await fetch(
      `${API_BASE_URL}/api${endpoint}`,
      requestOptions
    );

    return handleResponse<T>(response);
  } catch (error) {
    console.error(`API request failed for ${endpoint}:`, error);
    throw error;
  }
};

// Authentication API Functions
// Note: Login is now handled directly by Supabase in AuthContext
// This function is kept for backward compatibility but is not used
export const login = async (): Promise<never> => {
  throw new Error("Login should be handled through Supabase Auth, not the backend API");
};

export const getCurrentUser = async (): Promise<User> => {
  try {
    const result = await apiRequest<User>("/auth/me");
    if (!result) {
      throw new Error("No user data returned");
    }
    return result;
  } catch (error) {
    // If it's an authentication error, clear local storage and don't redirect
    // Let the calling component handle the redirect logic
    const apiError = error as ApiError;
    if (apiError.status === 401 || apiError.status === 403) {
      console.log(
        "Authentication error in getCurrentUser, clearing local storage"
      );
      localStorage.removeItem("token");
      localStorage.removeItem("user_type");
      localStorage.removeItem("user");
      // Don't redirect here, let App.tsx handle it
      throw error;
    }
    // For other errors, just rethrow
    throw error;
  }
};

