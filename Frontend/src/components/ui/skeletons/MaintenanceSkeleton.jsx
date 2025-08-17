import React from 'react';
import PropTypes from 'prop-types';
import { SkeletonLine, SkeletonCircle, SkeletonPill } from './SkeletonPrimitives';
import { StatusCardSkeleton } from './CardSkeleton';

/**
 * Maintenance dashboard skeleton that matches the actual layout structure
 * Includes status cards, tabs, and table layout
 */
const MaintenanceSkeleton = ({
  rowCount = 6,
  className = '',
  ...props
}) => (
  <div className={`p-6 ${className}`} {...props}>
    {/* Status Cards Grid */}
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <StatusCardSkeleton />
      <StatusCardSkeleton />
      <StatusCardSkeleton />
      <StatusCardSkeleton />
    </div>

    {/* Main Table Container */}
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Header with tabs and new request button */}
      <div className="flex justify-between items-center px-6 py-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center space-x-1">
          {/* Tabs */}
          <SkeletonPill width="7rem" height="2.25rem" />
          <SkeletonPill width="6rem" height="2.25rem" />
          <SkeletonPill width="8rem" height="2.25rem" />
          <SkeletonPill width="7.5rem" height="2.25rem" />
        </div>
        <div className="flex items-center">
          {/* New Request Button */}
          <SkeletonPill width="12rem" height="2.25rem" />
        </div>
      </div>

      {/* Table */}
      <MaintenanceTableSkeleton rowCount={rowCount} />

      {/* Pagination Footer */}
      <div className="px-6 py-4 flex items-center justify-between border-t border-gray-200">
        <div className="flex items-center">
          <SkeletonLine width="15rem" height="0.875rem" />
        </div>
        <div className="flex items-center space-x-2">
          <SkeletonPill width="4rem" height="2rem" />
          <SkeletonPill width="4rem" height="2rem" />
          <SkeletonPill width="3rem" height="2rem" />
        </div>
      </div>
    </div>
  </div>
);

MaintenanceSkeleton.propTypes = {
  rowCount: PropTypes.number,
  className: PropTypes.string,
};

/**
 * Table skeleton specifically for maintenance requests
 * Matches the MaintenanceTable component structure
 */
export const MaintenanceTableSkeleton = ({ rowCount = 6 }) => (
  <div className="overflow-x-auto">
    <table className="min-w-full divide-y divide-gray-200">
      {/* Table Header */}
      <thead className="bg-gray-50">
        <tr>
          <th className="px-6 py-3 text-center w-1/12">
            <SkeletonLine width="1.5rem" height="0.75rem" />
          </th>
          <th className="px-6 py-3 text-left w-2/12">
            <SkeletonLine width="4rem" height="0.75rem" />
          </th>
          <th className="px-6 py-3 text-left w-2/12">
            <SkeletonLine width="5rem" height="0.75rem" />
          </th>
          <th className="px-6 py-3 text-left w-2/12">
            <SkeletonLine width="4rem" height="0.75rem" />
          </th>
          <th className="px-6 py-3 text-center w-1/12">
            <SkeletonLine width="3rem" height="0.75rem" />
          </th>
          <th className="px-6 py-3 text-center w-1/12">
            <SkeletonLine width="4rem" height="0.75rem" />
          </th>
          <th className="px-6 py-3 text-center w-2/12">
            <SkeletonLine width="5rem" height="0.75rem" />
          </th>
          <th className="px-6 py-3 text-center w-1/12">
            <SkeletonLine width="4rem" height="0.75rem" />
          </th>
          <th className="px-6 py-3 text-center w-1/12">
            <SkeletonLine width="3rem" height="0.75rem" />
          </th>
        </tr>
      </thead>

      {/* Table Body */}
      <tbody className="bg-white divide-y divide-gray-200">
        {Array.from({ length: rowCount }, (_, rowIndex) => (
          <tr key={rowIndex} className="hover:bg-gray-50">
            {/* # */}
            <td className="px-6 py-4 text-center w-1/12">
              <SkeletonLine width="1.5rem" height="1rem" />
            </td>
            
            {/* Issue Title */}
            <td className="px-6 py-4 w-2/12">
              <SkeletonLine width="85%" height="1rem" className="mb-1" />
              <SkeletonLine width="65%" height="0.75rem" />
            </td>
            
            {/* Property/Unit */}
            <td className="px-6 py-4 w-2/12">
              <SkeletonLine width="80%" height="1rem" />
            </td>
            
            {/* Tenant */}
            <td className="px-6 py-4 w-2/12">
              <SkeletonLine width="75%" height="1rem" />
            </td>
            
            {/* Request Date */}
            <td className="px-6 py-4 text-center w-1/12">
              <SkeletonLine width="4rem" height="0.875rem" />
            </td>
            
            {/* Priority */}
            <td className="px-6 py-4 text-center w-1/12">
              <SkeletonPill width="4rem" height="1.5rem" />
            </td>
            
            {/* Assigned To */}
            <td className="px-6 py-4 text-center w-2/12">
              <SkeletonLine width="5rem" height="0.875rem" />
            </td>
            
            {/* Status */}
            <td className="px-6 py-4 text-center w-1/12">
              <div className="flex justify-center">
                <SkeletonPill width="4.5rem" height="1.5rem" />
              </div>
            </td>
            
            {/* Actions */}
            <td className="px-6 py-4 text-center w-1/12">
              <div className="flex justify-center space-x-1">
                <SkeletonCircle size="1.5rem" />
                <SkeletonCircle size="1.5rem" />
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

MaintenanceTableSkeleton.propTypes = {
  rowCount: PropTypes.number,
};

export default MaintenanceSkeleton;