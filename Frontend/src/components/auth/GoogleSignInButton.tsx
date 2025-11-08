import React from "react";
import { supabase } from "../../supabaseClient";

// Google SVG Icon
const GoogleIcon = () => (
  <svg viewBox="0 0 24 24" className="h-5 w-5 mr-3">
    <path
      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      fill="#4285F4"
    />
    <path
      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      fill="#34A853"
    />
    <path
      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      fill="#FBBC05"
    />
    <path
      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      fill="#EA4335"
    />
  </svg>
);

interface GoogleSignInButtonProps {
  setLoading: (loading: boolean) => void;
  setError: (error: string) => void;
}

const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({ 
  setLoading, 
  setError 
}) => {
  const handleGoogleSignIn = async () => {
    setLoading(true);
    setError("");

    if (import.meta.env.MODE === 'development') {
      console.log("Attempting Google Sign-In");
    }

    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
      });

      if (error) {
        console.error("Google Sign-In error:", error);
        setError(
          error.message || "Failed to sign in with Google. Please try again."
        );
        setLoading(false);
        
        if (import.meta.env.MODE === 'development') {
          console.log("Google Sign-In Failed", { error: error.message });
        }
      }
    } catch (err) {
      console.error("Unexpected error during Google Sign-In:", err);
      setError("An unexpected error occurred. Please try again.");
      setLoading(false);
      
      if (import.meta.env.MODE === 'development') {
        console.log("Google Sign-In Unexpected Error", { 
          error: err instanceof Error ? err.message : String(err) 
        });
      }
    }
  };

  return (
    <button
      type="button"
      onClick={handleGoogleSignIn}
      className="w-full flex items-center justify-center py-2 px-4 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-teal mb-4 transition-colors duration-200"
    >
      <GoogleIcon />
      Continue with Google
    </button>
  );
};

export default GoogleSignInButton;

