import React from 'react';
import { FaPlus, FaShieldAlt } from 'react-icons/fa';
import PaymentMethodCard from './PaymentMethodCard';
import type { PaymentMethod } from '@/types';

interface PaymentMethodsProps {
  paymentMethods: PaymentMethod[];
  onAddPaymentMethod: () => void;
  onRemovePaymentMethod: (methodId: string) => void;
}

/**
 * PaymentMethods Component
 * Displays saved payment methods or helpful empty state
 */
const PaymentMethods: React.FC<PaymentMethodsProps> = ({ 
  paymentMethods, 
  onAddPaymentMethod, 
  onRemovePaymentMethod 
}) => {
  const EmptyMethodsState: React.FC = () => (
    <div className="text-center py-8">
      <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-gray-100 mb-3">
        <FaShieldAlt className="h-6 w-6 text-gray-400" />
      </div>
      <h3 className="text-base font-medium text-gray-900 mb-2">
        No Payment Methods
      </h3>
      <p className="text-sm text-gray-500 mb-4">
        Add a payment method to make future payments quick and secure
      </p>
    </div>
  );

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Payment Methods</h2>
      </div>
      
      {paymentMethods.length === 0 && <EmptyMethodsState />}
      
      {paymentMethods.length > 0 && (
        <div className="space-y-3 mb-4">
          {paymentMethods.map((method) => (
            <PaymentMethodCard 
              key={method.id} 
              method={method} 
              onRemove={onRemovePaymentMethod}
            />
          ))}
        </div>
      )}

      <button
        onClick={onAddPaymentMethod}
        className="w-full border-2 border-dashed border-gray-300 text-gray-600 hover:border-gray-400 hover:bg-gray-50 transition-all duration-200 rounded-md p-4 flex items-center justify-center space-x-2 cursor-pointer"
      >
        <FaPlus className="text-sm" />
        <span className="font-medium">Add Payment Method</span>
      </button>
    </div>
  );
};

export default PaymentMethods;

