// API utility functions for interacting with the backend

// Sanitize the base URL: strip any trailing slash to avoid duplicate slashes when concatenating
const API_BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");

if (!API_BASE_URL) {
  console.error("CRITICAL: VITE_API_URL environment variable is not defined!");
  // Optionally, set a default for local development, but throw error in production?
  // Or just let it fail clearly. For now, we log the error.
  // Fallback or error handling logic might be needed depending on requirements.
} else {
  console.log(`API Base URL: ${API_BASE_URL}`);
}

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
        // For /auth/me calls, don't redirect automatically - let the caller handle it
        if (response.url.includes("/auth/me")) {
          console.error("Authentication error on /auth/me:", errorData);
          throw Object.assign(
            new Error("Authentication failed. Session expired."),
            errorObj
          );
        }

        // For other endpoints, clear auth data and redirect to login
        console.error("Authentication error:", errorData);
        localStorage.removeItem("token");
        localStorage.removeItem("user_type");
        localStorage.removeItem("user");
        window.location.href = "/login";
        throw Object.assign(
          new Error("Authentication failed. Please log in again."),
          errorObj
        );
      }

      // Throw enhanced error with all details
      throw Object.assign(
        new Error(errorData.detail || `API error: ${response.status}`),
        errorObj
      );
    } catch (e) {
      // If response is not JSON or another error occurs
      if (e.data) {
        // This is our enhanced error from above, just rethrow it
        throw e;
      }

      if (response.status === 401) {
        // For /auth/me calls, don't redirect automatically
        if (response.url.includes("/auth/me")) {
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
const apiRequest = async (endpoint, options = {}) => {
  const token = localStorage.getItem("token");

  // Use the validated API_BASE_URL
  if (!API_BASE_URL) {
    console.error("API URL is not configured. Cannot make API requests.");
    // Optionally, redirect to an error page or show a message
    throw new Error("API configuration error.");
  }

  // Check if token exists before making authenticated requests
  // Skip this check for /auth/me as it's used to validate the token
  if (!token && !endpoint.includes("/auth/")) {
    console.error("No token found for authenticated request");
    window.location.href = "/login";
    throw new Error("Authentication required. Please log in.");
  }

  const defaultOptions = {
    headers: {
      "Content-Type": "application/json",
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  };

  const requestOptions = {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...(options.headers || {}),
    },
  };

  // Debug logging for request data
  if (endpoint.includes("/accounting/payments") && options.method === "POST") {
    console.log("Payment request data:", JSON.parse(options.body));
  }

  try {
    // Use the validated API_BASE_URL
    const response = await fetch(
      `${API_BASE_URL}/api${endpoint}`,
      requestOptions
    );

    // For debugging: Log the raw response for payment creation
    if (
      endpoint.includes("/accounting/payments") &&
      options.method === "POST"
    ) {
      const responseClone = response.clone();
      const rawText = await responseClone.text();
      console.log("Raw payment response:", rawText || "Empty response");

      if (!response.ok) {
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

// Dashboard API Functions
export const fetchDashboardData = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.property_id) queryParams.append("property_id", params.property_id);
  if (params.time_period) queryParams.append("time_period", params.time_period);

  const queryString = queryParams.toString();
  return apiRequest(`/dashboard${queryString ? "?" + queryString : ""}`);
};

// Leases API Functions
export const fetchLeases = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.status) queryParams.append("status", params.status);
  if (params.property_id) queryParams.append("property_id", params.property_id);
  if (params.tenant_id) queryParams.append("tenant_id", params.tenant_id);

  const queryString = queryParams.toString();
  return apiRequest(`/leases${queryString ? "?" + queryString : ""}`);
};

export const fetchLease = async (leaseId) => {
  return apiRequest(`/leases/${leaseId}`);
};

export const createLease = async (leaseData) => {
  return apiRequest("/leases", {
    method: "POST",
    body: JSON.stringify(leaseData),
  });
};

export const updateLease = async (leaseId, leaseData) => {
  return apiRequest(`/leases/${leaseId}`, {
    method: "PUT",
    body: JSON.stringify(leaseData),
  });
};

export const validateLease = async (leaseId) => {
  return apiRequest(`/leases/${leaseId}/validate`, {
    method: "POST",
  });
};

export const updateLeaseStatus = async (leaseId, status) => {
  console.log(
    `Sending lease status update request: lease ID ${leaseId}, status ${status}`
  );

  try {
    const userType = localStorage.getItem("user_type");
    console.log(`Current user type: ${userType}`);

    // Only allow LANDLORD and ADMIN users to update lease status
    if (userType !== "LANDLORD" && userType !== "ADMIN") {
      console.error(
        `User type ${userType} is not authorized to update lease status`
      );
      throw {
        status: 403,
        message:
          "You are not authorized to update lease status. Only landlords and administrators can update lease status.",
      };
    }

    // First attempt using apiRequest helper
    try {
      return await apiRequest(`/leases/${leaseId}/status`, {
        method: "POST",
        body: JSON.stringify({ status }),
      });
    } catch (apiError) {
      console.error("First attempt failed with apiRequest:", apiError);

      // If first attempt failed with CORS error or network error, try direct fetch
      if (
        apiError.message &&
        (apiError.message.includes("Failed to fetch") ||
          apiError.message.includes("NetworkError"))
      ) {
        console.log("Attempting direct fetch as fallback...");
        const token = localStorage.getItem("token");
        const response = await fetch(
          `${API_BASE_URL}/api/leases/${leaseId}/status`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ status }),
          }
        );

        if (!response.ok) {
          const errorText = await response.text();
          console.error(
            `Error response from server: ${response.status} ${response.statusText}`
          );
          console.error(`Error details: ${errorText}`);
          throw {
            status: response.status,
            message: `Server error: ${errorText || response.statusText}`,
          };
        }

        return await response.json();
      }

      // Rethrow if it's not a network error
      throw apiError;
    }
  } catch (err) {
    console.error("Lease status update failed:", err);
    // Rethrow the error to be handled by the caller
    throw err;
  }
};

