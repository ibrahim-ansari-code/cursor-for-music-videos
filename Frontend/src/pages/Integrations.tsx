import React, { memo } from 'react';
import * as Sentry from '@sentry/react';
import IntegrationsSkeleton from '../components/ui/skeletons/IntegrationsSkeleton';
import ErrorMessage from '../components/integrations/ErrorMessage';
import QuickBooksCard from '../components/integrations/QuickBooksCard';
import PlaceholderCard from '../components/integrations/PlaceholderCard';
import ConfirmationModal from '../components/integrations/ConfirmationModal';
import { useQuickBooksIntegration } from '../hooks/useQuickBooksIntegration';

/**
 * Integrations page component - fully optimized TypeScript version
 *
 * Key optimizations:
 * - Separated business logic into custom hooks
 * - Memoized sub-components to prevent unnecessary re-renders
 * - Consolidated loading states using discriminated unions
 * - Added comprehensive TypeScript types
 * - Improved error handling with Sentry integration
 * - QuickBooks functionality temporarily disabled for production key finalization
 */
const Integrations: React.FC = memo(() => {
  const {
    status,
    operationState,
    showConfirmDisconnect,
    handleConnect,
    handleDisconnect,
    handleConfirmDisconnect,
    handleCancelDisconnect,
    handleSyncPayments,
    handleSyncInvoices,
    handleSyncExpenses,
    refreshStatus,
    isOperationInProgress,
  } = useQuickBooksIntegration();

  // Show loading skeleton while handling URL params or during operations
  const isLoading = operationState.type === 'loading';
  const isSyncing = operationState.type === 'syncing';

  if (isLoading || isSyncing) {
    return (
      <Sentry.ErrorBoundary
        fallback={({ error, resetError }) => (
          <div className="p-4 text-center">
            <h2 className="text-xl font-semibold text-red-600 mb-2">
              Something went wrong loading integrations
            </h2>
            <p className="text-gray-600 mb-4">{error instanceof Error ? error.message : 'An unexpected error occurred'}</p>
            <button
              onClick={resetError}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Try again
            </button>
          </div>
        )}
        beforeCapture={(scope) => {
          scope.setTag('component', 'Integrations');
          scope.setTag('page', 'integrations');
        }}
      >
        <IntegrationsSkeleton showPlaceholder={!isSyncing} />
      </Sentry.ErrorBoundary>
    );
  }

  return (
    <Sentry.ErrorBoundary
      fallback={({ error, resetError }) => (
        <div className="p-4 text-center">
          <h2 className="text-xl font-semibold text-red-600 mb-2">
            Something went wrong loading integrations
          </h2>
          <p className="text-gray-600 mb-4">{error instanceof Error ? error.message : 'An unexpected error occurred'}</p>
          <button
            onClick={resetError}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Try again
          </button>
        </div>
      )}
      beforeCapture={(scope) => {
        scope.setTag('component', 'Integrations');
        scope.setTag('page', 'integrations');
        scope.setContext('integrationState', {
          quickBooksConnected: status?.connected || false,
          operationType: operationState.type,
          hasError: operationState.type === 'error',
        });
      }}
    >
      <main className="p-4 sm:p-6 lg:p-8 dark-bg min-h-screen" role="main">
        <div className="max-w-5xl mx-auto">
          <header className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Manage Integrations</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Connect your Brikli account to other services to streamline your workflows.
            </p>
          </header>

          <div role="region" aria-label="Integration status and actions">
            {/* Error Message */}
            {operationState.type === 'error' && (
              <ErrorMessage
                error={operationState.message}
                onRetry={refreshStatus}
              />
            )}

            {/* QuickBooks Integration Card - Temporarily Disabled */}
            <QuickBooksCard
              status={status}
              operationState={operationState}
              onConnect={handleConnect}
              onDisconnect={handleDisconnect}
              onSyncPayments={handleSyncPayments}
              onSyncInvoices={handleSyncInvoices}
              onSyncExpenses={handleSyncExpenses}
              disabled={true} // Temporarily disabled for production key finalization
            />

            {/* Placeholder for Future Integrations */}
            <PlaceholderCard />
          </div>

          {/* Confirmation Modal for Disconnect */}
          <ConfirmationModal
            isOpen={showConfirmDisconnect}
            onClose={handleCancelDisconnect}
            onConfirm={handleConfirmDisconnect}
            title="Disconnect from QuickBooks"
            message="Are you sure you want to disconnect from QuickBooks? This will stop syncing your accounting data and you'll need to reconnect to resume synchronization."
            confirmText="Disconnect"
            cancelText="Cancel"
            variant="danger"
            isLoading={isOperationInProgress}
          />
        </div>
      </main>
    </Sentry.ErrorBoundary>
  );
});

Integrations.displayName = 'Integrations';

export default Integrations;