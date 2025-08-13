import React from 'react';
import PropTypes from 'prop-types';
import { SkeletonLine, SkeletonCircle } from './SkeletonPrimitives';

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
  showActionButtons = true,
  showPagination = true,
  ...props
}) => (
  <div className={`space-y-4 ${className}`} {...props}>
    {/* Action Buttons Skeleton */}
    {showActionButtons && (
      <div className="flex justify-end space-x-3">
        <SkeletonLine width="120px" height="2.5rem" rounded="md" />
        <SkeletonLine width="80px" height="2.5rem" rounded="md" />
      </div>
    )}

    {/* Filters Skeleton */}
    {showFilters && (
      <div className="bg-white p-4 rounded-lg shadow-sm">
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
          <div className="flex items-center">
            <SkeletonLine width="240px" height="2.5rem" rounded="md" />
          </div>
        </div>
      </div>
    )}

    {/* Table Skeleton */}
    <div className="bg-white shadow rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          {showHeader && (
            <thead className="bg-gray-50">
              <tr>
                {columns.map((width, index) => (
                  <th
                    key={index}
                    className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${width}`}
                  >
                    <SkeletonLine width="80%" height="0.75rem" />
                  </th>
                ))}
              </tr>
            </thead>
          )}
          <tbody className="bg-white divide-y divide-gray-200">
            {Array.from({ length: rowCount }, (_, rowIndex) => (
              <tr key={rowIndex} className="hover:bg-gray-50">
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
        <div className="flex justify-between items-center mt-4 p-4">
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
    columns={['w-4/12', 'w-2/12', 'w-2/12', 'w-2/12', 'w-1/12', 'w-1/12', 'w-1/12']}
    showAvatar={true}
    avatarColumn={0}
    {...props}
  />
);

/**
 * Pre-configured skeleton for Expenses table
 */
export const ExpensesTableSkeleton = (props) => (
  <AccountingTableSkeleton
    columns={['w-3/12', 'w-2/12', 'w-2/12', 'w-2/12', 'w-2/12', 'w-1/12', 'w-1/12', 'w-1/12']}
    showAvatar={false}
    {...props}
  />
);

/**
 * Pre-configured skeleton for Invoices table
 */
export const InvoicesTableSkeleton = (props) => (
  <AccountingTableSkeleton
    columns={['w-2/12', 'w-3/12', 'w-2/12', 'w-2/12', 'w-2/12', 'w-1/12', 'w-1/12', 'w-1/12']}
    showAvatar={false}
    {...props}
  />
);

export default AccountingTableSkeleton;
