import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/contexts/AuthProvider';
import ProtectedRoute from '@/components/ProtectedRoute';
import Layout from '@/components/Layout';
import ErrorBoundary from '@/components/ErrorBoundary';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import ResetPassword from '@/pages/ResetPassword';
import Payments from '@/pages/Payments';
import AcceptInvite from '@/pages/AcceptInvite';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 30, // 30 minutes (formerly cacheTime)
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

/**
 * App Component
 * Main application entry point with routing configuration
 * Follows React Router v7 patterns with protected routes
 */
function App() {
  return (
    <QueryClientProvider client={queryClient}>
    <Router>
      <AuthProvider>
        <ErrorBoundary>
          <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/accept-invite" element={<AcceptInvite />} />
          
          {/* Protected routes with Layout */}
          <Route path="/" element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }>
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="payments" element={<Payments />} />
            <Route path="documents" element={
              <div className="flex items-center justify-center h-64">
                <h1 className="text-2xl font-bold text-gray-900">Documents - Coming Soon</h1>
              </div>
            } />
            <Route path="maintenance" element={
              <div className="flex items-center justify-center h-64">
                <h1 className="text-2xl font-bold text-gray-900">Maintenance - Coming Soon</h1>
              </div>
            } />
            <Route path="notifications" element={
              <div className="flex items-center justify-center h-64">
                <h1 className="text-2xl font-bold text-gray-900">Notifications - Coming Soon</h1>
              </div>
            } />
            <Route path="settings" element={
              <div className="flex items-center justify-center h-64">
                <h1 className="text-2xl font-bold text-gray-900">Settings - Coming Soon</h1>
              </div>
            } />
            {/* Default redirect to dashboard */}
            <Route index element={<Navigate to="/dashboard" replace />} />
          </Route>
          
          
          {/* 404 catch-all */}
          <Route path="*" element={
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
              <div className="text-center">
                <h1 className="text-6xl font-bold text-gray-900">404</h1>
                <p className="mt-2 text-lg text-gray-600">Page not found</p>
                <Link to="/dashboard" className="mt-4 inline-block text-teal-600 hover:text-teal-700">
                  Return to Dashboard
                </Link>
              </div>
            </div>
          } />
          </Routes>
        </ErrorBoundary>
      </AuthProvider>
    </Router>
    </QueryClientProvider>
  );
}

export default App;

