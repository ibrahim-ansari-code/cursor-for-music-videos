import React, { useMemo, useEffect, useState } from "react";
import { toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import useProperties from "../hooks/useProperties";
import { preloadGoogleMaps } from "../utils/googleMapsLoader";
import NewPropertyModal from "../components/properties/NewPropertyModal";
import EditPropertyModal from "../components/properties/EditPropertyModal";
import { DeletePropertyConfirmation } from "../components/properties/DeletePropertyConfirmation";
import { BulkDeleteConfirmationModal } from "../components/properties/BulkDeleteConfirmationModal";

import { StatusCardsGrid } from "../components/properties/PropertiesPage/components/StatusCards/StatusCardsGrid";
import { PropertyTable } from "../components/properties/PropertiesPage/components/PropertiesTable/PropertyTable";
import { PropertiesToolbar } from "../components/properties/PropertiesPage/components/PropertiesToolbar/PropertiesToolbar";
import { usePropertiesFilters } from "../components/properties/PropertiesPage/hooks/usePropertiesFilters";
import { usePropertiesSorting } from "../components/properties/PropertiesPage/hooks/usePropertiesSorting";
import { usePropertiesActions } from "../components/properties/PropertiesPage/hooks/usePropertiesActions";
import { usePropertiesUI } from "../components/properties/PropertiesPage/hooks/usePropertiesUI";
import { usePropertySelection } from "../components/properties/PropertiesPage/hooks/usePropertySelection";
import { useBulkDeleteProperties } from "../hooks/usePropertiesMutations";
import { filterProperties } from "../components/properties/PropertiesPage/utils/propertyFiltering";
import { sortProperties } from "../components/properties/PropertiesPage/utils/propertySorting";
import { calculateStatusCounts } from "../components/properties/PropertiesPage/utils/statusCounts";
import { SortOption } from "../components/properties/PropertiesPage/constants/sortOptions";
import { reportError } from "../utils/error-reporting";

const Properties: React.FC = () => {
  // Data hooks
  const { properties, loading, error } = useProperties();

  // Feature hooks
  const filtersState = usePropertiesFilters();
  const sortingState = usePropertiesSorting();
  const actionsState = usePropertiesActions();
  const uiState = usePropertiesUI();

  // Bulk delete state
  const [showBulkDeleteModal, setShowBulkDeleteModal] = useState(false);
  const bulkDeleteMutation = useBulkDeleteProperties();

  // Memoized filtered and sorted properties
  const filteredProperties = useMemo(() => {
    return filterProperties(
      properties,
      filtersState.statusFilter,
      filtersState.searchTerm,
      filtersState.filterOptions
    );
  }, [
    properties,
    filtersState.statusFilter,
    filtersState.searchTerm,
    filtersState.filterOptions,
  ]);

  const sortedProperties = useMemo(() => {
    return sortProperties(filteredProperties, sortingState.sortOption);
  }, [filteredProperties, sortingState.sortOption]);

  // Selection hook - uses sorted properties (current page)
  const selectionState = usePropertySelection(sortedProperties);

  // Memoized status counts
  const statusCounts = useMemo(() => {
    return calculateStatusCounts(filteredProperties);
  }, [filteredProperties]);

  // Convert error to string for PropertyTable
  const errorMessage = useMemo(() => {
    if (!error) return null;
    if (typeof error === "string") return error;
    return error.message || "An error occurred";
  }, [error]);

  // Preload Google Maps when Properties page mounts for optimal UX
  useEffect(() => {
    try {
      preloadGoogleMaps();
    } catch (err) {
      // Guard against any synchronous errors in preload function
      if (import.meta.env.DEV) {
        console.warn("Failed to preload Google Maps", err);
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

  // Handle bulk delete click
  const handleBulkDeleteClick = () => {
    if (selectionState.selectedPropertyIdsArray.length === 0) return;
    setShowBulkDeleteModal(true);
  };

  // Handle confirmed bulk deletion
  const handleConfirmBulkDelete = async () => {
    if (selectionState.selectedPropertyIdsArray.length === 0) return;

    const propertyIds = selectionState.selectedPropertyIdsArray;

    try {
      await bulkDeleteMutation.mutateAsync(propertyIds);
      toast.success(
        `${propertyIds.length} ${
          propertyIds.length === 1 ? "property" : "properties"
        } deleted successfully`
      );
      setShowBulkDeleteModal(false);
      selectionState.clearSelection();
    } catch (err: any) {
      console.error("Failed to bulk delete properties:", err);

      // Report error to Sentry
      reportError(
        err instanceof Error ? err : new Error(String(err)),
        {
          component: "Properties",
          action: "bulk_delete_properties",
          extra: {
            propertyIds,
            propertyCount: propertyIds.length,
          },
        },
        "error"
      );

      // Extract error message with better hierarchy
      const errorMessage =
        err?.response?.data?.detail ||
        err?.data?.detail ||
        err?.message ||
        "Failed to delete selected properties. Please try again.";

      // Close modal on error so user can see the error toast
      setShowBulkDeleteModal(false);
      toast.error(errorMessage, {
        autoClose: 5000,
      });
    }
  };

  // Handle close bulk delete modal
  const handleCloseBulkDeleteModal = () => {
    if (!bulkDeleteMutation.isPending) {
      setShowBulkDeleteModal(false);
    }
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
          selectedCount={selectionState.selectedPropertyIdsArray.length}
          onBulkDelete={handleBulkDeleteClick}
        />
        <PropertyTable
          properties={sortedProperties}
          loading={
            loading ||
            actionsState.deletePropertyMutation.isPending ||
            bulkDeleteMutation.isPending
          }
          error={errorMessage}
          onDelete={actionsState.handleDeleteClick}
          onEdit={actionsState.handleEditProperty}
          allSelected={selectionState.allSelected}
          someSelected={selectionState.someSelected}
          onToggleSelectAll={selectionState.toggleSelectAll}
          isSelected={selectionState.isSelected}
          onToggleProperty={selectionState.toggleProperty}
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

      {/* Bulk Delete Confirmation Modal */}
      <BulkDeleteConfirmationModal
        isOpen={showBulkDeleteModal}
        onClose={handleCloseBulkDeleteModal}
        onConfirm={handleConfirmBulkDelete}
        properties={selectionState.selectedProperties}
        isDeleting={bulkDeleteMutation.isPending}
      />
    </div>
  );
};

export default Properties;