export const uploadLeaseDocument = async (leaseId, formData) => {
  const token = localStorage.getItem("token");

  const response = await fetch(`${API_BASE_URL}/api/leases/${leaseId}/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      // Don't set Content-Type as it will be set automatically for FormData
    },
    body: formData,
  });

  return handleResponse(response);
};

export const fetchLeaseDocuments = async (leaseId) => {
  return apiRequest(`/leases/${leaseId}/documents`);
};

// Vendors API Functions
export const fetchVendors = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.status) queryParams.append("status", params.status);
  if (params.business_type)
    queryParams.append("business_type", params.business_type);

  const queryString = queryParams.toString();
  return apiRequest(`/vendors${queryString ? "?" + queryString : ""}`);
};

export const fetchVendor = async (vendorId) => {
  return apiRequest(`/vendors/${vendorId}`);
};

export const createVendor = async (vendorData) => {
  return apiRequest("/vendors", {
    method: "POST",
    body: JSON.stringify(vendorData),
  });
};

export const updateVendor = async (vendorId, vendorData) => {
  return apiRequest(`/vendors/${vendorId}`, {
    method: "PUT",
    body: JSON.stringify(vendorData),
  });
};

export const updateVendorStatus = async (vendorId, status) => {
  return apiRequest(`/vendors/${vendorId}/status?status=${status}`, {
    method: "POST",
  });
};

export const uploadVendorDocument = async (vendorId, formData) => {
  const token = localStorage.getItem("token");

  const response = await fetch(
    `${API_BASE_URL}/api/vendors/${vendorId}/upload`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        // Don't set Content-Type as it will be set automatically for FormData
      },
      body: formData,
    }
  );

  return handleResponse(response);
};

export const fetchVendorDocuments = async (vendorId) => {
  return apiRequest(`/vendors/${vendorId}/documents`);
};

export const assignVendorToProperty = async (vendorId, assignmentData) => {
  return apiRequest(`/vendors/${vendorId}/properties`, {
    method: "POST",
    body: JSON.stringify(assignmentData),
  });
};

export const getVendorOnboardingHelp = async (query) => {
  return apiRequest("/vendors/ai/onboarding-help", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
};

// Accounting API Functions
export const fetchPayments = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.lease_id) queryParams.append("lease_id", params.lease_id);
  if (params.tenant_id) queryParams.append("tenant_id", params.tenant_id);
  if (params.payment_status)
    queryParams.append("payment_status", params.payment_status);
  if (params.start_date) queryParams.append("start_date", params.start_date);
  if (params.end_date) queryParams.append("end_date", params.end_date);

  const queryString = queryParams.toString();
  return apiRequest(
    `/accounting/payments${queryString ? "?" + queryString : ""}`
  );
};

export const createPayment = async (paymentData) => {
  return apiRequest("/accounting/payments", {
    method: "POST",
    body: JSON.stringify(paymentData),
  });
};

export const updatePayment = async (paymentId, paymentData) => {
  return apiRequest(`/accounting/payments/${paymentId}`, {
    method: "PUT",
    body: JSON.stringify(paymentData),
  });
};

export const fetchInvoices = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.tenant_id) queryParams.append("tenant_id", params.tenant_id);
  if (params.property_id) queryParams.append("property_id", params.property_id);
  if (params.status) queryParams.append("status", params.status);
  if (params.start_date) queryParams.append("start_date", params.start_date);
  if (params.end_date) queryParams.append("end_date", params.end_date);

  const queryString = queryParams.toString();
  return apiRequest(
    `/accounting/invoices${queryString ? "?" + queryString : ""}`
  );
};

export const createInvoice = async (invoiceData) => {
  return apiRequest("/accounting/invoices", {
    method: "POST",
    body: JSON.stringify(invoiceData),
  });
};

export const fetchExpenses = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.property_id) queryParams.append("property_id", params.property_id);
  if (params.vendor_id) queryParams.append("vendor_id", params.vendor_id);
  if (params.category) queryParams.append("category", params.category);
  if (params.start_date) queryParams.append("start_date", params.start_date);
  if (params.end_date) queryParams.append("end_date", params.end_date);

  const queryString = queryParams.toString();
  return apiRequest(
    `/accounting/expenses${queryString ? "?" + queryString : ""}`
  );
};

export const createExpense = async (expenseData) => {
  return apiRequest("/accounting/expenses", {
    method: "POST",
    body: JSON.stringify(expenseData),
  });
};

export const getOccupancyRates = async (propertyId) => {
  const queryParams = propertyId ? `?property_id=${propertyId}` : "";
  return apiRequest(`/accounting/occupancy${queryParams}`);
};

export const getRevenueTrends = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.period_type) queryParams.append("period_type", params.period_type);
  if (params.year) queryParams.append("year", params.year);
  if (params.property_id) queryParams.append("property_id", params.property_id);

  const queryString = queryParams.toString();
  return apiRequest(
    `/accounting/revenue-trends${queryString ? "?" + queryString : ""}`
  );
};

export const getAccountingOverview = async () => {
  return apiRequest("/accounting/overview");
};

// Communication API Functions
export const fetchConversations = async () => {
  return apiRequest("/messages/conversations");
};

export const createConversation = async (conversationData) => {
  return apiRequest("/messages/conversations", {
    method: "POST",
    body: JSON.stringify(conversationData),
  });
};

export const fetchMessages = async (conversationId, params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.limit) queryParams.append("limit", params.limit);
  if (params.before_id) queryParams.append("before_id", params.before_id);

  const queryString = queryParams.toString();
  return apiRequest(
    `/messages/conversations/${conversationId}/messages${
      queryString ? "?" + queryString : ""
    }`
  );
};

export const sendMessage = async (messageData) => {
  return apiRequest("/messages/messages", {
    method: "POST",
    body: JSON.stringify(messageData),
  });
};

export const markMessageAsRead = async (messageId) => {
  return apiRequest(`/messages/messages/${messageId}/read`, {
    method: "PUT",
  });
};

export const sendAnnouncement = async (content, recipientType) => {
  const queryParams = recipientType ? `?recipient_type=${recipientType}` : "";
  return apiRequest(`/messages/announcements${queryParams}`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
};

// AI Chatbot API Functions
export const sendChatMessage = async (messages, context, documentIds) => {
  return apiRequest("/ai/chat", {
    method: "POST",
    body: JSON.stringify({
      messages,
      context,
      document_ids: documentIds,
    }),
  });
};

export const documentQA = async (messages, documentIds, context) => {
  return apiRequest("/ai/document-qa", {
    method: "POST",
    body: JSON.stringify({
      messages,
      document_ids: documentIds,
      context,
    }),
  });
};

export const getTenantSupport = async (messages, context) => {
  return apiRequest("/ai/tenant-support", {
    method: "POST",
    body: JSON.stringify({
      messages,
      context,
    }),
  });
};

// Property Management API Functions
export const fetchProperties = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.owner_id) queryParams.append("owner_id", params.owner_id);
  if (params.property_type)
    queryParams.append("property_type", params.property_type);

  const queryString = queryParams.toString();
  return apiRequest(`/properties${queryString ? "?" + queryString : ""}`);
};

export const fetchPropertyById = async (propertyId) => {
  return apiRequest(`/properties/${propertyId}`);
};

export const fetchProperty = async (propertyId) => {
  return apiRequest(`/properties/${propertyId}`);
};

export const createProperty = async (propertyData) => {
  return apiRequest("/properties", {
    method: "POST",
    body: JSON.stringify(propertyData),
  });
};

export const updateProperty = async (propertyId, propertyData) => {
  return apiRequest(`/properties/${propertyId}`, {
    method: "PUT",
    body: JSON.stringify(propertyData),
  });
};

export const deleteProperty = async (propertyId) => {
  return apiRequest(`/properties/${propertyId}`, {
    method: "DELETE",
  });
};

export const fetchPropertyUnits = async (propertyId) => {
  return apiRequest(`/properties/${propertyId}/units`);
};

export const createUnit = async (propertyId, unitData) => {
  console.log(`Creating unit for property ${propertyId} with data:`, unitData);
  return apiRequest(`/properties/${propertyId}/units`, {
    method: "POST",
    body: JSON.stringify(unitData),
  });
};

export const updateUnit = async (unitId, unitData) => {
  console.log(`Updating unit ${unitId} with data:`, unitData);

  try {
    // Ensure numeric values are properly formatted
    const formattedData = {
      ...unitData,
      monthly_rent: unitData.monthly_rent
        ? parseFloat(unitData.monthly_rent)
        : null,
      size: unitData.size ? parseFloat(unitData.size) : null,
      bedrooms: unitData.bedrooms ? parseInt(unitData.bedrooms, 10) : null,
      bathrooms: unitData.bathrooms ? parseFloat(unitData.bathrooms) : null,
      floor: unitData.floor ? parseInt(unitData.floor, 10) : null,
      tenant_id: unitData.tenant_id || null,
    };

    const response = await apiRequest(`/units/${unitId}`, {
      method: "PUT",
      body: JSON.stringify(formattedData),
    });

    console.log(`Unit ${unitId} updated successfully:`, response);
    return response;
  } catch (error) {
    console.error(`Error updating unit ${unitId}:`, error);
    // Enhance error message for better user feedback
    const errorMessage = error.message || "Failed to update unit";
    const enhancedError = new Error(errorMessage);
    enhancedError.originalError = error;
    throw enhancedError;
  }
};

export const deleteUnit = async (unitId) => {
  console.log(`Deleting unit with ID: ${unitId}`);

  try {
    const response = await apiRequest(`/units/${unitId}`, {
      method: "DELETE",
    });
    // The response will be null for 204 status, which is OK
    return response;
  } catch (error) {
    console.error(`Error deleting unit ${unitId}:`, error);
    throw error;
  }
};

// Tenant Management API Functions
export const fetchTenants = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.property_id) queryParams.append("property_id", params.property_id);
  if (params.status) queryParams.append("status", params.status);
  if (params.search) queryParams.append("search", params.search);

  const queryString = queryParams.toString();
  return apiRequest(`/tenants${queryString ? "?" + queryString : ""}`);
};

export const fetchTenant = async (tenantId) => {
  return apiRequest(`/tenants/${tenantId}`);
};

export const createTenant = async (tenantData) => {
  console.log("Creating tenant with data:", tenantData);
  try {
    const sanitizedData = { ...tenantData };

    // Handle email sanitization
    if (typeof sanitizedData.email === "string") {
      sanitizedData.email = sanitizedData.email.trim().toLowerCase();

      // Email format validation
      const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
      if (sanitizedData.email && !emailRegex.test(sanitizedData.email)) {
        throw new Error("Invalid email format");
      }

      // If email is empty string, set to null to avoid validation issues
      if (sanitizedData.email === "") {
        sanitizedData.email = null;
      }
    }

    // Ensure status is properly formatted for the backend enum (First letter uppercase, rest lowercase)
    if (sanitizedData.status) {
      sanitizedData.status =
        sanitizedData.status.charAt(0).toUpperCase() +
        sanitizedData.status.slice(1).toLowerCase();
    }

    // Always set user_id to null for new tenants to avoid unique constraint violations
    sanitizedData.user_id = null;

    console.log("Sending sanitized tenant data:", sanitizedData);

    // Get token from localStorage for authentication
    const token = localStorage.getItem("token");

    // Check if token exists
    if (!token) {
      console.error("No token found for authenticated request");
      throw new Error("Authentication required. Please log in.");
    }

    const response = await fetch(`${API_BASE_URL}/api/tenants`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(sanitizedData),
    });

    // Log response headers for debugging
    console.log("Create tenant response status:", response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Error response text:", errorText);

      let errorData;
      try {
        errorData = JSON.parse(errorText);
        console.error("Parsed error data:", errorData);
      } catch (e) {
        console.error("Failed to parse error response as JSON");
        errorData = { detail: errorText };
      }

      // Enhanced error with response details
      const error = new Error(
        `Failed to create tenant: ${response.statusText}`
      );
      error.status = response.status;
      error.data = errorData;
      error.rawResponse = errorText;
      throw error;
    }

    return await response.json();
  } catch (error) {
    console.error("Error in createTenant:", error);
    throw error;
  }
};

export const updateTenant = async (tenantId, tenantData) => {
  console.log(`Updating tenant ${tenantId} with data:`, tenantData);
  try {
    const sanitizedData = { ...tenantData };

    // Handle email sanitization
    if (typeof sanitizedData.email === "string") {
      sanitizedData.email = sanitizedData.email.trim().toLowerCase();

      // Email format validation
      const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
      if (sanitizedData.email && !emailRegex.test(sanitizedData.email)) {
        throw new Error("Invalid email format");
      }

      // If email is empty string, set to null to avoid validation issues
      if (sanitizedData.email === "") {
        sanitizedData.email = null;
      }
    }

    // Ensure status is properly formatted for the backend enum (First letter uppercase, rest lowercase)
    if (sanitizedData.status) {
      sanitizedData.status =
        sanitizedData.status.charAt(0).toUpperCase() +
        sanitizedData.status.slice(1).toLowerCase();
    }

    // For updates, we should keep the existing user_id if provided
    // This will be handled in the TenantModal.jsx file

    console.log("Sending sanitized tenant data for update:", sanitizedData);

    // Get token from localStorage for authentication
    const token = localStorage.getItem("token");

    // Check if token exists
    if (!token) {
      console.error("No token found for authenticated request");
      throw new Error("Authentication required. Please log in.");
    }

    const response = await fetch(`${API_BASE_URL}/api/tenants/${tenantId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(sanitizedData),
    });

    console.log("Update tenant response status:", response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Error response text:", errorText);

      let errorData;
      try {
        errorData = JSON.parse(errorText);
        console.error("Parsed error data:", errorData);
      } catch (e) {
        console.error("Failed to parse error response as JSON");
        errorData = { detail: errorText };
      }

      // Enhanced error with response details
      const error = new Error(
        `Failed to update tenant: ${response.statusText}`
      );
      error.status = response.status;
      error.data = errorData;
      error.rawResponse = errorText;
      throw error;
    }

    return await response.json();
  } catch (error) {
    console.error("Error in updateTenant:", error);
    throw error;
  }
};

