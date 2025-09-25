import React from 'react';
import PropTypes from 'prop-types';
import { SkeletonLine, SkeletonBlock } from './SkeletonPrimitives';
import { StatusCardSkeleton } from './CardSkeleton';

/**
 * Property detail page skeleton that matches the layout structure
 * Includes header, stats cards, and units table
 */
const PropertyDetailSkeleton = ({ 
  className = '',
  ...props 
}) => (
  <div className={`min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300 ${className}`} {...props}>
    <div className="bg-white dark:bg-gray-800 shadow transition-colors duration-300">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="py-6">
          {/* Breadcrumb */}
          <nav className="flex mb-4" aria-label="Breadcrumb">
            <SkeletonLine width="8rem" height="1rem" />
          </nav>

          {/* Property Header */}
          <div className="lg:flex lg:items-center lg:justify-between">
            <div className="min-w-0 flex-1">
              <SkeletonLine width="15rem" height="2rem" className="mb-2" />
              <div className="mt-1 flex flex-col sm:mt-0 sm:flex-row sm:flex-wrap sm:space-x-6">
                <SkeletonLine width="12rem" height="1rem" />
              </div>
            </div>
            <div className="mt-5 flex lg:mt-0 lg:ml-4">
              <SkeletonBlock width="10rem" height="2.5rem" rounded="md" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
      {/* Stats Cards Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 mb-8">
        <StatusCardSkeleton />
        <StatusCardSkeleton />
        <StatusCardSkeleton />
      </div>

      {/* Units Section */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg transition-colors duration-300">
        {/* Section Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 transition-colors duration-300">
          <div className="flex justify-between items-center">
            <div>
              <SkeletonLine width="6rem" height="1.5rem" className="mb-1" />
              <SkeletonLine width="18rem" height="0.875rem" />
            </div>
            <div className="flex space-x-3">
              <SkeletonBlock width="8rem" height="2.25rem" rounded="md" />
              <SkeletonBlock width="7rem" height="2.25rem" rounded="md" />
            </div>
          </div>
        </div>

        {/* Units Table */}
        <UnitsTableSkeleton />
      </div>
    </main>
  </div>
);

PropertyDetailSkeleton.propTypes = {
  className: PropTypes.string,
};

/**
 * Units table skeleton component
 */
export const UnitsTableSkeleton = ({ rowCount = 6 }) => (
  <div className="overflow-x-auto">
    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
      {/* Table Header */}
      <thead className="bg-gray-50 dark:bg-gray-800 transition-colors duration-300">
        <tr>
          <th className="px-6 py-3 text-left w-3/12">
            <SkeletonLine width="4rem" height="0.75rem" />
          </th>
          <th className="px-6 py-3 text-left w-2/12">
            <SkeletonLine width="3rem" height="0.75rem" />
          </th>
          <th className="px-6 py-3 text-left w-2/12">
            <SkeletonLine width="4rem" height="0.75rem" />
          </th>
          <th className="px-6 py-3 text-left w-2/12">
            <SkeletonLine width="5rem" height="0.75rem" />
          </th>
          <th className="px-6 py-3 text-center w-2/12">
            <SkeletonLine width="4rem" height="0.75rem" />
          </th>
          <th className="px-6 py-3 text-center w-1/12">
            <SkeletonLine width="4rem" height="0.75rem" />
          </th>
        </tr>
      </thead>

      {/* Table Body */}
      <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700 transition-colors duration-300">
        {Array.from({ length: rowCount }, (_, rowIndex) => (
          <tr key={rowIndex}>
            {/* Unit Name */}
            <td className="px-6 py-4 w-3/12">
              <SkeletonLine width="6rem" height="1rem" />
            </td>
            
            {/* Type */}
            <td className="px-6 py-4 w-2/12">
              <SkeletonLine width="5rem" height="1rem" />
            </td>
            
            {/* Rent */}
            <td className="px-6 py-4 w-2/12">
              <SkeletonLine width="4rem" height="1rem" />
            </td>
            
            {/* Current Tenant */}
            <td className="px-6 py-4 w-2/12">
              <SkeletonLine width="7rem" height="1rem" />
            </td>
            
            {/* Status */}
            <td className="px-6 py-4 text-center w-2/12">
              <div className="flex justify-center">
                <SkeletonBlock width="4rem" height="1.5rem" rounded="lg" />
              </div>
            </td>
            
            {/* Actions */}
            <td className="px-6 py-4 text-center w-1/12">
              <div className="flex justify-center space-x-2">
                <SkeletonBlock width="1.5rem" height="1.5rem" rounded="sm" />
                <SkeletonBlock width="1.5rem" height="1.5rem" rounded="sm" />
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

UnitsTableSkeleton.propTypes = {
  rowCount: PropTypes.number,
};

export default PropertyDetailSkeleton;