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
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Payment Methods</h2>
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
        className="w-full border-2 border-dashed border-gray-300 text-gray-600 hover:border-brand-teal hover:text-brand-teal hover:bg-brand-teal hover:bg-opacity-5 transition-all duration-200 rounded-lg p-4 flex items-center justify-center space-x-2 group shadow-sm hover:shadow-md"
      >
        <FaPlus className="text-sm group-hover:text-brand-teal transition-colors" />
        <span className="font-medium">Add Payment Method</span>
      </button>
    </div>
  );
};

export default PaymentMethods;

