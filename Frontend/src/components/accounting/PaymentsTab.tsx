/**
 * PaymentsTab Component
 * 
 * Main payments ledger for landlords. Shows all payment sources:
 * - Manual entries
 * - QuickBooks synced
 * - Online payments via Stripe Connect
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { toast } from 'react-toastify';
import { CSVLink } from 'react-csv';
import NewPaymentModal from './modals/NewPaymentModal';
import EditPaymentModal from './modals/EditPaymentModal';
import CSVImportModal from './modals/CSVImportModal';
import RefundModal from './modals/RefundModal';
import OnlinePaymentsBanner from './OnlinePaymentsBanner';
import { PaymentsTableSkeleton } from '../ui/skeletons';
import { useAccounting } from './AccountingContext';
import { usePayments, useDeletePayment } from '../../hooks/useAccountingQueries';
import { importPaymentsFromCSV } from '../../utils/api/accounting';
import { getTenantDisplayName, getTenantInitials } from '../../utils/tenantUtils';
import { useSubscriptionGuard } from '../../hooks/useSubscriptionGuard';
import type { 
  Payment, 
  PaymentFilters, 
  PaymentQueryParams,
  PaginationState,
  TableColumn,
  CSVHeader,
  CSVImportConfig,
} from '../../types/rentPayments';

// =============================================================================
// Constants
// =============================================================================

const PAYMENT_TABLE_COLUMNS: TableColumn[] = [
  { key: 'tenant', label: 'Tenant', align: 'left' },
  { key: 'amount', label: 'Amount', align: 'center' },
  { key: 'date', label: 'Date', align: 'center' },
  { key: 'method', label: 'Method', align: 'center' },
  { key: 'status', label: 'Status', align: 'center' },
  { key: 'source', label: 'Source', align: 'center' },
  { key: 'actions', label: 'Actions', align: 'center' },
];

const CSV_HEADERS: CSVHeader[] = [
  { label: 'Tenant', key: 'tenant_name' },
  { label: 'Property', key: 'property_name' },
  { label: 'Amount', key: 'amount' },
  { label: 'Payment Date', key: 'payment_date' },
  { label: 'Payment Method', key: 'payment_method' },
  { label: 'Status', key: 'status' },
  { label: 'Transaction Reference', key: 'transaction_reference' },
  { label: 'Description', key: 'description' },
  { label: 'Source', key: 'source' },
];

const CSV_IMPORT_CONFIG: CSVImportConfig = {
  title: 'Import Payments',
  description: 'Upload your payment data',
  apiFunction: (data: unknown[]) => importPaymentsFromCSV(data as Record<string, unknown>[]),
  expectedHeaders: [
    { key: 'amount', label: 'Amount', required: true, type: 'number', aliases: ['amount', 'payment_amount', 'total'] },
    { key: 'payment_date', label: 'Payment Date', required: true, type: 'date', aliases: ['date', 'payment_date', 'received_date'] },
    { key: 'tenant_name', label: 'Tenant Name', required: false, aliases: ['tenant', 'tenant_name', 'payer'] },
    { key: 'property_name', label: 'Property Name', required: false, aliases: ['property', 'property_name', 'address'] },
    { key: 'payment_method', label: 'Payment Method', required: false, aliases: ['method', 'payment_method', 'payment_type'] },
    { key: 'status', label: 'Status', required: false, aliases: ['status', 'payment_status', 'state'] },
    { key: 'transaction_reference', label: 'Transaction Reference', required: false, aliases: ['reference', 'transaction_reference', 'confirmation'] },
    { key: 'description', label: 'Description', required: false, aliases: ['description', 'notes', 'memo'] },
    { key: 'reduction_amount', label: 'Reduction Amount', required: false, type: 'number', aliases: ['reduction', 'reduction_amount', 'discount'] },
    { key: 'reduction_reason', label: 'Reduction Reason', required: false, aliases: ['reduction_reason', 'discount_reason', 'adjustment_reason'] },
  ],
  sampleData: [
    {
      amount: 1500.00,
      payment_date: '2024-01-15',
      tenant_name: 'John Smith',
      property_name: '123 Main St',
      payment_method: 'Bank Transfer',
      status: 'Paid',
      transaction_reference: 'TXN123456',
      description: 'Monthly rent payment',
    },
    {
      amount: 1200.00,
      payment_date: '2024-01-20',
      tenant_name: 'Jane Doe',
      property_name: '456 Oak Ave',
      payment_method: 'Credit Card',
      status: 'Pending',
      description: 'Rent payment',
    },
  ],
  validationTips: [
    'Amount is required and should be a positive number without currency symbols',
    'Payment date is required in YYYY-MM-DD format or MM/DD/YYYY',
    'Either tenant name or property name should be provided for proper matching',
    'Payment methods: Credit Card, Debit Card, Bank Transfer, Cash, Check, PayPal, Other',
    'Status options: Pending, Paid, Partial, Overdue, Cancelled, Refunded, Draft, Void',
    'Tenant and property names should match exactly as they appear in your system',
  ],
};

// =============================================================================
// Helper Functions
// =============================================================================

function getStatusBadgeClass(status: string): string {
  switch (status.toLowerCase()) {
    case 'paid':
      return 'badge-success';
    case 'pending':
    case 'partial':
      return 'badge-warning';
    case 'late':
    case 'overdue':
      return 'badge-danger';
    case 'refunded':
      return 'badge-info';
    case 'processing':
      return 'badge-warning';
    default:
      return 'badge-info';
  }
}

function getPaymentSource(payment: Payment): { text: string; isStripe: boolean } {
  // Check for online payment (Stripe)
  if (payment.stripe_payment_intent_id) {
    // Determine if bank or card based on payment method
    const method = payment.payment_method?.toLowerCase() || '';
    if (method.includes('bank') || method.includes('transfer')) {
      return { text: 'Stripe - Bank Transfer', isStripe: true };
    }
    return { text: 'Stripe - Card', isStripe: true };
  }
  
  // QuickBooks synced
  if (payment.quickbooks_id) {
    return { text: 'QuickBooks', isStripe: false };
  }
  
  // Manual entry
  return { text: 'Manual', isStripe: false };
}

function getSourceBadgeClass(sourceText: string): string {
  if (sourceText.startsWith('Stripe')) {
    return 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30';
  }
  if (sourceText === 'QuickBooks') {
    return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30';
  }
  return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/30';
}

// =============================================================================
// Component
// =============================================================================

const PaymentsTab: React.FC = () => {
  // Subscription guard for premium features
  const guardAction = useSubscriptionGuard({ featureName: 'recording payments' });

  const { handlePreviewReceipt } = useAccounting();

  // Pagination state
  const [pagination, setPagination] = useState<PaginationState>({
    currentPage: 0,
    limit: 15,
    hasMore: true,
  });

  // Filter state
  const [filters, setFilters] = useState<PaymentFilters>({
    status: 'all',
    dateRange: 'all_time',
    search: '',
  });

  // Modal states
  const [showNewPaymentModal, setShowNewPaymentModal] = useState(false);
  const [showEditPaymentModal, setShowEditPaymentModal] = useState(false);
  const [showCSVImportModal, setShowCSVImportModal] = useState(false);
  const [showRefundModal, setShowRefundModal] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState<Payment | null>(null);

  // Build query parameters
  const queryParams = useMemo<PaymentQueryParams>(() => {
    const params: PaymentQueryParams = {
      limit: pagination.limit,
      offset: pagination.currentPage * pagination.limit,
    };

    if (filters.status !== 'all') {
      params.payment_status = filters.status.charAt(0).toUpperCase() + filters.status.slice(1);
    }

    if (filters.search?.trim()) {
      params.search = filters.search.trim();
    }

    // Convert date range to actual date params
    const today = new Date();
    const dateRanges: Record<string, number> = {
      week: 7,
      month: 30,
      quarter: 90,
      year: 365,
    };

    if (filters.dateRange in dateRanges) {
      const daysAgo = new Date();
      daysAgo.setDate(today.getDate() - dateRanges[filters.dateRange]);
      params.start_date = daysAgo.toISOString().split('T')[0];
      params.end_date = today.toISOString().split('T')[0];
    }

    return params;
  }, [filters, pagination.currentPage, pagination.limit]);

  // TanStack Query hooks
  const { data: paymentsData, isLoading, error, refetch } = usePayments(queryParams);
  const deletePaymentMutation = useDeletePayment();

  // Extract payments
  const payments = (paymentsData?.items || []) as unknown as Payment[];

  // Reset to first page on filter change
  useEffect(() => {
    setPagination((prev) => ({ ...prev, currentPage: 0 }));
  }, [filters]);

  // Update pagination when data changes
  useEffect(() => {
    if (paymentsData) {
      setPagination((prev) => ({ ...prev, hasMore: paymentsData.has_more || false }));
    }
  }, [paymentsData]);

  // Handlers
  const handleEditPayment = useCallback((payment: Payment) => {
    setSelectedPayment(payment);
    setShowEditPaymentModal(true);
  }, []);

  const handleRefundPayment = useCallback((payment: Payment) => {
    setSelectedPayment(payment);
    setShowRefundModal(true);
  }, []);

  const handleDeletePayment = useCallback(async (paymentId: number) => {
    if (!window.confirm('Are you sure you want to delete this payment? This action cannot be undone.')) {
      return;
    }

    try {
      await deletePaymentMutation.mutateAsync(paymentId);
      toast.success('Payment deleted successfully.');
    } catch (err) {
      console.error('Failed to delete payment:', err);
      toast.error((err as Error).message || 'Failed to delete payment.');
    }
  }, [deletePaymentMutation]);

  const handleNextPage = useCallback(() => {
    setPagination((prev) => ({ ...prev, currentPage: prev.currentPage + 1 }));
  }, []);

  const handlePreviousPage = useCallback(() => {
    setPagination((prev) => ({ ...prev, currentPage: Math.max(0, prev.currentPage - 1) }));
  }, []);

  const handleShowModal = guardAction(() => {
    setShowNewPaymentModal(true);
  });

  const handleCloseModals = useCallback(() => {
    setShowNewPaymentModal(false);
    setShowEditPaymentModal(false);
    setSelectedPayment(null);
  }, []);

  const handleCSVImportSuccess = useCallback(() => {
    refetch();
    setShowCSVImportModal(false);
  }, [refetch]);

  // CSV Export helpers
  const getFilterDescription = useCallback((): string => {
    const parts: string[] = [];
    if (filters.status !== 'all') parts.push(`Status: ${filters.status}`);
    if (filters.dateRange !== 'all_time') parts.push(`Date Range: ${filters.dateRange.replace('_', ' ')}`);
    if (filters.search) parts.push(`Search: "${filters.search}"`);
    return parts.length > 0 ? parts.join(', ') : 'No filters applied';
  }, [filters]);

  const csvData = useMemo(() => [
    // Header row with metadata
    {
      tenant_name: 'Brikli Payments Report',
      property_name: `Exported: ${new Date().toLocaleDateString()}`,
      amount: `Filters: ${getFilterDescription()}`,
      payment_date: `Records: ${payments.length}`,
      payment_method: '',
      status: '',
      transaction_reference: '',
      description: '',
      source: '',
    },
    // Empty separator row
    { tenant_name: '', property_name: '', amount: '', payment_date: '', payment_method: '', status: '', transaction_reference: '', description: '', source: '' },
    // Actual data
    ...payments.map((payment) => {
      const amt = Number(payment.amount ?? 0);
      const paymentDate = payment.payment_date ? new Date(payment.payment_date) : null;
      return {
        tenant_name: payment.tenant_name || 'N/A',
        property_name: payment.property_name || 'N/A',
        amount: Number.isFinite(amt) ? amt.toFixed(2) : '0.00',
        payment_date: paymentDate && !isNaN(paymentDate.getTime()) ? paymentDate.toLocaleDateString() : 'N/A',
        payment_method: payment.payment_method || 'N/A',
        status: payment.status || 'N/A',
        transaction_reference: payment.transaction_reference || 'N/A',
        description: payment.description || 'N/A',
        source: getPaymentSource(payment).text,
      };
    }),
  ], [payments, getFilterDescription]);

  const generateFilename = useCallback((): string => {
    const now = new Date();
    const dateStr = now.toISOString().split('T')[0];
    const timeStr = now.toTimeString().split(' ')[0].replace(/:/g, '');
    const filterSuffix = filters.status !== 'all' ? `-${filters.status}` : '';
    const searchSuffix = filters.search ? '-search' : '';
    return `Brikli-Payments-Report${filterSuffix}${searchSuffix}-${dateStr}-${timeStr}.csv`;
  }, [filters]);

  // Loading state
  if (isLoading) {
    return <PaymentsTableSkeleton rowCount={8} />;
  }

  return (
    <div>
      {/* Online Payments Banner */}
      <OnlinePaymentsBanner dismissible />

      {/* Error State */}
      {error && (
        <div className="bg-red-100 dark:bg-red-900/20 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-400 px-4 py-3 rounded mb-4">
          <p>{String(error)}</p>
          <button
            onClick={() => refetch()}
            className="mt-2 bg-red-500 dark:bg-red-600 hover:bg-red-700 dark:hover:bg-red-500 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0 transition-colors duration-300 mb-4">
        <div className="flex flex-col sm:flex-row sm:space-x-4 space-y-2 sm:space-y-0">
          <div>
            <label
              htmlFor="payment-status"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Status
            </label>
            <select
              id="payment-status"
              className="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              value={filters.status}
              onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value }))}
            >
              <option value="all">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="paid">Paid</option>
              <option value="partial">Partial</option>
              <option value="overdue">Overdue</option>
              <option value="cancelled">Cancelled</option>
              <option value="refunded">Refunded</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="payment-date-range"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Date Range
            </label>
            <select
              id="payment-date-range"
              className="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              value={filters.dateRange}
              onChange={(e) => setFilters((prev) => ({ ...prev, dateRange: e.target.value }))}
            >
              <option value="all_time">All Time</option>
              <option value="week">Last 7 Days</option>
              <option value="month">Last 30 Days</option>
              <option value="quarter">Last 3 Months</option>
              <option value="year">Last 12 Months</option>
            </select>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="relative rounded-md shadow-sm">
            <input
              type="search"
              placeholder="Search payments..."
              value={filters.search}
              onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
              className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 pr-3 py-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-md text-sm"
            />
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <i className="fas fa-search text-gray-400 dark:text-gray-500" />
            </div>
          </div>

          <button
            onClick={() => setShowCSVImportModal(true)}
            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i className="fas fa-upload mr-2" />
            Import CSV
          </button>

          <CSVLink
            data={csvData}
            headers={CSV_HEADERS}
            filename={generateFilename()}
            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i className="fas fa-download mr-2" />
            Export CSV
          </CSVLink>

          <button
            onClick={handleShowModal}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i className="fas fa-plus mr-2" />
            New Payment
          </button>
        </div>
      </div>

      {/* Payments Table */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden transition-colors duration-300">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                {PAYMENT_TABLE_COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    scope="col"
                    className={`px-6 py-3 ${
                      col.align === 'center' ? 'text-center' : 'text-left'
                    } text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider`}
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {payments.length > 0 ? (
                payments.map((payment, index) => {
                  const bgColor = index % 2 === 0
                    ? 'bg-white dark:bg-gray-800'
                    : 'bg-gray-50 dark:bg-gray-700/50';
                  const source = getPaymentSource(payment);

                  return (
                    <tr
                      key={payment.id}
                      className={`${bgColor} hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors duration-150`}
                    >
                      {/* Tenant */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-8 w-8 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center text-gray-600 dark:text-gray-300">
                            {getTenantInitials(payment.tenant)}
                          </div>
                          <div className="ml-3">
                            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              {payment.tenant_name || getTenantDisplayName(payment.tenant, `Tenant #${payment.tenant_id}`)}
                            </div>
                            <div className="text-sm text-gray-500 dark:text-gray-400">
                              {payment.property_name || `Lease #${payment.lease_id}`}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Amount */}
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <div className="text-sm text-gray-900 dark:text-gray-100">
                          ${Number.parseFloat(String(payment.amount)).toFixed(2)}
                        </div>
                      </td>

                      {/* Date */}
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <div className="text-sm text-gray-900 dark:text-gray-100">
                          {new Date(payment.payment_date).toLocaleDateString()}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(payment.payment_date).toLocaleTimeString()}
                        </div>
                      </td>

                      {/* Method */}
                      <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500 dark:text-gray-400">
                        {payment.payment_method}
                      </td>

                      {/* Status */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex justify-center">
                          <span className={`badge ${getStatusBadgeClass(payment.status)}`}>
                            {payment.status.charAt(0).toUpperCase() + payment.status.slice(1).toLowerCase()}
                          </span>
                        </div>
                      </td>

                      {/* Source */}
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        {source.isStripe && payment.receipt_url ? (
                          <a
                            href={payment.receipt_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getSourceBadgeClass(source.text)} hover:underline hover:opacity-80 cursor-pointer transition-opacity`}
                            title="View Stripe receipt"
                          >
                            {source.text}
                            <i className="fas fa-external-link-alt ml-1 text-[10px]" />
                          </a>
                        ) : (
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getSourceBadgeClass(source.text)}`}>
                            {source.text}
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                        <div className="flex justify-center space-x-2">
                          {payment.receipt_url && (
                            <button
                              type="button"
                              onClick={() => {
                                // Stripe receipts must open in new tab due to CSP restrictions
                                if (payment.stripe_payment_intent_id) {
                                  window.open(payment.receipt_url!, '_blank', 'noopener,noreferrer');
                                } else {
                                  const descriptiveName = `Receipt for ${payment.tenant_name || 'Unknown Tenant'}${
                                    payment.property_name ? ` - ${payment.property_name}` : ''
                                  }`;
                                  handlePreviewReceipt(payment.receipt_url!, descriptiveName);
                                }
                              }}
                              className="text-blue-600 dark:text-blue-400 hover:text-blue-900 dark:hover:text-blue-300 p-1"
                              title="View Receipt"
                            >
                              <i className="fas fa-eye" />
                            </button>
                          )}
                          {payment.stripe_payment_intent_id && payment.status === 'Paid' && (
                            <button
                              type="button"
                              onClick={() => handleRefundPayment(payment)}
                              className="text-yellow-600 dark:text-yellow-400 hover:text-yellow-900 dark:hover:text-yellow-300 p-1"
                              title="Issue Refund"
                            >
                              <i className="fas fa-undo" />
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => handleEditPayment(payment)}
                            className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300"
                            title="Edit"
                          >
                            <i className="fas fa-edit" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeletePayment(payment.id)}
                            className="text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300"
                            title="Delete"
                          >
                            <i className="fas fa-trash-alt" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td
                    colSpan={PAYMENT_TABLE_COLUMNS.length}
                    className="px-6 py-4 text-center text-sm text-gray-500 dark:text-gray-400"
                  >
                    No payments found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex justify-between items-center mt-4 p-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
          <button
            type="button"
            onClick={handlePreviousPage}
            disabled={pagination.currentPage === 0 || isLoading}
            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Go to previous page"
          >
            <i className="fas fa-arrow-left mr-2" aria-hidden="true" />
            Previous
          </button>
          <span className="text-sm text-gray-700 dark:text-gray-300">
            Page {pagination.currentPage + 1}
          </span>
          <button
            type="button"
            onClick={handleNextPage}
            disabled={!pagination.hasMore || isLoading}
            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Go to next page"
          >
            Next
            <i className="fas fa-arrow-right ml-2" aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Modals */}
      {showNewPaymentModal && (
        <NewPaymentModal
          isOpen={showNewPaymentModal}
          onClose={handleCloseModals}
          onSuccess={() => {
            setShowNewPaymentModal(false);
            refetch();
            toast.success('Payment created successfully');
          }}
        />
      )}

      {showEditPaymentModal && selectedPayment && (
        <EditPaymentModal
          isOpen={showEditPaymentModal}
          onClose={() => {
            setShowEditPaymentModal(false);
            setSelectedPayment(null);
          }}
          onSuccess={() => {
            setShowEditPaymentModal(false);
            setSelectedPayment(null);
            refetch();
            toast.success('Payment updated successfully');
          }}
          paymentData={selectedPayment}
        />
      )}

      {showCSVImportModal && (
        <CSVImportModal
          isOpen={showCSVImportModal}
          onClose={() => setShowCSVImportModal(false)}
          onSuccess={handleCSVImportSuccess}
          config={CSV_IMPORT_CONFIG}
        />
      )}

      {showRefundModal && selectedPayment && (
        <RefundModal
          isOpen={showRefundModal}
          onClose={() => {
            setShowRefundModal(false);
            setSelectedPayment(null);
          }}
          payment={selectedPayment}
          onSuccess={async () => {
            setShowRefundModal(false);
            setSelectedPayment(null);
            
            // Immediately refetch to show processing status
            await refetch();
            
            // Poll for status update (webhook typically processes within 2-3 seconds)
            const pollInterval = setInterval(async () => {
              await refetch();
            }, 2000);
            
            // Stop polling after 10 seconds
            setTimeout(() => {
              clearInterval(pollInterval);
            }, 10000);
          }}
        />
      )}
    </div>
  );
};

export default PaymentsTab;


