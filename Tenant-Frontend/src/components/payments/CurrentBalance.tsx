import React from 'react';
import { FaDollarSign, FaExclamationTriangle, FaHome, FaCheckCircle } from 'react-icons/fa';
import type { TenantBalance, AutopayStatus } from '@/types/payments';

interface CurrentBalanceProps {
  balanceData: TenantBalance | null;
  autopayStatus: AutopayStatus | null;
  onMakePayment: () => void;
  onSetupAutopay: () => void;
}

/**
 * CurrentBalance Component
 * Displays current balance with property context and action buttons
 */
const CurrentBalance: React.FC<CurrentBalanceProps> = ({ 
  balanceData,
  autopayStatus,
  onMakePayment, 
  onSetupAutopay,
}) => {
  const formatCurrency = (amountCents: number): string => {
    return new Intl.NumberFormat('en-CA', {
      style: 'currency',
      currency: 'CAD',
    }).format(amountCents / 100);
  };

  const isOverdue = (): boolean => {
    // Only show overdue if BOTH conditions are true:
    // 1. Past the due date
    // 2. Balance is greater than $0
    if (!balanceData?.due_date) return false;
    const hasPastDue = new Date(balanceData.due_date) < new Date();
    const hasBalance = balanceData.current_balance_cents > 0;
    return hasPastDue && hasBalance;
  };

  const getStatusBadge = () => {
    if (!balanceData) return null;
    
    // Show "Paid" badge if balance is $0
    if (balanceData.current_balance_cents === 0) {
      return (
        <div className="inline-flex items-center px-3 py-1 rounded-full bg-green-100 text-green-800 text-sm font-medium">
          ✓ Paid
        </div>
      );
    }
    
    // Show "Overdue" badge if past due date with outstanding balance
    const overdue = isOverdue();
    if (overdue) {
      return (
        <div className="inline-flex items-center px-3 py-1 rounded-full bg-red-100 text-red-800 text-sm font-medium">
          <FaExclamationTriangle className="mr-1.5 text-xs" />
          Overdue
        </div>
      );
    }
    
    return null;
  };
  const EmptyBalanceState: React.FC = () => (
    <div className="text-center py-8">
      <div className="mx-auto flex items-center justify-center h-14 w-14 rounded-full bg-gray-100 mb-4">
        <FaDollarSign className="h-7 w-7 text-gray-400" />
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-2">
        No Balance Information
      </h3>
      <p className="text-sm text-gray-500 max-w-sm mx-auto">
        Your rent balance will appear here once your lease is active and rent is calculated.
      </p>
    </div>
  );

  const BalanceContent: React.FC = () => {
    const formatDate = (dateString: string) => {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-CA', { 
        month: 'long', 
        day: 'numeric', 
        year: 'numeric' 
      });
    };

    return (
      <div>
        {/* Property Context */}
        <div className="bg-gray-50 rounded-lg p-3 mb-6 flex items-start">
          <FaHome className="text-gray-400 mt-0.5 mr-2.5 shrink-0" />
          <div className="text-left">
            <p className="text-sm font-medium text-gray-900">{balanceData!.property_name}</p>
            <p className="text-xs text-gray-600 mt-0.5">Landlord: {balanceData!.landlord_name}</p>
          </div>
        </div>

        {/* Balance Amount and Due Date */}
        <div className="mb-6">
          <div className="flex items-start justify-between">
            <div className="flex items-baseline">
              <span className="text-3xl font-bold text-gray-900">
                {formatCurrency(balanceData!.current_balance_cents)}
              </span>
              {balanceData!.due_date && (
                <span className="ml-2 text-sm text-gray-500">
                  due on {formatDate(balanceData!.due_date)}
                </span>
              )}
            </div>
            {/* Badges on the right side */}
            <div className="flex items-center gap-2">
              {/* Autopay Badge (if active) */}
              {autopayStatus?.is_enrolled && autopayStatus?.is_active && (
                <div className="inline-flex items-center px-3 py-1 rounded-full bg-blue-100 text-blue-800 text-sm font-medium">
                  <FaCheckCircle className="mr-1.5 text-xs" />
                  Autopay Active
                </div>
              )}
              
              {/* Status Badge (Overdue/Paid) */}
              {getStatusBadge()}
            </div>
          </div>
      </div>

      {/* Action Buttons */}
        <div className="flex items-center space-x-3">
        <button
          onClick={onMakePayment}
          disabled={balanceData!.current_balance_cents === 0}
          className={`px-4 py-2 rounded-md font-medium transition-all duration-200 ${
            balanceData!.current_balance_cents === 0
              ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
              : 'bg-gray-900 text-white hover:bg-gray-800 cursor-pointer'
          }`}
          title={balanceData!.current_balance_cents === 0 ? 'No payment due' : 'Make a payment'}
        >
          {balanceData!.current_balance_cents === 0 ? 'No Payment Due' : 'Make a Payment'}
        </button>
        <button
          onClick={onSetupAutopay}
          className="border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 hover:border-gray-400 transition-all duration-200 font-medium cursor-pointer"
        >
          {autopayStatus?.is_enrolled && autopayStatus?.is_active ? 'Manage Autopay' : 'Set Up Autopay'}
        </button>
      </div>
    </div>
  );
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Current Balance</h2>
      
      {balanceData ? <BalanceContent /> : <EmptyBalanceState />}
    </div>
  );
};

export default CurrentBalance;

