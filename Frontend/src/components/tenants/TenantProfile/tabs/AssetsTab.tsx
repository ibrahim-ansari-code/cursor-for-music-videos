import React from 'react';
import { useOutletContext } from 'react-router-dom';
import { EnrichedTenant } from '../../../../types/tenant';

interface OutletContext {
  tenant: EnrichedTenant;
  refetch: () => void;
}

const AssetsTab: React.FC = () => {
  const context = useOutletContext<OutletContext>();

  // Guard: Handle undefined context gracefully (occurs during refetch or initial load)
  if (!context || !context.tenant) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-blue-200 dark:border-blue-800 border-t-blue-600 dark:border-t-blue-400 rounded-full animate-spin" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading assets...</p>
        </div>
      </div>
    );
  }


  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-12">
      <div className="text-center">
        <div className="mx-auto w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Assets & Inventory
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Tenant assets and property inventory will be available here
        </p>
      </div>
    </div>
  );
};

export default AssetsTab;
