import React from "react";
import BrandingPanel from "../components/BrandingPanel";
import RegisterForm from "../components/RegisterForm";

const RegisterPage = () => {
  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Left Column - Branding Panel */}
      <div className="hidden md:block md:w-1/2 lg:w-2/5">
        <BrandingPanel />
      </div>

      {/* Right Column - Registration Form */}
      <div className="w-full md:w-1/2 lg:w-3/5 bg-white flex items-center justify-center">
        <div className="w-full max-w-md px-6 py-8 md:px-8 md:py-12 mx-auto rounded-2xl md:shadow-lg md:border border-gray-100">
          <RegisterForm />
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
