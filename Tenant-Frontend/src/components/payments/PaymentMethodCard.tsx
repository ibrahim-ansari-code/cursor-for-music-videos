import React from 'react';
import { FaCreditCard, FaUniversity, FaTrash, FaCheckCircle } from 'react-icons/fa';
import type { PaymentMethod } from '@/types';

interface PaymentMethodCardProps {
  method: PaymentMethod;
  onRemove: (methodId: string) => void;
}

/**
 * PaymentMethodCard Component
 * Displays a single payment method (card or bank account) with remove functionality
 */
const PaymentMethodCard: React.FC<PaymentMethodCardProps> = ({ method, onRemove }) => {
  return (
    <div className="bg-white border border-gray-200 rounded-md p-3 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <div className="shrink-0">
          {method.type === 'card' ? (
            <FaCreditCard className="text-lg text-gray-600" />
          ) : (
            <FaUniversity className="text-lg text-gray-600" />
          )}
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-900 text-sm">
            {method.type === 'card' 
                ? `${method.brand ? method.brand.charAt(0).toUpperCase() + method.brand.slice(1) : 'Card'} ending in ${method.last4}`
                : `Bank Account (****${method.last4})`
            }
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
            {method.type === 'card' ? (
              method.expiryDate && <span>Expires {method.expiryDate}</span>
            ) : (
              <>
                {method.isVerified ? (
                  <span className="flex items-center text-green-600">
                    <FaCheckCircle className="mr-1 text-[10px]" />
                    Verified
                  </span>
                ) : (
                  <span className="text-yellow-600">Pending verification</span>
                )}
                {method.bankName && <span>{method.bankName}</span>}
              </>
            )}
          </div>
        </div>
      </div>
      <button
        onClick={() => onRemove(method.id)}
        className="text-gray-400 hover:text-red-600 transition-colors p-1 cursor-pointer"
        aria-label="Remove payment method"
      >
        <FaTrash className="text-xs" />
      </button>
    </div>
  );
};

export default PaymentMethodCard;

