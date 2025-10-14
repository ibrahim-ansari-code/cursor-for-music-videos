import React from 'react';
import { useOutletContext } from 'react-router-dom';
import { EnrichedTenant } from '../../../../types/tenant';

interface OutletContext {
  tenant: EnrichedTenant;
  refetch: () => void;
}

const BackgroundTab: React.FC = () => {
  const context = useOutletContext<OutletContext>();

  // Guard: Handle undefined context gracefully (occurs during refetch or initial load)
  if (!context || !context.tenant) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-blue-200 dark:border-blue-800 border-t-blue-600 dark:border-t-blue-400 rounded-full animate-spin" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading background...</p>
        </div>
      </div>
    );
  }


  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-12">
      <div className="text-center">
        <div className="mx-auto w-16 h-16 bg-indigo-100 dark:bg-indigo-900/30 rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Background Checks
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Background check information and screening results will be available here
        </p>
      </div>
    </div>
  );
};

export default BackgroundTab;
