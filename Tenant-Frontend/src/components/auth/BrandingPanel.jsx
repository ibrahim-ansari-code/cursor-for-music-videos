import React from "react";

// Icon components for better maintainability
const HomeIcon = () => (
  <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-label="Rental home management icon">
    <path 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      strokeWidth={2} 
      d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" 
    />
  </svg>
);

const CreditCardIcon = () => (
  <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-label="Easy rent payments icon">
    <path 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      strokeWidth={2} 
      d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" 
    />
  </svg>
);

const WrenchIcon = () => (
  <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-label="Maintenance requests icon">
    <path 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      strokeWidth={2} 
      d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" 
    />
    <path 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      strokeWidth={2} 
      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" 
    />
  </svg>
);

const BrandingPanel = () => {
  const features = [
    {
      icon: <HomeIcon />,
      title: "Your Rental Home",
      description: "Access lease details, payment history, and important documents all in one secure place."
    },
    {
      icon: <CreditCardIcon />,
      title: "Easy Rent Payments",
      description: "Pay rent online, set up autopay, and track your payment history with complete transparency."
    },
    {
      icon: <WrenchIcon />,
      title: "Maintenance Requests",
      description: "Submit and track maintenance requests with photos and updates directly from your portal."
    }
  ];

  return (
    <div className="hidden md:flex flex-col h-full w-full bg-gradient-to-br from-brand-green to-brand-teal text-white relative overflow-hidden"
         style={{ padding: 'calc(32px + 1.5625vw)' }}>
      {/* Background effects */}
      <BackgroundEffects />
      
      {/* Main content */}
      <div className="flex flex-col justify-center h-full max-w-xl mx-auto w-full relative z-10">
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          gap: 'calc(48px + 1.5625vw)' 
        }}>
          {/* Header section */}
          <div className="text-center"
               style={{ 
                 display: 'flex', 
                 flexDirection: 'column', 
                 gap: 'calc(24px + 0.78125vw)' 
               }}>
            <img
              src="/BrikliTransparentWhite.png"
              alt="Brikli - Tenant Portal"
              width={192}
              height={96}
              className="h-auto w-48 max-w-full drop-shadow-2xl mx-auto animate-fade-in"
              loading="eager"
            />
            <div>
              <h1 className="text-5xl font-bold mb-1 tracking-tight leading-tight">
                Welcome to Your
              </h1>
              <h1 className="text-5xl font-bold mb-1 tracking-tight leading-tight">
                Tenant Portal
              </h1>
              <p className="text-xl text-white/80 font-light tracking-wide">
                Manage your rental experience with ease
              </p>
            </div>
          </div>
          
          {/* Features list */}
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            gap: 'calc(24px + 0.78125vw)' 
          }}>
            {features.map((feature, index) => (
              <FeatureItem key={index} {...feature} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

const BackgroundEffects = () => (
  <>
    {/* Gradient orbs */}
    <div className="absolute inset-0">
      <div className="absolute top-0 right-0 w-72 h-72 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl" />
      <div className="absolute bottom-0 left-0 w-72 h-72 bg-white/10 rounded-full translate-y-1/2 -translate-x-1/2 blur-3xl" />
      <div className="absolute top-1/2 left-1/2 w-48 h-48 bg-brand-teal/20 rounded-full -translate-x-1/2 -translate-y-1/2 blur-2xl" />
    </div>
    
    {/* Dot pattern */}
    <div 
      className="absolute inset-0 opacity-20"
      style={{
        backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px)',
        backgroundSize: '40px 40px'
      }}
    />
    
    {/* Right edge accent */}
    <div className="absolute right-0 top-0 h-full w-px bg-gradient-to-b from-transparent via-white/20 to-transparent" />
  </>
);

const FeatureItem = ({ icon, title, description }) => (
  <div className="flex group cursor-default items-start"
       style={{ gap: 'calc(24px + 0.78125vw)' }}>
    <div className="flex-shrink-0 mt-3.5">
      <div className="w-14 h-14 bg-white/10 backdrop-blur-sm rounded-2xl flex items-center justify-center group-hover:bg-white/20 transition-all duration-300 group-hover:scale-105 shadow-sm">
        {icon}
      </div>
    </div>
    <div className="flex-1">
      <h3 className="font-semibold text-white text-lg mb-2 leading-tight">
        {title}
      </h3>
      <p className="text-white/70 text-base leading-relaxed">
        {description}
      </p>
    </div>
  </div>
);

export default BrandingPanel;