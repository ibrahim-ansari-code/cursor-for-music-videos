// API utility functions for interacting with the backend

// Helper function to handle API responses
const handleResponse = async (response) => {
  if (!response.ok) {
    // Try to parse error message from response
    try {
      const errorData = await response.json();
      throw new Error(errorData.detail || `API error: ${response.status}`);
    } catch (e) {
      if (response.status === 401) {
        // Clear auth data and redirect to login
        localStorage.removeItem('token');
        localStorage.removeItem('user_type');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
      // If response is not JSON or another error occurs
      throw new Error(`API error: ${response.status}`);
    }
  }
  
  return response.json();
};

// Base API request function with authentication
const apiRequest = async (endpoint, options = {}) => {
  const token = localStorage.getItem('token');
  
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers
    }
  };
  
  const requestOptions = {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...(options.headers || {})
    }
  };
  
  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api${endpoint}`, requestOptions);
  return handleResponse(response);
};

// Authentication API Functions
export const login = async (email, password) => {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);
  
  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/auth/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData,
  });
  
  return handleResponse(response);
};

export const register = async (userData) => {
  return apiRequest('/auth/register', {
    method: 'POST',
    body: JSON.stringify(userData)
  });
};

export const getCurrentUser = async () => {
  return apiRequest('/auth/me');
};

// Dashboard API Functions
export const fetchDashboardData = async (params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.property_id) queryParams.append('property_id', params.property_id);
  if (params.time_period) queryParams.append('time_period', params.time_period);
  
  const queryString = queryParams.toString();
  return apiRequest(`/dashboard${queryString ? '?' + queryString : ''}`);
};

// Leases API Functions
export const fetchLeases = async (params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.status) queryParams.append('status', params.status);
  if (params.property_id) queryParams.append('property_id', params.property_id);
  if (params.tenant_id) queryParams.append('tenant_id', params.tenant_id);
  
  const queryString = queryParams.toString();
  return apiRequest(`/leases${queryString ? '?' + queryString : ''}`);
};

export const fetchLease = async (leaseId) => {
  return apiRequest(`/leases/${leaseId}`);
};

export const createLease = async (leaseData) => {
  return apiRequest('/leases', {
    method: 'POST',
    body: JSON.stringify(leaseData)
  });
};

export const updateLease = async (leaseId, leaseData) => {
  return apiRequest(`/leases/${leaseId}`, {
    method: 'PUT',
    body: JSON.stringify(leaseData)
  });
};

export const validateLease = async (leaseId) => {
  return apiRequest(`/leases/${leaseId}/validate`, {
    method: 'POST'
  });
};

export const updateLeaseStatus = async (leaseId, status) => {
  return apiRequest(`/leases/${leaseId}/status?status=${status}`, {
    method: 'POST'
  });
};

export const uploadLeaseDocument = async (leaseId, formData) => {
  const token = localStorage.getItem('token');
  
  const response = await fetch(`/api/leases/${leaseId}/upload`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      // Don't set Content-Type as it will be set automatically for FormData
    },
    body: formData
  });
  
  return handleResponse(response);
};

export const fetchLeaseDocuments = async (leaseId) => {
  return apiRequest(`/leases/${leaseId}/documents`);
};

// Vendors API Functions
export const fetchVendors = async (params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.status) queryParams.append('status', params.status);
  if (params.business_type) queryParams.append('business_type', params.business_type);
  
  const queryString = queryParams.toString();
  return apiRequest(`/vendors${queryString ? '?' + queryString : ''}`);
};

export const fetchVendor = async (vendorId) => {
  return apiRequest(`/vendors/${vendorId}`);
};

export const createVendor = async (vendorData) => {
  return apiRequest('/vendors', {
    method: 'POST',
    body: JSON.stringify(vendorData)
  });
};

export const updateVendor = async (vendorId, vendorData) => {
  return apiRequest(`/vendors/${vendorId}`, {
    method: 'PUT',
    body: JSON.stringify(vendorData)
  });
};

export const updateVendorStatus = async (vendorId, status) => {
  return apiRequest(`/vendors/${vendorId}/status?status=${status}`, {
    method: 'POST'
  });
};

export const uploadVendorDocument = async (vendorId, formData) => {
  const token = localStorage.getItem('token');
  
  const response = await fetch(`/api/vendors/${vendorId}/upload`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      // Don't set Content-Type as it will be set automatically for FormData
    },
    body: formData
  });
  
  return handleResponse(response);
};

export const fetchVendorDocuments = async (vendorId) => {
  return apiRequest(`/vendors/${vendorId}/documents`);
};

export const assignVendorToProperty = async (vendorId, assignmentData) => {
  return apiRequest(`/vendors/${vendorId}/properties`, {
    method: 'POST',
    body: JSON.stringify(assignmentData)
  });
};

export const getVendorOnboardingHelp = async (query) => {
  return apiRequest('/vendors/ai/onboarding-help', {
    method: 'POST',
    body: JSON.stringify({ query })
  });
};

// Accounting API Functions
export const fetchPayments = async (params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.lease_id) queryParams.append('lease_id', params.lease_id);
  if (params.tenant_id) queryParams.append('tenant_id', params.tenant_id);
  if (params.status) queryParams.append('status', params.status);
  if (params.start_date) queryParams.append('start_date', params.start_date);
  if (params.end_date) queryParams.append('end_date', params.end_date);
  
  const queryString = queryParams.toString();
  return apiRequest(`/accounting/payments${queryString ? '?' + queryString : ''}`);
};

export const createPayment = async (paymentData) => {
  return apiRequest('/accounting/payments', {
    method: 'POST',
    body: JSON.stringify(paymentData)
  });
};

export const updatePayment = async (paymentId, paymentData) => {
  return apiRequest(`/accounting/payments/${paymentId}`, {
    method: 'PUT',
    body: JSON.stringify(paymentData)
  });
};

export const fetchInvoices = async (params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.tenant_id) queryParams.append('tenant_id', params.tenant_id);
  if (params.property_id) queryParams.append('property_id', params.property_id);
  if (params.status) queryParams.append('status', params.status);
  if (params.start_date) queryParams.append('start_date', params.start_date);
  if (params.end_date) queryParams.append('end_date', params.end_date);
  
  const queryString = queryParams.toString();
  return apiRequest(`/accounting/invoices${queryString ? '?' + queryString : ''}`);
};

export const createInvoice = async (invoiceData) => {
  return apiRequest('/accounting/invoices', {
    method: 'POST',
    body: JSON.stringify(invoiceData)
  });
};

export const fetchExpenses = async (params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.property_id) queryParams.append('property_id', params.property_id);
  if (params.vendor_id) queryParams.append('vendor_id', params.vendor_id);
  if (params.category) queryParams.append('category', params.category);
  if (params.start_date) queryParams.append('start_date', params.start_date);
  if (params.end_date) queryParams.append('end_date', params.end_date);
  
  const queryString = queryParams.toString();
  return apiRequest(`/accounting/expenses${queryString ? '?' + queryString : ''}`);
};

export const createExpense = async (expenseData) => {
  return apiRequest('/accounting/expenses', {
    method: 'POST',
    body: JSON.stringify(expenseData)
  });
};

export const getOccupancyRates = async (propertyId) => {
  const queryParams = propertyId ? `?property_id=${propertyId}` : '';
  return apiRequest(`/accounting/occupancy${queryParams}`);
};

export const getRevenueTrends = async (params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.period_type) queryParams.append('period_type', params.period_type);
  if (params.year) queryParams.append('year', params.year);
  if (params.property_id) queryParams.append('property_id', params.property_id);
  
  const queryString = queryParams.toString();
  return apiRequest(`/accounting/revenue-trends${queryString ? '?' + queryString : ''}`);
};

// Communication API Functions
export const fetchConversations = async () => {
  return apiRequest('/messages/conversations');
};

export const createConversation = async (conversationData) => {
  return apiRequest('/messages/conversations', {
    method: 'POST',
    body: JSON.stringify(conversationData)
  });
};

export const fetchMessages = async (conversationId, params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.limit) queryParams.append('limit', params.limit);
  if (params.before_id) queryParams.append('before_id', params.before_id);
  
  const queryString = queryParams.toString();
  return apiRequest(`/messages/conversations/${conversationId}/messages${queryString ? '?' + queryString : ''}`);
};

export const sendMessage = async (messageData) => {
  return apiRequest('/messages/messages', {
    method: 'POST',
    body: JSON.stringify(messageData)
  });
};

export const markMessageAsRead = async (messageId) => {
  return apiRequest(`/messages/messages/${messageId}/read`, {
    method: 'PUT'
  });
};

export const sendAnnouncement = async (content, recipientType) => {
  const queryParams = recipientType ? `?recipient_type=${recipientType}` : '';
  return apiRequest(`/messages/announcements${queryParams}`, {
    method: 'POST',
    body: JSON.stringify({ content })
  });
};

// AI Chatbot API Functions
export const sendChatMessage = async (messages, context, documentIds) => {
  return apiRequest('/ai/chat', {
    method: 'POST',
    body: JSON.stringify({
      messages,
      context,
      document_ids: documentIds
    })
  });
};

export const documentQA = async (messages, documentIds, context) => {
  return apiRequest('/ai/document-qa', {
    method: 'POST',
    body: JSON.stringify({
      messages,
      document_ids: documentIds,
      context
    })
  });
};

export const getTenantSupport = async (messages, context) => {
  return apiRequest('/ai/tenant-support', {
    method: 'POST',
    body: JSON.stringify({
      messages,
      context
    })
  });
};

// Property Management API Functions
export const fetchProperties = async (params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.owner_id) queryParams.append('owner_id', params.owner_id);
  if (params.property_type) queryParams.append('property_type', params.property_type);
  
  const queryString = queryParams.toString();
  return apiRequest(`/properties${queryString ? '?' + queryString : ''}`);
};

export const fetchProperty = async (propertyId) => {
  return apiRequest(`/properties/${propertyId}`);
};

export const createProperty = async (propertyData) => {
  return apiRequest('/properties', {
    method: 'POST',
    body: JSON.stringify(propertyData)
  });
};

export const updateProperty = async (propertyId, propertyData) => {
  return apiRequest(`/properties/${propertyId}`, {
    method: 'PUT',
    body: JSON.stringify(propertyData)
  });
};

export const fetchPropertyUnits = async (propertyId) => {
  return apiRequest(`/properties/${propertyId}/units`);
};

// Tenant Management API Functions
export const fetchTenants = async (params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.property_id) queryParams.append('property_id', params.property_id);
  if (params.status) queryParams.append('status', params.status);
  
  const queryString = queryParams.toString();
  return apiRequest(`/tenants${queryString ? '?' + queryString : ''}`);
};

export const fetchTenant = async (tenantId) => {
  return apiRequest(`/tenants/${tenantId}`);
};

export const createTenant = async (tenantData) => {
  return apiRequest('/tenants', {
    method: 'POST',
    body: JSON.stringify(tenantData)
  });
};

export const updateTenant = async (tenantId, tenantData) => {
  return apiRequest(`/tenants/${tenantId}`, {
    method: 'PUT',
    body: JSON.stringify(tenantData)
  });
};

// Landlord Management API Functions
export const fetchLandlords = async () => {
  return apiRequest('/landlords');
};

export const fetchLandlord = async (landlordId) => {
  return apiRequest(`/landlords/${landlordId}`);
};

export const createLandlord = async (landlordData) => {
  return apiRequest('/landlords', {
    method: 'POST',
    body: JSON.stringify(landlordData)
  });
};

export const updateLandlord = async (landlordId, landlordData) => {
  return apiRequest(`/landlords/${landlordId}`, {
    method: 'PUT',
    body: JSON.stringify(landlordData)
  });
};

// Maintenance API Functions
export const fetchMaintenanceRequests = async (params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.property_id) queryParams.append('property_id', params.property_id);
  if (params.status) queryParams.append('status', params.status);
  if (params.priority) queryParams.append('priority', params.priority);
  
  const queryString = queryParams.toString();
  return apiRequest(`/maintenance${queryString ? '?' + queryString : ''}`);
};

export const createMaintenanceRequest = async (requestData) => {
  return apiRequest('/maintenance', {
    method: 'POST',
    body: JSON.stringify(requestData)
  });
};

export const updateMaintenanceRequest = async (requestId, requestData) => {
  return apiRequest(`/maintenance/${requestId}`, {
    method: 'PUT',
    body: JSON.stringify(requestData)
  });
};

export const assignMaintenanceRequest = async (requestId, vendorId) => {
  return apiRequest(`/maintenance/${requestId}/assign?vendor_id=${vendorId}`, {
    method: 'POST'
  });
};
