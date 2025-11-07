// Comprehensive type definitions for accounting domain

export interface TaxDetail {
  id?: number;
  tax_name: string;
  tax_rate: string; // Backend uses Decimal which serializes to string
  tax_amount?: string; // Backend uses Decimal which serializes to string
}

export interface Expense {
  id: number;
  property_id: number;
  property_name?: string;
  category: string;
  subtotal_amount: string; // Backend uses Decimal which serializes to string
  total_amount: string; // Backend uses Decimal which serializes to string
  tax_amount?: string; // Backend uses Decimal which serializes to string
  expense_date: string;
  payment_method?: string;
  receipt_url?: string | null;
  quickbooks_id?: string | null;
  description?: string;
  source?: string;
  has_receipt?: boolean;
  taxes?: TaxDetail[];
  created_at?: string;
  updated_at?: string;
}

export interface CreateExpenseRequest {
  property_id: number;
  category: string;
  subtotal_amount: string; // Backend uses Decimal which serializes to string
  expense_date: string;
  description?: string;
  receipt_url?: string | null;
  payment_method?: string;
  taxes?: Array<{
    tax_name: string;
    tax_rate: string; // Backend uses Decimal which serializes to string
  }>;
}

export interface UpdateExpenseRequest extends Partial<CreateExpenseRequest> {
  id: number;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  amount: string; // Backend uses Decimal which serializes to string
  description?: string;
  issue_date: string;
  due_date: string;
  status: string;
  property_id?: number;
  tenant_id?: number;
  quickbooks_id?: string | null;
  property?: {
    id: number;
    name: string;
  };
  tenant?: {
    id: number;
    full_name?: string;
    first_name?: string;
    last_name?: string;
    company_name?: string;
    tenant_type?: string;
  };
  taxes?: TaxDetail[];
  created_at?: string;
  updated_at?: string;
}

export interface CreateInvoiceRequest {
  invoice_number: string;
  amount: string; // Backend uses Decimal which serializes to string
  description: string;
  issue_date: string;
  due_date: string;
  status?: string;
  property_id?: number;
  tenant_id?: number;
  taxes?: Array<{
    tax_name: string;
    tax_rate: string; // Backend uses Decimal which serializes to string
  }>;
}

export interface UpdateInvoiceRequest extends Partial<CreateInvoiceRequest> {
  id: number;
}

