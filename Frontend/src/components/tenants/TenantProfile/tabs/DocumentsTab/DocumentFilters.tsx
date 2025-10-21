/**
 * Document Filters Component
 * 
 * Search and filter controls for tenant documents.
 * Includes search input, category/type/status dropdowns, and upload button.
 */

import React, { useState, useEffect } from 'react';
import { DocumentFilters, DocumentCategory, DocumentStatus, CATEGORY_LABELS, STATUS_LABELS } from '../../../../../types/tenantDocument';
import { useDocumentTaxonomy } from '../../../../../hooks/useTenantDocuments';

interface DocumentFiltersProps {
  filters: DocumentFilters;
  onFiltersChange: (filters: DocumentFilters) => void;
  onUploadClick: () => void;
  documentCount?: number;
}

const DocumentFiltersComponent: React.FC<DocumentFiltersProps> = ({
  filters,
  onFiltersChange,
  onUploadClick,
  documentCount = 0,
}) => {
  const [searchInput, setSearchInput] = useState(filters.search || '');
  const [selectedCategory, setSelectedCategory] = useState<DocumentCategory | ''>
(filters.category || '');
  const [selectedType, setSelectedType] = useState(filters.type || '');
  const [selectedStatus, setSelectedStatus] = useState<DocumentStatus | ''>(filters.status || '');

  // Fetch taxonomy for category/type dropdowns
  const { data: taxonomy } = useDocumentTaxonomy();

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      // Avoid triggering a filter change if the search input hasn't actually changed
      if (searchInput !== (filters.search || '')) {
        onFiltersChange({ ...filters, search: searchInput || undefined });
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchInput, filters, onFiltersChange]);

  // Handle category change
  const handleCategoryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const category = e.target.value as DocumentCategory | '';
    setSelectedCategory(category);
    setSelectedType(''); // Reset type when category changes
    
    onFiltersChange({
      ...filters,
      category: category || undefined,
      type: undefined, // Clear type filter
    });
  };

  // Handle type change
  const handleTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const type = e.target.value;
    setSelectedType(type);
    
    onFiltersChange({
      ...filters,
      type: type || undefined,
    });
  };

  // Handle status change
  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const status = e.target.value as DocumentStatus | '';
    setSelectedStatus(status);
    
    onFiltersChange({
      ...filters,
      status: status || undefined,
    });
  };

  // Get types for selected category
  const availableTypes = selectedCategory && taxonomy
    ? taxonomy.categories.find(cat => cat.key === selectedCategory)?.types || []
    : [];

  // Clear all filters
  const handleClearFilters = () => {
    setSearchInput('');
    setSelectedCategory('');
    setSelectedType('');
    setSelectedStatus('');
    onFiltersChange({});
  };

  const hasActiveFilters = searchInput || selectedCategory || selectedType || selectedStatus;

  return (
    <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        {/* Left side: Filters */}
        <div className="flex flex-col sm:flex-row gap-3 flex-1">
          {/* Search Input */}
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              type="text"
              placeholder="Search documents..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
            {searchInput && (
              <button
                onClick={() => setSearchInput('')}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={handleCategoryChange}
            className="block px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm min-w-[180px]"
          >
            <option value="">All Categories</option>
            {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>

          {/* Type Filter (enabled only when category selected) */}
          <select
            value={selectedType}
            onChange={handleTypeChange}
            disabled={!selectedCategory}
            className="block px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm disabled:opacity-50 disabled:cursor-not-allowed min-w-[150px]"
          >
            <option value="">All Types</option>
            {availableTypes.map((type) => (
              <option key={type} value={type}>
                {type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={handleStatusChange}
            className="block px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm min-w-[140px]"
          >
            <option value="">All Status</option>
            {Object.entries(STATUS_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>

          {/* Clear Filters Button */}
          {hasActiveFilters && (
            <button
              onClick={handleClearFilters}
              className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors whitespace-nowrap"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Right side: Upload Button + Count */}
        <div className="flex items-center gap-4">
          {/* Document Count */}
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {documentCount} document{documentCount !== 1 ? 's' : ''}
          </span>

          {/* Upload Button */}
          <button
            onClick={onUploadClick}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Upload
          </button>
        </div>
      </div>
    </div>
  );
};

export default DocumentFiltersComponent;


