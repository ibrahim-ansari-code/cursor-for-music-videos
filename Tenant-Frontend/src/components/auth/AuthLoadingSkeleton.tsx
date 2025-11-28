import React from 'react';

const AuthLoadingSkeleton: React.FC = () => {
  return (
    <div className="min-h-screen flex bg-gray-50 dark:bg-gray-900">
      {/* Left Column - Branding Panel Skeleton */}
      <div className="hidden md:block md:w-3/5 bg-gradient-to-br from-brand-green to-brand-teal relative overflow-hidden"
           style={{ padding: 'calc(32px + 1.5625vw)' }}>
        
        {/* Background effects to match BrandingPanel */}
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
        
        <div className="flex flex-col h-full max-w-xl mx-auto w-full relative z-10"
             style={{ paddingTop: 'calc(40px + 2.5vh)' }}>
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            gap: 'calc(48px + 1.5625vw)' 
          }} className="animate-pulse">
            {/* Header section skeleton */}
            <div className="text-center"
                 style={{ 
                   display: 'flex', 
                   flexDirection: 'column', 
                   gap: 'calc(24px + 0.78125vw)' 
                 }}>
              <div className="h-24 w-48 bg-white/20 rounded-lg mx-auto"></div>
              <div>
                <div className="h-12 w-72 bg-white/20 rounded-lg mx-auto mb-1"></div>
                <div className="h-6 w-96 bg-white/20 rounded-lg mx-auto"></div>
              </div>
            </div>
            
            {/* Features list skeleton */}
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              gap: 'calc(24px + 0.78125vw)' 
            }}>
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-start"
                     style={{ gap: 'calc(24px + 0.78125vw)' }}>
                  <div className="w-14 h-14 bg-white/10 rounded-2xl flex-shrink-0 mt-3.5"></div>
                  <div className="flex-1">
                    <div className="h-6 w-48 bg-white/20 rounded mb-2"></div>
                    <div className="h-4 w-full bg-white/20 rounded mb-1"></div>
                    <div className="h-4 w-3/4 bg-white/20 rounded"></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Right Column - Form Skeleton */}
      <div className="w-full md:w-2/5 bg-white dark:bg-gray-800 flex items-center justify-center p-8 md:p-12">
        <div className="w-full max-w-sm animate-pulse">
          <div className="space-y-6">
            <div className="space-y-2">
              <div className="h-8 w-32 bg-gray-200 dark:bg-gray-700 rounded transition-colors"></div>
              <div className="h-4 w-48 bg-gray-200 dark:bg-gray-700 rounded transition-colors"></div>
            </div>
            
            <div className="space-y-4">
              <div className="h-10 w-full bg-gray-200 dark:bg-gray-700 rounded transition-colors"></div>
              <div className="h-10 w-full bg-gray-200 dark:bg-gray-700 rounded transition-colors"></div>
              <div className="h-10 w-full bg-gray-200 dark:bg-gray-700 rounded transition-colors"></div>
            </div>
            
            <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded ml-auto transition-colors"></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthLoadingSkeleton;

