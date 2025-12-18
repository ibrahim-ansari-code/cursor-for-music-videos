import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchPayments,
  createPayment,
  updatePayment,
  deletePayment,
  generateDuePayments,
  fetchOutstandingPayments,
  parsePaymentReceipt,
  fetchInvoices,
  createInvoice,
  fetchInvoice,
  updateInvoice,
  deleteInvoice,
  markInvoicePaid,
  fetchExpenses,
  createExpense,
  parseExpenseReceipt,
  updateExpense,
  deleteExpense,
  getOccupancyRates,
  getRevenueTrends,
  getAccountingOverview,
  createRefund,
  fetchRefunds,
  fetchRefund,
  fetchDisputes,
  fetchDispute,
} from "../utils/api/accounting";
import { fetchReportSummary } from "../utils/api/reports";
import { fetchRentTracker } from "../utils/api/rentTracker";
import { QUERY_KEYS } from "./queryKeys";

// ===== PAYMENT QUERIES =====
export const usePayments = (params = {}) => {
  return useQuery({
    queryKey: QUERY_KEYS.accounting.payments(params),
    queryFn: () => fetchPayments(params),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

export const useOutstandingPayments = (params = {}) => {
  return useQuery({
    queryKey: QUERY_KEYS.accounting.outstandingPayments(params),
    queryFn: () => fetchOutstandingPayments(params),
    staleTime: 1 * 60 * 1000, // 1 minute (more frequent updates for outstanding payments)
  });
};

export const useCreatePayment = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: createPayment,
    onSuccess: () => {
      // Invalidate and refetch payment-related queries
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.accounting.payments() });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.accounting.outstandingPayments() });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.accounting.overview() });
    },
  });
};

export const useUpdatePayment = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ paymentId, paymentData }) => updatePayment(paymentId, paymentData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounting", "payments"] });
      queryClient.invalidateQueries({ queryKey: ["accounting", "outstandingPayments"] });
      queryClient.invalidateQueries({ queryKey: ["accounting", "overview"] });
    },
  });
};

export const useDeletePayment = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: deletePayment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounting", "payments"] });
      queryClient.invalidateQueries({ queryKey: ["accounting", "outstandingPayments"] });
      queryClient.invalidateQueries({ queryKey: ["accounting", "overview"] });
    },
  });
};

export const useGenerateDuePayments = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: generateDuePayments,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.accounting.payments() });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.accounting.outstandingPayments() });
    },
  });
};

export const useParsePaymentReceipt = () => {
  return useMutation({
    mutationFn: parsePaymentReceipt,
  });
};

// ===== INVOICE QUERIES =====
export const useInvoices = (params = {}) => {
  return useQuery({
    queryKey: QUERY_KEYS.accounting.invoices(params),
    queryFn: () => fetchInvoices(params),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

export const useInvoice = (invoiceId) => {
  return useQuery({
    queryKey: QUERY_KEYS.accounting.invoice(invoiceId),
    queryFn: () => fetchInvoice(invoiceId),
    enabled: !!invoiceId,
    staleTime: 5 * 60 * 1000, // 5 minutes for individual invoices
  });
};

export const useCreateInvoice = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: createInvoice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounting", "invoices"] });
      queryClient.invalidateQueries({ queryKey: ["accounting", "overview"] });
    },
  });
};

export const useUpdateInvoice = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ invoiceId, invoiceData }) => updateInvoice(invoiceId, invoiceData),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["accounting", "invoices"] });
      queryClient.invalidateQueries({ queryKey: ["accounting", "invoice", variables.invoiceId] });
      queryClient.invalidateQueries({ queryKey: ["accounting", "overview"] });
    },
  });
};

export const useDeleteInvoice = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: deleteInvoice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounting", "invoices"] });
      queryClient.invalidateQueries({ queryKey: ["accounting", "overview"] });
    },
  });
};

export const useMarkInvoicePaid = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: markInvoicePaid,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounting", "invoices"] });
      queryClient.invalidateQueries({ queryKey: ["accounting", "payments"] });
      queryClient.invalidateQueries({ queryKey: ["accounting", "overview"] });
    },
  });
};

