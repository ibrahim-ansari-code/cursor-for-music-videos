import React from 'react';
import PropTypes from 'prop-types';
import { FaDownload, FaHistory, FaCreditCard } from 'react-icons/fa';

/**
 * PaymentHistory Component
 * Displays payment history table or helpful empty state
 */
const PaymentHistory = ({ 
  paymentHistory, 
  onDownloadReceipt, 
  formatCurrency,
  onMakePayment 
}) => {
  const EmptyHistoryState = () => (
    <div className="text-center py-12">
      <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-gray-100 mb-3">
        <FaHistory className="h-6 w-6 text-gray-400" />
      </div>
      <h3 className="text-base font-medium text-gray-900 mb-2">
        No Payment History Yet
      </h3>
      <p className="text-sm text-gray-500 mb-4 max-w-sm mx-auto">
        Your payment records will appear here after you make your first payment.
      </p>
      <button
        onClick={onMakePayment}
        className="inline-flex items-center bg-brand-teal text-white px-4 py-2 rounded-lg hover:bg-brand-green transition-all duration-200 font-medium text-sm shadow-sm hover:shadow-md"
      >
        <FaCreditCard className="mr-2 text-sm" />
        Make Your First Payment
      </button>
    </div>
  );

  const PaymentTable = () => (
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
                  payment.status === 'Pending' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {payment.status}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                {payment.receiptUrl && (
                  <button
                    onClick={() => onDownloadReceipt(payment.receiptUrl)}
                    className="text-brand-teal hover:text-brand-green transition-all duration-200 flex items-center space-x-1 text-sm font-medium hover:bg-brand-teal hover:bg-opacity-10 px-2 py-1 rounded"
                  >
                    <FaDownload className="text-xs" />
                    <span>Download</span>
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-xl font-semibold text-gray-900">Payment History</h2>
      </div>
      
      {paymentHistory.length > 0 ? (
        <PaymentTable />
      ) : (
        <EmptyHistoryState />
      )}
    </div>
  );
};

PaymentHistory.propTypes = {
  paymentHistory: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    date: PropTypes.string.isRequired,
    description: PropTypes.string.isRequired,
    paymentMethod: PropTypes.string.isRequired,
    amount: PropTypes.number.isRequired,
    status: PropTypes.string.isRequired,
    receiptUrl: PropTypes.string
  })).isRequired,
  onDownloadReceipt: PropTypes.func.isRequired,
  formatCurrency: PropTypes.func.isRequired,
  onMakePayment: PropTypes.func.isRequired
};

export default PaymentHistory;
