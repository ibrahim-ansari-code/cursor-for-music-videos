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
    {/* Summary Cards Skeleton */}
    <div className="grid gap-4" style={{gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))"}}>
      {/* Total Expected */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm transition-colors">
        <SkeletonLine width="90px" height="0.875rem" className="mb-2" />
        <SkeletonLine width="120px" height="1.75rem" className="mb-1" />
      </div>
      {/* Total Collected */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm transition-colors">
        <SkeletonLine width="100px" height="0.875rem" className="mb-2" />
        <SkeletonLine width="80px" height="1.75rem" className="mb-1" />
      </div>
      {/* Outstanding */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm transition-colors">
        <SkeletonLine width="80px" height="0.875rem" className="mb-2" />
        <SkeletonLine width="120px" height="1.75rem" className="mb-1" />
      </div>
      {/* Collection Rate */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm transition-colors">
        <SkeletonLine width="100px" height="0.875rem" className="mb-2" />
        <SkeletonLine width="60px" height="1.75rem" className="mb-1" />
      </div>
      {/* Status Breakdown */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm transition-colors">
        <SkeletonLine width="120px" height="0.875rem" className="mb-2" />
        <div className="flex items-center space-x-2">
          <SkeletonLine width="30px" height="1rem" />
          <SkeletonLine width="30px" height="1rem" />
          <SkeletonLine width="30px" height="1rem" />
        </div>
      </div>
    </div>

    {/* Export Buttons Skeleton */}
    <div className="flex justify-end space-x-3">
      <SkeletonLine width="100px" height="2.5rem" rounded="md" />
      <SkeletonLine width="100px" height="2.5rem" rounded="md" />
    </div>

    {/* Filters Skeleton - matches exact grid layout from RentTracker */}
    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm transition-colors">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Month Filter */}
        <div>
          <SkeletonLine width="50px" height="1rem" className="mb-1" />
          <SkeletonLine width="120px" height="2.5rem" rounded="md" />
        </div>
        {/* Year Filter */}
        <div>
          <SkeletonLine width="40px" height="1rem" className="mb-1" />
          <SkeletonLine width="100px" height="2.5rem" rounded="md" />
        </div>
        {/* Property Filter */}
        <div>
          <SkeletonLine width="60px" height="1rem" className="mb-1" />
          <SkeletonLine width="160px" height="2.5rem" rounded="md" />
        </div>
        {/* Status Filter */}
        <div>
          <SkeletonLine width="50px" height="1rem" className="mb-1" />
          <SkeletonLine width="140px" height="2.5rem" rounded="md" />
        </div>
        {/* Search Filter - spans 2 columns on larger screens */}
        <div className="sm:col-span-2 lg:col-span-2 xl:col-span-2">
          <SkeletonLine width="50px" height="1rem" className="mb-1" />
          <SkeletonLine width="100%" height="2.5rem" rounded="md" />
        </div>
      </div>
    </div>

    {/* Table Skeleton */}
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden transition-colors">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              {/* TENANT */}
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <SkeletonLine width="60px" height="0.75rem" />
              </th>
              {/* PROPERTY */}
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <SkeletonLine width="70px" height="0.75rem" />
              </th>
              {/* RENT */}
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <SkeletonLine width="40px" height="0.75rem" className="mx-auto" />
              </th>
              {/* PAID */}
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <SkeletonLine width="40px" height="0.75rem" className="mx-auto" />
              </th>
              {/* DUE */}
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <SkeletonLine width="30px" height="0.75rem" className="mx-auto" />
              </th>
              {/* DUE DATE */}
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <SkeletonLine width="70px" height="0.75rem" className="mx-auto" />
              </th>
              {/* LAST PAYMENT */}
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <SkeletonLine width="90px" height="0.75rem" className="mx-auto" />
              </th>
              {/* STATUS */}
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <SkeletonLine width="50px" height="0.75rem" className="mx-auto" />
              </th>
              {/* ACTIONS */}
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <SkeletonLine width="60px" height="0.75rem" className="mx-auto" />
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {Array.from({ length: rowCount }, (_, index) => (
              <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                {/* Tenant Column */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <SkeletonLine width="120px" height="1rem" />
                </td>
                
                {/* Property Column */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <SkeletonLine width="140px" height="1rem" className="mb-1" />
                    <SkeletonLine width="80px" height="0.75rem" />
                  </div>
                </td>
                
                {/* Rent Column */}
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <SkeletonLine width="80px" height="1rem" className="mx-auto" />
                </td>
                
                {/* Paid Column */}
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <SkeletonLine width="60px" height="1rem" className="mx-auto" />
                </td>
                
                {/* Due Column */}
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <SkeletonLine width="80px" height="1rem" className="mx-auto" />
                </td>
                
                {/* Due Date Column */}
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <div>
                    <SkeletonLine width="80px" height="1rem" className="mx-auto mb-1" />
                    <SkeletonLine width="60px" height="0.75rem" className="mx-auto" />
                  </div>
                </td>
                
                {/* Last Payment Column */}
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <SkeletonLine width="40px" height="1rem" className="mx-auto" />
                </td>
                
                {/* Status Column */}
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <SkeletonLine width="80px" height="1.25rem" rounded="md" className="mx-auto" />
                </td>
                
                {/* Actions Column */}
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <SkeletonLine width="120px" height="2rem" rounded="md" className="mx-auto" />
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
