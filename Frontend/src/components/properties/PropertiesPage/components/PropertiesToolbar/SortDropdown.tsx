import React from 'react';
import { SORT_SECTIONS, SortOption } from '../../constants/sortOptions';

interface SortDropdownProps {
  sortOption: SortOption | null;
  showSortMenu: boolean;
  onToggle: () => void;
  onSortSelect: (option: SortOption) => void;
}

export const SortDropdown = React.forwardRef<HTMLDivElement, SortDropdownProps>(({
  sortOption,
  showSortMenu,
  onToggle,
  onSortSelect,
}, ref) => {
  return (
    <div className="relative" ref={ref}>
      <button
        onClick={onToggle}
        className={`inline-flex items-center px-4 py-2 border rounded-lg shadow-sm text-sm font-medium transition-colors duration-300 ${
          sortOption
            ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-600'
            : 'text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600'
        } hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
      >
        <i className="fas fa-sort mr-2"></i>
        Sort
      </button>

      {showSortMenu && (
        <div className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white dark:bg-gray-800 ring-1 ring-black dark:ring-gray-600 ring-opacity-5 divide-y divide-gray-100 dark:divide-gray-600 focus:outline-none z-10 transition-colors duration-300">
          {SORT_SECTIONS.map((section) => (
            <div key={section.title} className="p-2">
              <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2 px-3 pt-1 transition-colors duration-300">
                {section.title}
              </h3>
              <div className="space-y-1">
                {section.options.map((option) => (
                  <button
                    key={option.id}
                    onClick={() => onSortSelect(option.id as SortOption)}
                    className={`group flex items-center w-full px-3 py-2 text-sm rounded-md transition-colors duration-300 ${
                      sortOption === option.id
                        ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    <i className={`${option.icon} mr-2`}></i>
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
});

SortDropdown.displayName = 'SortDropdown';