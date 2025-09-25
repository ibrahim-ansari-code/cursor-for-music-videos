import React from 'react';
import PropTypes from 'prop-types';
import { SkeletonLine, SkeletonCircle } from './SkeletonPrimitives';

/**
 * Configurable table skeleton that preserves exact table layout
 * Prevents layout shifts by matching real table structure
 */
const TableSkeleton = ({
  rowCount = 8,
  columns = ['w-4/12', 'w-3/12', 'w-2/12', 'w-2/12', 'w-1/12'],
  showHeader = true,
  showAvatar = true,
  avatarColumn = 0,
  className = '',
  tableClassName = '',
  ...props
}) => (
  <div className={`dark-panel dark-shadow rounded-lg overflow-hidden transition-colors ${className}`} {...props}>
    <div className="overflow-x-auto">
      <table className={`min-w-full divide-y dark-divider ${tableClassName}`}>
        {showHeader && (
          <thead className="dark-input">
            <tr>
              {columns.map((width, index) => (
                <th
                  key={index}
                  className={`px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider transition-colors ${width}`}
                >
                  <SkeletonLine width="80%" height="0.75rem" />
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody className="dark-panel divide-y dark-divider">
          {Array.from({ length: rowCount }, (_, rowIndex) => (
            <tr key={rowIndex} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
              {columns.map((width, colIndex) => (
                <td key={colIndex} className={`px-6 py-4 whitespace-nowrap ${width}`}>
                  {colIndex === avatarColumn && showAvatar ? (
                    <div className="flex items-center">
                      <SkeletonCircle size="2.5rem" className="mr-4" />
                      <div className="flex-1">
                        <SkeletonLine width="80%" height="1rem" className="mb-1" />
                        <SkeletonLine width="60%" height="0.75rem" />
                      </div>
                    </div>
                  ) : (
                    <SkeletonLine 
                      width={
                        colIndex === columns.length - 1 ? '60%' : 
                        colIndex === 0 && !showAvatar ? '90%' : 
                        '80%'
                      } 
                      height="1rem" 
                    />
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

TableSkeleton.propTypes = {
  rowCount: PropTypes.number,
  columns: PropTypes.arrayOf(PropTypes.string),
  showHeader: PropTypes.bool,
  showAvatar: PropTypes.bool,
  avatarColumn: PropTypes.number,
  className: PropTypes.string,
  tableClassName: PropTypes.string,
};

/**
 * Pre-configured skeleton for Properties table
 */
export const PropertiesTableSkeleton = (props) => (
  <TableSkeleton
    columns={['w-4/12', 'w-2/12', 'w-3/12', 'w-1/12', 'w-1/12', 'w-1/12']}
    showAvatar={true}
    avatarColumn={0}
    {...props}
  />
);

/**
 * Pre-configured skeleton for Leases table  
 */
export const LeasesTableSkeleton = (props) => (
  <TableSkeleton
    columns={['w-4/12', 'w-2/12', 'w-2/12', 'w-2/12', 'w-1/12', 'w-1/12']}
    showAvatar={true}
    avatarColumn={0}
    {...props}
  />
);

/**
 * Pre-configured skeleton for Tenants table
 */
export const TenantsTableSkeleton = (props) => (
  <TableSkeleton
    columns={['w-4/12', 'w-3/12', 'w-2/12', 'w-2/12', 'w-1/12']}
    showAvatar={true}
    avatarColumn={0}
    {...props}
  />
);

export default TableSkeleton;
