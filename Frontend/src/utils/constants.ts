// Payment-related constants for reuse across components

export const PAYMENT_METHODS = [
  "Credit Card",
  "Debit Card",
  "Bank Transfer",
  "Wire Transfer",
  "Direct Deposit",
  "Interac e-Transfer",
  "Cash",
  "Check",
  "Bank Draft",
  "PayPal",
  "Internal Transfer",
  "Other",
] as const;

export const EXPENSE_CATEGORIES = [
  "maintenance",
  "utilities", 
  "taxes",
  "insurance",
  "administrative",
  "other"
] as const;

export const PAYMENT_STATUSES = [
  "Pending",
  "Paid",
  "Partial",
  "Overdue",
  "Cancelled",
  "Refunded",
] as const;

export const INVOICE_STATUSES = [
  "Draft",
  "Pending", 
  "Paid",
  "Partial",
  "Overdue",
  "Cancelled",
  "Refunded",
  "Void",
  "Uncollectible"
] as const;

// Type exports for better type safety
export type PaymentMethod = typeof PAYMENT_METHODS[number];
export type ExpenseCategory = typeof EXPENSE_CATEGORIES[number];
export type PaymentStatus = typeof PAYMENT_STATUSES[number];
export type InvoiceStatus = typeof INVOICE_STATUSES[number];
