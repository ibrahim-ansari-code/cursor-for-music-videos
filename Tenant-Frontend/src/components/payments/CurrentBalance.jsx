import React from 'react';
import PropTypes from 'prop-types';
import { FaDollarSign, FaCalendarAlt } from 'react-icons/fa';

/**
 * CurrentBalance Component
 * Displays current balance with action buttons or helpful empty state
 */
const CurrentBalance = ({ 
  currentBalance, 
  onMakePayment, 
  onSetupAutopay,
  formatCurrency 
}) => {
  const EmptyBalanceState = () => (
    <div className="text-center py-4">
      <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-gray-100 mb-6">
        <FaDollarSign className="h-8 w-8 text-gray-400" />
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-4">
        No Balance Information
      </h3>
      <p className="text-gray-500 mb-10 max-w-sm mx-auto">
        Your rent balance will appear here once it's been calculated.
      </p>
      <div className="flex flex-col sm:flex-row gap-3 justify-center mt-2">
        <button
          onClick={onMakePayment}
          className="bg-brand-teal text-white px-6 py-3 rounded-lg hover:bg-brand-green transition-all duration-200 font-medium shadow-sm hover:shadow-md"
        >
          Make a Payment
        </button>
        <button
          onClick={onSetupAutopay}
          className="border border-gray-300 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-all duration-200 font-medium shadow-sm hover:shadow-md"
        >
          Set Up Autopay
        </button>
      </div>
    </div>
  );

  const BalanceContent = () => (
    <div className="text-center">
      {/* Hero Balance Amount */}
      <div className="mb-12">
        <div className="text-4xl font-bold text-gray-900 mb-4">
          {formatCurrency(currentBalance.amount)}
        </div>
        {currentBalance.dueDate && (
          <div className="flex items-center justify-center space-x-2 text-gray-600 mt-3">
            <FaCalendarAlt className="text-sm" />
            <span className="text-base font-medium">Due on {currentBalance.dueDate}</span>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3 justify-center mt-2">
        <button
          onClick={onMakePayment}
          className="bg-brand-teal text-white px-6 py-3 rounded-lg hover:bg-brand-green transition-all duration-200 font-medium shadow-sm hover:shadow-md"
        >
          Make a Payment
        </button>
        <button
          onClick={onSetupAutopay}
          className="border border-gray-300 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-all duration-200 font-medium shadow-sm hover:shadow-md"
        >
          Set Up Autopay
        </button>
      </div>
    </div>
  );

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
      <h2 className="text-xl font-semibold text-gray-900 mb-8">Current Balance</h2>
      
      {currentBalance ? <BalanceContent /> : <EmptyBalanceState />}
    </div>
  );
};

CurrentBalance.propTypes = {
  currentBalance: PropTypes.shape({
    amount: PropTypes.number.isRequired,
    dueDate: PropTypes.string,
    status: PropTypes.string
  }),
  onMakePayment: PropTypes.func.isRequired,
  onSetupAutopay: PropTypes.func.isRequired,
  formatCurrency: PropTypes.func.isRequired
};

export default CurrentBalance;