export const deleteTenant = async (tenantId) => {
  return apiRequest(`/tenants/${tenantId}`, {
    method: "DELETE",
  });
};

export const fetchTenantsByProperty = async (propertyId) => {
  if (!propertyId) {
    console.error("fetchTenantsByProperty called without propertyId");
    return []; // Return empty array instead of throwing
  }

  try {
    const queryParams = new URLSearchParams({ property_id: propertyId });
    const data = await apiRequest(`/tenants?${queryParams.toString()}`);

    console.log("Tenants fetched successfully:", data);

    // Handle both array and object responses
    if (Array.isArray(data)) {
      return data;
    } else if (data && typeof data === "object") {
      // Some APIs return { results: [...] } or similar
      return Array.isArray(data.results)
        ? data.results
        : Array.isArray(data.tenants)
        ? data.tenants
        : [data]; // If it's a single tenant object, wrap it
    }

    return [];
  } catch (error) {
    console.error("Error in fetchTenantsByProperty:", error);
    return []; // Return empty array on error to avoid breaking the UI
  }
};

// Landlord Management API Functions
export const fetchLandlords = async () => {
  return apiRequest("/landlords");
};

export const fetchLandlord = async (landlordId) => {
  return apiRequest(`/landlords/${landlordId}`);
};

export const createLandlord = async (landlordData) => {
  return apiRequest("/landlords", {
    method: "POST",
    body: JSON.stringify(landlordData),
  });
};

