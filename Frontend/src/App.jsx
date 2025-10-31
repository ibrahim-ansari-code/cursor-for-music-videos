import React, { useContext, Suspense, useEffect } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "./styles/ui-feedback.css";
import { SkeletonTheme } from "react-loading-skeleton";
import "react-loading-skeleton/dist/skeleton.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Auth
import { AuthProvider } from "./contexts/AuthProvider";
import { AuthContext } from "./contexts/AuthContext";
import { NotificationProvider } from "./contexts/NotificationContext";

//Theme
import { ThemeProvider } from "./contexts/ThemeSwitch";
// Components
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ResetPassword from "./pages/ResetPassword";
import PageLoader from "./components/ui/PageLoader";

// Pages (lazy-loaded for automatic code splitting)
const Leases = React.lazy(() => import("./pages/Leases"));
const Vendors = React.lazy(() => import("./pages/Vendors"));
const Messages = React.lazy(() => import("./pages/Messages"));
const Properties = React.lazy(() => import("./pages/Properties"));
const PropertyDetail = React.lazy(() => import("./pages/PropertyDetail"));
const Tenants = React.lazy(() => import("./pages/Tenants"));
const TenantProfile = React.lazy(() => import("./pages/TenantProfile"));
const Maintenance = React.lazy(() => import("./pages/Maintenance.tsx"));
const Reports = React.lazy(() => import("./pages/Reports"));
const Settings = React.lazy(() => import("./pages/Settings.tsx"));
const Integrations = React.lazy(() => import("./pages/Integrations"));

// Accounting pages/tabs (lazy-loaded)
const Accounting = React.lazy(() => import("./pages/Accounting"));
const OverviewTab = React.lazy(() => import("./components/accounting/OverviewTab"));
const PaymentsTab = React.lazy(() => import("./components/accounting/PaymentsTab"));
const ExpensesTab = React.lazy(() => import("./components/accounting/ExpensesTab"));
const RentTrackerTab = React.lazy(() => import("./components/accounting/RentTrackerTab"));
const InvoicesTab = React.lazy(() => import("./components/accounting/InvoicesTab"));
// Tenant Profile Tabs (lazy-loaded)
const TenantOverviewTab = React.lazy(() => import("./components/tenants/TenantProfile/tabs/OverviewTab"));
const TenantLeasesTab = React.lazy(() => import("./components/tenants/TenantProfile/tabs/LeasesTab"));
const TenantDocumentsTab = React.lazy(() => import("./components/tenants/TenantProfile/tabs/DocumentsTab/DocumentsTab"));
const TenantMaintenanceTab = React.lazy(() => import("./components/tenants/TenantProfile/tabs/MaintenanceTab"));
const TenantPaymentsTab = React.lazy(() => import("./components/tenants/TenantProfile/tabs/PaymentsTab"));
const TenantMessagingTab = React.lazy(() => import("./components/tenants/TenantProfile/tabs/MessagingTab"));
const TenantBackgroundTab = React.lazy(() => import("./components/tenants/TenantProfile/tabs/BackgroundTab"));
const TenantAssetsTab = React.lazy(() => import("./components/tenants/TenantProfile/tabs/AssetsTab"));
const TenantSettingsTab = React.lazy(() => import("./components/tenants/TenantProfile/tabs/SettingsTab"));

// QuickBooks callback (eager - needed for OAuth flow)
import QuickBooksCallback from "./pages/QuickBooksCallback";

/**
 * Protected Route component
 */
const ProtectedRoute = ({ children }) => {
  const ctx = useContext(AuthContext);
  const user = ctx?.user;
  const loading = ctx?.loading;
  if (loading) return null; // wait until auth is initialized
  return user ? children : <Navigate to="/login" />;
};

/**
 * App Routes component - contains all routing logic
 */
