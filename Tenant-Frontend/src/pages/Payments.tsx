import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { 
  CurrentBalance,
  PaymentHistory,
  PaymentMethods
} from '@/components/payments';
import PayRentModal from '@/components/payments/PayRentModal';
import AddPaymentMethodModal from '@/components/payments/AddPaymentMethodModal';
import SetupAutopayModal from '@/components/payments/SetupAutopayModal';
import {
  useTenantBalance,
  usePaymentMethods,
  useRentTransactions,
  useDeletePaymentMethod,
  useAutopayStatus,
} from '@/hooks/usePayments';
import type { PaymentMethod, PaymentHistoryItem } from '@/types';
import type { SavedPaymentMethod } from '@/types/payments';
import { useQueryClient } from '@tanstack/react-query';
import { paymentsKeys } from '@/hooks/usePayments';

/**
 * Payments Component
 * Comprehensive rent and payments management page
 */
const Payments: React.FC = () => {
  const [isPayRentModalOpen, setIsPayRentModalOpen] = useState(false);
  const [isAddPaymentMethodModalOpen, setIsAddPaymentMethodModalOpen] = useState(false);
  const [isSetupAutopayModalOpen, setIsSetupAutopayModalOpen] = useState(false);

  // Fetch data from API
  const { data: balanceData, isLoading: isLoadingBalance } = useTenantBalance();
  const { data: savedPaymentMethods = [], isLoading: isLoadingMethods } = usePaymentMethods();
  const { data: transactions = [], isLoading: isLoadingTransactions } = useRentTransactions();
  const { data: autopayStatusData, isLoading: isLoadingAutopay } = useAutopayStatus(balanceData?.lease_id);
  const deletePaymentMethod = useDeletePaymentMethod();
  const queryClient = useQueryClient();

  const loading = isLoadingBalance || isLoadingMethods || isLoadingTransactions || isLoadingAutopay;
  
  // Auto-refresh transactions if any paid/refunded transactions are missing receipts
  // Stripe generates receipts asynchronously, so we poll until they're available
  useEffect(() => {
    const hasPendingReceipts = transactions.some(
      (txn) => (txn.status === 'succeeded' || txn.status === 'refunded') && !txn.receipt_url
    );

    if (hasPendingReceipts) {
      // Poll every 3 seconds for up to 30 seconds (10 attempts)
      let attempts = 0;
      const maxAttempts = 10;
      
      const pollInterval = setInterval(() => {
        attempts++;
        queryClient.invalidateQueries({ queryKey: paymentsKeys.transactions() });
        
        if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
        }
      }, 3000);

      return () => clearInterval(pollInterval);
    }
  }, [transactions, queryClient]);

  // Transform API data to component format
  const paymentMethods: PaymentMethod[] = savedPaymentMethods.map((method: SavedPaymentMethod) => ({
    id: method.id,
    type: method.payment_method_type === 'acss_debit' ? 'bank' : 'card',
    last4: method.last_four,
    brand: method.brand || undefined,
    bankName: method.bank_name || undefined,
    expiryDate:
      method.exp_month && method.exp_year
        ? `${method.exp_month.toString().padStart(2, '0')}/${method.exp_year.toString().slice(-2)}`
        : undefined,
    expMonth: method.exp_month || undefined,
    expYear: method.exp_year || undefined,
    isDefault: method.is_default,
    isVerified: method.is_verified,
  }));

  const paymentHistory: PaymentHistoryItem[] = transactions.map((transaction) => ({
    id: transaction.id,
    date: format(new Date(transaction.created_at), 'MMM d, yyyy'),
    description: 'Rent Payment',
    paymentMethod:
      transaction.payment_method_type === 'acss_debit'
        ? 'Bank Transfer (PAD)'
        : transaction.payment_method_type === 'card'
        ? 'Credit/Debit Card'
        : 'Online Payment',
    amount: transaction.amount_cents / 100,
    status:
      transaction.status === 'succeeded'
        ? 'Paid'
        : transaction.status === 'refunded'
        ? 'Refunded'
        : transaction.status === 'failed'
        ? 'Failed'
        : 'Pending',
    receiptUrl: transaction.receipt_url || undefined,
  }));

  const handleMakePayment = (): void => {
    setIsPayRentModalOpen(true);
  };

  const handleSetupAutopay = (): void => {
    setIsSetupAutopayModalOpen(true);
  };

  const handleAddPaymentMethod = (): void => {
    setIsAddPaymentMethodModalOpen(true);
  };

  const handleRemovePaymentMethod = (methodId: string): void => {
    if (confirm('Are you sure you want to remove this payment method?')) {
      deletePaymentMethod.mutate(methodId);
    }
  };

  const handleDownloadReceipt = (receiptUrl: string): void => {
    window.open(receiptUrl, '_blank');
  };

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-CA', {
      style: 'currency',
      currency: 'CAD',
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow border border-gray-200">
        <div className="p-6">
          {/* Page Header */}
          <div className="mb-6">
            <h1 className="text-2xl font-semibold text-gray-800">Rent & Payments</h1>
            <p className="text-gray-600">Manage your rent payments and payment methods</p>
          </div>

          <div className="space-y-6">
            {/* Top Grid Loading */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="md:col-span-2 border border-gray-200 rounded-lg p-6 animate-pulse">
                <div className="h-6 bg-gray-200 rounded w-32 mb-4"></div>
                <div className="h-10 bg-gray-200 rounded w-40 mb-4"></div>
                <div className="flex space-x-3">
                  <div className="h-10 bg-gray-200 rounded w-32"></div>
                  <div className="h-10 bg-gray-200 rounded w-32"></div>
                </div>
              </div>
              <div className="border border-gray-200 rounded-lg p-6 animate-pulse">
                <div className="h-6 bg-gray-200 rounded w-40 mb-4"></div>
                <div className="space-y-3">
                  <div className="h-16 bg-gray-200 rounded"></div>
                  <div className="h-16 bg-gray-200 rounded"></div>
                </div>
              </div>
            </div>

            {/* Bottom Full Width Loading */}
            <div className="border border-gray-200 rounded-lg overflow-hidden animate-pulse">
              <div className="h-6 bg-gray-200 rounded w-40 m-6"></div>
              <div className="space-y-3 px-6 pb-6">
                <div className="h-20 bg-gray-200 rounded"></div>
                <div className="h-20 bg-gray-200 rounded"></div>
                <div className="h-20 bg-gray-200 rounded"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="bg-white rounded-lg shadow border border-gray-200">
        <div className="p-6">
          {/* Page Header */}
          <div className="mb-6">
            <h1 className="text-2xl font-semibold text-gray-800">Rent & Payments</h1>
            <p className="text-gray-600">Manage your rent payments and payment methods</p>
          </div>

          <div className="space-y-6">
            {/* Top Row - Current Balance & Payment Methods */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Left - Current Balance (2/3 width) */}
              <div className="md:col-span-2">
                <CurrentBalance
                  balanceData={balanceData || null}
                  autopayStatus={autopayStatusData || null}
                  onMakePayment={handleMakePayment}
                  onSetupAutopay={handleSetupAutopay}
                />
              </div>
              
              {/* Right - Payment Methods (1/3 width) */}
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
              balanceData={balanceData || null}
            />
          </div>
        </div>
      </div>

      {/* Modals */}
      <PayRentModal
        isOpen={isPayRentModalOpen}
        onClose={() => setIsPayRentModalOpen(false)}
        leaseId={balanceData?.lease_id || 0}
        amountDue={balanceData?.current_balance_cents ? balanceData.current_balance_cents / 100 : 0}
        landlordName={balanceData?.landlord_name || 'Landlord'}
        propertyAddress={balanceData?.property_name || 'Property'}
        savedPaymentMethods={savedPaymentMethods}
      />

      <AddPaymentMethodModal
        isOpen={isAddPaymentMethodModalOpen}
        onClose={() => setIsAddPaymentMethodModalOpen(false)}
        onSuccess={() => {
          setIsAddPaymentMethodModalOpen(false);
        }}
      />

      <SetupAutopayModal
        isOpen={isSetupAutopayModalOpen}
        onClose={() => setIsSetupAutopayModalOpen(false)}
        savedPaymentMethods={savedPaymentMethods}
        leaseId={balanceData?.lease_id}
      />
    </>
  );
};

export default Payments;

