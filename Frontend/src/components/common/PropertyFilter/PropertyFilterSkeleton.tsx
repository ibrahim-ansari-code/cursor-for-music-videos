import React from "react";

const PropertyFilterSkeleton: React.FC = () => {
  return (
    <div className="inline-flex items-center px-4 py-2 border rounded-lg shadow-sm text-sm font-medium bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 animate-pulse">
      <div className="h-4 w-4 bg-gray-300 dark:bg-gray-600 rounded mr-2"></div>
      <div className="h-4 w-32 bg-gray-300 dark:bg-gray-600 rounded"></div>
      <div className="h-4 w-3 bg-gray-300 dark:bg-gray-600 rounded ml-2"></div>
    </div>
  );
};

export default PropertyFilterSkeleton;
