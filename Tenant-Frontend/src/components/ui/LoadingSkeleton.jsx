import React from 'react';
import PropTypes from 'prop-types';

/**
 * Generic loading skeleton component for better UX
 */
const LoadingSkeleton = ({ className = '', width = '100%', height = '1rem', rounded = 'rounded' }) => (
  <div 
    className={`animate-pulse bg-gray-200 dark:bg-gray-700 transition-colors ${rounded} ${className}`}
    style={{ width, height }}
  />
);

LoadingSkeleton.propTypes = {
  className: PropTypes.string,
  width: PropTypes.string,
  height: PropTypes.string,
  rounded: PropTypes.string
};

/**
 * Card skeleton for dashboard cards
 */
export const CardSkeleton = () => (
  <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 transition-colors">
    <div className="flex items-start justify-between">
      <div className="flex-1 space-y-2">
        <LoadingSkeleton width="60%" height="0.875rem" />
        <LoadingSkeleton width="80%" height="2rem" />
        <LoadingSkeleton width="40%" height="0.75rem" />
      </div>
      <div className="p-3 rounded-lg bg-gray-100 dark:bg-gray-700 transition-colors">
        <LoadingSkeleton width="1.25rem" height="1.25rem" rounded="rounded-none" />
      </div>
    </div>
  </div>
);

/**
 * Text skeleton for various text elements
 */
export const TextSkeleton = ({ lines = 1, className = '' }) => (
  <div className={`space-y-2 ${className}`}>
    {Array.from({ length: lines }, (_, i) => (
      <LoadingSkeleton 
        key={i}
        width={i === lines - 1 ? '75%' : '100%'} 
        height="1rem"
      />
    ))}
  </div>
);

TextSkeleton.propTypes = {
  lines: PropTypes.number,
  className: PropTypes.string
};

/**
 * Button skeleton
 */
export const ButtonSkeleton = ({ className = '' }) => (
  <LoadingSkeleton 
    className={`${className}`}
    width="120px" 
    height="2.5rem" 
    rounded="rounded-lg" 
  />
);

ButtonSkeleton.propTypes = {
  className: PropTypes.string
};

/**
 * Dashboard loading skeleton with full layout
 */
export const DashboardSkeleton = () => (
  <div className="animate-fade-in">
    {/* Welcome section skeleton */}
    <div className="mb-8">
      <LoadingSkeleton width="300px" height="2.25rem" className="mb-2" />
      <LoadingSkeleton width="450px" height="1.5rem" />
    </div>

    {/* Dashboard cards skeleton */}
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
      {Array.from({ length: 4 }, (_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>

    {/* Recent Payments Table skeleton */}
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 mb-8 transition-colors">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <LoadingSkeleton width="150px" height="1.5rem" />
        <LoadingSkeleton width="80px" height="1rem" />
      </div>
      
      <div className="p-8 text-center">
        <LoadingSkeleton width="250px" height="1rem" className="mx-auto" />
      </div>
    </div>

    {/* Quick Actions skeleton */}
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 transition-colors">
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 bg-gray-100 dark:bg-gray-700 rounded-lg transition-colors">
              <LoadingSkeleton width="2rem" height="2rem" rounded="rounded-none" />
            </div>
            <div className="ml-4 flex-1">
              <LoadingSkeleton width="120px" height="1.5rem" className="mb-2" />
              <LoadingSkeleton width="160px" height="0.875rem" />
            </div>
            <LoadingSkeleton width="1rem" height="1rem" rounded="rounded-none" />
          </div>
        </div>
      ))}
    </div>
  </div>
);

export default LoadingSkeleton;