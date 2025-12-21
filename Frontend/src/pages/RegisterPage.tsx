import React from "react";
import BrandingPanel from "../components/auth/BrandingPanel";
import RegisterForm from "../components/auth/RegisterForm";

const RegisterPage: React.FC = () => {
  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Left Column - Branding Panel (Fixed) */}
      <div className="hidden md:block md:w-3/5 sticky top-0 h-screen overflow-hidden">
        <BrandingPanel />
      </div>

      {/* Right Column - Registration Form (Scrollable) */}
      <div className="w-full md:w-2/5 bg-white flex items-center justify-center p-8 md:p-12 overflow-y-auto">
        <div className="w-full max-w-sm my-8">
          <RegisterForm />
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;