export const updateLandlord = async (landlordId, landlordData) => {
  return apiRequest(`/landlords/${landlordId}`, {
    method: "PUT",
    body: JSON.stringify(landlordData),
  });
};

// Maintenance API Functions
export const fetchMaintenanceRequests = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.property_id) queryParams.append("property_id", params.property_id);
  if (params.status) queryParams.append("status", params.status);
  if (params.priority) queryParams.append("priority", params.priority);

  const queryString = queryParams.toString();
  return apiRequest(`/maintenance${queryString ? "?" + queryString : ""}`);
};

export const createMaintenanceRequest = async (requestData) => {
  return apiRequest("/maintenance", {
    method: "POST",
    body: JSON.stringify(requestData),
  });
};

export const updateMaintenanceRequest = async (requestId, requestData) => {
  return apiRequest(`/maintenance/${requestId}`, {
    method: "PUT",
    body: JSON.stringify(requestData),
  });
};

export const assignMaintenanceRequest = async (requestId, vendorId) => {
  return apiRequest(`/maintenance/${requestId}/assign?vendor_id=${vendorId}`, {
    method: "POST",
  });
};

export const analyzeLease = async (formData) => {
  const token = localStorage.getItem("token");

  const response = await fetch(`${API_BASE_URL}/api/leases/analyze`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Failed to analyze lease");
  }

  return response.json();
};

