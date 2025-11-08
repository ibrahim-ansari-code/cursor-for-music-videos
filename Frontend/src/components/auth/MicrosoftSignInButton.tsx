import React from "react";
import { supabase } from "../../supabaseClient";

// Microsoft SVG Icon
const MicrosoftIcon = () => (
  <svg viewBox="0 0 24 24" className="h-5 w-5 mr-3">
    <path d="M0 0h11.377v11.372H0z" fill="#f25022" />
    <path d="M12.623 0H24v11.372H12.623z" fill="#00a4ef" />
    <path d="M0 12.628h11.377V24H0z" fill="#7fba00" />
    <path d="M12.623 12.628H24V24H12.623z" fill="#ffb900" />
  </svg>
);

interface MicrosoftSignInButtonProps {
  setLoading: (loading: boolean) => void;
  setError: (error: string) => void;
}

const MicrosoftSignInButton: React.FC<MicrosoftSignInButtonProps> = ({ 
  setLoading, 
  setError 
}) => {
  const handleMicrosoftSignIn = async () => {
    setLoading(true);
    setError("");

    if (import.meta.env.MODE === 'development') {
      console.log("Attempting Microsoft Sign-In");
    }

    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "azure",
      });

      if (error) {
        console.error("Microsoft Sign-In error:", error);
        setError(
          error.message || "Failed to sign in with Microsoft. Please try again."
        );
        setLoading(false);
        
        if (import.meta.env.MODE === 'development') {
          console.log("Microsoft Sign-In Failed", { error: error.message });
        }
      }
    } catch (err) {
      console.error("Unexpected error during Microsoft Sign-In:", err);
      setError("An unexpected error occurred. Please try again.");
      setLoading(false);
      
      if (import.meta.env.MODE === 'development') {
        console.log("Microsoft Sign-In Unexpected Error", { 
          error: err instanceof Error ? err.message : String(err) 
        });
      }
    }
  };

  return (
    <button
      type="button"
      onClick={handleMicrosoftSignIn}
      className="w-full flex items-center justify-center py-2 px-4 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-teal mb-4 transition-colors duration-200"
    >
      <MicrosoftIcon />
      Continue with Microsoft
    </button>
  );
};

export default MicrosoftSignInButton;