const AppRoutes = () => {
  const { user } = useContext(AuthContext);

  // Idle prefetch of accounting chunks to minimize first navigation latency
  useEffect(() => {
    const prefetch = () => {
      import("./pages/Accounting");
      import("./components/accounting/OverviewTab");
      import("./components/accounting/PaymentsTab");
      import("./components/accounting/ExpensesTab");
      import("./components/accounting/InvoicesTab");
      import("./components/accounting/RentTrackerTab");
    };

    if (typeof window !== "undefined") {
      if ("requestIdleCallback" in window) {
        // @ts-ignore
        window.requestIdleCallback(prefetch);
      } else {
        setTimeout(prefetch, 0);
      }
    }
  }, []);

  return (
    <Routes>
      {/* Public OAuth callback route (no auth gate) */}
      <Route path="/oauth/quickbooks/callback" element={<QuickBooksCallback />} />
      <Route
        path="/"
        element={<ProtectedRoute><Layout /></ProtectedRoute>}
      >
        <Route index element={<Navigate to="/dashboard" />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="properties" element={<Suspense fallback={<PageLoader />}><Properties /></Suspense>} />
        <Route path="properties/:id" element={<Suspense fallback={<PageLoader />}><PropertyDetail /></Suspense>} />
        <Route path="leases" element={<Suspense fallback={<PageLoader />}><Leases /></Suspense>} />
        <Route path="vendors" element={<Suspense fallback={<PageLoader />}><Vendors /></Suspense>} />
        <Route path="accounting/*" element={<Suspense fallback={<PageLoader />}><Accounting /></Suspense>}>
          <Route index element={<Navigate to="overview" />} />
          <Route path="overview" element={<Suspense fallback={<PageLoader />}><OverviewTab /></Suspense>} />
          <Route path="payments" element={<Suspense fallback={<PageLoader />}><PaymentsTab /></Suspense>} />
          <Route path="expenses" element={<Suspense fallback={<PageLoader />}><ExpensesTab /></Suspense>} />
          <Route path="invoices" element={<Suspense fallback={<PageLoader />}><InvoicesTab /></Suspense>} />
          <Route path="rent-tracker" element={<Suspense fallback={<PageLoader />}><RentTrackerTab /></Suspense>} />
        </Route>
        <Route path="messages" element={<Suspense fallback={<PageLoader />}><Messages /></Suspense>} />
        <Route path="tenants" element={<Suspense fallback={<PageLoader />}><Tenants /></Suspense>} />
        <Route path="tenants/:id" element={<Suspense fallback={<PageLoader />}><TenantProfile /></Suspense>}>
          <Route index element={<Suspense fallback={<PageLoader />}><TenantOverviewTab /></Suspense>} />
          <Route path="leases" element={<Suspense fallback={<PageLoader />}><TenantLeasesTab /></Suspense>} />
          <Route path="documents" element={<Suspense fallback={<PageLoader />}><TenantDocumentsTab /></Suspense>} />
          <Route path="maintenance" element={<Suspense fallback={<PageLoader />}><TenantMaintenanceTab /></Suspense>} />
          <Route path="payments" element={<Suspense fallback={<PageLoader />}><TenantPaymentsTab /></Suspense>} />
          <Route path="messaging" element={<Suspense fallback={<PageLoader />}><TenantMessagingTab /></Suspense>} />
          <Route path="background" element={<Suspense fallback={<PageLoader />}><TenantBackgroundTab /></Suspense>} />
          <Route path="assets" element={<Suspense fallback={<PageLoader />}><TenantAssetsTab /></Suspense>} />
          <Route path="settings" element={<Suspense fallback={<PageLoader />}><TenantSettingsTab /></Suspense>} />
        </Route>
        <Route path="maintenance" element={<Suspense fallback={<PageLoader />}><Maintenance /></Suspense>} />
        <Route path="reports" element={<Suspense fallback={<PageLoader />}><Reports /></Suspense>} />
        <Route path="settings" element={<Suspense fallback={<PageLoader />}><Settings /></Suspense>} />
        <Route path="integrations" element={<Suspense fallback={<PageLoader />}><Integrations /></Suspense>} />
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
  );
};

// Create a client for TanStack Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

/**
 * Main App component
 */
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <Router>
          <SkeletonTheme 
            baseColor="#e5e7eb" 
            highlightColor="#f3f4f6"
            // Dark theme will be handled by CSS custom properties in ThemeProvider
          >
            <AuthProvider>
              <NotificationProvider>
                <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
                  <ToastContainer
                    position="top-right"
                    autoClose={5000}
                    theme="colored"
                    toastClassName="!bg-white !text-gray-900 dark:!bg-gray-800 dark:!text-gray-100"
                    bodyClassName="!text-gray-900 dark:!text-gray-100"
                    progressClassName="!bg-blue-500"
                  />
                  <AppRoutes />
                  <div className="recaptcha-notice">
                    Protected by reCAPTCHA v3 —
                    <a href="https://policies.google.com/privacy" rel="noopener noreferrer" target="_blank"> Privacy</a>
                    {" • "}
                    <a href="https://policies.google.com/terms" rel="noopener noreferrer" target="_blank"> Terms</a>
                  </div>
                </div>
              </NotificationProvider>
            </AuthProvider>
          </SkeletonTheme>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;