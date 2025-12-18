// Accounting API Functions
import { apiRequest } from './core';
import type {
  Expense,
  Invoice,
  Payment,
  CreateExpenseRequest,
  UpdateExpenseRequest,
  CreateInvoiceRequest,
  UpdateInvoiceRequest,
  CreatePaymentRequest,
  UpdatePaymentRequest,
  ExpensesResponse,
  InvoicesResponse,
  PaymentsResponse,
  ExpenseQueryParams,
  InvoiceQueryParams,
  PaymentQueryParams,
  SmartTaxRecommendation,
  ReceiptParsingResponse,
  CSVImportResponse
} from '../../types/accounting';

// ===== LOCAL TYPE DEFINITIONS =====
interface InsightParams {
  property_id?: number;
  period_type?: string;
  year?: number;
}

export interface TaxData {
  tax_name: string;
  tax_rate: string; // Backend uses Decimal which serializes to string
}

interface TaxPreference {
  tax_name: string;
  tax_rate: string; // Backend uses Decimal which serializes to string
  source: string;
}

interface HistoricalTaxUsage {
  tax_name: string;
  tax_rate: string; // Backend uses Decimal which serializes to string
  usage_count: number;
  last_used: string;
  percentage: number;
}

// ===== TAX PREFERENCES =====
export const getSmartTaxRecommendation = async (params: { property_id: number; category: string }): Promise<{ success: boolean; data?: SmartTaxRecommendation; error?: string }> => {
  try {
    const queryParams = new URLSearchParams();
    queryParams.append("property_id", params.property_id.toString());
    queryParams.append("category", params.category);
    
    const queryString = queryParams.toString();
    const response = await apiRequest(`/accounting/tax-preferences/smart?${queryString}`);
    
    // Backend returns SmartTaxResponse directly
    if (response && typeof response.confidence === 'number') {
      return {
        success: true,
        data: response
      };
    } else {
      return {
        success: false,
        error: 'Invalid smart tax response format'
      };
    }
  } catch (error) {
    console.error('getSmartTaxRecommendation: API request failed:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to load tax recommendations'
    };
  }
};

export const getUserTaxDefault = async (): Promise<TaxPreference | null> => {
  return apiRequest('/accounting/tax-preferences/default');
};

