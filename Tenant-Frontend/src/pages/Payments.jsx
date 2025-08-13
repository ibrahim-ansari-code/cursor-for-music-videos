import React, { useState, useEffect } from 'react';
import { 
  CurrentBalance,
  PaymentHistory,
  PaymentMethods
} from '../components/payments';

/**
 * Payments Component
 * Comprehensive rent and payments management page
 */
const Payments = () => {
  const [loading, setLoading] = useState(true);
  const [currentBalance, _setCurrentBalance] = useState(null);
  const [paymentMethods, _setPaymentMethods] = useState([]);
  const [paymentHistory, _setPaymentHistory] = useState([]);

  // Load payment data from API
  useEffect(() => {
    const loadPaymentData = async () => {
      try {
        // TODO: Implement actual API calls to load:
        // - Current balance and due date
        // - User's saved payment methods
        // - Payment history
        
        // Simulate loading delay
        await new Promise(resolve => setTimeout(resolve, 300));
        
        setLoading(false);
      } catch (error) {
        console.error('Error loading payment data:', error);
        setLoading(false);
      }
    };

    loadPaymentData();
  }, []);

  const handleMakePayment = () => {
    // TODO: Implement payment flow
    console.log('Make payment clicked');
  };

  const handleSetupAutopay = () => {
    // TODO: Implement autopay setup
    console.log('Setup autopay clicked');
  };

  const handleAddPaymentMethod = () => {
    // TODO: Implement add payment method
    console.log('Add payment method clicked');
  };

  const handleRemovePaymentMethod = (methodId) => {
    // TODO: Implement remove payment method
    console.log('Remove payment method:', methodId);
  };

  const handleDownloadReceipt = (receiptUrl) => {
    // TODO: Implement receipt download
    console.log('Download receipt:', receiptUrl);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        {/* Top Grid Loading */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-32 mb-4"></div>
            <div className="h-10 bg-gray-200 rounded w-40 mb-4"></div>
            <div className="flex space-x-3">
              <div className="h-10 bg-gray-200 rounded w-32"></div>
              <div className="h-10 bg-gray-200 rounded w-32"></div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-40 mb-4"></div>
            <div className="space-y-3">
              <div className="h-16 bg-gray-200 rounded"></div>
              <div className="h-16 bg-gray-200 rounded"></div>
              <div className="h-12 bg-gray-200 rounded border-2 border-dashed"></div>
            </div>
          </div>
        </div>

        {/* Bottom Full Width Loading */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-40 mb-4"></div>
          <div className="space-y-3">
            <div className="h-20 bg-gray-200 rounded"></div>
            <div className="h-20 bg-gray-200 rounded"></div>
            <div className="h-20 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Row - Current Balance & Payment Methods */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left - Current Balance */}
        <CurrentBalance
          currentBalance={currentBalance}
          onMakePayment={handleMakePayment}
          onSetupAutopay={handleSetupAutopay}
          formatCurrency={formatCurrency}
        />
        
        {/* Right - Payment Methods */}
        <PaymentMethods
          paymentMethods={paymentMethods}
          onAddPaymentMethod={handleAddPaymentMethod}
          onRemovePaymentMethod={handleRemovePaymentMethod}
        />
      </div>

      {/* Bottom Row - Payment History (Full Width) */}
      <PaymentHistory
        paymentHistory={paymentHistory}
        onDownloadReceipt={handleDownloadReceipt}
        formatCurrency={formatCurrency}
        onMakePayment={handleMakePayment}
      />
    </div>
  );
};

export default Payments;