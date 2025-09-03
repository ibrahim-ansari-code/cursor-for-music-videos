import React from 'react';
import { FilterOptions } from '../../types.js';
import { StatusBadge } from '../PropertiesTable/StatusBadge';

interface ActiveFiltersDisplayProps {
  statusFilter: string | null;
  filterOptions: FilterOptions;
  onClearFilters: () => void;
}



export const ActiveFiltersDisplay: React.FC<ActiveFiltersDisplayProps> = ({
  statusFilter,
  filterOptions,
  onClearFilters,
}) => {
  const hasActiveFilters = statusFilter || 
    filterOptions.propertyType !== null || 
    filterOptions.dateAdded !== null;

  if (!hasActiveFilters) return null;

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-500">Filtered by:</span>
      {statusFilter && <StatusBadge status={statusFilter} />}
      {filterOptions.propertyType && (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
          Type: {filterOptions.propertyType}
        </span>
      )}
      {filterOptions.dateAdded && (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
          Date:{' '}
          {filterOptions.dateAdded === 'last-week'
            ? 'Last week'
            : filterOptions.dateAdded === 'last-month'
            ? 'Last month'
            : 'Last year'}
        </span>
      )}
      <button
        onClick={onClearFilters}
        className="text-sm text-gray-500 hover:text-gray-700"
      >
        <i className="fas fa-times-circle"></i>
      </button>
    </div>
  );
};