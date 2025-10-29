import React from 'react';

interface PageLoaderProps {
  message?: string;
}

/**
 * Generic page loader for Suspense fallbacks
 * Provides a consistent, minimal loading state that doesn't compete with component-level skeletons
 */
const PageLoader: React.FC<PageLoaderProps> = ({ message = 'Loading...' }) => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="flex flex-col items-center gap-3">
        <div className="relative">
          {/* Animated spinner */}
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-gray-200 dark:border-gray-700 border-t-green-600 dark:border-t-green-400"></div>
          {/* Inner pulse */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="h-6 w-6 rounded-full bg-green-600 dark:bg-green-400 animate-pulse opacity-20"></div>
          </div>
        </div>
        <p className="text-sm font-medium text-gray-600 dark:text-gray-400 animate-pulse">
          {message}
        </p>
      </div>
    </div>
  );
};

export default PageLoader;