export const submitLease = async (leaseData) => {
  try {
    console.log("Submitting lease data:", leaseData);
    const token = localStorage.getItem("token");

    const response = await fetch(`${API_BASE_URL}/api/leases`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(leaseData),
    });

    const result = await handleResponse(response);
    console.log("Lease created successfully:", result);
    return result;
  } catch (error) {
    console.error("Error in submitLease:", error);
    throw error;
  }
};

export const parseLease = async (formData) => {
  const token = localStorage.getItem("token");

  if (!token) {
    throw new Error("Authentication required. Please log in.");
  }

  try {
    console.log("Calling parseLease API endpoint...");
    // Ensure URL is correctly formatted - normalize the URL to not have a trailing slash
    const baseUrl = API_BASE_URL.replace(/\/$/, "");
    const url = `${baseUrl}/api/leases/parse`;

    console.log("API URL:", url);

    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    // Log response status for debugging
    console.log("Parse lease response status:", response.status);

    if (!response.ok) {
      let errorMessage = "Failed to parse lease";
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
        console.error("Error response:", errorData);
      } catch (e) {
        // If JSON parsing fails, get text content instead
        const errorText = await response.text();
        console.error("Error response text:", errorText);
        errorMessage = `${errorMessage}: ${response.status} ${response.statusText}`;
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    console.log("Lease parse successful:", data);
    return data;
  } catch (error) {
    console.error("Error in parseLease:", error);
    throw error;
  }
};

// Add these functions after the existing accounting API functions

export const generateDuePayments = async () => {
  return apiRequest("/accounting/generate-due-payments", {
    method: "POST",
  });
};

export const fetchOutstandingPayments = async () => {
  return apiRequest("/accounting/outstanding-payments");
};

export const fetchRentTracker = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.month) queryParams.append("month", params.month);
  if (params.year) queryParams.append("year", params.year);

  const queryString = queryParams.toString();
  return apiRequest(`/rent-tracker${queryString ? "?" + queryString : ""}`);
};

