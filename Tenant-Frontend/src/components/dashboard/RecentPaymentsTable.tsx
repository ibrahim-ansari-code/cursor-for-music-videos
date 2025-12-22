import React from 'react';
import { useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { FaDownload, FaHistory, FaCreditCard } from 'react-icons/fa';
import { useRentTransactions } from '@/hooks/usePayments';
import type { RentTransaction } from '@/types/payments';

/**
 * RecentPaymentsTable Component
 * Displays recent payment history on the dashboard with link to full payments page
 */
const RecentPaymentsTable: React.FC = () => {
  const navigate = useNavigate();
  const { data: transactions = [], isLoading } = useRentTransactions();

  // Get only the most recent 3 payments
  const recentPayments = transactions.slice(0, 3);

  const formatCurrency = (amountCents: number): string => {
    return new Intl.NumberFormat('en-CA', {
      style: 'currency',
      currency: 'CAD',
    }).format(amountCents / 100);
  };

  const getStatusBadge = (status: RentTransaction['status']) => {
    const styles = {
      succeeded: 'bg-green-100 text-green-800',
      refunded: 'bg-blue-100 text-blue-800',
      pending: 'bg-yellow-100 text-yellow-800',
      processing: 'bg-yellow-100 text-yellow-800',
      failed: 'bg-red-100 text-red-800',
    };

    const labels = {
      succeeded: 'Paid',
      refunded: 'Refunded',
      pending: 'Pending',
      processing: 'Processing',
      failed: 'Failed',
    };

    return (
      <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${styles[status]}`}>
        {labels[status]}
      </span>
    );
  };

  const getPaymentMethodLabel = (transaction: RentTransaction): string => {
    const lastFour = transaction.payment_method_last_four;

    if (transaction.payment_method_type === 'acss_debit') {
      if (transaction.payment_method_bank_name && lastFour) {
        return `${transaction.payment_method_bank_name} ****${lastFour}`;
      }
      if (lastFour) {
        return `Bank ****${lastFour}`;
      }
      return 'Bank Transfer';
    }
    if (transaction.payment_method_type === 'card') {
      if (lastFour) {
        return `Card ****${lastFour}`;
      }
      return 'Credit/Debit Card';
    }
    return 'Online Payment';
  };

  const handleDownloadReceipt = (receiptUrl: string): void => {
    window.open(receiptUrl, '_blank');
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="mt-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <div className="h-5 bg-gray-200 rounded w-32 animate-pulse"></div>
            <div className="h-4 bg-gray-200 rounded w-14 animate-pulse"></div>
          </div>
          <div className="divide-y divide-gray-100">
            {[1, 2, 3].map((i) => (
              <div key={i} className="px-4 py-3 flex items-center justify-between animate-pulse">
                <div className="flex-1">
                  <div className="h-4 bg-gray-200 rounded w-20 mb-1"></div>
                  <div className="h-3 bg-gray-200 rounded w-28"></div>
                </div>
                <div className="h-4 bg-gray-200 rounded w-16"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (recentPayments.length === 0) {
    return (
      <div className="mt-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-base font-semibold text-gray-900">Recent Payments</h3>
            <button
              onClick={() => navigate('/payments')}
              className="text-sm font-medium text-gray-900 hover:text-brand-teal transition-colors cursor-pointer"
            >
              View All
            </button>
          </div>

          <div className="p-6 text-center">
            <div className="mx-auto flex items-center justify-center h-10 w-10 rounded-full bg-gray-100 mb-2">
              <FaHistory className="h-4 w-4 text-gray-400" />
            </div>
            <p className="text-sm text-gray-500 mb-3">
              No payment history yet
            </p>
            <button
              onClick={() => navigate('/payments')}
              className="inline-flex items-center text-sm font-medium text-brand-teal hover:text-brand-green transition-colors"
            >
              <FaCreditCard className="mr-1.5 h-3.5 w-3.5" />
              Make a Payment
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-base font-semibold text-gray-900">Recent Payments</h3>
          <button
            onClick={() => navigate('/payments')}
            className="text-sm font-medium text-gray-900 hover:text-brand-teal transition-colors cursor-pointer"
          >
            View All
          </button>
        </div>

        {/* Payments List - Compact design */}
        <div className="divide-y divide-gray-100">
          {recentPayments.map((payment) => (
            <div
              key={payment.id}
              className="px-4 py-3 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center justify-between">
                {/* Left side - Date and Payment Method */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-gray-900">
                      {format(new Date(payment.created_at), 'MMM d')}
                    </p>
                    {getStatusBadge(payment.status)}
                  </div>
                  <p className="text-xs text-gray-500 truncate">
                    {getPaymentMethodLabel(payment)}
                  </p>
                </div>

                {/* Right side - Amount and Receipt */}
                <div className="flex items-center gap-2 ml-3">
                  <p className="text-sm font-semibold text-gray-900">
                    {formatCurrency(payment.amount_cents)}
                  </p>

                  {/* Receipt Download - compact */}
                  {payment.receipt_url ? (
                    <button
                      onClick={() => handleDownloadReceipt(payment.receipt_url!)}
                      className="p-1.5 text-gray-400 hover:text-brand-teal rounded transition-colors"
                      title="Download Receipt"
                    >
                      <FaDownload className="h-3.5 w-3.5" />
                    </button>
                  ) : (payment.status === 'succeeded' || payment.status === 'refunded') ? (
                    <div className="p-1.5" title="Receipt generating...">
                      <svg
                        className="animate-spin h-3.5 w-3.5 text-gray-400"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        />
                      </svg>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
};

export default RecentPaymentsTable;
