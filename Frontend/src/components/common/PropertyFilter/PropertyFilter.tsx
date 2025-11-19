import React, { useState, Fragment } from 'react';
import { Combobox, Transition } from '@headlessui/react';
import type { Property } from '../../../types/property';

interface PropertyFilterProps {
  selectedProperty: number | null;
  onPropertyChange: (propertyId: number | null) => void;
  properties: Property[];
  disabled?: boolean;
  placeholder?: string;
}

const PropertyFilter: React.FC<PropertyFilterProps> = ({
  selectedProperty,
  onPropertyChange,
  properties,
  disabled = false,
  placeholder = 'All Properties',
}) => {
  const [query, setQuery] = useState('');

  // Find the selected property object
  const selectedPropertyObj =
    selectedProperty !== null
      ? properties.find((p) => p.id === selectedProperty)
      : null;

  // Filter properties based on search query
  const filteredProperties =
    query === ''
      ? properties
      : properties.filter((property) => {
          const searchQuery = query.toLowerCase();
          return (
            property.name.toLowerCase().includes(searchQuery) ||
            property.address?.toLowerCase().includes(searchQuery) ||
            false
          );
        });

  // Determine button text and styling
  const isFiltered = selectedProperty !== null;
  const displayText = selectedPropertyObj?.name || placeholder;

  return (
    <Combobox
      value={selectedProperty}
      onChange={onPropertyChange}
      disabled={disabled}
    >
      <div className="relative">
        {/* Combobox Button */}
        <Combobox.Button
          className={`inline-flex items-center px-4 py-2 border rounded-lg shadow-sm text-sm font-medium transition-colors duration-300 ${
            isFiltered
              ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-600'
              : 'text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600'
          } hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          <i className="fas fa-building mr-2"></i>
          <span className="truncate max-w-[200px]">{displayText}</span>
          <i className="fas fa-chevron-down ml-2 transition-transform duration-200 ui-open:rotate-180"></i>
        </Combobox.Button>

        {/* Dropdown Panel */}
        <Transition
          as={Fragment}
          leave="transition ease-in duration-100"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
          afterLeave={() => setQuery('')}
        >
          <Combobox.Options className="absolute left-0 mt-2 w-72 rounded-md shadow-lg bg-white dark:bg-gray-800 ring-1 ring-black dark:ring-gray-600 ring-opacity-5 focus:outline-none z-50 transition-colors duration-300 flex flex-col">
            {/* Search Input */}
            <div className="p-2 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
              <input
                type="text"
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Search properties..."
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                autoFocus
              />
            </div>

            {/* Options List */}
            <div className="py-1 overflow-y-auto max-h-80">
              {/* All Properties Option */}
              <Combobox.Option
                value={null}
                className={({ active }) =>
                  `group flex items-center w-full px-4 py-3 text-sm transition-colors duration-300 cursor-pointer ${
                    selectedProperty === null
                      ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300'
                      : active
                      ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                      : 'text-gray-700 dark:text-gray-300'
                  }`
                }
              >
                {selectedProperty === null && (
                  <svg
                    className="mr-3 h-5 w-5 text-blue-500 dark:text-blue-400 flex-shrink-0"
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
                <div className="flex items-center flex-1">
                  <i className="fas fa-globe mr-3 text-gray-400 dark:text-gray-500"></i>
                  <span className="font-medium">{placeholder}</span>
                </div>
              </Combobox.Option>

              {/* Divider */}
              {filteredProperties.length > 0 && (
                <div className="border-t border-gray-100 dark:border-gray-700 my-1"></div>
              )}

              {/* Individual Property Options */}
              {filteredProperties.length === 0 && query !== '' ? (
                <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 text-center">
                  No properties found
                </div>
              ) : (
                filteredProperties.map((property) => (
                  <Combobox.Option
                    key={property.id}
                    value={property.id}
                    className={({ active }) =>
                      `group flex items-center w-full px-4 py-3 text-sm transition-colors duration-300 cursor-pointer ${
                        selectedProperty === property.id
                          ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300'
                          : active
                          ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                          : 'text-gray-700 dark:text-gray-300'
                      }`
                    }
                  >
                    {selectedProperty === property.id && (
                      <svg
                        className="mr-3 h-5 w-5 text-blue-500 dark:text-blue-400 flex-shrink-0"
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
                    <div className="flex flex-col items-start flex-1 min-w-0">
                      <span className="font-medium truncate w-full">
                        {property.name}
                      </span>
                      {property.address && (
                        <span className="text-xs text-gray-500 dark:text-gray-400 truncate w-full">
                          {property.address}
                        </span>
                      )}
                    </div>
                  </Combobox.Option>
                ))
              )}
            </div>
          </Combobox.Options>
        </Transition>
      </div>
    </Combobox>
  );
};

export default PropertyFilter;
