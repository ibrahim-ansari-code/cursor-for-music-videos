/**
 * Transaction Ledger Utilities for Tenant Payment History
 * 
 * Merges payments and invoices into a unified chronological transaction view
 * with running balance calculations.
 */

import { Lease, Payment, Invoice } from '../types/tenant';

export interface Transaction {
  id: string;                    // Composite: 'payment-123' or 'invoice-456'
  date: Date;                    // payment_date or issue_date
  type: 'charge' | 'payment';    // Derived from source
  source: 'invoice' | 'payment'; // Original source
  description: string;           // invoice.description or payment description
  amount: number;                // Always positive
  balance: number;               // Running balance (calculated later)
  paymentMethod?: string;        // payment.payment_method (payments only)
  receiptUrl?: string;           // payment.receipt_url (payments only)
  status: string;                // payment.status or invoice.status
  isCharge: boolean;             // true for invoices, false for payments
  rawData: Payment | Invoice;    // Original data for reference
}

export interface LedgerMetrics {
  totalPaid: number;             // Sum of paid payments
  totalCharges: number;          // Sum of all invoices
  currentBalance: number;        // totalCharges - totalPaid
  lastPaymentDate: Date | null;  // Most recent payment
  nextDueDate: Date | null;      // Next rent due date
  transactionCount: number;      // Total transactions
}

/**
 * Build unified transaction ledger from payments and invoices
 */
export const buildTransactionLedger = (
  payments: Payment[] | undefined,
  invoices: Invoice[] | undefined
): Transaction[] => {
  const transactions: Transaction[] = [];

  // Add payments as transactions
  if (payments && payments.length > 0) {
    payments.forEach(payment => {
      transactions.push({
        id: `payment-${payment.id}`,
        date: new Date(payment.payment_date),
        type: 'payment',
        source: 'payment',
        description: payment.description || 'Rent Payment',
        amount: Number(payment.amount),
        balance: 0, // Will be calculated
        paymentMethod: payment.payment_method,
        receiptUrl: payment.receipt_url || undefined,
        status: payment.status,
        isCharge: false,
        rawData: payment
      });
    });
  }

  // Add invoices as transactions
  if (invoices && invoices.length > 0) {
    invoices.forEach(invoice => {
      transactions.push({
        id: `invoice-${invoice.id}`,
        date: new Date(invoice.issue_date),
        type: 'charge',
        source: 'invoice',
        description: invoice.description || `Invoice ${invoice.invoice_number}`,
        amount: Number(invoice.amount),
        balance: 0, // Will be calculated
        status: invoice.status,
        isCharge: true,
        rawData: invoice
      });
    });
  }

  // Sort chronologically (oldest first for running balance)
  transactions.sort((a, b) => a.date.getTime() - b.date.getTime());

  // Calculate running balance
  // IMPORTANT: Only "Paid" payments affect the balance. Pending, Cancelled,
  // Refunded, or Void payments are shown in the ledger but don't reduce balance.
  // This ensures financial accuracy and prevents accounting errors.
  let runningBalance = 0;
  transactions.forEach(txn => {
    if (txn.isCharge) {
      // All charges/invoices increase the balance owed
      runningBalance += txn.amount;
    } else if (txn.status === 'Paid') {
      // Only successful "Paid" payments reduce the balance
      runningBalance -= txn.amount;
    }
    // Pending/Cancelled/Refunded/Void payments don't affect balance
    // but are still shown in the ledger for transparency
    txn.balance = runningBalance;
  });

  // Return in reverse chronological order for display (newest first)
  return transactions.reverse();
};

/**
 * Calculate financial metrics from transaction data
 */
export const calculateLedgerMetrics = (
  payments: Payment[] | undefined,
  invoices: Invoice[] | undefined,
  activeLease: Lease | undefined
): LedgerMetrics => {
  // Calculate total paid (only "Paid" status payments)
  const totalPaid = payments
    ?.filter(p => p.status === 'Paid')
    .reduce((sum, p) => sum + Number(p.amount), 0) || 0;

  // Calculate total charges (all invoices)
  const totalCharges = invoices
    ?.reduce((sum, inv) => sum + Number(inv.amount), 0) || 0;

  // Current balance
  const currentBalance = totalCharges - totalPaid;

  // Find last payment date
  let lastPaymentDate: Date | null = null;
  if (payments && payments.length > 0) {
    const sortedPayments = [...payments].sort((a, b) => 
      new Date(b.payment_date).getTime() - new Date(a.payment_date).getTime()
    );
    if (sortedPayments[0]) {
      lastPaymentDate = new Date(sortedPayments[0].payment_date);
    }
  }

  // Next due date from active lease
  let nextDueDate: Date | null = null;
  if (activeLease) {
    const today = new Date();
    const rentDueDay = activeLease.rent_due_day || 1;
    const currentMonth = today.getMonth();
    const currentYear = today.getFullYear();
    const currentDay = today.getDate();
    
    // If due day hasn't passed this month, return this month's due date
    if (currentDay <= rentDueDay) {
      nextDueDate = new Date(currentYear, currentMonth, rentDueDay);
    } else {
      // Otherwise, return next month's due date
      nextDueDate = new Date(currentYear, currentMonth + 1, rentDueDay);
    }
  }

  const transactionCount = (payments?.length || 0) + (invoices?.length || 0);

  return {
    totalPaid,
    totalCharges,
    currentBalance,
    lastPaymentDate,
    nextDueDate,
    transactionCount
  };
};

/**
 * Format currency for display
 */
export const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value);
};

/**
 * Format amount with +/- prefix for transaction display
 */
export const formatTransactionAmount = (amount: number, isCharge: boolean): string => {
  const formatted = formatCurrency(Math.abs(amount));
  return isCharge ? `+${formatted}` : `-${formatted}`;
};

/**
 * Get color class for balance display in summary cards
 */
export const getBalanceColor = (balance: number): string => {
  if (balance > 0) return 'text-red-600 dark:text-red-400';  // Owes money
  if (balance < 0) return 'text-green-600 dark:text-green-400';  // Overpaid/credit
  return 'text-gray-900 dark:text-gray-100';  // Paid up - white
};

/**
 * Get status badge class
 */
export const getStatusBadgeClass = (status: string): string => {
  switch (status.toLowerCase()) {
    case 'paid':
      return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300';
    case 'pending':
    case 'partial':
      return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300';
    case 'overdue':
      return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300';
    case 'cancelled':
    case 'refunded':
      return 'bg-gray-100 dark:bg-gray-900/30 text-gray-700 dark:text-gray-300';
    default:
      return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300';
  }
};

/**
 * Format date for CSV export (ISO 8601: YYYY-MM-DD)
 * Uses en-CA locale for consistent, sortable date format
 */
export const formatDateForCSV = (date: Date): string => {
  return date.toLocaleDateString('en-CA'); // YYYY-MM-DD format
};

/**
 * Format date for UI display (US format: MMM DD, YYYY)
 * Uses en-US locale for consistent user-facing display
 */
export const formatDateForDisplay = (date: Date, options?: Intl.DateTimeFormatOptions): string => {
  const defaultOptions: Intl.DateTimeFormatOptions = {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  };
  return date.toLocaleDateString('en-US', options || defaultOptions);
};

