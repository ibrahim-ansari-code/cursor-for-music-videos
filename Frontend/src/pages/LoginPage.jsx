import React from "react";
import BrandingPanel from "../components/auth/BrandingPanel";
import LoginForm from "../components/auth/LoginForm";

const LoginPage = () => {
  return (
    <div className="min-h-screen flex bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
      {/* Left Column - Branding Panel (Fixed) */}
      <div className="hidden md:block md:w-3/5 sticky top-0 h-screen overflow-hidden">
        <BrandingPanel />
      </div>

      {/* Right Column - Login Form (Scrollable) */}
      <div className="w-full md:w-2/5 bg-white dark:bg-gray-900 flex items-center justify-center p-8 md:p-12 overflow-y-auto transition-colors duration-200">
        <div className="w-full max-w-sm my-8">
          <LoginForm />
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
