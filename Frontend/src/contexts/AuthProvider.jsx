import React, { createContext, useState, useEffect } from "react";
import { supabase } from "../supabaseClient";
import { getCurrentUser } from "../utils/api";
import AuthLoadingSkeleton from "../components/auth/AuthLoadingSkeleton";
import { AuthContext } from "./AuthContext";

/**
 * AuthProvider component that manages authentication state, session persistence, and user profile.
 * 
 * Initializes authentication state using Supabase, fetches user profile from the backend, 
 * and provides authentication context to the app. Handles login, logout, and session changes.
 * 
 * If authentication or user profile fetching fails, the user is signed out and local 
 * authentication data is cleared.
 */
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const currentUserIdRef = React.useRef(null);

  React.useEffect(() => {
    currentUserIdRef.current = user?.id || null;
  }, [user]);

  // Sign in function to be provided by context
  const signIn = async (email, password) => {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        // Supabase error object structure might be { name, message, status }
        // Adapt error handling as needed based on Supabase error structure
        throw error;
      }

      if (data && data.user && data.session) {
        // Supabase login successful, token is managed by supabase.auth.onAuthStateChange
        // The onAuthStateChange listener will handle setting the user from localStorage/API
        return true;
      }
      return false;
    } catch (error) {
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
      if (error.status) errToThrow.status = error.status; // Preserve status if available
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
        clearTimeout(authTimeout); // Clear timeout since we got a response

        if (error) {
          if (import.meta.env.MODE === 'development') {
            console.error("Error getting session:", error);
          }
          // Clear any stale auth data
          localStorage.removeItem("token");
          localStorage.removeItem("user_type");
          localStorage.removeItem("user");
          setUser(null);
          setLoading(false);
          return;
        }

        if (session) {
          // If session exists, fetch our backend's user profile
          try {
            // getCurrentUser uses the token from localStorage, which should be set by Supabase client
            const userInfo = await getCurrentUser(); // Fetches from /api/auth/me
            if (userInfo) {
              const userType = userInfo.user_type?.toUpperCase();
              userInfo.user_type = userType;
              localStorage.setItem("user_type", userType); // Ensure consistent casing
              localStorage.setItem("user", JSON.stringify(userInfo));
              setUser(userInfo);
            } else {
              // No user profile from backend, clear local auth data
              // This could happen if Supabase session is valid but user not in our DB
              // or /me failed.
              await supabase.auth.signOut(); // Sign out from Supabase too for consistency
              localStorage.removeItem("token"); // Redundant if Supabase handles it, but good practice
              localStorage.removeItem("user_type");
              localStorage.removeItem("user");
              setUser(null);
            }
          } catch (e) {
            if (import.meta.env.MODE === 'development') {
              console.error(
                "Error fetching user profile with existing session:",
                e
              );
            }
            // If the error is authentication-related (401, 403), sign out
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
          // No session, ensure clean state
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
        // Only log auth events in development
        if (import.meta.env.MODE === 'development') {
          console.log("Auth state change:", event, session?.user?.id);
        }
        const currentToken = session?.access_token || null;

        // Store/remove Supabase token for api.js to pick up
        if (currentToken) {
          localStorage.setItem("token", currentToken);
        } else {
          localStorage.removeItem("token");
        }

        if (event === "INITIAL_SESSION" || event === "SIGNED_IN") {
          // Check if this is the same user already loaded (tab switch scenario)
          // Use ref instead of state to avoid closure issues
          const currentUserId = currentUserIdRef.current;
          const newUserId = session?.user?.id;

          if (currentUserId && newUserId && currentUserId === newUserId) {
            // Only log in development mode for security
            if (import.meta.env.MODE === 'development') {
              console.log(`Same user already loaded (${event}), skipping refresh on tab switch`);
            }
            return;
          }

          // Set loading state for both events since both can trigger user fetching
          setLoading(true);

          if (session && session.user) {
            try {
              const userInfo = await getCurrentUser(); // Fetches from /api/auth/me
              if (userInfo) {
                const userType = userInfo.user_type?.toUpperCase();
                userInfo.user_type = userType;
                localStorage.setItem("user_type", userType);
                localStorage.setItem("user", JSON.stringify(userInfo));
                setUser(userInfo);
              } else {
                // Handle case: Supabase signed in, but no profile in our DB
                await supabase.auth.signOut(); // Sign out from Supabase
                localStorage.removeItem("user_type");
                localStorage.removeItem("user");
                setUser(null);
              }
            } catch (e) {
              if (import.meta.env.MODE === 'development') {
                console.error("Error fetching user profile:", e);
              }
              // If the error is authentication-related, sign out
              if (e.status === 401 || e.status === 403) {
                await supabase.auth.signOut();
              }
              localStorage.removeItem("user_type");
              localStorage.removeItem("user");
              setUser(null);
            } finally {
              // Always clear loading state, even if errors occur
              setLoading(false);
            }
          } else {
            // No session, clear loading immediately
            setLoading(false);
          }
        } else if (event === "SIGNED_OUT") {
          localStorage.removeItem("user_type");
          localStorage.removeItem("user");
          setUser(null);
          // Navigate to login? Handled by ProtectedRoute logic.
        } else if (event === "TOKEN_REFRESHED") {
          // Supabase client handles token refresh automatically.
          // If you store the token manually elsewhere, update it here.
          // localStorage 'token' is updated above.
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
      // Handle logout error if necessary
    }
    // The onAuthStateChange listener (SIGNED_OUT event) will handle clearing localStorage and user state.
    // Explicitly clearing here can be redundant but ensures immediate UI update if needed.
    localStorage.removeItem("token");
    localStorage.removeItem("user_type");
    localStorage.removeItem("user");
    setUser(null);
  };

  const authValue = {
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
    </AuthContext.Provider>
  );
};

export default AuthProvider;