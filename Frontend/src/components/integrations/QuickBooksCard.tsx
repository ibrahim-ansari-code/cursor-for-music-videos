import React, { memo, useMemo } from 'react';
import { QuickBooksCardProps } from '../../types/integrations';

const QuickBooksCard: React.FC<QuickBooksCardProps> = memo(({
  status,
  operationState,
  onConnect,
  onDisconnect,
  onSyncPayments,
  onSyncInvoices,
  onSyncExpenses,
  disabled = false
}) => {
  const isConnected = status?.connected ?? false;
  const isLoading = operationState.type === 'loading';
  const isSyncing = operationState.type === 'syncing';
  const isAnyOperationInProgress = isLoading || isSyncing;

  // Generate unique IDs for accessibility
  const connectionStatusId = useMemo(() => `quickbooks-status-${Math.random().toString(36).substring(2, 9)}`, []);
  const connectionDateId = useMemo(() => `quickbooks-date-${Math.random().toString(36).substring(2, 9)}`, []);

  // Determine loading state text based on operation
  const getLoadingText = (): string => {
    if (operationState.type === 'loading') {
      return operationState.operation ? `${operationState.operation}...` : 'Loading...';
    }
    if (operationState.type === 'syncing') {
      switch (operationState.operation) {
        case 'payments': return 'Syncing Payments...';
        case 'invoices': return 'Syncing Invoices...';
        case 'expenses': return 'Syncing Expenses...';
        case 'initial': return 'Initial Sync...';
        default: return 'Syncing...';
      }
    }
    return '';
  };

  // If disabled (coming soon mode), show different UI
  if (disabled) {
    return (
      <article
        className="dark-panel dark-shadow rounded-lg dark-divider border mb-6 overflow-hidden"
        aria-labelledby="quickbooks-heading"
        aria-describedby="quickbooks-description"
      >
        <div className="p-6 flex items-center justify-between">
          <div className="flex items-center space-x-6">
             <img
               src="/Intuit_QuickBooks_logo.svg"
               alt="Intuit QuickBooks integration logo"
               loading="lazy"
               className="h-8 dark:invert dark:hue-rotate-180"
               role="img"
             />
            <div>
              <h3 id="quickbooks-heading" className="text-lg font-semibold text-gray-800 dark:text-gray-100">
                Intuit QuickBooks
              </h3>
              <p id="quickbooks-description" className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                Sync payments, expenses and invoices with QuickBooks
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-6">
            <div className="min-w-[120px] flex justify-center">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200">
                <i className="fas fa-clock mr-2" aria-hidden="true" />
                Coming Soon
              </span>
            </div>
            <div>
              <button
                type="button"
                disabled
                className="inline-flex items-center justify-center px-4 py-2 dark-divider border text-sm font-medium rounded-md text-gray-500 dark:text-gray-400 dark-input cursor-not-allowed"
              >
                <i className="fas fa-tools mr-2" aria-hidden="true" />
                In Development
              </button>
            </div>
          </div>
        </div>
      </article>
    );
  }

  return (
    <article
      className="dark-panel dark-shadow rounded-lg dark-divider border mb-6 overflow-hidden"
      aria-labelledby="quickbooks-heading"
      aria-describedby={`quickbooks-description ${connectionStatusId} ${isConnected && status?.connected_at ? connectionDateId : ''}`}
    >
      <div className="p-6 flex items-center justify-between">
        <div className="flex items-center space-x-6">
           <img
             src="/Intuit_QuickBooks_logo.svg"
             alt="Intuit QuickBooks integration logo"
             loading="lazy"
             className="h-8"
             role="img"
           />
          <div>
            <h3 id="quickbooks-heading" className="text-lg font-semibold text-gray-800 dark:text-gray-100">
              Intuit QuickBooks
            </h3>
            <p id="quickbooks-description" className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Sync payments, expenses and invoices with QuickBooks
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-6">
          <div className="min-w-[120px]">
            {isConnected ? (
              <div className="flex flex-col items-center">
                <span
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200"
                  role="status"
                  aria-label="QuickBooks integration status"
                  id={connectionStatusId}
                >
                  <i className="fas fa-check-circle mr-2" aria-hidden="true" />
                  Connected
                </span>
                {status?.connected_at && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 text-center" id={connectionDateId}>
                    <span className="sr-only">Connected on: </span>
                    On: {new Date(status.connected_at).toLocaleDateString()}
                  </p>
                )}
              </div>
            ) : (
              <div className="flex justify-center">
                <span
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 dark:bg-gray-900/30 text-gray-800 dark:text-gray-200"
                  role="status"
                  aria-label="QuickBooks integration status"
                  id={connectionStatusId}
                >
                  <i className="fas fa-times-circle mr-2" aria-hidden="true" />
                  Not Connected
                </span>
              </div>
            )}
          </div>

          <div>
            {isConnected ? (
              <div className="flex items-center space-x-3">
                <button
                  type="button"
                  onClick={onSyncPayments}
                  disabled={isAnyOperationInProgress}
                  className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 transition-colors"
                >
                  {operationState.type === 'syncing' && operationState.operation === 'payments' ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2" />
                      Syncing...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-sync-alt mr-2" />
                      Sync Payments
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={onSyncInvoices}
                  disabled={isAnyOperationInProgress}
                  className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
                >
                  {operationState.type === 'syncing' && operationState.operation === 'invoices' ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2" />
                      Syncing...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-file-invoice mr-2" />
                      Sync Invoices
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={onSyncExpenses}
                  disabled={isAnyOperationInProgress}
                  className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 transition-colors"
                >
                  {operationState.type === 'syncing' && operationState.operation === 'expenses' ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2" />
                      Syncing...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-receipt mr-2" />
                      Sync Expenses
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={onDisconnect}
                  disabled={isAnyOperationInProgress}
                  className="inline-flex items-center justify-center px-4 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  aria-describedby={connectionStatusId}
                  aria-label={isLoading ? "Disconnecting from QuickBooks" : "Disconnect from QuickBooks integration"}
                >
                  {isLoading ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2" aria-hidden="true" />
                      <span>Disconnecting...</span>
                      <span className="sr-only">Please wait</span>
                    </>
                  ) : (
                    'Disconnect'
                  )}
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={onConnect}
                disabled={isAnyOperationInProgress}
                className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                aria-describedby={connectionStatusId}
                aria-label={isLoading ? "Connecting to QuickBooks" : "Connect to QuickBooks integration"}
              >
                {isLoading ? (
                  <>
                    <i className="fas fa-spinner fa-spin mr-2" aria-hidden="true" />
                    <span>{getLoadingText()}</span>
                    <span className="sr-only">Please wait</span>
                  </>
                ) : (
                  <>
                    <i className="fas fa-plug mr-2" aria-hidden="true" />
                    Connect
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </article>
  );
});

QuickBooksCard.displayName = 'QuickBooksCard';

export default QuickBooksCard;