import React, { useContext } from "react";
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

// Components
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
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

/**
 * Protected Route component
 */
const ProtectedRoute = ({ children }) => {
  const { user } = useContext(AuthContext);
  return user ? children : <Navigate to="/login" />;
};

/**
 * App Routes component - contains all routing logic
 */
const AppRoutes = () => {
  const { user } = useContext(AuthContext);

  return (
    <Routes>
      <Route
        path="/"
        element={<ProtectedRoute><Layout /></ProtectedRoute>}
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
      <Router>
        <SkeletonTheme baseColor="#e5e7eb" highlightColor="#f3f4f6">
          <AuthProvider>
            <ToastContainer position="top-right" autoClose={5000} />
            <AppRoutes />
          </AuthProvider>
        </SkeletonTheme>
      </Router>
    </QueryClientProvider>
  );
}

export default App;