import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import {
  connectToQuickBooks,
  getQuickBooksStatus,
  disconnectQuickBooks,
} from '../utils/api';

// --- Reusable Components (Tailored to Brikli's Style) ---

const LoadingSpinner = () => (
  <div 
    className="flex justify-center items-center h-full p-8"
    role="status"
    aria-live="polite"
    aria-label="Loading integrations"
  >
    <div className="text-center">
      <div 
        className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"
        aria-hidden="true"
      ></div>
      <p className="mt-3 text-gray-600" id="loading-text">Loading Integrations...</p>
    </div>
  </div>
);

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

const QuickBooksCard = ({ status, actionLoading, onConnect, onDisconnect }) => {
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
            <h3 id="quickbooks-heading" className="text-xl font-semibold text-gray-800">
              QuickBooks Online
            </h3>
            <p id="quickbooks-description" className="text-gray-500 mt-1">
              Sync your invoices, payments, and expenses with your QuickBooks account.
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="text-right">
            {isConnected ? (
              <>
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
                  <p className="text-xs text-gray-500 mt-1" id={connectionDateId}>
                    <span className="sr-only">Connected on: </span>
                    On: {new Date(status.connected_at).toLocaleDateString()}
                  </p>
                )}
              </>
            ) : (
              <span 
                className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800"
                role="status"
                aria-label="QuickBooks integration status"
                id={connectionStatusId}
              >
                <i className="fas fa-times-circle mr-2" aria-hidden="true"></i>
                Not Connected
              </span>
            )}
          </div>
          
          <div>
            {isConnected ? (
              <button
                type="button"
                onClick={onDisconnect}
                disabled={actionLoading}
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

// --- Main Page Component ---
const Integrations = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quickBooksStatus, setQuickBooksStatus] = useState({ connected: false });
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    fetchQuickBooksStatus();
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

  const handleConnect = async () => {
    try {
      setActionLoading(true);
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
      setActionLoading(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Are you sure you want to disconnect from QuickBooks? This will stop syncing your accounting data.')) {
      return;
    }

    try {
      setActionLoading(true);
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
      setActionLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner />;
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
            actionLoading={actionLoading}
            onConnect={handleConnect}
            onDisconnect={handleDisconnect}
          />

          <PlaceholderCard />
        </div>
      </div>
    </main>
  );
};

export default Integrations; 