// Accounting API Functions
import { apiRequest } from './core';

// ===== PAYMENTS =====
export const fetchPayments = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.lease_id) queryParams.append("lease_id", params.lease_id);
  if (params.tenant_id) queryParams.append("tenant_id", params.tenant_id);
  if (params.payment_status)
    queryParams.append("payment_status", params.payment_status);
  if (params.search) queryParams.append("search", params.search);
  if (params.start_date) queryParams.append("start_date", params.start_date);
  if (params.end_date) queryParams.append("end_date", params.end_date);
  if (params.limit) queryParams.append("limit", params.limit);
  if (params.offset) queryParams.append("offset", params.offset);

  const queryString = queryParams.toString();
  return apiRequest(`/accounting/payments${queryString ? '?' + queryString : ''}`);
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

export const deletePayment = async (paymentId) => {
  return apiRequest(`/accounting/payments/${paymentId}`, {
    method: "DELETE",
  });
};

export const generateDuePayments = async () => {
  return apiRequest("/accounting/payments/generate/monthly-rent", {
    method: "POST",
  });
};

export const fetchOutstandingPayments = async (params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.property_id) queryParams.append("property_id", params.property_id);
  
  const queryString = queryParams.toString();
  return apiRequest(`/accounting/payments/outstanding/current-month${queryString ? '?' + queryString : ''}`);
};

export const parsePaymentReceipt = async (fileFormData) => {
  return apiRequest("/accounting/payments/receipts/parse", {
    method: "POST",
    body: fileFormData,
  });
};

// ===== INVOICES =====
export const fetchInvoices = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.tenant_id) queryParams.append("tenant_id", params.tenant_id);
  if (params.property_id) queryParams.append("property_id", params.property_id);
  if (params.payment_status_filter) queryParams.append("payment_status_filter", params.payment_status_filter);
  if (params.status) queryParams.append("status", params.status);
  if (params.search) queryParams.append("search", params.search);
  if (params.start_date) queryParams.append("start_date", params.start_date);
  if (params.end_date) queryParams.append("end_date", params.end_date);
  if (params.limit) queryParams.append("limit", params.limit);
  if (params.offset) queryParams.append("offset", params.offset);

  const queryString = queryParams.toString();
  return apiRequest(`/accounting/invoices${queryString ? '?' + queryString : ''}`);
};

export const createInvoice = async (invoiceData) => {
  return apiRequest("/accounting/invoices", {
    method: "POST",
    body: JSON.stringify(invoiceData),
  });
};

export const fetchInvoice = async (invoiceId) => {
  return apiRequest(`/accounting/invoices/${invoiceId}`);
};

export const updateInvoice = async (invoiceId, invoiceData) => {
  return apiRequest(`/accounting/invoices/${invoiceId}`, {
    method: "PUT",
    body: JSON.stringify(invoiceData),
  });
};

export const deleteInvoice = async (invoiceId) => {
  return apiRequest(`/accounting/invoices/${invoiceId}`, {
    method: "DELETE",
  });
};

export const markInvoicePaid = async (invoiceId) => {
  return apiRequest(`/accounting/invoices/mark-paid/${invoiceId}`, {
    method: "POST",
  });
};

// ===== EXPENSES =====
export const fetchExpenses = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.property_id) queryParams.append("property_id", params.property_id);
  if (params.category) queryParams.append("category", params.category);
  if (params.start_date) queryParams.append("start_date", params.start_date);
  if (params.end_date) queryParams.append("end_date", params.end_date);
  if (params.search) queryParams.append("search", params.search);
  if (params.limit) queryParams.append("limit", params.limit);
  if (params.offset) queryParams.append("offset", params.offset);

  const queryString = queryParams.toString();
  return apiRequest(`/accounting/expenses${queryString ? '?' + queryString : ''}`);
};

export const createExpense = async (expenseData) => {
  return apiRequest("/accounting/expenses", {
    method: "POST",
    body: JSON.stringify(expenseData),
  });
};

export const parseExpenseReceipt = async (fileFormData, options = {}) => {
  return apiRequest("/accounting/expenses/parse-receipt", {
    method: "POST",
    body: fileFormData,
    ...options,
  });
};

export const updateExpense = async (expenseId, expenseData) => {
  return apiRequest(`/accounting/expenses/${expenseId}`, {
    method: "PUT",
    body: JSON.stringify(expenseData),
  });
};

export const deleteExpense = async (expenseId) => {
  return apiRequest(`/accounting/expenses/${expenseId}`, {
    method: "DELETE",
  });
};

// ===== INSIGHTS =====
export const getOccupancyRates = async (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.property_id) queryParams.append("property_id", params.property_id);
  
  const queryString = queryParams.toString();
  return apiRequest(`/accounting/insights/occupancy${queryString ? '?' + queryString : ''}`);
};

export const getRevenueTrends = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.period_type) queryParams.append("period_type", params.period_type);
  if (params.year) queryParams.append("year", params.year);
  if (params.property_id) queryParams.append("property_id", params.property_id);

  const queryString = queryParams.toString();
  return apiRequest(`/accounting/insights/revenue-trends${queryString ? '?' + queryString : ''}`);
};

export const getAccountingOverview = async (params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.property_id) queryParams.append("property_id", params.property_id);
  
  const queryString = queryParams.toString();
  return apiRequest(`/accounting/insights/overview${queryString ? '?' + queryString : ''}`);
}; 