import React, { useMemo } from 'react';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import useProperties from '../hooks/useProperties';
import NewPropertyModal from '../components/properties/NewPropertyModal';

import { StatusCardsGrid } from '../components/properties/PropertiesPage/components/StatusCards/StatusCardsGrid';
import { PropertyTable } from '../components/properties/PropertiesPage/components/PropertiesTable/PropertyTable';
import { PropertiesToolbar } from '../components/properties/PropertiesPage/components/PropertiesToolbar/PropertiesToolbar';
import { usePropertiesFilters } from '../components/properties/PropertiesPage/hooks/usePropertiesFilters';
import { usePropertiesSorting } from '../components/properties/PropertiesPage/hooks/usePropertiesSorting';
import { usePropertiesActions } from '../components/properties/PropertiesPage/hooks/usePropertiesActions';
import { usePropertiesUI } from '../components/properties/PropertiesPage/hooks/usePropertiesUI';
import { filterProperties } from '../components/properties/PropertiesPage/utils/propertyFiltering';
import { sortProperties } from '../components/properties/PropertiesPage/utils/propertySorting';
import { calculateStatusCounts } from '../components/properties/PropertiesPage/utils/statusCounts';
import { SortOption } from '../components/properties/PropertiesPage/constants/sortOptions';


const Properties: React.FC = () => {
  // Data hooks
  const { properties, loading, error, refetch } = useProperties();
  
  // Feature hooks
  const filtersState = usePropertiesFilters();
  const sortingState = usePropertiesSorting();
  const actionsState = usePropertiesActions();
  const uiState = usePropertiesUI();

  // Memoized filtered and sorted properties
  const filteredProperties = useMemo(() => {
    return filterProperties(
      properties,
      filtersState.statusFilter,
      filtersState.searchTerm,
      filtersState.filterOptions
    );
  }, [properties, filtersState.statusFilter, filtersState.searchTerm, filtersState.filterOptions]);

  const sortedProperties = useMemo(() => {
    return sortProperties(filteredProperties, sortingState.sortOption);
  }, [filteredProperties, sortingState.sortOption]);

  // Memoized status counts
  const statusCounts = useMemo(() => {
    return calculateStatusCounts(filteredProperties);
  }, [filteredProperties]);

  const clearAllFiltersAndSorting = () => {
    filtersState.clearFilters();
    sortingState.clearSorting();
  };

  const handleSortSelect = (option: SortOption) => {
    sortingState.handleSortSelect(option);
    uiState.handleSortToggle(); // Close the menu after selection
  };

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <StatusCardsGrid
        statusCounts={statusCounts}
        statusFilter={filtersState.statusFilter}
        onStatusCardClick={filtersState.handleStatusCardClick}
        onClearFilters={clearAllFiltersAndSorting}
        isLoading={loading}
        hasProperties={properties.length > 0}
      />

      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <PropertiesToolbar
          searchTerm={filtersState.searchTerm}
          onSearch={filtersState.handleSearch}
          filterOptions={filtersState.filterOptions}
          showFilterMenu={uiState.showFilterMenu}
          showSortMenu={uiState.showSortMenu}
          sortOption={sortingState.sortOption}
          onFilterToggle={uiState.handleFilterToggle}
          onSortToggle={uiState.handleSortToggle}
          onFilterSelect={filtersState.handleFilterSelect}
          onSortSelect={handleSortSelect}
          onClearFilters={clearAllFiltersAndSorting}
          onAddProperty={actionsState.handleAddProperty}
          filterMenuRef={uiState.filterMenuRef}
          sortMenuRef={uiState.sortMenuRef}
        />
        <PropertyTable
          properties={sortedProperties}
          loading={loading || actionsState.deletePropertyMutation.isPending}
          error={error}
          onDelete={actionsState.handleDeleteProperty}
          onEdit={actionsState.handleEditProperty}
          onRetry={refetch}
        />
      </div>

      <NewPropertyModal
        isOpen={actionsState.isModalOpen}
        onClose={actionsState.handleCloseModal}
        propertyData={actionsState.currentProperty as Record<string, unknown> | null}
        isEditing={actionsState.isEditing}
      />

      {/* Toast Notifications */}
      <ToastContainer
        position="top-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
      />
    </div>
  );
};

export default Properties;
