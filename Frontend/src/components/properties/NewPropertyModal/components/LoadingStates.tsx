import React from 'react';
import { motion } from 'framer-motion';

// Skeleton loader for form fields
export const FieldSkeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`animate-pulse ${className}`}>
    <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded mb-2 transition-colors"></div>
    <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded transition-colors"></div>
  </div>
);

// Skeleton loader for the location step
export const LocationStepSkeleton: React.FC = () => (
  <div className="space-y-6">
    <div className="animate-pulse">
      <div className="h-6 w-48 bg-gray-200 dark:bg-gray-700 rounded mb-2 transition-colors"></div>
      <div className="h-4 w-96 bg-gray-200 dark:bg-gray-700 rounded transition-colors"></div>
    </div>
    
    <FieldSkeleton />
    
    <div className="animate-pulse">
      <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded mb-2 transition-colors"></div>
      <div className="h-96 bg-gray-200 dark:bg-gray-700 rounded-lg transition-colors"></div>
    </div>
    
    <div className="grid grid-cols-2 gap-4">
      <FieldSkeleton />
      <FieldSkeleton />
      <FieldSkeleton />
      <FieldSkeleton />
    </div>
  </div>
);

// Loading spinner for async operations
export const LoadingSpinner: React.FC<{ 
  size?: 'sm' | 'md' | 'lg';
  message?: string;
}> = ({ size = 'md', message }) => {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };
  
  return (
    <div className="flex flex-col items-center justify-center">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        className={`border-2 border-blue-600 dark:border-blue-400 border-t-transparent rounded-full ${sizeClasses[size]} transition-colors`}
      />
      {message && (
        <p className="mt-3 text-sm text-gray-600 dark:text-gray-400 transition-colors">{message}</p>
      )}
    </div>
  );
};

// Full page loading overlay
export const LoadingOverlay: React.FC<{ 
  isVisible: boolean;
  message?: string;
}> = ({ isVisible, message = 'Loading...' }) => {
  if (!isVisible) return null;
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm z-50 flex items-center justify-center transition-colors"
    >
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 flex items-center space-x-4 border dark:border-gray-700 transition-colors">
        <LoadingSpinner size="md" />
        <span className="text-gray-700 dark:text-gray-200 font-medium transition-colors">{message}</span>
      </div>
    </motion.div>
  );
};

// Progress bar for multi-step operations
export const ProgressBar: React.FC<{ 
  progress: number;
  message?: string;
}> = ({ progress, message }) => (
  <div className="w-full">
    {message && (
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2 transition-colors">{message}</p>
    )}
    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden transition-colors">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        transition={{ duration: 0.3 }}
        className="h-full bg-gradient-to-r from-blue-500 to-blue-600 dark:from-blue-400 dark:to-blue-500"
      />
    </div>
    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 transition-colors">{Math.min(100, Math.max(0, Math.round(progress)))}% complete</p>
  </div>
);

// Inline loading indicator for buttons
export const ButtonSpinner: React.FC<{ className?: string }> = ({ className = '' }) => (
  <svg
    className={`animate-spin h-4 w-4 ${className}`}
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
  >
    <circle
      className="opacity-25"
      cx="12"
      cy="12"
      r="10"
      stroke="currentColor"
      strokeWidth="4"
    />
    <path
      className="opacity-75"
      fill="currentColor"
      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
    />
  </svg>
);

// Placeholder for empty states
export const EmptyStatePlaceholder: React.FC<{
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}> = ({ icon, title, description, action }) => (
  <div className="text-center py-12">
    <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full mb-4 transition-colors">
      {icon}
    </div>
    <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2 transition-colors">{title}</h3>
    {description && (
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 transition-colors">{description}</p>
    )}
    {action}
  </div>
);

// Error state component
export const ErrorState: React.FC<{
  error: Error | string;
  onRetry?: () => void;
}> = ({ error, onRetry }) => (
  <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg p-4 transition-colors">
    <div className="flex items-start">
      <div className="flex-shrink-0">
        <svg
          className="h-5 w-5 text-red-400 dark:text-red-300"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
            clipRule="evenodd"
          />
        </svg>
      </div>
      <div className="ml-3 flex-1">
        <h3 className="text-sm font-medium text-red-800 dark:text-red-200 transition-colors">
          {typeof error === 'string' ? error : error.message}
        </h3>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-2 text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 underline transition-colors"
          >
            Try again
          </button>
        )}
      </div>
    </div>
  </div>
);

// Success animation
export const SuccessAnimation: React.FC<{ message?: string }> = ({ message = 'Success!' }) => (
  <motion.div
    initial={{ scale: 0 }}
    animate={{ scale: 1 }}
    transition={{ type: 'spring', stiffness: 200, damping: 15 }}
    className="text-center"
  >
    <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full mb-4 transition-colors">
      <motion.svg
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="w-8 h-8 text-green-600 dark:text-green-400"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        viewBox="0 0 24 24"
      >
        <motion.path
          d="M5 13l4 4L19 7"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </motion.svg>
    </div>
    <p className="text-lg font-medium text-gray-900 dark:text-gray-100 transition-colors">{message}</p>
  </motion.div>
);