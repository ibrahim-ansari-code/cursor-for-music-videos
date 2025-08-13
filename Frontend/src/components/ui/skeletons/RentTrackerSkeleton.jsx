import React from 'react';
import PropTypes from 'prop-types';
import { SkeletonLine } from './SkeletonPrimitives';

/**
 * RentTracker skeleton component that matches the exact structure
 * Prevents layout shifts during loading
 */
const RentTrackerSkeleton = ({
  rowCount = 6,
  className = '',
  ...props
}) => (
  <div className={`space-y-4 ${className}`} {...props}>
    {/* Date Filters Skeleton */}
    <div className="bg-white p-4 rounded-lg shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0">
        <div className="flex items-center space-x-4">
          <div>
            <SkeletonLine width="50px" height="1rem" className="mb-1" />
            <SkeletonLine width="120px" height="2.5rem" rounded="md" />
          </div>
          <div>
            <SkeletonLine width="40px" height="1rem" className="mb-1" />
            <SkeletonLine width="100px" height="2.5rem" rounded="md" />
          </div>
        </div>
        
        {/* Search Bar Skeleton */}
        <div className="flex items-center">
          <SkeletonLine width="240px" height="2.5rem" rounded="md" />
        </div>
      </div>
    </div>

    {/* Table Skeleton */}
    <div className="bg-white shadow rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <SkeletonLine width="60px" height="0.75rem" />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <SkeletonLine width="70px" height="0.75rem" />
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <SkeletonLine width="90px" height="0.75rem" className="mx-auto" />
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <SkeletonLine width="80px" height="0.75rem" className="mx-auto" />
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <SkeletonLine width="90px" height="0.75rem" className="mx-auto" />
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <SkeletonLine width="60px" height="0.75rem" className="mx-auto" />
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {Array.from({ length: rowCount }, (_, index) => (
              <tr key={index} className="hover:bg-gray-50">
                {/* Tenant Column */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <SkeletonLine width="120px" height="1rem" />
                </td>
                
                {/* Property Column */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <SkeletonLine width="140px" height="1rem" />
                </td>
                
                {/* Monthly Rent Column */}
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <SkeletonLine width="80px" height="1rem" className="mx-auto" />
                </td>
                
                {/* Paid This Month Column */}
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <SkeletonLine width="60px" height="1rem" className="mx-auto" />
                </td>
                
                {/* Amount Due Column */}
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <SkeletonLine width="80px" height="1rem" className="mx-auto" />
                </td>
                
                {/* Status Column */}
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <SkeletonLine width="60px" height="1.25rem" rounded="full" className="mx-auto" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  </div>
);

RentTrackerSkeleton.propTypes = {
  rowCount: PropTypes.number,
  className: PropTypes.string,
};

export default RentTrackerSkeleton;
