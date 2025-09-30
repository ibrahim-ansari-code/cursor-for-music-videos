// QuickBooks Integration API Functions
import { apiRequest } from './core';

export const connectToQuickBooks = async () => {
  // Backend currently exposes GET; use GET here for compatibility
  return apiRequest("/quickbooks/connect", {
    method: "GET",
    recaptchaAction: 'quickbooks_connect',
  });
};

export const getQuickBooksStatus = async () => {
  return apiRequest("/quickbooks/status");
};

export const disconnectQuickBooks = async () => {
  return apiRequest("/quickbooks/disconnect", {
    method: "POST",
  });
};

export const handleQuickBooksCallback = async (code, realmId, state) => {
  return apiRequest(`/quickbooks/callback?code=${encodeURIComponent(code)}&realmId=${encodeURIComponent(realmId)}&state=${encodeURIComponent(state)}`, {
    method: "GET",
  });
};

export const initialQuickBooksSync = async () => {
  return apiRequest("/quickbooks/initial-sync", {
    method: "POST",
  });
};

export const syncQuickBooksPayments = async () => {
  return apiRequest("/quickbooks/sync/payments", {
    method: "POST",
  });
};

export const syncQuickBooksInvoices = async () => {
  return apiRequest("/quickbooks/sync/invoices", {
    method: "POST",
  });
};

export const syncQuickBooksExpenses = async () => {
  return apiRequest("/quickbooks/sync/expenses", {
    method: "POST",
  });
};

export const syncAllQuickBooksData = async () => {
  return apiRequest("/quickbooks/sync/all", {
    method: "POST",
  });
};

export const getQuickBooksDiagnostics = async () => {
  return apiRequest("/quickbooks/diagnostics");
};

// Preview and Account Management
export const previewQuickBooksSync = async () => {
  return apiRequest("/quickbooks/sync/preview");
};

export const getQuickBooksAccounts = async () => {
  return apiRequest("/quickbooks/accounts");
}; 