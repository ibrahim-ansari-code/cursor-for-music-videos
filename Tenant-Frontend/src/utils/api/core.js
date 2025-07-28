// Core API utility functions for tenant portal backend integration

// Sanitize the base URL: strip any trailing slash to avoid duplicate slashes when concatenating
const API_BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");

if (!API_BASE_URL) {
  throw new Error("CRITICAL: VITE_API_URL environment variable is not defined! Cannot initialize API client.");
}

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
          } catch {
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
      } catch {
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
export const apiRequest = async (endpoint, options = {}) => {
  const token = localStorage.getItem("token");

  // Use the validated API_BASE_URL
  // API_BASE_URL is already validated at module initialization, no need to check again

  if (!token && !endpoint.includes("/auth/")) {
    console.error("No token found for authenticated request");
    window.location.href = "/login";
    throw new Error("Authentication required. Please log in.");
  }

  const requestHeaders = {
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

  const requestOptions = {
    ...options, // Spread options first to allow overriding method, body, etc.
    headers: requestHeaders,
  };

  try {
    // Use the validated API_BASE_URL
    const response = await fetch(
      `${API_BASE_URL}/api${endpoint}`,
      requestOptions
    );

    return handleResponse(response);
  } catch (error) {
    console.error(`API request failed for ${endpoint}:`, error);
    throw error;
  }
};

// Authentication API Functions
// Note: Login is now handled directly by Supabase in AuthContext
// This function is kept for backward compatibility but is not used
export const login = async (email, password) => {
  throw new Error("Login should be handled through Supabase Auth, not the backend API");
};

export const getCurrentUser = async () => {
  try {
    return await apiRequest("/auth/me");
  } catch (error) {
    // If it's an authentication error, clear local storage and don't redirect
    // Let the calling component handle the redirect logic
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