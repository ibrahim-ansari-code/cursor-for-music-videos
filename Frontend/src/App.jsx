import React, { createContext, useState, useEffect } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "./styles/ui-feedback.css";
import Layout from "./components/Layout";
import Dashboard from "./components/Dashboard";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ResetPassword from "./pages/ResetPassword";

// Pages
import Leases from "./pages/Leases";
import Vendors from "./pages/Vendors";
import Accounting from "./pages/Accounting";
import OverviewTab from "./components/accounting/OverviewTab";
import PaymentsTab from "./components/accounting/PaymentsTab";
import ExpensesTab from "./components/accounting/ExpensesTab";
import RentTrackerTab from "./components/accounting/RentTrackerTab";
import InvoicesTab from "./components/accounting/InvoicesTab";
import Messages from "./pages/Messages";
import Properties from "./pages/Properties";
import PropertyDetail from "./pages/PropertyDetail";
import Tenants from "./pages/Tenants";
import Maintenance from "./pages/Maintenance";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";
import Integrations from "./pages/Integrations";

// Import the login API function
import { getCurrentUser } from "./utils/api";
import { supabase } from "./supabaseClient"; // Import Supabase client
import AuthLoadingSkeleton from "./components/auth/AuthLoadingSkeleton";
import { AuthContext } from "./contexts/AuthContext";

/**
 * Main application component that manages authentication state, session persistence, and protected routing.
 *
 * Initializes authentication state using Supabase, fetches user profile from the backend, and provides authentication context to the app. Handles login, logout, and session changes, and conditionally renders routes based on authentication status.
 *
 * @returns {JSX.Element} The root component of the authenticated single-page application.
 *
 * @remark
 * If authentication or user profile fetching fails, the user is signed out and local authentication data is cleared.
 */
function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Login function to be provided by context
  const login = async (email, password) => {
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
        // Now fetch our backend's user profile
        // The onAuthStateChange listener will handle setting the user from localStorage/API
        // For an immediate update after login, we can fetch user profile here too
        // However, onAuthStateChange should be the primary driver for consistency.
        // The token will be available in onAuthStateChange, or supabase.auth.getSession()

        // For now, we assume onAuthStateChange will pick up the new session and trigger profile fetch.
        // If immediate navigation based on this login is needed before onAuthStateChange fully processes,
        // you might need to manually trigger a profile fetch and setUser here.
        return true;
      }
      return false;
    } catch (error) {
      console.error("Login process failed:", error);
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
      console.warn("Authentication check timed out, clearing loading state");
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
          console.error("Error getting session:", error);
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
            console.error(
              "Error fetching user profile with existing session:",
              e
            );
            // If the error is authentication-related (401, 403), sign out
            if (e.status === 401 || e.status === 403) {
              console.log("Authentication error detected, signing out...");
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
        console.error("Error in getSession:", error);
        localStorage.removeItem("token");
        localStorage.removeItem("user_type");
        localStorage.removeItem("user");
        setUser(null);
        setLoading(false);
      });

    const { data: authSubscriptionData } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log("Auth state change:", event, session?.user?.id);
        const currentToken = session?.access_token || null;

        // Store/remove Supabase token for api.js to pick up
        if (currentToken) {
          localStorage.setItem("token", currentToken);
        } else {
          localStorage.removeItem("token");
        }

        if (event === "SIGNED_IN") {
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
              console.error("Error fetching user profile after SIGNED_IN:", e);
              // If the error is authentication-related, sign out
              if (e.status === 401 || e.status === 403) {
                await supabase.auth.signOut();
              }
              localStorage.removeItem("user_type");
              localStorage.removeItem("user");
              setUser(null);
            }
          }
          setLoading(false);
        } else if (event === "SIGNED_OUT") {
          localStorage.removeItem("user_type");
          localStorage.removeItem("user");
          setUser(null);
          // Navigate to login? Handled by ProtectedRoute logic.
        } else if (event === "TOKEN_REFRESHED") {
          // Supabase client handles token refresh automatically.
          // If you store the token manually elsewhere, update it here.
          // localStorage 'token' is updated above.
          console.log("Token refreshed");
        }
      }
    );

    return () => {
      clearTimeout(authTimeout);
      authSubscriptionData?.subscription?.unsubscribe();
    };
  }, []);

  const logout = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error("Error logging out:", error);
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
    login, // Provide the new login function
    logout,
    isAuthenticated: !!user,
  };

  if (loading) {
    return <AuthLoadingSkeleton />;
  }

  return (
    <AuthContext.Provider value={authValue}>
      <Router>
        <ToastContainer position="top-right" autoClose={5000} />
        <Routes>
          <Route
            path="/"
            element={user ? <Layout /> : <Navigate to="/login" />}
          >
            <Route index element={<Navigate to="/dashboard" />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="properties" element={<Properties />} />
            <Route path="properties/:id" element={<PropertyDetail />} />
            <Route path="leases" element={<Leases />} />
            <Route path="vendors" element={<Vendors />} />
            <Route path="accounting/*" element={<Accounting />}>
              <Route index element={<Navigate to="overview" />} />
              <Route path="overview" element={<OverviewTab />} />
              <Route path="payments" element={<PaymentsTab />} />
              <Route path="expenses" element={<ExpensesTab />} />
              <Route path="invoices" element={<InvoicesTab />} />
              <Route path="rent-tracker" element={<RentTrackerTab />} />
            </Route>
            <Route path="messages" element={<Messages />} />
            <Route path="tenants" element={<Tenants />} />
            <Route path="maintenance" element={<Maintenance />} />
            <Route path="reports" element={<Reports />} />
            <Route path="settings" element={<Settings />} />
            <Route path="integrations" element={<Integrations />} />
          </Route>
          <Route
            path="/login"
            element={!user ? <LoginPage /> : <Navigate to="/dashboard" />}
          />
          <Route
            path="/register"
            element={!user ? <RegisterPage /> : <Navigate to="/dashboard" />}
          />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route
            path="*"
            element={<Navigate to={user ? "/dashboard" : "/login"} />}
          />
        </Routes>
      </Router>
    </AuthContext.Provider>
  );
}

export default App;
