import React from "react";
import BrandingPanel from "../components/auth/BrandingPanel";
import LoginForm from "../components/auth/LoginForm";

const LoginPage = () => {
  return (
    <div className="min-h-screen flex bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
      {/* Left Column - Branding Panel */}
      <div className="hidden md:block md:w-3/5">
        <BrandingPanel />
      </div>

      {/* Right Column - Login Form */}
      <div className="w-full md:w-2/5 bg-white dark:bg-gray-900 flex items-center justify-center p-8 md:p-12 transition-colors duration-200">
        <div className="w-full max-w-sm">
          <LoginForm />
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
