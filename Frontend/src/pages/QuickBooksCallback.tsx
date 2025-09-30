import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function QuickBooksCallback() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [message, setMessage] = useState('Processing QuickBooks connection...');

  useEffect(() => {
    async function handleCallback() {
      try {
        const url = new URL(window.location.href);
        const code = url.searchParams.get('code');
        const realmId = url.searchParams.get('realmId');
        const state = url.searchParams.get('state');
        const error = url.searchParams.get('error');
        const errorDescription = url.searchParams.get('error_description');

        // Log all OAuth callback parameters for debugging
        console.log('QuickBooks OAuth Callback:', {
          code: code ? 'present' : 'missing',
          realmId: realmId ? 'present' : 'missing',
          state: state ? 'present' : 'missing',
          error,
          errorDescription,
          fullUrl: window.location.href
        });

        // Handle OAuth errors
        if (error || errorDescription) {
          console.error('QuickBooks OAuth error:', { error, errorDescription });

          // Special handling for scope errors to provide better message
          if (error === 'invalid_scope') {
            setStatus('error');
            setMessage('QuickBooks authorization failed: Invalid scope configuration. Please contact support.');

            sessionStorage.setItem('qb_oauth_error', JSON.stringify({
              error: 'invalid_scope',
              errorDescription: 'The OAuth scope configuration is invalid. This is a configuration issue.'
            }));
          } else {
            setStatus('error');
            setMessage(errorDescription || error || 'Authorization failed');

            // Store error for integration page
            sessionStorage.setItem('qb_oauth_error', JSON.stringify({
              error,
              errorDescription
            }));
          }

          // Navigate after a brief delay to show the error
          setTimeout(() => navigate('/integrations', { replace: true }), 3000);
          return;
        }

        // Validate required parameters
        if (!code || !realmId || !state) {
          setStatus('error');
          setMessage('Missing required authorization parameters');

          sessionStorage.setItem('qb_oauth_error', JSON.stringify({
            error: 'invalid_request',
            errorDescription: 'Missing authorization code, realm ID, or state parameter'
          }));

          setTimeout(() => navigate('/integrations', { replace: true }), 2000);
          return;
        }

        // Call the new callback endpoint - use fetch directly to avoid auth interceptor
        setMessage('Connecting to QuickBooks...');

        const apiUrl = import.meta.env.VITE_API_URL || '';
        const token = localStorage.getItem('token');

        const fetchResponse = await fetch(
          `${apiUrl}/api/quickbooks/callback?code=${encodeURIComponent(code)}&realmId=${encodeURIComponent(realmId)}&state=${encodeURIComponent(state)}`,
          {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        );

        if (!fetchResponse.ok) {
          const errorData = await fetchResponse.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP ${fetchResponse.status}: ${fetchResponse.statusText}`);
        }

        const response = await fetchResponse.json();

        if (response.success) {
          setStatus('success');
          setMessage(`Successfully connected to QuickBooks${response.company_name ? ` (${response.company_name})` : ''}!`);

          // Store success status for integration page
          sessionStorage.setItem('qb_oauth_success', JSON.stringify({
            success: true,
            company_name: response.company_name,
            connected_at: response.connected_at
          }));

          // Navigate after showing success message
          setTimeout(() => navigate('/integrations', { replace: true }), 1500);
        } else {
          throw new Error(response.message || 'Connection failed');
        }

      } catch (error: any) {
        console.error('Error processing QuickBooks callback:', error);

        setStatus('error');
        setMessage(
          error?.message ||
          error?.detail ||
          'Failed to connect to QuickBooks. Please try again.'
        );

        // Store error for integration page
        sessionStorage.setItem('qb_oauth_error', JSON.stringify({
          error: 'connection_failed',
          errorDescription: error?.message || 'Connection failed'
        }));

        // Navigate after showing error
        setTimeout(() => navigate('/integrations', { replace: true }), 3000);
      }
    }

    handleCallback();
  }, [navigate]);

  // Show loading/status UI instead of null
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-md p-8 max-w-md w-full text-center">
        <div className="mb-6">
          <img
            src="/Intuit_QuickBooks_logo.svg"
            alt="QuickBooks"
            className="h-12 mx-auto mb-4"
          />
          <h1 className="text-xl font-semibold text-gray-800">
            QuickBooks Integration
          </h1>
        </div>

        <div className="mb-6">
          {status === 'processing' && (
            <div className="flex items-center justify-center space-x-3 text-blue-600">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span>Processing...</span>
            </div>
          )}

          {status === 'success' && (
            <div className="flex items-center justify-center space-x-3 text-green-600">
              <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Success!</span>
            </div>
          )}

          {status === 'error' && (
            <div className="flex items-center justify-center space-x-3 text-red-600">
              <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span>Error</span>
            </div>
          )}
        </div>

        <p className="text-gray-600 text-sm">{message}</p>

        {status === 'error' && (
          <p className="text-gray-500 text-xs mt-2">
            You will be redirected to the integrations page shortly.
          </p>
        )}
      </div>
    </div>
  );
}


