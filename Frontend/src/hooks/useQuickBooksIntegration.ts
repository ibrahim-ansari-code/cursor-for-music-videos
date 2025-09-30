import { useState, useCallback, useEffect } from 'react';
import { toast } from 'react-toastify';
import {
  getQuickBooksStatus,
  connectToQuickBooks,
  disconnectQuickBooks,
  syncAllQuickBooksData,
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
      toast.error(errorMessage);
      setOperationState({ type: 'idle' });
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

      // Validate result exists and has expected structure
      if (result && typeof result === 'object') {
        if (result.success === true) {
          const message = result.message && typeof result.message === 'string'
            ? result.message
            : `${displayName} sync completed successfully`;
          toast.success(message);
          // Refresh status after successful sync
          await refreshStatus();
        } else {
          const errorMessage = result.message && typeof result.message === 'string'
            ? result.message
            : `An unknown error occurred during ${displayName} sync.`;
          toast.error(errorMessage);
        }
      } else {
        // Handle case where result is undefined or not an object
        toast.success(`${displayName} sync completed`);
        await refreshStatus();
      }
    } catch (error: any) {
      console.error(`Error syncing ${displayName}:`, error);
      const errorMessage = error?.message || `Failed to sync ${displayName}.`;
      toast.error(errorMessage);
    } finally {
      // Only set to idle if we're not in an error state
      setOperationState(prevState =>
        prevState.type === 'error' ? prevState : { type: 'idle' }
      );
    }
  }, [operationState.type, refreshStatus]);

  // Note: Removed handleInitialSync function - initial sync should be triggered manually by user

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
      setOperationState({ type: 'idle' });
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
      setOperationState({ type: 'idle' });
    }
  }, [refreshStatus]);

  const handleCancelDisconnect = useCallback(() => {
    setShowConfirmDisconnect(false);
  }, []);

  // Sync handlers
  const handleSyncAll = useCallback(() =>
    runSync(syncAllQuickBooksData, 'all', 'unified'),
    [runSync]
  );

  // Handle OAuth callback success/error from QuickBooksCallback page
  useEffect(() => {
    const handleOAuthCallback = async () => {
      console.log('Integration page loaded, checking for OAuth status...');

      // Check for OAuth errors from callback page
      const storedError = sessionStorage.getItem('qb_oauth_error');
      if (storedError) {
        try {
          const { error, errorDescription } = JSON.parse(storedError);
          console.log('OAuth error from callback:', { error, errorDescription });
          toast.error(`QuickBooks authorization failed: ${errorDescription || error || 'Unknown error'}`);
          sessionStorage.removeItem('qb_oauth_error');
          refreshStatus(); // Refresh to show current status
          return;
        } catch (e) {
          console.error('Error parsing stored OAuth error:', e);
          sessionStorage.removeItem('qb_oauth_error');
        }
      }

      // Check for OAuth success from callback page
      const storedSuccess = sessionStorage.getItem('qb_oauth_success');
      if (storedSuccess) {
        try {
          const successData = JSON.parse(storedSuccess);
          console.log('OAuth success from callback:', successData);
          toast.success(`Successfully connected to QuickBooks${successData.company_name ? ` (${successData.company_name})` : ''}!`);
          sessionStorage.removeItem('qb_oauth_success');

          // Refresh status to show connected state (no automatic sync)
          await refreshStatus();
          return;
        } catch (e) {
          console.error('Error parsing stored OAuth success:', e);
          sessionStorage.removeItem('qb_oauth_success');
        }
      }

      // Normal page load - fetch status
      refreshStatus();
    };

    handleOAuthCallback();
  }, [refreshStatus]);

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
    handleSyncAll,

    // Utilities
    refreshStatus,
    isOperationInProgress,
  };
};