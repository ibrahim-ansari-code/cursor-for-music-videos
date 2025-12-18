import React from 'react';
import { FaDownload, FaHistory, FaCreditCard } from 'react-icons/fa';
import type { PaymentHistoryItem } from '@/types';
import type { TenantBalance } from '@/types/payments';

interface PaymentHistoryProps {
  paymentHistory: PaymentHistoryItem[];
  onDownloadReceipt: (receiptUrl: string) => void;
  formatCurrency: (amount: number) => string;
  onMakePayment: () => void;
  balanceData: TenantBalance | null;
}

/**
 * PaymentHistory Component
 * Displays payment history table or helpful empty state
 */
const PaymentHistory: React.FC<PaymentHistoryProps> = ({ 
  paymentHistory, 
  onDownloadReceipt, 
  formatCurrency,
  onMakePayment,
  balanceData
}) => {
  const hasNoBalance = balanceData?.current_balance_cents === 0;
  
  const EmptyHistoryState: React.FC = () => (
    <div className="text-center py-12">
      <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-gray-100 mb-3">
        <FaHistory className="h-6 w-6 text-gray-400" />
      </div>
      <h3 className="text-base font-medium text-gray-900 mb-2">
        No Payment History Yet
      </h3>
      <p className="text-sm text-gray-500 mb-4 max-w-sm mx-auto">
        {hasNoBalance 
          ? 'Your payment history is empty. Future payments will appear here.'
          : 'Your payment records will appear here after you make your first payment.'}
      </p>
      {!hasNoBalance && (
        <button
          onClick={onMakePayment}
          className="inline-flex items-center bg-gray-900 text-white px-4 py-2 rounded-md hover:bg-gray-800 transition-all duration-200 font-medium text-sm cursor-pointer"
        >
          <FaCreditCard className="mr-2 text-sm" />
          Make Your First Payment
        </button>
      )}
    </div>
  );

  const PaymentTable: React.FC = () => (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Date
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Description
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Payment Method
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Amount
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Receipt
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {paymentHistory.map((payment) => (
            <tr key={payment.id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {payment.date}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {payment.description}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {payment.paymentMethod}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {formatCurrency(payment.amount)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                  payment.status === 'Paid' ? 'bg-green-100 text-green-800' :
                  payment.status === 'Refunded' ? 'bg-blue-100 text-blue-800' :
                  payment.status === 'Pending' ? 'bg-yellow-100 text-yellow-800' :
                  payment.status === 'Failed' ? 'bg-red-100 text-red-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {payment.status}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                {payment.receiptUrl ? (
                  <button
                    onClick={() => onDownloadReceipt(payment.receiptUrl!)}
                    className="text-black hover:text-brand-green transition-all duration-200 flex items-center space-x-1 text-sm font-medium hover:bg-brand-teal hover:bg-opacity-10 px-2 py-1 rounded cursor-pointer"
                  >
                    <FaDownload className="text-xs" />
                    <span>Download</span>
                  </button>
                ) : (payment.status === 'Paid' || payment.status === 'Refunded') ? (
                  <div className="flex items-center space-x-2 text-xs text-gray-500">
                    <svg className="animate-spin h-3 w-3 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Generating...</span>
                  </div>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-800">Payment History</h2>
      </div>
      
      {paymentHistory.length > 0 ? (
        <PaymentTable />
      ) : (
        <EmptyHistoryState />
      )}
    </div>
  );
};

export default PaymentHistory;