// ===== EXPENSE QUERIES =====
export const useExpenses = (params = {}) => {
  return useQuery({
    queryKey: QUERY_KEYS.accounting.expenses(params),
    queryFn: () => fetchExpenses(params),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

export const useCreateExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: createExpense,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounting", "expenses"] });
      queryClient.invalidateQueries({ queryKey: ["accounting", "overview"] });
    },
  });
};

export const useUpdateExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ expenseId, expenseData }) => updateExpense(expenseId, expenseData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounting", "expenses"] });
      queryClient.invalidateQueries({ queryKey: ["accounting", "overview"] });
    },
  });
};

export const useDeleteExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: deleteExpense,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounting", "expenses"] });
      queryClient.invalidateQueries({ queryKey: ["accounting", "overview"] });
    },
  });
};

export const useParseExpenseReceipt = () => {
  return useMutation({
    mutationFn: parseExpenseReceipt,
  });
};

// ===== INSIGHTS QUERIES =====
export const useOccupancyRates = (params = {}) => {
  return useQuery({
    queryKey: QUERY_KEYS.accounting.insights.occupancy(params),
    queryFn: () => getOccupancyRates(params),
    staleTime: 5 * 60 * 1000, // 5 minutes for insights
  });
};

export const useRevenueTrends = (params = {}) => {
  return useQuery({
    queryKey: QUERY_KEYS.accounting.insights.revenue(params),
    queryFn: () => getRevenueTrends(params),
    staleTime: 5 * 60 * 1000, // 5 minutes for insights
  });
};

export const useAccountingOverview = (params = {}) => {
  return useQuery({
    queryKey: QUERY_KEYS.accounting.overview(params),
    queryFn: () => getAccountingOverview(params),
    staleTime: 2 * 60 * 1000, // 2 minutes for overview data
  });
};

// ===== SUPPORTING DATA QUERIES =====
export const useReportSummary = (params = {}) => {
  return useQuery({
    queryKey: QUERY_KEYS.accounting.reports(params),
    queryFn: () => fetchReportSummary(params),
    staleTime: 3 * 60 * 1000, // 3 minutes for report summaries
  });
};

export const useRentTracker = (params = {}) => {
  return useQuery({
    queryKey: QUERY_KEYS.accounting.rentTracker(params),
    queryFn: () => fetchRentTracker(params),
    staleTime: 2 * 60 * 1000, // 2 minutes for rent tracker
  });
};

// ===== REFUND & DISPUTE QUERIES =====

/**
 * Fetch refunds for a specific transaction or all refunds
 */
export const useRefunds = (params = {}) => {
  return useQuery({
    queryKey: ['refunds', params],
    queryFn: () => fetchRefunds(params),
    staleTime: 1 * 60 * 1000, // 1 minute
    enabled: !!params.transaction_id || params.enabled !== false,
  });
};

/**
 * Fetch a single refund by ID
 */
export const useRefund = (refundId) => {
  return useQuery({
    queryKey: ['refunds', refundId],
    queryFn: () => fetchRefund(refundId),
    enabled: !!refundId,
    staleTime: 1 * 60 * 1000,
  });
};

/**
 * Create a refund for a rent payment transaction
 */
export const useCreateRefund = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: createRefund,
    onSuccess: (data) => {
      // Invalidate refunds list
      queryClient.invalidateQueries({ queryKey: ['refunds'] });
      // Invalidate payments to show updated status
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.accounting.payments() });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.accounting.overview() });
    },
  });
};

/**
 * Fetch disputes for a specific transaction or all disputes
 */
export const useDisputes = (params = {}) => {
  return useQuery({
    queryKey: ['disputes', params],
    queryFn: () => fetchDisputes(params),
    staleTime: 1 * 60 * 1000, // 1 minute
    enabled: !!params.transaction_id || params.enabled !== false,
  });
};

/**
 * Fetch a single dispute by ID
 */
export const useDispute = (disputeId) => {
  return useQuery({
    queryKey: ['disputes', disputeId],
    queryFn: () => fetchDispute(disputeId),
    enabled: !!disputeId,
    staleTime: 1 * 60 * 1000,
  });
};
