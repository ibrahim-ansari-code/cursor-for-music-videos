import React, { useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '@/contexts/AuthContext';
import BrandingPanel from '@/components/auth/BrandingPanel';
import LoginForm from '@/components/auth/LoginForm';

/**
 * Login Page Component
 * Full-page authentication screen with split design matching landlord portal
 * Uses proper responsive design and viewport-based sizing
 */
const Login: React.FC = () => {
  const navigate = useNavigate();
  const authContext = useContext(AuthContext);
  const { user, isAuthenticated } = authContext || {};

  // Redirect if already authenticated
  useEffect(() => {
    // Only redirect if both conditions are met to avoid edge cases
    if (isAuthenticated && user) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, user, navigate]);

  const handleLoginSuccess = (): void => {
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Left Column - Branding Panel */}
      <div className="hidden md:block md:w-3/5">
        <BrandingPanel />
      </div>

      {/* Right Column - Login Form */}
      <div className="w-full md:w-2/5 bg-white flex items-center justify-center p-8 md:p-12">
        <div className="w-full max-w-sm">
          <LoginForm onSuccess={handleLoginSuccess} />
        </div>
      </div>
    </div>
  );
};

export default Login;

