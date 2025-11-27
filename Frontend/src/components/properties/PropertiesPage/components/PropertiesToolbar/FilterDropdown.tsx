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

  // Status labels mapping for proper display
  const statusLabels: Record<string, string> = {
    ACTIVE: 'Active',
    INACTIVE: 'Inactive',
    DRAFT: 'Draft',
    ARCHIVED: 'Archived',
    RENTED: 'Rented',
    VACANT: 'Vacant',
    PARTIALLY_RENTED: 'Partially Rented',
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={onToggle}
        className={`inline-flex items-center px-4 py-2 border rounded-lg shadow-sm text-sm font-medium transition-colors duration-300 ${
          hasActiveFilters
            ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-600'
            : 'text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600'
        } hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
      >
        <i className="fas fa-filter mr-2"></i>
        Filter
      </button>

      {showFilterMenu && (
        <div className="origin-top-right absolute right-0 mt-2 w-[600px] rounded-md shadow-lg bg-white dark:bg-gray-800 ring-1 ring-black dark:ring-gray-600 ring-opacity-5 focus:outline-none z-50 transition-colors duration-300">
          <div className="p-4">
            {/* Property Type and Status in a grid */}
            <div className="grid grid-cols-2 gap-4 mb-4">
              {/* Property Type */}
              <div>
                <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2 transition-colors duration-300">
                  Property Type
                </h3>
                <div className="space-y-1">
                  {PROPERTY_TYPES.map((type) => (
                    <button
                      key={type}
                      onClick={() => onFilterSelect('propertyType', type)}
                      className={`group flex items-center w-full px-3 py-2 text-sm rounded-md transition-colors duration-300 ${
                        filterOptions.propertyType === type
                          ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      {filterOptions.propertyType === type && (
                        <svg
                          className="mr-2 h-4 w-4 text-blue-500 dark:text-blue-400"
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

              {/* Status */}
              <div>
                <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2 transition-colors duration-300">
                  Status
                </h3>
                <div className="space-y-1">
                  {PROPERTY_STATUSES.map((status) => (
                    <button
                      key={status}
                      onClick={() => onFilterSelect('status', status)}
                      className={`group flex items-center w-full px-3 py-2 text-sm rounded-md transition-colors duration-300 ${
                        filterOptions.status === status
                          ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      {filterOptions.status === status && (
                        <svg
                          className="mr-2 h-4 w-4 text-blue-500 dark:text-blue-400"
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
                      {statusLabels[status] || status}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Date Added - Full Width */}
            <div className="border-t border-gray-100 dark:border-gray-600 pt-3">
              <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2 transition-colors duration-300">
                Date Added
              </h3>
              <div className="grid grid-cols-2 gap-1">
                {DATE_FILTER_OPTIONS.map((option) => (
                  <button
                    key={option.id}
                    onClick={() => onFilterSelect('dateAdded', option.id)}
                    className={`group flex items-center w-full px-3 py-2 text-sm rounded-md transition-colors duration-300 ${
                      filterOptions.dateAdded === option.id
                        ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    {filterOptions.dateAdded === option.id && (
                      <svg
                        className="mr-2 h-4 w-4 text-blue-500 dark:text-blue-400"
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
          </div>

          <div className="p-2">
            <button
              onClick={onClearFilters}
              className="w-full flex justify-center items-center px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors duration-300"
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