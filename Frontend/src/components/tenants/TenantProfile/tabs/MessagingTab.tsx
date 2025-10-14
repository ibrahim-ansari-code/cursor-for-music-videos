import React from 'react';
import { useOutletContext } from 'react-router-dom';
import { EnrichedTenant } from '../../../../types/tenant';

interface OutletContext {
  tenant: EnrichedTenant;
  refetch: () => void;
}

const MessagingTab: React.FC = () => {
  const context = useOutletContext<OutletContext>();

  // Guard: Handle undefined context gracefully (occurs during refetch or initial load)
  if (!context || !context.tenant) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-blue-200 dark:border-blue-800 border-t-blue-600 dark:border-t-blue-400 rounded-full animate-spin" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading messages...</p>
        </div>
      </div>
    );
  }


  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-12">
      <div className="text-center">
        <div className="mx-auto w-16 h-16 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Messaging
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Communication history and messaging will be available here
        </p>
      </div>
    </div>
  );
};

export default MessagingTab;
