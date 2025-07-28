import React from 'react';

/**
 * GoogleSignInButton Component
 * Styled to match landlord portal design
 * For tenant portal authentication
 */
const GoogleSignInButton = ({ setLoading, setError }) => {
  const handleGoogleSignIn = async () => {
    // TODO: Implement Google Sign-In for tenant portal
    // Feature is currently disabled during development. The button is disabled
    // to prevent user confusion and provide a better user experience than showing
    // a misleading error message. A tooltip is provided on hover for more context.
    return;
  };

  return (
    <button
      type="button"
      onClick={handleGoogleSignIn}
      disabled={true}
      className="w-full flex justify-center items-center px-4 py-3 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-400 bg-gray-50 cursor-not-allowed transition-all duration-200"
      title="Google Sign-In is coming soon for the tenant portal."
    >
      <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
        <path
          fill="#4285F4"
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        />
        <path
          fill="#34A853"
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        />
        <path
          fill="#FBBC05"
          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        />
        <path
          fill="#EA4335"
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        />
      </svg>
      Continue with Google
    </button>
  );
};

export default GoogleSignInButton;