import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ResetPassword from './pages/ResetPassword';

/**
 * App Component
 * Main application entry point with routing configuration
 * Follows React Router v6 patterns with protected routes
 */
function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          
          {/* Protected routes */}
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />
          
          {/* Placeholder routes - to be implemented */}
          <Route path="/payments" element={
            <ProtectedRoute>
              <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <h1 className="text-2xl font-bold text-gray-900">Payments - Coming Soon</h1>
              </div>
            </ProtectedRoute>
          } />
          
          <Route path="/documents" element={
            <ProtectedRoute>
              <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <h1 className="text-2xl font-bold text-gray-900">Documents - Coming Soon</h1>
              </div>
            </ProtectedRoute>
          } />
          
          <Route path="/maintenance" element={
            <ProtectedRoute>
              <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <h1 className="text-2xl font-bold text-gray-900">Maintenance - Coming Soon</h1>
              </div>
            </ProtectedRoute>
          } />
          
          <Route path="/notifications" element={
            <ProtectedRoute>
              <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <h1 className="text-2xl font-bold text-gray-900">Notifications - Coming Soon</h1>
              </div>
            </ProtectedRoute>
          } />
          
          <Route path="/settings" element={
            <ProtectedRoute>
              <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <h1 className="text-2xl font-bold text-gray-900">Settings - Coming Soon</h1>
              </div>
            </ProtectedRoute>
          } />
          
          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          
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
      </AuthProvider>
    </Router>
  );
}

export default App;
