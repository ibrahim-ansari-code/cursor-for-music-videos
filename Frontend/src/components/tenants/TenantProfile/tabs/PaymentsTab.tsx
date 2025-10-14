import React from 'react';
import { useOutletContext } from 'react-router-dom';
import { EnrichedTenant } from '../../../../types/tenant';

interface OutletContext {
  tenant: EnrichedTenant;
  refetch: () => void;
}

const PaymentsTab: React.FC = () => {
  const { tenant } = useOutletContext<OutletContext>();

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-12">
      <div className="text-center">
        <div className="mx-auto w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Payments & Invoices
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Payment history and invoice management will be available here
        </p>
      </div>
    </div>
  );
};

export default PaymentsTab;
