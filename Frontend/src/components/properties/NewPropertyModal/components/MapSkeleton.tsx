import React from 'react';

/**
 * Skeleton loader for Google Maps
 * Shows a smooth loading state while the map is being initialized
 */
interface MapSkeletonProps {
  className?: string;
  style?: React.CSSProperties;
}

const MapSkeleton: React.FC<MapSkeletonProps> = ({ className = '', style }) => {
  // Generate unique pattern ID to avoid conflicts with multiple instances
  const patternId = `grid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  
  return (
    <div className={`relative bg-gray-100 dark:bg-gray-800 rounded-lg overflow-hidden transition-colors ${className}`} style={style}>
      {/* Map placeholder with gradient animation */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-100 via-gray-200 to-gray-100 dark:from-gray-800 dark:via-gray-700 dark:to-gray-800 animate-pulse transition-colors">
        {/* Map controls placeholder */}
        <div className="absolute top-3 right-3 space-y-2">
          <div className="w-10 h-10 bg-white dark:bg-gray-600 rounded shadow-md transition-colors"></div>
          <div className="w-10 h-10 bg-white dark:bg-gray-600 rounded shadow-md transition-colors"></div>
        </div>
        
        {/* Map pin placeholder */}
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
          <div className="w-8 h-8 bg-blue-400 dark:bg-blue-500 rounded-full opacity-50 animate-ping transition-colors"></div>
          <div className="w-8 h-8 bg-blue-500 dark:bg-blue-400 rounded-full absolute top-0 transition-colors"></div>
        </div>
        
        {/* Loading text */}
        <div className="absolute bottom-4 left-4 bg-white dark:bg-gray-700 px-3 py-2 rounded shadow-md border dark:border-gray-600 transition-colors">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce transition-colors" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2 h-2 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce transition-colors" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2 h-2 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce transition-colors" style={{ animationDelay: '300ms' }}></div>
            <span className="text-sm text-gray-600 dark:text-gray-300 ml-2 transition-colors">Loading map</span>
          </div>
        </div>
      </div>
      
      {/* Grid lines to simulate map tiles */}
      <svg className="absolute inset-0 w-full h-full opacity-10 dark:opacity-20" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id={patternId} width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="gray" strokeWidth="1"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill={`url(#${patternId})`} />
      </svg>
    </div>
  );
};

export default MapSkeleton;