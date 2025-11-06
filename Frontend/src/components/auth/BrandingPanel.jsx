import React from "react";

// Icon components for better maintainability
const ComputerIcon = () => (
  <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-label="AI automation icon">
    <path 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      strokeWidth={2} 
      d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" 
    />
  </svg>
);

const CalculatorIcon = () => (
  <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-label="Automated accounting icon">
    <path 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      strokeWidth={2} 
      d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" 
    />
  </svg>
);

const LightningIcon = () => (
  <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-label="Time-saving efficiency icon">
    <path 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      strokeWidth={2} 
      d="M13 10V3L4 14h7v7l9-11h-7z" 
    />
  </svg>
);

const BrandingPanel = () => {
  const features = [
    {
      icon: <ComputerIcon />,
      title: "Let AI handle your paperwork",
      description: "Instantly extract data from receipts, invoices, and leases—turning hours of work into seconds."
    },
    {
      icon: <CalculatorIcon />,
      title: "Automated accounting, zero headaches",
      description: "From rent collection to tax-ready reports, Brikli keeps your books balanced and stress-free."
    },
    {
      icon: <LightningIcon />,
      title: "Your time is your most valuable asset",
      description: "Manage properties in minutes, not hours. Focus on growing your portfolio while Brikli handles the rest."
    }
  ];

  return (
    <div className="hidden md:flex flex-col h-full w-full bg-brand-green text-white relative overflow-hidden"
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
              alt="Brikli - Landlord Portal"
              width={192}
              height={96}
              className="h-auto w-48 max-w-full drop-shadow-2xl mx-auto animate-fade-in"
              loading="eager"
            />
            <div>
              <h1 className="text-5xl font-bold mb-1 tracking-tight leading-tight">
                Welcome to Your<br />
                Landlord Portal
              </h1>
              <p className="text-xl text-white/80 font-light tracking-wide">
                Property Management Made Simple with AI
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
