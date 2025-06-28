import React from "react";

const AuthLoadingSkeleton = () => {
  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Left Column - Branding Panel Skeleton */}
      <div className="hidden md:block md:w-3/5 bg-gradient-to-br from-brand-green to-brand-teal relative overflow-hidden">
        <div className="flex flex-col h-full max-w-xl mx-auto w-full relative z-10 pt-20 p-14">
          <div className="space-y-16 animate-pulse">
            {/* Logo skeleton */}
            <div className="text-center space-y-8">
              <div className="h-24 w-48 bg-white/20 rounded-lg mx-auto"></div>
              <div className="space-y-3">
                <div className="h-12 w-72 bg-white/20 rounded-lg mx-auto"></div>
                <div className="h-6 w-96 bg-white/20 rounded-lg mx-auto"></div>
              </div>
            </div>
            
            {/* Features skeleton */}
            <div className="space-y-8">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex gap-8 items-start">
                  <div className="w-14 h-14 bg-white/20 rounded-2xl flex-shrink-0"></div>
                  <div className="flex-1 space-y-3">
                    <div className="h-6 w-48 bg-white/20 rounded"></div>
                    <div className="h-4 w-full bg-white/20 rounded"></div>
                    <div className="h-4 w-3/4 bg-white/20 rounded"></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Right Column - Form Skeleton */}
      <div className="w-full md:w-2/5 bg-white flex items-center justify-center p-8 md:p-12">
        <div className="w-full max-w-sm animate-pulse">
          <div className="space-y-6">
            <div className="space-y-2">
              <div className="h-8 w-32 bg-gray-200 rounded"></div>
              <div className="h-4 w-48 bg-gray-200 rounded"></div>
            </div>
            
            <div className="space-y-4">
              <div className="h-10 w-full bg-gray-200 rounded"></div>
              <div className="h-10 w-full bg-gray-200 rounded"></div>
              <div className="h-10 w-full bg-gray-200 rounded"></div>
            </div>
            
            <div className="h-4 w-32 bg-gray-200 rounded ml-auto"></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthLoadingSkeleton;