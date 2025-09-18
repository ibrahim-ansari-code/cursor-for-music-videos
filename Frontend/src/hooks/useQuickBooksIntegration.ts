import { useState, useCallback, useEffect } from 'react';
import { toast } from 'react-toastify';
import {
  getQuickBooksStatus,
  connectToQuickBooks,
  disconnectQuickBooks,
  initialQuickBooksSync,
  syncQuickBooksPayments,
  syncQuickBooksInvoices,
  syncQuickBooksExpenses,
} from '../utils/api/quickbooks';
import {
  QuickBooksStatus,
  OperationState,
  SyncOperation,
  UseQuickBooksIntegrationReturn,
  QuickBooksSyncResponse,
  QuickBooksConnectResponse
} from '../types/integrations';

export const useQuickBooksIntegration = (): UseQuickBooksIntegrationReturn => {
  const [status, setStatus] = useState<QuickBooksStatus | null>(null);
  const [operationState, setOperationState] = useState<OperationState>({ type: 'idle' });
  const [showConfirmDisconnect, setShowConfirmDisconnect] = useState(false);

  // Utility to check if any operation is in progress
  const isOperationInProgress = operationState.type === 'loading' || operationState.type === 'syncing';

  // Fetch QuickBooks status with error handling
  const refreshStatus = useCallback(async () => {
    try {
      setOperationState({ type: 'loading', operation: 'Fetching status' });
      const fetchedStatus = await getQuickBooksStatus();
      setStatus(fetchedStatus);
      setOperationState({ type: 'idle' });
    } catch (error: any) {
      console.error('Error fetching QuickBooks status:', error);
      const errorMessage = error?.message || 'Failed to load integration status. Please try again.';
      setOperationState({ type: 'error', message: errorMessage });
      toast.error(errorMessage);
    }
  }, []);

  // Generic sync function with proper error handling
  const runSync = useCallback(async (
    apiFunc: () => Promise<QuickBooksSyncResponse>,
    operation: SyncOperation,
    displayName: string
  ) => {
    try {
      setOperationState({ type: 'syncing', operation });
      toast.info(`Starting ${displayName} sync with QuickBooks...`);

      const result = await apiFunc();

      if (result.success) {
        toast.success(result.message);
        // Refresh status after successful sync
        await refreshStatus();
      } else {
        toast.error(result.message || `An unknown error occurred during ${displayName} sync.`);
        setOperationState({ type: 'error', message: result.message || `Failed to sync ${displayName}` });
      }
    } catch (error: any) {
      console.error(`Error syncing ${displayName}:`, error);
      const errorMessage = error?.message || `Failed to sync ${displayName}.`;
      toast.error(errorMessage);
      setOperationState({ type: 'error', message: errorMessage });
    } finally {
      // Only set to idle if we're not in an error state
      setOperationState(prevState =>
        prevState.type === 'error' ? prevState : { type: 'idle' }
      );
    }
  }, [operationState.type, refreshStatus]);

  // Handle initial sync after OAuth redirect
  const handleInitialSync = useCallback(async () => {
    try {
      setOperationState({ type: 'syncing', operation: 'initial' });
      toast.info("Connection successful! Starting initial sync with QuickBooks...");

      const syncResult = await initialQuickBooksSync();
      toast.success(syncResult.message);
      setOperationState({ type: 'idle' });
    } catch (error: any) {
      console.error('Error during initial sync:', error);
      const errorMessage = error.message || "Initial sync failed. Please try again from the settings page.";
      toast.error(errorMessage);
      setOperationState({ type: 'error', message: errorMessage });
    } finally {
      // Always refresh status regardless of sync success/failure
      await refreshStatus();
      // Clean up URL params
      window.history.replaceState({}, document.title, "/integrations");
    }
  }, [refreshStatus]);

  // Connect to QuickBooks
  const handleConnect = useCallback(async () => {
    try {
      setOperationState({ type: 'loading', operation: 'Connecting' });

      const response: QuickBooksConnectResponse = await connectToQuickBooks();

      if (response?.redirect_url) {
        // Announce navigation to screen readers
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'assertive');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = 'Redirecting to QuickBooks for authentication';
        document.body.appendChild(announcement);

        setTimeout(() => {
          document.body.removeChild(announcement);
          window.location.href = response.redirect_url!;
        }, 100);
      } else {
        throw new Error('No redirect URL received from server.');
      }
    } catch (error: any) {
      console.error('Error connecting to QuickBooks:', error);
      const errorMessage = error.message || 'Failed to initiate QuickBooks connection.';
      toast.error(errorMessage);
      setOperationState({ type: 'error', message: errorMessage });
    }
  }, []);

  // Disconnect handlers
  const handleDisconnect = useCallback(() => {
    setShowConfirmDisconnect(true);
  }, []);

  const handleConfirmDisconnect = useCallback(async () => {
    setShowConfirmDisconnect(false);

    try {
      setOperationState({ type: 'loading', operation: 'Disconnecting' });
      await disconnectQuickBooks();
      toast.success('Successfully disconnected from QuickBooks.');
      await refreshStatus();
    } catch (error: any) {
      console.error('Error disconnecting from QuickBooks:', error);
      const errorMessage = error.message || 'Failed to disconnect from QuickBooks.';
      toast.error(errorMessage);
      setOperationState({ type: 'error', message: errorMessage });
    }
  }, [refreshStatus]);

  const handleCancelDisconnect = useCallback(() => {
    setShowConfirmDisconnect(false);
  }, []);

  // Sync handlers
  const handleSyncPayments = useCallback(() =>
    runSync(syncQuickBooksPayments, 'payments', 'payment'),
    [runSync]
  );

  const handleSyncInvoices = useCallback(() =>
    runSync(syncQuickBooksInvoices, 'invoices', 'invoice'),
    [runSync]
  );

  const handleSyncExpenses = useCallback(() =>
    runSync(syncQuickBooksExpenses, 'expenses', 'expense'),
    [runSync]
  );

  // Handle URL parameters for OAuth redirect
  useEffect(() => {
    const queryParams = new URLSearchParams(window.location.search);
    const code = queryParams.get('code');
    const oauthError = queryParams.get('error');
    const errorDescription = queryParams.get('error_description');

    if (code) {
      handleInitialSync();
    } else if (oauthError) {
      toast.error('OAuth authorization failed. Please try again.');
      window.history.replaceState({}, document.title, "/integrations");
    } else if (errorDescription) {
      setOperationState({ type: 'error', message: errorDescription });
      toast.error(errorDescription);
      window.history.replaceState({}, document.title, "/integrations");
    } else {
      // Normal page load - fetch status
      refreshStatus();
    }
  }, [handleInitialSync, refreshStatus]);

  return {
    // State
    status,
    operationState,
    showConfirmDisconnect,

    // Actions
    handleConnect,
    handleDisconnect,
    handleConfirmDisconnect,
    handleCancelDisconnect,
    handleSyncPayments,
    handleSyncInvoices,
    handleSyncExpenses,

    // Utilities
    refreshStatus,
    isOperationInProgress,
  };
};