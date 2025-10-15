import React, { useMemo } from 'react';
import { useOutletContext } from 'react-router-dom';
import { CSVLink } from 'react-csv';
import { EnrichedTenant } from '../../../../types/tenant';
import {
  buildTransactionLedger,
  calculateLedgerMetrics,
  formatCurrency,
  formatTransactionAmount,
  getBalanceColor,
  getStatusBadgeClass,
  formatDateForCSV,
  formatDateForDisplay,
  Transaction
} from '../../../../utils/transactionLedger';

interface OutletContext {
  tenant: EnrichedTenant;
  refetch: () => void;
  openPaymentModal: (initialData: any) => void;
  openFilePreviewModal: (url: string, name: string) => void;
}

const PaymentsTab: React.FC = () => {
  const context = useOutletContext<OutletContext>();

  // Guard: Handle undefined context gracefully
  if (!context || !context.tenant) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-blue-200 dark:border-blue-800 border-t-blue-600 dark:border-t-blue-400 rounded-full animate-spin" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading payment history...</p>
        </div>
      </div>
    );
  }

  const { tenant, openPaymentModal, openFilePreviewModal } = context;

  // Get active lease
  const activeLease = tenant.leases?.find(lease => lease.status === 'ACTIVE');

  // Build transaction ledger with running balance
  const transactions = useMemo(() => {
    return buildTransactionLedger(tenant.payments, tenant.invoices);
  }, [tenant.payments, tenant.invoices]);

  // Calculate metrics
  const metrics = useMemo(() => {
    return calculateLedgerMetrics(tenant.payments, tenant.invoices, activeLease);
  }, [tenant.payments, tenant.invoices, activeLease]);

  // Handle Record Payment
  const handleRecordPayment = () => {
    if (!activeLease) {
      return;
    }

    const tenantName = tenant.tenant_type === 'Company'
      ? tenant.company_name || 'Company Tenant'
      : `${tenant.first_name || ''} ${tenant.last_name || ''}`.trim();

    const propertyName = activeLease.property?.name || tenant.property?.name || '';
    const propertyId = activeLease.property?.id || tenant.current_property_id;

    const initialData = {
      tenant_id: tenant.id,
      tenant_name: tenantName,
      property_id: propertyId?.toString() || '',
      property_name: propertyName,
      lease_id: activeLease.id,
      amount: activeLease.monthly_rent?.toString() || '',
      payment_date: new Date().toISOString().split('T')[0],
      payment_method: 'Other',
      status: 'Paid',
    };

    openPaymentModal(initialData);
  };

  // Handle Receipt Preview
  const handleViewReceipt = (transaction: Transaction) => {
    if (!transaction.receiptUrl) return;
    
    openFilePreviewModal(transaction.receiptUrl, `Receipt - ${transaction.description}`);
  };

  // CSV Export Data
  const csvData = useMemo(() => {
    const tenantName = tenant.tenant_type === 'Company'
      ? tenant.company_name
      : `${tenant.first_name} ${tenant.last_name}`;

    return [
      // Header row with metadata
      {
        Date: `${tenantName} - Payment History`,
        Type: `Exported: ${formatDateForDisplay(new Date())}`,
        Description: `Transactions: ${transactions.length}`,
        Amount: '',
        Balance: '',
        'Payment Method': '',
        Status: ''
      },
      // Empty separator
      { Date: '', Type: '', Description: '', Amount: '', Balance: '', 'Payment Method': '', Status: '' },
      // Transaction data
      ...transactions.map(txn => ({
        Date: formatDateForCSV(txn.date),  // YYYY-MM-DD format (sortable)
        Type: txn.type,
        Description: txn.description,
        Amount: formatTransactionAmount(txn.amount, txn.isCharge),
        Balance: formatCurrency(txn.balance),
        'Payment Method': txn.paymentMethod || '-',
        Status: txn.status
      }))
    ];
  }, [transactions, tenant]);

  const csvFilename = useMemo(() => {
    const tenantName = tenant.tenant_type === 'Company'
      ? tenant.company_name?.replace(/\s+/g, '-')
      : `${tenant.first_name}-${tenant.last_name}`;
    const date = new Date().toISOString().split('T')[0];
    return `${tenantName}-Payments-${date}.csv`;
  }, [tenant]);

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Total Paid */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Total Paid</h4>
            <div className="w-8 h-8 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
              <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div className="mb-1">
            <span className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              {formatCurrency(metrics.totalPaid)}
            </span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {metrics.lastPaymentDate
              ? `Last payment: ${formatDateForDisplay(metrics.lastPaymentDate)}`
              : 'No payments yet'}
          </p>
        </div>

        {/* Total Charges */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Total Charges</h4>
            <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
              <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
          </div>
          <div className="mb-1">
            <span className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              {formatCurrency(metrics.totalCharges)}
            </span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            All invoices and charges
          </p>
        </div>

        {/* Account Balance */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Account Balance</h4>
            <div className={`w-8 h-8 rounded-lg ${metrics.currentBalance > 0 ? 'bg-red-100 dark:bg-red-900/30' : 'bg-green-100 dark:bg-green-900/30'} flex items-center justify-center`}>
              <svg className={`w-4 h-4 ${metrics.currentBalance > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
          </div>
          <div className="mb-1">
            <span className={`text-3xl font-bold ${getBalanceColor(metrics.currentBalance)}`}>
              {formatCurrency(Math.abs(metrics.currentBalance))}
            </span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {metrics.currentBalance > 0 
              ? 'Per ledger'
              : metrics.currentBalance < 0
              ? 'Credit on account'
              : 'All paid up!'}
          </p>
        </div>
      </div>

      {/* Transaction Ledger */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Transaction Ledger</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {metrics.transactionCount} transaction{metrics.transactionCount !== 1 ? 's' : ''}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <CSVLink
              data={csvData}
              filename={csvFilename}
              className="inline-flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors text-sm font-medium"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Export CSV
            </CSVLink>
            {activeLease && (
              <button
                onClick={handleRecordPayment}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Record Payment
              </button>
            )}
          </div>
        </div>

        {transactions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Description</th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Amount</th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Balance</th>
                  <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Status</th>
                  <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Payment Method</th>
                  <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Receipt</th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:border-gray-700">
                {transactions.map((txn, index) => (
                  <tr key={txn.id} className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${index % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-700/50'}`}>
                    {/* Date */}
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                      {formatDateForDisplay(txn.date)}
                    </td>

                    {/* Type */}
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold ${
                        txn.isCharge 
                          ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                          : 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                      }`}>
                        {txn.isCharge ? 'Charge' : 'Payment'}
                      </span>
                    </td>

                    {/* Description */}
                    <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-100">
                      <div className="max-w-xs truncate" title={txn.description}>
                        {txn.description}
                      </div>
                    </td>

                    {/* Amount */}
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-right text-gray-900 dark:text-gray-100">
                      {formatTransactionAmount(txn.amount, txn.isCharge)}
                    </td>

                    {/* Balance */}
                    <td className={`px-6 py-4 whitespace-nowrap text-sm font-bold text-right ${
                      txn.balance > 0
                        ? 'text-red-600 dark:text-red-400'  // Owes money - red
                        : txn.balance < 0
                        ? 'text-green-600 dark:text-green-400'  // Overpaid - green
                        : 'text-gray-900 dark:text-gray-100'  // Zero - white
                    }`}>
                      {formatCurrency(txn.balance)}
                    </td>

                    {/* Status */}
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold ${getStatusBadgeClass(txn.status)}`}>
                        {txn.status}
                      </span>
                    </td>

                    {/* Payment Method */}
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-600 dark:text-gray-400">
                      {txn.paymentMethod || '-'}
                    </td>

                    {/* Receipt */}
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      {txn.receiptUrl ? (
                        <button
                          onClick={() => handleViewReceipt(txn)}
                          className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
                          title="View Receipt"
                        >
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        </button>
                      ) : (
                        <span className="text-gray-400 dark:text-gray-600">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center">
            <div className="mx-auto w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              No transaction history
        </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Payments and charges will appear here once recorded
            </p>
            {activeLease && (
              <button
                onClick={handleRecordPayment}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Record First Payment
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PaymentsTab;
