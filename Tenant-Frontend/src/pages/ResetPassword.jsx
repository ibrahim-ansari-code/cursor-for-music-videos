import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../utils/supabaseClient';

/**
 * ResetPassword Component
 * 
 * Handles password reset functionality with proper deep linking support for Supabase.
 * 
 * Supabase password reset flow:
 * 1. User requests reset via resetPasswordForEmail()
 * 2. Supabase sends email with link like: https://app.brikli.com/reset-password#access_token=xxx&refresh_token=yyy&type=recovery
 * 3. This component parses URL hash fragments and establishes a session
 * 4. User enters new password and component calls updateUser()
 * 5. User is redirected to dashboard on success
 * 
 * Deep linking improvements:
 * - Explicit parsing of URL hash fragments for tokens
 * - Automatic session establishment from URL tokens
 * - URL cleanup after successful session establishment
 * - Comprehensive error handling for invalid/expired tokens
 */
const ResetPassword = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    password: '',
    confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isValidSession, setIsValidSession] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const redirectTimeoutRef = useRef(null);

  useEffect(() => {
    // Parse URL hash fragments for password reset tokens
    const parseUrlTokens = () => {
      const hashParams = new URLSearchParams(window.location.hash.substring(1));
      const accessToken = hashParams.get('access_token');
      const refreshToken = hashParams.get('refresh_token');
      const type = hashParams.get('type');
      
      return { accessToken, refreshToken, type };
    };

    // Check if we have a valid session for password recovery
    const checkSession = async () => {
      try {
        // First, check if we already have a valid session
        const { data: { session: existingSession } } = await supabase.auth.getSession();
        if (existingSession) {
          setIsValidSession(true);
          return;
        }
        
        // If no existing session, check if we have tokens in the URL
        const { accessToken, refreshToken, type } = parseUrlTokens();
        
        if (accessToken && type === 'recovery') {
          // If we have recovery tokens in URL, set the session
          const { data, error } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken || ''
          });
          
          if (error) {
            console.error('Error setting session from URL tokens:', error);
            setError('Invalid or expired reset link. Please request a new password reset.');
            redirectTimeoutRef.current = setTimeout(() => navigate('/login'), 3000);
            return;
          }
          
          if (data.session) {
            setIsValidSession(true);
            // Clean up URL hash after successful session establishment
            window.history.replaceState(null, '', window.location.pathname);
            return;
          }
        }
        
        // No session found and no valid tokens in URL
        setError('No valid reset session found. Please request a new password reset.');
        redirectTimeoutRef.current = setTimeout(() => navigate('/login'), 3000);
      } catch (err) {
        console.error("Session check error:", err);
        setError('Failed to validate reset link. Please try again.');
        redirectTimeoutRef.current = setTimeout(() => navigate('/login'), 3000);
      }
    };

    checkSession();

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "PASSWORD_RECOVERY") {
        setIsValidSession(true);
      } else if (event === "SIGNED_OUT") {
        navigate("/login");
      }
    });

    return () => subscription.unsubscribe();
  }, [navigate]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (redirectTimeoutRef.current) {
        clearTimeout(redirectTimeoutRef.current);
      }
    };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match.');
      setLoading(false);
      return;
    }

    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters long.');
      setLoading(false);
      return;
    }

    try {
      // Double-check we have a valid session before attempting password update
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        setError('Session expired. Please request a new password reset.');
        redirectTimeoutRef.current = setTimeout(() => navigate('/login'), 3000);
        return;
      }

      const { data, error } = await supabase.auth.updateUser({
        password: formData.password
      });

      if (error) {
        // Handle specific Supabase errors
        if (error.message.includes('session_not_found')) {
          setError('Session expired. Please request a new password reset.');
          redirectTimeoutRef.current = setTimeout(() => navigate('/login'), 3000);
        } else if (error.message.includes('weak_password')) {
          setError('Password is too weak. Please choose a stronger password.');
        } else {
          setError(error.message);
        }
      } else {
        // Password updated successfully
        setError(''); // Clear any previous errors
        setShowSuccess(true);
        redirectTimeoutRef.current = setTimeout(() => {
          navigate('/dashboard', { replace: true });
        }, 2000);
      }
    } catch (err) {
      console.error('Password update error:', err);
      setError('Failed to update password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!isValidSession) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-brand-green to-brand-teal flex items-center justify-center p-4">
        <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-2xl border border-white/20 max-w-md w-full mx-auto animate-fade-in">
          <div className="p-8 text-center">
            {error ? (
              <div className="space-y-4">
                <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                  <svg
                    className="h-6 w-6 text-red-600"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
                    />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900">Reset Link Invalid</h3>
                <p className="text-sm text-gray-600">{error}</p>
                <button
                  onClick={() => navigate('/login')}
                  className="mt-4 bg-brand-teal text-white px-4 py-2 rounded-md hover:bg-brand-teal/90 transition-colors"
                >
                  Back to Login
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-teal mx-auto"></div>
                <h3 className="text-lg font-medium text-gray-900">Validating Reset Link</h3>
                <p className="text-sm text-gray-600">
                  Please wait while we verify your password reset request...
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-green to-brand-teal flex items-center justify-center p-4">
      <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-2xl border border-white/20 max-w-md w-full mx-auto animate-fade-in">
        {/* Header */}
        <div className="p-6 border-b border-gray-200/50 text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Reset Your Password</h1>
          <p className="text-gray-600">Enter your new password below</p>
        </div>

        {/* Form */}
        <div className="p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                New Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-teal focus:outline-none focus:ring-1 focus:ring-brand-teal sm:text-sm"
                placeholder="Enter new password"
                value={formData.password}
                onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-teal focus:outline-none focus:ring-1 focus:ring-brand-teal sm:text-sm"
                placeholder="Confirm new password"
                value={formData.confirmPassword}
                onChange={(e) => setFormData(prev => ({ ...prev, confirmPassword: e.target.value }))}
              />
            </div>

            {error && (
              <div className="rounded-lg bg-red-50 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {showSuccess && (
              <div className="rounded-lg bg-green-50 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg
                      className="h-5 w-5 text-green-400"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-green-700">
                      Password updated successfully! Redirecting to dashboard...
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="flex space-x-3">
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="flex-1 rounded-lg border border-gray-300/50 bg-white/70 backdrop-blur-sm py-2 px-4 text-sm font-medium text-gray-700 hover:bg-white/90 focus:outline-none focus:ring-2 focus:ring-brand-teal focus:ring-offset-2 transition-all duration-200"
              >
                Back to Login
              </button>
              <button
                type="submit"
                disabled={loading || showSuccess}
                className="flex-1 rounded-lg border border-transparent bg-brand-teal py-2 px-4 text-sm font-medium text-white hover:bg-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-brand-teal focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg"
              >
                {loading ? 'Updating...' : showSuccess ? 'Success!' : 'Update Password'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ResetPassword; 