// User Settings API Functions

/**
 * Update user profile information.
 * @param {number} userId - The ID of the user to update.
 * @param {object} profileData - Object containing first_name, last_name, phone.
 * @returns {Promise<object>} The updated user data.
 */
export const updateUserProfile = async (userId, profileData) => {
  if (!userId) throw new Error("User ID is required to update profile.");
  return apiRequest(`/users/${userId}/profile`, {
    method: "PUT", // Or PATCH depending on your backend implementation
    body: JSON.stringify(profileData),
  });
};

/**
 * Change the user's password.
 * @param {number} userId - The ID of the user.
 * @param {string} newPassword - The new password.
 * @returns {Promise<object>} Success message or error.
 */
export const changeUserPassword = async (userId, newPassword) => {
  if (!userId) throw new Error("User ID is required to change password.");
  return apiRequest(`/users/${userId}/password`, {
    method: "POST",
    body: JSON.stringify({ password: newPassword }),
  });
};

/**
 * Upload a new avatar for the user.
 * @param {number} userId - The ID of the user.
 * @param {FormData} formData - FormData object containing the avatar file under the key 'avatar'.
 * @returns {Promise<object>} Object containing the new profile_image_url.
 */
export const uploadUserAvatar = async (userId, formData) => {
  if (!userId) throw new Error("User ID is required to upload avatar.");
  const token = localStorage.getItem("token");

  // Use fetch directly for FormData as apiRequest might stringify it
  const response = await fetch(
    `${API_BASE_URL}/api/auth/users/${userId}/avatar`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        // 'Content-Type' header is automatically set by the browser for FormData
      },
      body: formData,
    }
  );

  return handleResponse(response);
};

// Add the new report summary function
export const fetchReportSummary = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.report_type) queryParams.append("report_type", params.report_type);
  if (params.date_range) queryParams.append("date_range", params.date_range);
  if (params.property_ids && params.property_ids.length > 0) {
    params.property_ids.forEach((id) => queryParams.append("property_ids", id));
  }

  const queryString = queryParams.toString();
  console.log(`Fetching report summary with query: ${queryString}`); // Debug log
  return apiRequest(`/reports/summary?${queryString}`);
};

// New function to upload lease PDF to blob storage
export const uploadLeasePDF = async (file) => {
  const token = localStorage.getItem("token");

  if (!token) {
    throw new Error("Authentication required. Please log in.");
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    console.log("Uploading lease PDF to blob storage...");
    const url = `${API_BASE_URL}/api/leases/upload-lease`;

    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      let errorMessage = "Failed to upload lease PDF";
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch (e) {
        const errorText = await response.text();
        errorMessage = `${errorMessage}: ${response.status} ${response.statusText}`;
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    console.log("Lease PDF uploaded successfully:", data);
    return data.file_url;
  } catch (error) {
    console.error("Error uploading lease PDF:", error);
    throw error;
  }
};
