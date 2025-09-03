import { useState } from 'react';
import { FilterOptions } from '../types.js';

export const usePropertiesFilters = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    propertyType: null,
    status: null,
    dateAdded: null,
  });

  const handleStatusCardClick = (status: string) => {
    setFilterOptions((prev) => ({
      ...prev,
      status: status.toUpperCase() === prev.status ? null : status.toUpperCase()
    }));
  };

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const handleFilterSelect = (type: keyof FilterOptions, value: string) => {
    setFilterOptions((prev) => ({
      ...prev,
      [type]: value === prev[type] ? null : value,
    }));
  };

  const clearFilters = () => {
    setFilterOptions({
      propertyType: null,
      status: null,
      dateAdded: null,
    });
    setSearchTerm('');
  };

  return {
    statusFilter: filterOptions.status, // Keep backward compatibility for components that expect statusFilter
    searchTerm,
    filterOptions,
    handleStatusCardClick,
    handleSearch,
    handleFilterSelect,
    clearFilters,
  };
};