export interface Payment {
  id: number;
  invoice_id?: number;
  tenant_id?: number;
  amount: string; // Backend uses Decimal which serializes to string
  payment_date: string;
  payment_method: string;
  description?: string;
  quickbooks_id?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface CreatePaymentRequest {
  lease_id?: number | null;
  tenant_id?: number | null;
  property_id?: number | null;
  invoice_id?: number;
  tenant_name?: string | null;
  amount: string | number; // Backend uses Decimal which serializes to string
  payment_date?: string | null;
  payment_method?: string;
  status?: string;
  description?: string;
  receipt_url?: string | null;
  transaction_reference?: string | null;
  reduction_amount?: number | null;
  reduction_reason?: string | null;
}

export interface UpdatePaymentRequest extends Partial<CreatePaymentRequest> {
  id: number;
}

// Pagination types
export interface PaginatedResponse<T> {
  items: T[];
  total?: number;
  has_more?: boolean;
  page?: number;
  limit?: number;
}

export type ExpensesResponse = PaginatedResponse<Expense>;
export type InvoicesResponse = PaginatedResponse<Invoice>;
export type PaymentsResponse = PaginatedResponse<Payment>;

// Query parameter types
export interface BaseQueryParams {
  limit?: number;
  offset?: number;
  search?: string;
  start_date?: string;
  end_date?: string;
}

export interface ExpenseQueryParams extends BaseQueryParams {
  category?: string;
  property_id?: number;
}

export interface InvoiceQueryParams extends BaseQueryParams {
  status?: string;
  property_id?: number;
  tenant_id?: number;
}

export interface PaymentQueryParams extends BaseQueryParams {
  invoice_id?: number;
  tenant_id?: number;
}

// Tax Preferences types (for Phase 3)
export interface SmartTaxRecommendation {
  tax_name: string;
  tax_rate: string; // Backend uses Decimal which serializes to string
  confidence: number;
  source: 'property_default' | 'user_default' | 'provincial_default' | 'usage_analysis' | 'historical_usage' | 'none';
  explanation?: string;
  reasoning?: string; // For backward compatibility with existing modals
}

export interface TaxPreferenceRequest {
  tax_name: string;
  tax_rate: string; // Backend uses Decimal which serializes to string
  property_id?: number; // If provided, sets property default; otherwise user default
}

export interface UserTaxDefaults {
  default_tax_name?: string;
  default_tax_rate?: string; // Backend uses Decimal which serializes to string
}

export interface PropertyTaxDefaults {
  default_tax_name?: string;
  default_tax_rate?: string; // Backend uses Decimal which serializes to string
}

// Receipt parsing types
export interface ParsedReceiptData {
  category?: string;
  amount?: string; // Backend uses Decimal which serializes to string
  subtotal_amount?: string; // Backend uses Decimal which serializes to string
  tax_amount?: string; // Backend uses Decimal which serializes to string
  expense_date?: string;
  description?: string;
  merchant?: string;
  taxes?: Array<{
    tax_name: string;
    tax_rate: string; // Backend uses Decimal which serializes to string
    tax_amount?: string; // Backend uses Decimal which serializes to string
  }>;
}

export interface ReceiptParsingResponse {
  success: boolean;
  data?: ParsedReceiptData;
  error?: string;
}

// CSV Import types
export interface CSVImportResponse {
  success: boolean;
  imported_count: number;
  failed_count: number;
  errors?: string[];
}

/**
 * Form data types for modals - UI-friendly field names and types
 * 
 * IMPORTANT: Form field names differ from API field names for better UX:
 * - Form 'amount' field → API 'subtotal_amount' field  
 * - Form 'property_id' (string) → API 'property_id' (number)
 * 
 * Transformation happens in form hooks (useExpenseForm, useInvoiceForm)
 * before sending data to the API endpoints.
 */
export interface ExpenseFormData {
  id?: string; // Optional for create mode, required for edit mode
  category: string;
  amount: string; // UI field name - transformed to 'subtotal_amount' for CreateExpenseRequest API
  expense_date: string;
  description: string;
  receipt_url: string | null;
  property_id: string; // Parsed to number for API
  property_name: string;
  payment_method: string;
  taxes: Array<{
    tax_name: string;
    tax_rate: string;
  }>;
}

export interface InvoiceFormData {
  id?: string; // Optional for create mode, required for edit mode
  invoice_number: string;
  amount: string; // UI field name - transformed to 'amount' for CreateInvoiceRequest API (invoices use 'amount', not 'subtotal_amount')
  description: string;
  issue_date: string;
  due_date: string;
  status: string;
  property_id: string; // Parsed to number for API
  property_name: string;
  tenant_id: string; // Parsed to number for API
  tenant_name: string;
  taxes: Array<{
    tax_name: string;
    tax_rate: string;
  }>;
}

// Error types
export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, unknown>;
}

// Constants
export const EXPENSE_CATEGORIES = [
  'maintenance',
  'utilities',
  'taxes',
  'insurance',
  'administrative',
  'other'
] as const;

export const PAYMENT_METHODS = [
  'Credit Card',
  'Debit Card',
  'Bank Transfer',
  'Cash',
  'Check',
  'Other'
] as const;

export const INVOICE_STATUSES = [
  'Draft',
  'Pending', 
  'Paid',
  'Partial',
  'Overdue',
  'Cancelled',
  'Refunded',
  'Void',
  'Uncollectible'
] as const;

export type ExpenseCategory = typeof EXPENSE_CATEGORIES[number];
export type PaymentMethod = typeof PAYMENT_METHODS[number];
export type InvoiceStatus = typeof INVOICE_STATUSES[number];