export const setUserTaxDefault = async (taxData: TaxData): Promise<{ success: boolean; data?: TaxPreference; error?: string }> => {
  try {
    const response = await apiRequest('/accounting/tax-preferences/default', {
      method: 'POST',
      body: JSON.stringify(taxData),
    });
    
    // Backend returns TaxPreferenceResponse directly, not wrapped in {success: boolean}
    if (response && response.tax_name && response.tax_rate) {
      return {
        success: true,
        data: response
      };
    } else {
      return {
        success: false,
        error: 'Invalid response format from server'
      };
    }
  } catch (error) {
    console.error('setUserTaxDefault: API request failed:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
};

export const clearUserTaxDefault = async (): Promise<void> => {
  return apiRequest('/accounting/tax-preferences/default', {
    method: 'DELETE',
  });
};

export const getPropertyTaxDefault = async (propertyId: number): Promise<TaxPreference | null> => {
  return apiRequest(`/accounting/tax-preferences/property/${propertyId}`);
};

export const setPropertyTaxDefault = async (params: { property_id: number; tax_name: string; tax_rate: string }): Promise<{ success: boolean; data?: TaxPreference; error?: string }> => {
  try {
    const { property_id, ...taxData } = params;
    const response = await apiRequest(`/accounting/tax-preferences/property/${property_id}`, {
      method: 'POST',
      body: JSON.stringify(taxData),
    });
    
    // Backend returns TaxPreferenceResponse directly, not wrapped in {success: boolean}
    if (response && response.tax_name && response.tax_rate) {
      return {
        success: true,
        data: response
      };
    } else {
      return {
        success: false,
        error: 'Invalid response format from server'
      };
    }
  } catch (error) {
    console.error('setPropertyTaxDefault: API request failed:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
};

export const clearPropertyTaxDefault = async (propertyId: number): Promise<void> => {
  return apiRequest(`/accounting/tax-preferences/property/${propertyId}`, {
    method: 'DELETE',
  });
};

export const getHistoricalTaxUsage = async (limit: number = 10): Promise<HistoricalTaxUsage[]> => {
  const queryParams = new URLSearchParams();
  queryParams.append("limit", limit.toString());
  
  const queryString = queryParams.toString();
  return apiRequest(`/accounting/tax-preferences/history${queryString ? '?' + queryString : ''}`);
};

// ===== PAYMENTS =====
export const fetchPayments = async (params: PaymentQueryParams = {}): Promise<PaymentsResponse> => {
  const queryParams = new URLSearchParams();

  if (params.tenant_id) queryParams.append("tenant_id", params.tenant_id.toString());
  if (params.search) queryParams.append("search", params.search);
  if (params.start_date) queryParams.append("start_date", params.start_date);
  if (params.end_date) queryParams.append("end_date", params.end_date);
  if (params.limit) queryParams.append("limit", params.limit.toString());
  if (params.offset) queryParams.append("offset", params.offset.toString());

  const queryString = queryParams.toString();
  return apiRequest(`/accounting/payments${queryString ? '?' + queryString : ''}`);
};

export const createPayment = async (paymentData: CreatePaymentRequest): Promise<Payment> => {
  return apiRequest("/accounting/payments", {
    method: "POST",
    body: JSON.stringify(paymentData),
    recaptchaAction: 'payment_create',
  });
};

export const updatePayment = async (paymentId: number, paymentData: UpdatePaymentRequest): Promise<Payment> => {
  return apiRequest(`/accounting/payments/${paymentId}`, {
    method: "PUT",
    body: JSON.stringify(paymentData),
  });
};

export const deletePayment = async (paymentId: number): Promise<void> => {
  return apiRequest(`/accounting/payments/${paymentId}`, {
    method: "DELETE",
  });
};

export const generateDuePayments = async (): Promise<{ generated_count: number }> => {
  return apiRequest("/accounting/payments/generate/monthly-rent", {
    method: "POST",
  });
};

export const fetchOutstandingPayments = async (params: { property_id?: number } = {}): Promise<Payment[]> => {
  const queryParams = new URLSearchParams();
  
  if (params.property_id) queryParams.append("property_id", params.property_id.toString());
  
  const queryString = queryParams.toString();
  return apiRequest(`/accounting/payments/outstanding/current-month${queryString ? '?' + queryString : ''}`);
};

export const parsePaymentReceipt = async (fileFormData: FormData): Promise<ReceiptParsingResponse> => {
  return apiRequest("/accounting/payments/receipts/parse", {
    method: "POST",
    body: fileFormData,
    recaptchaAction: 'payment_parse_receipt',
  });
};

// ===== INVOICES =====
export const fetchInvoices = async (params: InvoiceQueryParams = {}): Promise<InvoicesResponse> => {
  const queryParams = new URLSearchParams();

  if (params.tenant_id) queryParams.append("tenant_id", params.tenant_id.toString());
  if (params.property_id) queryParams.append("property_id", params.property_id.toString());
  if (params.status) queryParams.append("status", params.status);
  if (params.search) queryParams.append("search", params.search);
  if (params.start_date) queryParams.append("start_date", params.start_date);
  if (params.end_date) queryParams.append("end_date", params.end_date);
  if (params.limit) queryParams.append("limit", params.limit.toString());
  if (params.offset) queryParams.append("offset", params.offset.toString());

  const queryString = queryParams.toString();
  return apiRequest(`/accounting/invoices${queryString ? '?' + queryString : ''}`);
};

export const createInvoice = async (invoiceData: CreateInvoiceRequest): Promise<Invoice> => {
  return apiRequest("/accounting/invoices", {
    method: "POST",
    body: JSON.stringify(invoiceData),
    recaptchaAction: 'invoice_create',
  });
};

export const fetchInvoice = async (invoiceId: number): Promise<Invoice> => {
  return apiRequest(`/accounting/invoices/${invoiceId}`);
};

export const updateInvoice = async (invoiceId: number, invoiceData: UpdateInvoiceRequest): Promise<Invoice> => {
  return apiRequest(`/accounting/invoices/${invoiceId}`, {
    method: "PUT",
    body: JSON.stringify(invoiceData),
  });
};

export const deleteInvoice = async (invoiceId: number): Promise<void> => {
  return apiRequest(`/accounting/invoices/${invoiceId}`, {
    method: "DELETE",
  });
};

export const markInvoicePaid = async (invoiceId: number): Promise<Invoice> => {
  return apiRequest(`/accounting/invoices/mark-paid/${invoiceId}`, {
    method: "POST",
  });
};

export const importInvoicesFromCSV = async (csvData: Record<string, unknown>[]): Promise<CSVImportResponse> => {
  const payload = { invoices: csvData };
  return apiRequest("/accounting/invoices/import-csv", {
    method: "POST",
    body: JSON.stringify(payload),
    recaptchaAction: 'invoice_import_csv',
  });
};

export const importExpensesFromCSV = async (csvData: Record<string, unknown>[]): Promise<CSVImportResponse> => {
  const payload = { expenses: csvData };
  return apiRequest("/accounting/expenses/import-csv", {
    method: "POST",
    body: JSON.stringify(payload),
    recaptchaAction: 'expense_import_csv',
  });
};

export const importPaymentsFromCSV = async (csvData: Record<string, unknown>[]): Promise<CSVImportResponse> => {
  const payload = { payments: csvData };
  return apiRequest("/accounting/payments/import-csv", {
    method: "POST",
    body: JSON.stringify(payload),
    recaptchaAction: 'payment_import_csv',
  });
};

// ===== EXPENSES =====
export const fetchExpenses = async (params: ExpenseQueryParams = {}): Promise<ExpensesResponse> => {
  const queryParams = new URLSearchParams();

  if (params.property_id) queryParams.append("property_id", params.property_id.toString());
  if (params.category) queryParams.append("category", params.category);
  if (params.start_date) queryParams.append("start_date", params.start_date);
  if (params.end_date) queryParams.append("end_date", params.end_date);
  if (params.search) queryParams.append("search", params.search);
  if (params.limit) queryParams.append("limit", params.limit.toString());
  if (params.offset) queryParams.append("offset", params.offset.toString());

  const queryString = queryParams.toString();
  return apiRequest(`/accounting/expenses${queryString ? '?' + queryString : ''}`);
};

export const createExpense = async (expenseData: CreateExpenseRequest): Promise<Expense> => {
  return apiRequest("/accounting/expenses", {
    method: "POST",
    body: JSON.stringify(expenseData),
    recaptchaAction: 'expense_create',
  });
};

export const parseExpenseReceipt = async (
  fileFormData: FormData, 
  options: { signal?: AbortSignal } = {}
): Promise<ReceiptParsingResponse> => {
  const { signal } = options;
  return apiRequest("/accounting/expenses/parse-receipt", {
    method: "POST",
    body: fileFormData,
    signal,
    recaptchaAction: 'expense_parse_receipt',
  });
};

export const updateExpense = async (expenseId: number, expenseData: UpdateExpenseRequest): Promise<Expense> => {
  return apiRequest(`/accounting/expenses/${expenseId}`, {
    method: "PUT",
    body: JSON.stringify(expenseData),
  });
};

export const deleteExpense = async (expenseId: number): Promise<void> => {
  return apiRequest(`/accounting/expenses/${expenseId}`, {
    method: "DELETE",
  });
};

// ===== INSIGHTS =====
export const getOccupancyRates = async (params: InsightParams = {}): Promise<unknown> => {
  const queryParams = new URLSearchParams();
  if (params.property_id) queryParams.append("property_id", params.property_id.toString());
  
  const queryString = queryParams.toString();
  return apiRequest(`/accounting/insights/occupancy${queryString ? '?' + queryString : ''}`);
};

export const getRevenueTrends = async (params: InsightParams = {}): Promise<unknown> => {
  const queryParams = new URLSearchParams();

  if (params.period_type) queryParams.append("period_type", params.period_type);
  if (params.year) queryParams.append("year", params.year.toString());
  if (params.property_id) queryParams.append("property_id", params.property_id.toString());

  const queryString = queryParams.toString();
  return apiRequest(`/accounting/insights/revenue-trends${queryString ? '?' + queryString : ''}`);
};

export const getAccountingOverview = async (params: InsightParams = {}): Promise<unknown> => {
  const queryParams = new URLSearchParams();
  
  if (params.property_id) queryParams.append("property_id", params.property_id.toString());
  
  const queryString = queryParams.toString();
  return apiRequest(`/accounting/insights/overview${queryString ? '?' + queryString : ''}`);
};

/**
 * Generate a secure, time-limited URL for an expense receipt.
 * 
 * For private Azure containers, receipts require SAS tokens to be accessed.
 * This generates a 1-hour expiring SAS token for secure receipt viewing.
 */
export const getSecureExpenseReceiptUrl = async (receiptUrl: string): Promise<{
  secure_url: string;
  expires_at: string;
  expires_in_seconds: number;
}> => {
  const encodedUrl = encodeURIComponent(receiptUrl);
  return apiRequest(`/accounting/expenses/receipts/secure-url?receipt_url=${encodedUrl}`, {
    method: "POST",
  });
};

/**
 * Generate a secure, time-limited URL for a payment receipt.
 * 
 * For private Azure containers, receipts require SAS tokens to be accessed.
 * This generates a 1-hour expiring SAS token for secure receipt viewing.
 */
export const getSecurePaymentReceiptUrl = async (receiptUrl: string): Promise<{
  secure_url: string;
  expires_at: string;
  expires_in_seconds: number;
}> => {
  const encodedUrl = encodeURIComponent(receiptUrl);
  return apiRequest(`/accounting/payments/receipts/secure-url?receipt_url=${encodedUrl}`, {
    method: "POST",
  });
};

// ===== REFUND & DISPUTE FUNCTIONS =====

export const createRefund = async (refundData: {
  transaction_id: string;
  amount_cents: number;
  reason: string;
  notes?: string;
  refund_application_fee: boolean;
}): Promise<{
  id: string;
  transaction_id: string;
  stripe_refund_id: string;
  amount_cents: number;
  amount: number;
  status: string;
  reason: string;
  created_at: string;
}> => {
  return apiRequest(`/rent-payments/transactions/${refundData.transaction_id}/refund`, {
    method: 'POST',
    body: JSON.stringify({
      amount_cents: refundData.amount_cents,
      reason: refundData.reason,
      notes: refundData.notes,
      refund_application_fee: refundData.refund_application_fee,
    }),
  });
};

export const fetchRefunds = async (params: {
  transaction_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<{
  items: Array<{
    id: string;
    transaction_id: string;
    stripe_refund_id: string;
    amount_cents: number;
    amount: number;
    status: string;
    reason: string;
    notes: string | null;
    failure_reason: string | null;
    created_at: string;
    succeeded_at: string | null;
  }>;
  total: number;
  has_more: boolean;
}> => {
  const queryParams = new URLSearchParams();
  if (params.transaction_id) queryParams.append('transaction_id', params.transaction_id);
  if (params.status) queryParams.append('status', params.status);
  if (params.limit) queryParams.append('limit', params.limit.toString());
  if (params.offset) queryParams.append('offset', params.offset.toString());

  return apiRequest(`/rent-payments/refunds?${queryParams.toString()}`);
};

export const fetchRefund = async (refundId: string): Promise<{
  id: string;
  transaction_id: string;
  stripe_refund_id: string;
  amount_cents: number;
  amount: number;
  status: string;
  reason: string;
  notes: string | null;
  failure_reason: string | null;
  created_at: string;
  succeeded_at: string | null;
}> => {
  return apiRequest(`/rent-payments/refunds/${refundId}`);
};

export const fetchDisputes = async (params: {
  transaction_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<{
  items: Array<{
    id: string;
    transaction_id: string;
    stripe_dispute_id: string;
    amount_cents: number;
    amount: number;
    status: string;
    reason: string;
    evidence_due_by: string | null;
    evidence_submitted: boolean;
    needs_attention: boolean;
    days_until_due: number | null;
    created_at: string;
  }>;
  total: number;
  has_more: boolean;
  active_disputes: number;
}> => {
  const queryParams = new URLSearchParams();
  if (params.transaction_id) queryParams.append('transaction_id', params.transaction_id);
  if (params.status) queryParams.append('status', params.status);
  if (params.limit) queryParams.append('limit', params.limit.toString());
  if (params.offset) queryParams.append('offset', params.offset.toString());

  return apiRequest(`/rent-payments/disputes?${queryParams.toString()}`);
};

export const fetchDispute = async (disputeId: string): Promise<{
  id: string;
  transaction_id: string;
  stripe_dispute_id: string;
  amount_cents: number;
  amount: number;
  status: string;
  reason: string;
  evidence_due_by: string | null;
  evidence_submitted: boolean;
  needs_attention: boolean;
  days_until_due: number | null;
  created_at: string;
}> => {
  return apiRequest(`/rent-payments/disputes/${disputeId}`);
};
