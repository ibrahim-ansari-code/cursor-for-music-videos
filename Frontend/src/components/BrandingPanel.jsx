import React from "react";

const BrandingPanel = () => {
  return (
    <div className="hidden md:flex flex-col items-center justify-center h-full w-full bg-gradient-to-br from-brand-green to-brand-teal/90 p-8 text-white">
      <div className="flex flex-col items-center max-w-md text-center">
        <img
          src="/BrikliTransparentWhite.png"
          alt="Brikli Logo"
          className="h-20 w-auto mb-8"
        />
        <h1 className="text-4xl font-bold mb-4">Welcome to Brikli</h1>
        <p className="text-xl mb-6">
          Smarter Property Management, Powered by AI
        </p>
        <div className="space-y-4 mt-8">
          <FeatureItem icon="✓" text="Streamlined tenant management" />
          <FeatureItem icon="✓" text="AI-powered maintenance scheduling" />
          <FeatureItem icon="✓" text="Financial analytics and insights" />
        </div>
      </div>
    </div>
  );
};

const FeatureItem = ({ icon, text }) => (
  <div className="flex items-center">
    <span className="text-white/80 mr-2 text-xl">{icon}</span>
    <span className="text-white">{text}</span>
  </div>
);

export default BrandingPanel;
