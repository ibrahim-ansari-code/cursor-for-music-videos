import React from 'react';
import PropTypes from 'prop-types';
import { SkeletonLine, SkeletonCircle } from './SkeletonPrimitives';

// Column width constants to avoid duplication
const COLUMN_WIDTHS = {
  payments: ['w-4/12', 'w-2/12', 'w-2/12', 'w-2/12', 'w-1/12', 'w-1/12', 'w-1/12'],
  expenses: ['w-3/12', 'w-2/12', 'w-2/12', 'w-2/12', 'w-2/12', 'w-1/12', 'w-1/12', 'w-1/12'],
  invoices: ['w-2/12', 'w-3/12', 'w-2/12', 'w-2/12', 'w-2/12', 'w-1/12', 'w-1/12', 'w-1/12'],
};

/**
 * Accounting table skeleton component for consistent loading states
 * Prevents layout shifts by matching exact table structure
 */
const AccountingTableSkeleton = ({
  rowCount = 8,
  columns = ['w-4/12', 'w-2/12', 'w-2/12', 'w-2/12', 'w-1/12', 'w-1/12'],
  showHeader = true,
  showAvatar = true,
  avatarColumn = 0,
  className = '',
  showFilters = true,
  showActionButtons = false, // Changed default to false since buttons are now inside filters
  showPagination = true,
  ...props
}) => (
  <div className={`space-y-4 ${className}`} {...props}>
    {/* Action Buttons Skeleton - Only show if explicitly requested */}
    {showActionButtons && (
      <div className="flex justify-end space-x-3">
        <SkeletonLine width="120px" height="2.5rem" rounded="md" />
        <SkeletonLine width="80px" height="2.5rem" rounded="md" />
      </div>
    )}

    {/* Filters Skeleton with integrated buttons */}
    {showFilters && (
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border dark:border-gray-700 transition-colors">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0">
          <div className="flex flex-col sm:flex-row sm:space-x-4 space-y-2 sm:space-y-0">
            <div>
              <SkeletonLine width="60px" height="1rem" className="mb-1" />
              <SkeletonLine width="140px" height="2.5rem" rounded="md" />
            </div>
            <div>
              <SkeletonLine width="80px" height="1rem" className="mb-1" />
              <SkeletonLine width="160px" height="2.5rem" rounded="md" />
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <SkeletonLine width="200px" height="2.5rem" rounded="md" />
            <SkeletonLine width="100px" height="2.5rem" rounded="md" />
            <SkeletonLine width="120px" height="2.5rem" rounded="md" />
          </div>
        </div>
      </div>
    )}

    {/* Table Skeleton */}
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden border dark:border-gray-700 transition-colors">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          {showHeader && (
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                {columns.map((width, index) => (
                  <th
                    key={index}
                    className={`px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider ${width} transition-colors`}
                  >
                    <SkeletonLine width="80%" height="0.75rem" />
                  </th>
                ))}
              </tr>
            </thead>
          )}
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700 transition-colors">
            {Array.from({ length: rowCount }, (_, rowIndex) => (
              <tr key={rowIndex} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                {columns.map((width, colIndex) => (
                  <td key={colIndex} className={`px-6 py-4 whitespace-nowrap ${width}`}>
                    {colIndex === avatarColumn && showAvatar ? (
                      <div className="flex items-center">
                        <SkeletonCircle size="2rem" className="mr-4" />
                        <div className="flex-1">
                          <SkeletonLine width="85%" height="1rem" className="mb-1" />
                          <SkeletonLine width="65%" height="0.75rem" />
                        </div>
                      </div>
                    ) : (
                      <div className="text-center">
                        <SkeletonLine 
                          width={
                            colIndex === columns.length - 1 ? '60%' : 
                            colIndex === 0 && !showAvatar ? '90%' : 
                            '75%'
                          } 
                          height="1rem"
                          className="mx-auto"
                        />
                      </div>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {/* Pagination Skeleton */}
      {showPagination && (
        <div className="flex justify-between items-center mt-4 p-4 bg-gray-50 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600 transition-colors">
          <SkeletonLine width="80px" height="2.5rem" rounded="md" />
          <SkeletonLine width="60px" height="1rem" />
          <SkeletonLine width="60px" height="2.5rem" rounded="md" />
        </div>
      )}
    </div>
  </div>
);

AccountingTableSkeleton.propTypes = {
  rowCount: PropTypes.number,
  columns: PropTypes.arrayOf(PropTypes.string),
  showHeader: PropTypes.bool,
  showAvatar: PropTypes.bool,
  avatarColumn: PropTypes.number,
  className: PropTypes.string,
  showFilters: PropTypes.bool,
  showActionButtons: PropTypes.bool,
  showPagination: PropTypes.bool,
};

/**
 * Pre-configured skeleton for Payments table
 */
export const PaymentsTableSkeleton = (props) => (
  <AccountingTableSkeleton
    columns={COLUMN_WIDTHS.payments}
    showAvatar={true}
    avatarColumn={0}
    showActionButtons={false}
    {...props}
  />
);

/**
 * Pre-configured skeleton for Expenses table
 */
export const ExpensesTableSkeleton = (props) => (
  <AccountingTableSkeleton
    columns={COLUMN_WIDTHS.expenses}
    showAvatar={false}
    showActionButtons={false}
    {...props}
  />
);

/**
 * Pre-configured skeleton for Invoices table with unique 4-filter layout
 */
export const InvoicesTableSkeleton = (props) => (
  <div className="space-y-4">
    {/* Invoices-specific Filters Skeleton - 4 filters in grid + search/buttons */}
    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border dark:border-gray-700 transition-colors">
      {/* 4-filter grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <div>
          <SkeletonLine width="60px" height="1rem" className="mb-1" />
          <SkeletonLine width="140px" height="2.5rem" rounded="md" />
        </div>
        <div>
          <SkeletonLine width="80px" height="1rem" className="mb-1" />
          <SkeletonLine width="120px" height="2.5rem" rounded="md" />
        </div>
        <div>
          <SkeletonLine width="60px" height="1rem" className="mb-1" />
          <SkeletonLine width="160px" height="2.5rem" rounded="md" />
        </div>
        <div>
          <SkeletonLine width="50px" height="1rem" className="mb-1" />
          <SkeletonLine width="140px" height="2.5rem" rounded="md" />
        </div>
      </div>
      
      {/* Search bar and action buttons */}
      <div className="flex items-center justify-between">
        <SkeletonLine width="300px" height="2.5rem" rounded="md" />
        <div className="flex items-center space-x-4">
          <SkeletonLine width="100px" height="2.5rem" rounded="md" />
          <SkeletonLine width="120px" height="2.5rem" rounded="md" />
        </div>
      </div>
    </div>

    {/* Table Skeleton */}
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden border dark:border-gray-700 transition-colors">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              {COLUMN_WIDTHS.invoices.map((width, index) => (
                <th
                  key={index}
                  className={`px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider ${width} transition-colors`}
                >
                  <SkeletonLine width="80%" height="0.75rem" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700 transition-colors">
            {Array.from({ length: 8 }, (_, rowIndex) => (
              <tr key={rowIndex} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                {COLUMN_WIDTHS.invoices.map((width, colIndex) => (
                  <td key={colIndex} className={`px-6 py-4 whitespace-nowrap ${width}`}>
                    <div className="text-center">
                      <SkeletonLine 
                        width={colIndex === 0 ? '90%' : '75%'} 
                        height="1rem"
                        className="mx-auto"
                      />
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {/* Pagination Skeleton */}
      <div className="flex justify-between items-center mt-4 p-4 bg-gray-50 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600 transition-colors">
        <SkeletonLine width="80px" height="2.5rem" rounded="md" />
        <SkeletonLine width="60px" height="1rem" />
        <SkeletonLine width="60px" height="2.5rem" rounded="md" />
      </div>
    </div>
  </div>
);

export default AccountingTableSkeleton;
