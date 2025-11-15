import { useState, useCallback, useMemo } from 'react';
import { Property } from '../../../../types/property';

/**
 * Hook for managing property selection state
 * Handles individual selection, select all, and selection counts
 */
export const usePropertySelection = (properties: Property[]) => {
  const [selectedPropertyIds, setSelectedPropertyIds] = useState<Set<number>>(new Set());

  // Check if all properties in current page are selected
  const allSelected = useMemo(() => {
    if (properties.length === 0) return false;
    return properties.every((property) => property.id && selectedPropertyIds.has(property.id));
  }, [properties, selectedPropertyIds]);

  // Check if some (but not all) properties are selected
  const someSelected = useMemo(() => {
    if (properties.length === 0) return false;
    const selectedCount = properties.filter(
      (property) => property.id && selectedPropertyIds.has(property.id)
    ).length;
    return selectedCount > 0 && selectedCount < properties.length;
  }, [properties, selectedPropertyIds]);

  // Toggle individual property selection
  const toggleProperty = useCallback((propertyId: number) => {
    setSelectedPropertyIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(propertyId)) {
        newSet.delete(propertyId);
      } else {
        newSet.add(propertyId);
      }
      return newSet;
    });
  }, []);

  // Toggle select all for current page
  const toggleSelectAll = useCallback(() => {
    setSelectedPropertyIds((prev) => {
      const newSet = new Set(prev);
      const currentPageIds = properties
        .map((p) => p.id)
        .filter((id): id is number => id !== undefined && id !== null);

      if (allSelected) {
        // Deselect all on current page
        currentPageIds.forEach((id) => newSet.delete(id));
      } else {
        // Select all on current page
        currentPageIds.forEach((id) => newSet.add(id));
      }
      return newSet;
    });
  }, [properties, allSelected]);

  // Clear all selections
  const clearSelection = useCallback(() => {
    setSelectedPropertyIds(new Set());
  }, []);

  // Get selected properties array
  const selectedProperties = useMemo(() => {
    return properties.filter(
      (property) => property.id && selectedPropertyIds.has(property.id)
    );
  }, [properties, selectedPropertyIds]);

  // Get selected property IDs array
  const selectedPropertyIdsArray = useMemo(() => {
    return Array.from(selectedPropertyIds);
  }, [selectedPropertyIds]);

  // Check if a property is selected
  const isSelected = useCallback(
    (propertyId: number | undefined) => {
      if (!propertyId) return false;
      return selectedPropertyIds.has(propertyId);
    },
    [selectedPropertyIds]
  );

  return {
    selectedPropertyIds,
    selectedPropertyIdsArray,
    selectedProperties,
    allSelected,
    someSelected,
    toggleProperty,
    toggleSelectAll,
    clearSelection,
    isSelected,
  };
};

