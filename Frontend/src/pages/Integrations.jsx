import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { toast } from 'react-toastify';
import {
  connectToQuickBooks,
  getQuickBooksStatus,
  disconnectQuickBooks,
  initialQuickBooksSync,
  syncQuickBooksPayments,
  syncQuickBooksInvoices,
  syncQuickBooksExpenses,
} from '../utils/api';
import { ModalShell, Button } from '../components/ui/SharedModalComponents';
import LoadingSpinner from '../components/LoadingSpinner';

// --- Reusable Components (Tailored to Brikli's Style) ---

const ErrorMessage = ({ error, onRetry }) => {
  if (!error) return null;
  return (
    <div 
      className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-md mb-6"
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-center">
        <i className="fas fa-exclamation-circle mr-3 text-red-500" aria-hidden="true"></i>
        <span className="flex-grow" id="error-message">{error}</span>
        <button 
          type="button" 
          onClick={onRetry} 
          className="ml-4 bg-red-600 hover:bg-red-700 focus:bg-red-700 text-white font-bold py-1 px-3 rounded text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          aria-describedby="error-message"
          aria-label="Retry loading integrations"
        >
          Retry
        </button>
      </div>
    </div>
  );
};

const QuickBooksCard = ({ status, actionLoading, onConnect, onDisconnect, onSyncPayments, onSyncInvoices, onSyncExpenses, paymentsLoading, invoicesLoading, expensesLoading }) => {
  const isConnected = status?.connected;
  const connectionStatusId = `quickbooks-status-${Date.now()}`;
  const connectionDateId = `quickbooks-date-${Date.now()}`;

  return (
    <article 
      className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6 overflow-hidden"
      aria-labelledby="quickbooks-heading"
      aria-describedby={`quickbooks-description ${connectionStatusId} ${isConnected && status.connected_at ? connectionDateId : ''}`}
    >
      <div className="p-6 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <img 
            src="/QuickBooksLogo.jpg" 
            alt="QuickBooks Online integration logo" 
            loading="lazy" 
            className="w-14 h-14 rounded-lg"
            role="img"
          />
          <div>
            <h3 id="quickbooks-heading" className="text-lg font-semibold text-gray-800">
              QuickBooks Online
            </h3>
            <p id="quickbooks-description" className="text-xs text-gray-500 mt-0.5">
              Sync payments, expenses and invoices with QuickBooks
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-6">
          <div className="min-w-[120px]">
            {isConnected ? (
              <div className="flex flex-col items-center">
                <span 
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800"
                  role="status"
                  aria-label="QuickBooks integration status"
                  id={connectionStatusId}
                >
                  <i className="fas fa-check-circle mr-2" aria-hidden="true"></i>
                  Connected
                </span>
                {status.connected_at && (
                  <p className="text-xs text-gray-500 mt-1 text-center" id={connectionDateId}>
                    <span className="sr-only">Connected on: </span>
                    On: {new Date(status.connected_at).toLocaleDateString()}
                  </p>
                )}
              </div>
            ) : (
              <div className="flex justify-center">
                <span 
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800"
                  role="status"
                  aria-label="QuickBooks integration status"
                  id={connectionStatusId}
                >
                  <i className="fas fa-times-circle mr-2" aria-hidden="true"></i>
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
                  disabled={actionLoading || paymentsLoading}
                  className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 transition-colors"
                >
                  <i className="fas fa-sync-alt mr-2"></i> Sync Payments
                </button>
                <button
                  type="button"
                  onClick={onSyncInvoices}
                  disabled={actionLoading || invoicesLoading}
                  className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
                >
                  <i className="fas fa-file-invoice mr-2"></i> Sync Invoices
                </button>
                <button
                  type="button"
                  onClick={onSyncExpenses}
                  disabled={actionLoading || expensesLoading}
                  className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                >
                  <i className="fas fa-receipt mr-2"></i> Sync Expenses
                </button>
                <button
                  type="button"
                  onClick={onDisconnect}
                  disabled={actionLoading || paymentsLoading || invoicesLoading || expensesLoading}
                  className="inline-flex items-center justify-center px-4 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  aria-describedby={connectionStatusId}
                  aria-label={actionLoading ? "Disconnecting from QuickBooks" : "Disconnect from QuickBooks integration"}
                >
                  {actionLoading ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2" aria-hidden="true"></i>
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
                disabled={actionLoading}
                className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                aria-describedby={connectionStatusId}
                aria-label={actionLoading ? "Connecting to QuickBooks" : "Connect to QuickBooks integration"}
              >
                {actionLoading ? (
                  <>
                    <i className="fas fa-spinner fa-spin mr-2" aria-hidden="true"></i>
                    <span>Connecting...</span>
                    <span className="sr-only">Please wait</span>
                  </>
                ) : (
                  <>
                    <i className="fas fa-plug mr-2" aria-hidden="true"></i>
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
};

const PlaceholderCard = () => (
  <section 
    className="bg-white rounded-lg border-2 border-dashed border-gray-300" 
    role="region" 
    aria-labelledby="upcoming-integrations-heading"
  >
    <div className="p-12 text-center">
      <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center mx-auto mb-4">
        <i className="fas fa-puzzle-piece text-3xl text-gray-400" aria-hidden="true"></i>
      </div>
      <h3 id="upcoming-integrations-heading" className="text-lg font-medium text-gray-800 mb-2">
        More Integrations Coming Soon
      </h3>
      <p className="text-gray-500 max-w-md mx-auto">
        We're working on adding more integrations to help streamline your workflow.
      </p>
    </div>
  </section>
);

const ConfirmationModal = ({ isOpen, onClose, onConfirm, title, message, confirmText = "Confirm", cancelText = "Cancel", variant = "danger" }) => {
  if (!isOpen) return null;

  const footerContent = (
    <>
      <Button
        type="button"
        variant="secondary"
        onClick={onClose}
        aria-label={cancelText}
      >
        {cancelText}
      </Button>
      <Button
        type="button"
        variant={variant}
        onClick={onConfirm}
        aria-label={confirmText}
      >
        {confirmText}
      </Button>
    </>
  );

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      footerContent={footerContent}
      maxWidth="max-w-md"
    >
      <div className="py-4">
        <p className="text-gray-700 leading-relaxed">
          {message}
        </p>
      </div>
    </ModalShell>
  );
};

ConfirmationModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onConfirm: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
  message: PropTypes.string.isRequired,
  confirmText: PropTypes.string,
  cancelText: PropTypes.string,
  variant: PropTypes.oneOf(['danger', 'primary', 'secondary']),
};

// --- Main Page Component ---
const Integrations = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quickBooksStatus, setQuickBooksStatus] = useState({ connected: false });
  const [paymentsLoading, setPaymentsLoading] = useState(false);
  const [invoicesLoading, setInvoicesLoading] = useState(false);
  const [expensesLoading, setExpensesLoading] = useState(false);
  const [showConfirmDisconnect, setShowConfirmDisconnect] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  useEffect(() => {
    // Check for a redirect from Apideck and trigger initial sync
    const queryParams = new URLSearchParams(window.location.search);
    const code = queryParams.get('code');
    const oauthError = queryParams.get('error');
    
    if (code) {
        handleInitialSync();
    } else if (oauthError) {
        toast.error('OAuth authorization failed. Please try again.');
        // Clean up URL params
        window.history.replaceState({}, document.title, "/integrations");
    } else if (queryParams.has('error_description')) {
        const oauthErrorDescription = queryParams.get('error_description');
        setError(oauthErrorDescription);
        toast.error(oauthErrorDescription);
        // Clean up URL params
        window.history.replaceState({}, document.title, "/integrations");
     } else {
         fetchQuickBooksStatus();
     }
  }, []);

  const fetchQuickBooksStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const status = await getQuickBooksStatus();
      setQuickBooksStatus(status);
    } catch (err) {
      setError('Failed to load integration status. Please try again.');
      console.error('Error fetching QuickBooks status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleInitialSync = async () => {
    setIsSyncing(true);
    toast.info("Connection successful! Starting initial sync with QuickBooks...");
    try {
        const syncResult = await initialQuickBooksSync();
        toast.success(syncResult.message);
    } catch (err) {
        const errorMessage = err.message || "Initial sync failed. Please try again from the settings page.";
        setError(errorMessage);
        toast.error(errorMessage);
        console.error('Error during initial sync:', err);
    } finally {
        setIsSyncing(false);
        // Always refresh status regardless of sync success/failure
        fetchQuickBooksStatus();
        // Clean up URL params
        window.history.replaceState({}, document.title, "/integrations");
    }
  };

  const handleConnect = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await connectToQuickBooks();
      if (response?.redirect_url) {
        // Announce navigation to screen readers
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'assertive');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = 'Redirecting to QuickBooks for authentication';
        document.body.appendChild(announcement);
        
        setTimeout(() => {
          window.location.href = response.redirect_url;
        }, 100);
      } else {
        throw new Error('No redirect URL received from server.');
      }
    } catch (err) {
      const errorMessage = err.message || 'Failed to initiate QuickBooks connection.';
      setError(errorMessage);
      toast.error(errorMessage);
      console.error('Error connecting to QuickBooks:', err);
    } finally {
      setLoading(false);
    }
  };

  const runSync = async (apiFunc, displayName, setLoadingState) => {
    setLoadingState(true);
    toast.info(`Starting ${displayName} sync with QuickBooks...`);
    try {
      const result = await apiFunc();
      if (result.success) {
        toast.success(result.message);
        await fetchQuickBooksStatus();
      } else {
        toast.error(result.message || `An unknown error occurred during ${displayName} sync.`);
      }
    } catch (err) {
      toast.error(err.message || `Failed to sync ${displayName}.`);
      console.error(`Error syncing ${displayName}:`, err);
    } finally {
      setLoadingState(false);
    }
  };

  const handleSyncPayments = () => runSync(syncQuickBooksPayments, 'payment', setPaymentsLoading);
  const handleSyncInvoices = () => runSync(syncQuickBooksInvoices, 'invoice', setInvoicesLoading);
  const handleSyncExpenses = () => runSync(syncQuickBooksExpenses, 'expense', setExpensesLoading);

  const handleDisconnect = () => {
    setShowConfirmDisconnect(true);
  };

  const handleConfirmDisconnect = async () => {
    setShowConfirmDisconnect(false);
    
    try {
      setLoading(true);
      setError(null);
      await disconnectQuickBooks();
      toast.success('Successfully disconnected from QuickBooks.');
      await fetchQuickBooksStatus();
    } catch (err) {
      const errorMessage = err.message || 'Failed to disconnect from QuickBooks.';
      setError(errorMessage);
      toast.error(errorMessage);
      console.error('Error disconnecting from QuickBooks:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelDisconnect = () => {
    setShowConfirmDisconnect(false);
  };

  if (loading) {
    return <LoadingSpinner message="Loading Integrations..." />;
  }
  
  if (isSyncing) {
    return <LoadingSpinner message="Performing initial sync with QuickBooks... This may take a moment." />;
  }

  return (
    <main className="p-4 sm:p-6 lg:p-8" role="main">
      <div className="max-w-5xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Manage Integrations</h1>
          <p className="text-gray-600 mt-1">
            Connect your Brikli account to other services to streamline your workflows.
          </p>
        </header>

        <div role="region" aria-label="Integration status and actions">
          <ErrorMessage error={error} onRetry={fetchQuickBooksStatus} />

          <QuickBooksCard
            status={quickBooksStatus}
            actionLoading={loading || isSyncing}
            paymentsLoading={paymentsLoading}
            invoicesLoading={invoicesLoading}
            expensesLoading={expensesLoading}
            onConnect={handleConnect}
            onDisconnect={handleDisconnect}
            onSyncPayments={handleSyncPayments}
            onSyncInvoices={handleSyncInvoices}
            onSyncExpenses={handleSyncExpenses}
          />

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
        />
      </div>
    </main>
  );
};

export default Integrations; 