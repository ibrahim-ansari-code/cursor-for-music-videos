// QuickBooks Integration API Functions
import { apiRequest } from './core';

export const connectToQuickBooks = async () => {
  return apiRequest("/quickbooks/connect", {
    method: "POST",
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