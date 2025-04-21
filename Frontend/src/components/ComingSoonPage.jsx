import React from 'react';

const ComingSoonPage = ({ 
  title = "Coming Soon", 
  description = "We're working hard to bring you this feature soon.", 
  icon = "fa-rocket",
  ctaText = "Get notified when we launch",
  showCta = false,
  accentColor = "blue" 
}) => {
  // Color variants based on the accent color
  const colorVariants = {
    blue: {
      accent: "text-blue-600",
      button: "bg-blue-600 hover:bg-blue-700",
      iconBg: "bg-blue-100"
    },
    green: {
      accent: "text-green-600",
      button: "bg-green-600 hover:bg-green-700",
      iconBg: "bg-green-100"
    },
    purple: {
      accent: "text-purple-600",
      button: "bg-purple-600 hover:bg-purple-700",
      iconBg: "bg-purple-100"
    },
    indigo: {
      accent: "text-indigo-600",
      button: "bg-indigo-600 hover:bg-indigo-700",
      iconBg: "bg-indigo-100"
    },
    orange: {
      accent: "text-orange-600",
      button: "bg-orange-600 hover:bg-orange-700",
      iconBg: "bg-orange-100"
    }
  };

  const colors = colorVariants[accentColor] || colorVariants.blue;
  
  return (
    <div className="h-full flex items-center justify-center p-6">
      <div className="text-center max-w-lg mx-auto p-6 bg-white rounded-xl shadow-sm border border-gray-100">
        <div className={`${colors.iconBg} ${colors.accent} w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-6`}>
          <i className={`fas ${icon} text-2xl`}></i>
        </div>
        
        <h2 className={`text-3xl font-bold mb-3 ${colors.accent}`}>{title}</h2>
        
        <p className="text-gray-600 mb-8">{description}</p>
        
        {showCta && (
          <div className="mb-4">
            <div className="flex items-center">
              <input 
                type="email" 
                placeholder="Your email address" 
                className="flex-grow px-4 py-2 border border-gray-300 rounded-l-md focus:outline-none focus:ring-2 focus:ring-opacity-50 focus:ring-blue-500"
              />
              <button 
                className={`px-4 py-2 rounded-r-md text-white ${colors.button} transition duration-150`}
              >
                Notify Me
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2">We'll notify you when this feature becomes available.</p>
          </div>
        )}
        
        <div className="pt-4 border-t border-gray-100 mt-6">
          <p className="text-sm text-gray-500">
            Have questions? Contact us at <a href="mailto:support@brikli.com" className={`${colors.accent} hover:underline`}>support@brikli.com</a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default ComingSoonPage; 