import React from 'react';
import { supabase } from '../../utils/supabaseClient';

// Microsoft SVG Icon (inline or imported)
const MicrosoftIcon = () => (
  <svg viewBox="0 0 24 24" className="h-5 w-5 mr-3">
    <path d="M0 0h11.377v11.372H0z" fill="#f25022" />
    <path d="M12.623 0H24v11.372H12.623z" fill="#00a4ef" />
    <path d="M0 12.628h11.377V24H0z" fill="#7fba00" />
    <path d="M12.623 12.628H24V24H12.623z" fill="#ffb900" />
  </svg>
);

/**
 * MicrosoftSignInButton Component
 * Professional Microsoft Sign-in button for tenant portal
 * Features: OAuth integration, proper error handling, loading states
 */
const MicrosoftSignInButton = ({ setLoading, setError }) => {
  const handleMicrosoftSignIn = async () => {
    setLoading(true);
    setError("");
    // Analytics placeholder
    console.log("Attempting Microsoft Sign-In"); // Or your trackEvent('Login with Microsoft Attempt')

    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "azure",
        // Remove options.redirectTo to rely on Supabase dashboard configuration for redirects
        // options: {
        //   redirectTo: 'https://ajyvwgfynxjbtjrbwfc.supabase.co/auth/v1/callback',
        // },
      });

      if (error) {
        console.error("Microsoft Sign-In error:", error);
        setError(
          error.message || "Failed to sign in with Microsoft. Please try again."
        );
        // Analytics placeholder
        console.log("Microsoft Sign-In Failed", { error: error.message }); // Or trackEvent('Login with Microsoft Failed', { error: error.message })
      }
      // On success, Supabase handles the redirect. If it gets here without redirecting,
      // it implies an issue before the redirect could occur or a misconfiguration.
      // setLoading(false) might be needed if the redirect doesn't happen immediately
      // or if there's an error caught by the 'if (error)' block.
    } catch (err) {
      // Catch any other unexpected errors
      console.error("Unexpected error during Microsoft Sign-In:", err);
      setError("An unexpected error occurred. Please try again.");
      // Analytics placeholder
      console.log("Microsoft Sign-In Unexpected Error", { error: err.message }); // Or trackEvent('Login with Microsoft Unexpected Error', { error: err.message })
    } finally {
      // setLoading is typically managed by page navigation.
      // If an error occurs *before* navigation, we need to stop loading.
      // If Supabase successfully initiates redirect, this component will unmount.
      // The setLoading(false) will be called only if an error occurs *before* Supabase redirects.
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleMicrosoftSignIn}
      className="w-full flex items-center justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-teal mb-4"
    >
      <MicrosoftIcon />
      Continue with Microsoft
    </button>
  );
};

export default MicrosoftSignInButton;

