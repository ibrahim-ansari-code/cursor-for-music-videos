import React from 'react';
import { FilterOptions } from '../../types.js';
import { PROPERTY_TYPES, PROPERTY_STATUSES, DATE_FILTER_OPTIONS } from '../../constants/filterOptions';

interface FilterDropdownProps {
  filterOptions: FilterOptions;
  showFilterMenu: boolean;
  onToggle: () => void;
  onFilterSelect: (type: keyof FilterOptions, value: string) => void;
  onClearFilters: () => void;
}



export const FilterDropdown = React.forwardRef<HTMLDivElement, FilterDropdownProps>(({
  filterOptions,
  showFilterMenu,
  onToggle,
  onFilterSelect,
  onClearFilters,
}, ref) => {
  const hasActiveFilters = Object.values(filterOptions).some((val) => val !== null);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={onToggle}
        className={`inline-flex items-center px-4 py-2 border rounded-lg shadow-sm text-sm font-medium ${
          hasActiveFilters
            ? 'bg-blue-50 text-blue-700 border-blue-300'
            : 'text-gray-700 bg-white border-gray-300'
        } hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
      >
        <i className="fas fa-filter mr-2"></i>
        Filter
      </button>

      {showFilterMenu && (
        <div className="origin-top-right absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 divide-y divide-gray-100 focus:outline-none z-10">
          <div className="p-2">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3 pt-1">
              Property Type
            </h3>
            <div className="space-y-1">
              {PROPERTY_TYPES.map((type) => (
                <button
                  key={type}
                  onClick={() => onFilterSelect('propertyType', type)}
                  className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                    filterOptions.propertyType === type
                      ? 'bg-blue-100 text-blue-800'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {filterOptions.propertyType === type && (
                    <svg
                      className="mr-2 h-4 w-4 text-blue-500"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                  {type}
                </button>
              ))}
            </div>
          </div>

          <div className="p-2">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3 pt-1">
              Status
            </h3>
            <div className="space-y-1">
              {PROPERTY_STATUSES.map((status) => (
                <button
                  key={status}
                  onClick={() => onFilterSelect('status', status)}
                  className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                    filterOptions.status === status
                      ? 'bg-blue-100 text-blue-800'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {filterOptions.status === status && (
                    <svg
                      className="mr-2 h-4 w-4 text-blue-500"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                  {status.charAt(0).toUpperCase() + status.slice(1).toLowerCase()}
                </button>
              ))}
            </div>
          </div>

          <div className="p-2">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3 pt-1">
              Date Added
            </h3>
            <div className="space-y-1">
              {DATE_FILTER_OPTIONS.map((option) => (
                <button
                  key={option.id}
                  onClick={() => onFilterSelect('dateAdded', option.id)}
                  className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                    filterOptions.dateAdded === option.id
                      ? 'bg-blue-100 text-blue-800'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {filterOptions.dateAdded === option.id && (
                    <svg
                      className="mr-2 h-4 w-4 text-blue-500"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <div className="p-2">
            <button
              onClick={onClearFilters}
              className="w-full flex justify-center items-center px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md"
            >
              <i className="fas fa-times-circle mr-2"></i>
              Clear All Filters
            </button>
          </div>
        </div>
      )}
    </div>
  );
});

FilterDropdown.displayName = 'FilterDropdown';