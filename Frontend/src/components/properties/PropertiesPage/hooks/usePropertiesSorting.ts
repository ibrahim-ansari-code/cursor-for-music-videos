import { useState } from 'react';
import { SortOption } from '../constants/sortOptions';

export const usePropertiesSorting = () => {
  const [sortOption, setSortOption] = useState<SortOption | null>(null);

  const handleSortSelect = (option: SortOption) => {
    setSortOption(option === sortOption ? null : option);
  };

  const clearSorting = () => {
    setSortOption(null);
  };

  return {
    sortOption,
    handleSortSelect,
    clearSorting,
  };
};