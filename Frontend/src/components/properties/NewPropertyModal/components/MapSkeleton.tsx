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
    <div className={`relative bg-gray-100 rounded-lg overflow-hidden ${className}`} style={style}>
      {/* Map placeholder with gradient animation */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-100 via-gray-200 to-gray-100 animate-pulse">
        {/* Map controls placeholder */}
        <div className="absolute top-3 right-3 space-y-2">
          <div className="w-10 h-10 bg-white rounded shadow-md"></div>
          <div className="w-10 h-10 bg-white rounded shadow-md"></div>
        </div>
        
        {/* Map pin placeholder */}
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
          <div className="w-8 h-8 bg-blue-400 rounded-full opacity-50 animate-ping"></div>
          <div className="w-8 h-8 bg-blue-500 rounded-full absolute top-0"></div>
        </div>
        
        {/* Loading text */}
        <div className="absolute bottom-4 left-4 bg-white px-3 py-2 rounded shadow-md">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            <span className="text-sm text-gray-600 ml-2">Loading map</span>
          </div>
        </div>
      </div>
      
      {/* Grid lines to simulate map tiles */}
      <svg className="absolute inset-0 w-full h-full opacity-10" xmlns="http://www.w3.org/2000/svg">
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