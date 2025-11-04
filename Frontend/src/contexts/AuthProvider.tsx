import React, { useState, useEffect, useRef } from "react";
import * as Sentry from "@sentry/react";
import { supabase } from "../supabaseClient";
import { getCurrentUser } from "../utils/api";
import AuthLoadingSkeleton from "../components/auth/AuthLoadingSkeleton";
import { AuthContext, type User, type AuthContextType } from "./AuthContext";

interface AuthProviderProps {
  children: React.ReactNode;
}

/**
 * AuthProvider component that manages authentication state, session persistence, and user profile.
 * 
 * Initializes authentication state using Supabase, fetches user profile from the backend, 
 * and provides authentication context to the app. Handles login, logout, and session changes.
 * 
 * If authentication or user profile fetching fails, the user is signed out and local 
 * authentication data is cleared.
 */
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const currentUserIdRef = useRef<string | null>(null);
  const authFailureCountRef = useRef<number>(0);
  const lastFailureTimeRef = useRef<number>(0);
  const [showAuthError, setShowAuthError] = useState(false);
  const [authErrorMessage, setAuthErrorMessage] = useState("");

  // Circuit breaker for auth failures
  const handleAuthFailure = (error: any, context: string) => {
    const now = Date.now();
    const timeSinceLastFailure = now - lastFailureTimeRef.current;
    
    // Reset counter if it's been more than 5 minutes since last failure
    if (timeSinceLastFailure > 5 * 60 * 1000) {
      authFailureCountRef.current = 0;
      lastFailureTimeRef.current = now;
    }
    
    authFailureCountRef.current += 1;
    
    if (import.meta.env.MODE === 'development') {
      console.error(`Auth failure #${authFailureCountRef.current} in ${context}:`, error);
    }
    
    // Circuit breaker: after 3 failures, show error modal instead of infinite loop
    if (authFailureCountRef.current >= 3) {
      const errorMsg = error?.message || "Authentication failed repeatedly";
      setAuthErrorMessage(
        `Unable to authenticate after multiple attempts. ${errorMsg}. ` +
        "Please try refreshing the page or contact support if this persists."
      );
      setShowAuthError(true);
      
      Sentry.captureException(error, {
        tags: {
          component: 'AuthProvider',
          context: context,
          circuit_breaker: 'triggered',
          failure_count: authFailureCountRef.current,
        },
      });
      
      return true; // Circuit breaker triggered
    }
    
    return false; // Continue normal error handling
  };
  
  // Reset circuit breaker on successful auth
  const resetCircuitBreaker = () => {
    authFailureCountRef.current = 0;
    lastFailureTimeRef.current = 0;
    setShowAuthError(false);
    setAuthErrorMessage("");
  };

  // Set user context in Sentry when user changes
  useEffect(() => {
    currentUserIdRef.current = user?.id || null;
    
    // Update Sentry user context
    if (user) {
      Sentry.setUser({
        id: user.id,
        email: user.email,
        username: user.name || user.email,
        userType: user.user_type,
      });
      // Reset circuit breaker on successful auth
      resetCircuitBreaker();
    } else {
      // Clear user context on logout
      Sentry.setUser(null);
    }
  }, [user]);

  // Sign in function to be provided by context
  const signIn = async (email: string, password: string): Promise<boolean> => {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        throw error;
      }

      if (data && data.user && data.session) {
        // Supabase login successful, token is managed by supabase.auth.onAuthStateChange
        // The onAuthStateChange listener will handle setting the user from localStorage/API
        return true;
      }
      return false;
    } catch (error: any) {
      if (import.meta.env.MODE === 'development') {
        console.error("Login process failed:", error);
      }
      // Propagate the error so LoginForm can display it
      // Ensure error has a message property for consistent display
      const errToThrow = error.message
        ? error
        : new Error(
          error.detail || "Login failed. Please check your credentials."
        );
      if (error.status) errToThrow.status = error.status;
      throw errToThrow;
    }
  };

  // Check authentication status on mount and listen for changes
  useEffect(() => {
    setLoading(true);

    // Add a timeout to prevent infinite loading
    const authTimeout = setTimeout(() => {
      if (import.meta.env.MODE === 'development') {
        console.warn("Authentication check timed out, clearing loading state");
      }
      setLoading(false);
      setUser(null);
      localStorage.removeItem("token");
      localStorage.removeItem("user_type");
      localStorage.removeItem("user");
    }, 10000); // 10 second timeout

    // Get initial session
    supabase.auth
      .getSession()
      .then(async ({ data: { session }, error }) => {
        clearTimeout(authTimeout);

        if (error) {
          if (import.meta.env.MODE === 'development') {
            console.error("Error getting session:", error);
          }
          localStorage.removeItem("token");
          localStorage.removeItem("user_type");
          localStorage.removeItem("user");
          setUser(null);
          setLoading(false);
          return;
        }

        if (session) {
          try {
            const userInfo = await getCurrentUser();
            if (userInfo) {
              const userType = userInfo.user_type?.toUpperCase();
              userInfo.user_type = userType;
              localStorage.setItem("user_type", userType);
              localStorage.setItem("user", JSON.stringify(userInfo));
              setUser(userInfo as User);
            } else {
              await supabase.auth.signOut();
              localStorage.removeItem("token");
              localStorage.removeItem("user_type");
              localStorage.removeItem("user");
              setUser(null);
            }
          } catch (e: any) {
            if (handleAuthFailure(e, 'getSession_initial')) {
              // Circuit breaker triggered, stop processing
              setLoading(false);
              return;
            }
            
            if (import.meta.env.MODE === 'development') {
              console.error(
                "Error fetching user profile with existing session:",
                e
              );
            }
            if (e.status === 401 || e.status === 403) {
              if (import.meta.env.MODE === 'development') {
                console.log("Authentication error detected, signing out...");
              }
              await supabase.auth.signOut();
            }
            localStorage.removeItem("token");
            localStorage.removeItem("user_type");
            localStorage.removeItem("user");
            setUser(null);
          }
        } else {
          localStorage.removeItem("token");
          localStorage.removeItem("user_type");
          localStorage.removeItem("user");
          setUser(null);
        }
        setLoading(false);
      })
      .catch((error) => {
        clearTimeout(authTimeout);
        if (import.meta.env.MODE === 'development') {
          console.error("Error in getSession:", error);
        }
        localStorage.removeItem("token");
        localStorage.removeItem("user_type");
        localStorage.removeItem("user");
        setUser(null);
        setLoading(false);
      });

    const { data: authSubscriptionData } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (import.meta.env.MODE === 'development') {
          console.log("Auth state change:", event, session?.user?.id);
        }
        const currentToken = session?.access_token || null;

        if (currentToken) {
          localStorage.setItem("token", currentToken);
        } else {
          localStorage.removeItem("token");
        }

        if (event === "INITIAL_SESSION" || event === "SIGNED_IN") {
          const currentUserId = currentUserIdRef.current;
          const newUserId = session?.user?.id;

          if (currentUserId && newUserId && currentUserId === newUserId) {
            if (import.meta.env.MODE === 'development') {
              console.log(`Same user already loaded (${event}), skipping refresh on tab switch`);
            }
            return;
          }

          setLoading(true);

          if (session && session.user) {
            try {
              const userInfo = await getCurrentUser();
              if (userInfo) {
                const userType = userInfo.user_type?.toUpperCase();
                userInfo.user_type = userType;
                localStorage.setItem("user_type", userType);
                localStorage.setItem("user", JSON.stringify(userInfo));
                setUser(userInfo as User);
              } else {
                await supabase.auth.signOut();
                localStorage.removeItem("user_type");
                localStorage.removeItem("user");
                setUser(null);
              }
            } catch (e: any) {
              if (handleAuthFailure(e, 'onAuthStateChange')) {
                // Circuit breaker triggered, stop processing
                setLoading(false);
                return;
              }
              
              if (import.meta.env.MODE === 'development') {
                console.error("Error fetching user profile:", e);
              }
              if (e.status === 401 || e.status === 403) {
                await supabase.auth.signOut();
              }
              localStorage.removeItem("user_type");
              localStorage.removeItem("user");
              setUser(null);
            } finally {
              setLoading(false);
            }
          } else {
            setLoading(false);
          }
        } else if (event === "SIGNED_OUT") {
          localStorage.removeItem("user_type");
          localStorage.removeItem("user");
          setUser(null);
        } else if (event === "TOKEN_REFRESHED") {
          if (import.meta.env.MODE === 'development') {
            console.log("Token refreshed");
          }
        }
      }
    );

    return () => {
      clearTimeout(authTimeout);
      authSubscriptionData?.subscription?.unsubscribe();
    };
  }, []);

  const signOut = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) {
      if (import.meta.env.MODE === 'development') {
        console.error("Error logging out:", error);
      }
    }
    localStorage.removeItem("token");
    localStorage.removeItem("user_type");
    localStorage.removeItem("user");
    setUser(null);
  };

  const authValue: AuthContextType = {
    user,
    setUser,
    signIn,
    signOut,
    isAuthenticated: !!user,
  };

  if (loading) {
    return <AuthLoadingSkeleton />;
  }

  return (
    <AuthContext.Provider value={authValue}>
      {children}
      
      {/* Circuit Breaker Error Modal */}
      {showAuthError && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-center justify-center w-12 h-12 mx-auto mb-4 bg-red-100 rounded-full">
              <svg
                className="w-6 h-6 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 text-center mb-2">
              Authentication Error
            </h3>
            <p className="text-sm text-gray-600 text-center mb-6">
              {authErrorMessage}
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  resetCircuitBreaker();
                  window.location.reload();
                }}
                className="flex-1 px-4 py-2 bg-brand-teal text-white rounded-md hover:bg-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-brand-teal focus:ring-offset-2"
              >
                Refresh Page
              </button>
              <button
                onClick={async () => {
                  resetCircuitBreaker();
                  await supabase.auth.signOut();
                  window.location.href = "/login";
                }}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      )}
    </AuthContext.Provider>
  );
};

export default AuthProvider;

