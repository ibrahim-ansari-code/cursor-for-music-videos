import React, { useMemo, useEffect } from 'react';
import 'react-toastify/dist/ReactToastify.css';
import useProperties from '../hooks/useProperties';
import { preloadGoogleMaps } from '../utils/googleMapsLoader';
import NewPropertyModal from '../components/properties/NewPropertyModal';
import EditPropertyModal from '../components/properties/EditPropertyModal';
import { DeletePropertyConfirmation } from '../components/properties/DeletePropertyConfirmation';

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

  // Preload Google Maps when Properties page mounts for optimal UX
  useEffect(() => {
    try {
      preloadGoogleMaps();
    } catch (err) {
      // Guard against any synchronous errors in preload function
      if (import.meta.env.DEV) {
        console.warn('Failed to preload Google Maps', err);
      }
    }
  }, []);

  const clearAllFiltersAndSorting = () => {
    filtersState.clearFilters();
    sortingState.clearSorting();
  };

  const handleSortSelect = (option: SortOption) => {
    sortingState.handleSortSelect(option);
    uiState.handleSortToggle(); // Close the menu after selection
  };

  return (
    <div className="p-6 max-w-[1600px] mx-auto bg-gray-50 dark:bg-gray-900 min-h-screen transition-colors duration-200">
      <StatusCardsGrid
        statusCounts={statusCounts}
        statusFilter={filtersState.statusFilter}
        onStatusCardClick={filtersState.handleStatusCardClick}
        onClearFilters={clearAllFiltersAndSorting}
        isLoading={loading}
        hasProperties={properties.length > 0}
      />

      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm overflow-hidden border border-gray-200 dark:border-gray-700">
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
          onDelete={actionsState.handleDeleteClick}
          onEdit={actionsState.handleEditProperty}
          onRetry={refetch}
        />
      </div>

      {/* Create Property Modal */}
      <NewPropertyModal
        isOpen={actionsState.isCreateModalOpen}
        onClose={actionsState.handleCloseCreateModal}
        propertyData={null}
        isEditing={false}
      />

      {/* Edit Property Modal */}
      {actionsState.currentProperty && (
        <EditPropertyModal
          isOpen={actionsState.isEditModalOpen}
          onClose={actionsState.handleCloseEditModal}
          propertyData={actionsState.currentProperty}
          onSuccess={refetch}
        />
      )}

      {/* Delete Property Confirmation Modal */}
      <DeletePropertyConfirmation
        isOpen={actionsState.isDeleteModalOpen}
        onClose={actionsState.handleCancelDelete}
        onConfirm={actionsState.handleConfirmDelete}
        property={actionsState.propertyToDelete}
        isDeleting={actionsState.deletePropertyMutation.isPending}
      />
    </div>
  );
};

export default Properties;
