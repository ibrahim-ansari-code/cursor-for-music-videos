import React from 'react';
import { FilterOptions } from '../../types.js';
import { SortOption } from '../../constants/sortOptions';
import { preloadGoogleMaps } from '../../../../../utils/googleMapsLoader';
import { SearchInput } from './SearchInput';
import { ActiveFiltersDisplay } from './ActiveFiltersDisplay';
import { FilterDropdown } from './FilterDropdown';
import { SortDropdown } from './SortDropdown';

interface PropertiesToolbarProps {
  searchTerm: string;
  onSearch: (e: React.ChangeEvent<HTMLInputElement>) => void;
  filterOptions: FilterOptions;
  showFilterMenu: boolean;
  showSortMenu: boolean;
  sortOption: SortOption | null;
  onFilterToggle: () => void;
  onSortToggle: () => void;
  onFilterSelect: (type: keyof FilterOptions, value: string) => void;
  onSortSelect: (option: SortOption) => void;
  onClearFilters: () => void;
  onAddProperty: () => void;
  filterMenuRef: React.RefObject<HTMLDivElement | null>;
  sortMenuRef: React.RefObject<HTMLDivElement | null>;
}

export const PropertiesToolbar: React.FC<PropertiesToolbarProps> = ({
  searchTerm,
  onSearch,
  filterOptions,
  showFilterMenu,
  showSortMenu,
  sortOption,
  onFilterToggle,
  onSortToggle,
  onFilterSelect,
  onSortSelect,
  onClearFilters,
  onAddProperty,
  filterMenuRef,
  sortMenuRef,
}) => (
  <div className="p-4 border-b border-gray-200 dark:border-gray-600 transition-colors duration-300">
    <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
      <SearchInput searchTerm={searchTerm} onChange={onSearch} />
      <div className="flex items-center gap-4">
        <ActiveFiltersDisplay
          statusFilter={filterOptions.status}
          filterOptions={filterOptions}
          onClearFilters={onClearFilters}
        />

        <button
          className="bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors duration-300"
          onClick={onAddProperty}
          onMouseEnter={() => preloadGoogleMaps()}
          onFocus={() => preloadGoogleMaps()}
        >
          <i className="fas fa-plus"></i>
          Add new property
        </button>

        <FilterDropdown
          ref={filterMenuRef}
          filterOptions={filterOptions}
          showFilterMenu={showFilterMenu}
          onToggle={onFilterToggle}
          onFilterSelect={onFilterSelect}
          onClearFilters={onClearFilters}
        />

        <SortDropdown
          ref={sortMenuRef}
          sortOption={sortOption}
          showSortMenu={showSortMenu}
          onToggle={onSortToggle}
          onSortSelect={onSortSelect}
        />
      </div>
    </div>
  </div>
);