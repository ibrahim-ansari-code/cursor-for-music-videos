import React, { useState, useEffect, type FormEvent, type ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import GoogleSignInButton from './GoogleSignInButton';
import MicrosoftSignInButton from './MicrosoftSignInButton';
import { supabase } from '@/utils/supabaseClient';

interface LoginFormProps {
  onSuccess?: () => void;
}

const LoginForm: React.FC<LoginFormProps> = ({ onSuccess: _onSuccess }) => {
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [showForgotPassword, setShowForgotPassword] = useState<boolean>(false);
  const [resetEmail, setResetEmail] = useState<string>("");
  const [resetLoading, setResetLoading] = useState<boolean>(false);
  const [resetMessage, setResetMessage] = useState<string>("");
  const [resetError, setResetError] = useState<string>("");
  const navigate = useNavigate();
  const { signIn, isAuthenticated } = useAuth();

  // Only redirect if user becomes authenticated via AuthContext
  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const { error } = await signIn(email, password);
      if (error) {
        setError(error?.message || "Login failed. Please check your credentials.");
      }
      // AuthContext will handle the redirect when authentication is successful
    } catch (err) {
      console.error("Login error in LoginForm:", err);
      const authError = err as Error & { status?: number };
      
      // Handle Supabase-specific error messages
      let errorMessage = "Login failed. Please try again.";
      
      if (authError.message) {
        // Common Supabase auth error messages and their user-friendly versions
        const errorMap: Record<string, string> = {
          "Invalid login credentials": "Invalid email or password.",
          "Email not confirmed": "Please confirm your email before logging in.",
          "User already registered": "This email is already registered.",
          "Invalid email or password": "Invalid email or password.",
          "missing_email": "Please enter your email address.",
          "missing_password": "Please enter your password.",
        };
        
        // Check if we have a mapped error message
        const mappedError = Object.entries(errorMap).find(([key]) => 
          authError.message.toLowerCase().includes(key.toLowerCase())
        );
        
        errorMessage = mappedError ? mappedError[1] : authError.message;
      } else if (authError.status === 401) {
        errorMessage = "Invalid email or password.";
      } else if (authError.status === 400) {
        errorMessage = "Please check your email and password.";
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setResetError("");
    setResetMessage("");
    setResetLoading(true);

    if (!resetEmail) {
      setResetError("Please enter your email address.");
      setResetLoading(false);
      return;
    }

    try {
      const { error } = await supabase.auth.resetPasswordForEmail(resetEmail, {
        redirectTo: `${window.location.origin}/reset-password`,
      });

      if (error) {
        setResetError(error.message);
      } else {
        setResetMessage("Password reset email sent! Please check your inbox.");
        setResetEmail("");
      }
    } catch (err) {
      console.error("Password reset error:", err);
      setResetError("Failed to send reset email. Please try again.");
    } finally {
      setResetLoading(false);
    }
  };

  const closeForgotPasswordModal = (): void => {
    setShowForgotPassword(false);
    setResetEmail("");
    setResetError("");
    setResetMessage("");
  };

  return (
    <>
      <div className="w-full h-full flex flex-col justify-center">
        <div className="sm:mx-auto sm:w-full">
          <h2 className="text-center text-3xl font-bold tracking-tight text-gray-900">
            Sign in to your account
          </h2>
        </div>

        <div className="mt-8 sm:mx-auto sm:w-full">
          <GoogleSignInButton setLoading={setLoading} setError={setError} />
          <MicrosoftSignInButton setLoading={setLoading} setError={setError} />

          <div className="relative my-4">
            <div
              className="absolute inset-0 flex items-center"
              aria-hidden="true"
            >
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">
                Or continue with email
              </span>
            </div>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            <div>
              <label
                htmlFor="email-address"
                className="block text-sm font-medium text-gray-700"
              >
                Email address
              </label>
              <input
                id="email-address"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-teal focus:outline-none focus:ring-brand-teal sm:text-sm"
                placeholder="Email address"
                value={email}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700"
              >
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-teal focus:outline-none focus:ring-brand-teal sm:text-sm"
                placeholder="Password"
                value={password}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
              />
            </div>

            {error && (
              <div className="rounded-md bg-red-50 p-4">
                <div className="flex">
                  <div className="shrink-0">
                    <svg
                      className="h-5 w-5 text-red-400"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                </div>
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={loading}
                className="flex w-full justify-center rounded-md border border-transparent bg-gray-900 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 disabled:opacity-75"
              >
                {loading ? "Signing in..." : "Sign in"}
              </button>
            </div>

            <div className="text-center text-sm">
              <button
                type="button"
                onClick={() => setShowForgotPassword(true)}
                className="font-medium text-brand-teal hover:text-brand-teal/80"
              >
                Forgot your password?
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {showForgotPassword && (
        <div className="fixed inset-0 backdrop-blur-md bg-black/20 flex items-center justify-center p-4 z-50">
          <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-2xl border border-white/20 max-w-md w-full mx-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900">
                Reset Password
              </h3>
              <button
                onClick={closeForgotPasswordModal}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            {/* Modal Content */}
            <div className="p-6">
              <p className="text-sm text-gray-600 mb-6">
                Enter your email address and we'll send you a link to reset your password.
              </p>

              <form onSubmit={handleForgotPassword} className="space-y-4">
                <div>
                  <label
                    htmlFor="reset-email"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Email address
                  </label>
                  <input
                    id="reset-email"
                    type="email"
                    required
                    className="w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-teal focus:outline-none focus:ring-1 focus:ring-brand-teal sm:text-sm"
                    placeholder="Enter your email"
                    value={resetEmail}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setResetEmail(e.target.value)}
                  />
                </div>

                {resetError && (
                  <div className="rounded-md bg-red-50 p-3">
                    <div className="flex">
                      <div className="shrink-0">
                        <svg
                          className="h-5 w-5 text-red-400"
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                        >
                          <path
                            fillRule="evenodd"
                            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </div>
                      <div className="ml-3">
                        <p className="text-sm text-red-700">{resetError}</p>
                      </div>
                    </div>
                  </div>
                )}

                {resetMessage && (
                  <div className="rounded-md bg-green-50 p-3">
                    <div className="flex">
                      <div className="shrink-0">
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
                        <p className="text-sm text-green-700">{resetMessage}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Modal Actions */}
                <div className="flex space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={closeForgotPasswordModal}
                    className="flex-1 rounded-md border border-gray-300 bg-white py-2 px-4 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-teal focus:ring-offset-2 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={resetLoading}
                    className="flex-1 rounded-md border border-transparent bg-brand-teal py-2 px-4 text-sm font-medium text-white hover:bg-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-brand-teal focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {resetLoading ? "Sending..." : "Send Reset Link"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default LoginForm;

