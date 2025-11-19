import React, { useState, useRef, useEffect } from 'react';
import type { Property } from '../../../types/property';

interface PropertyFilterDropdownProps {
  selectedProperty: number | null;
  onPropertyChange: (propertyId: number | null) => void;
  properties: Property[];
}

const PropertyFilterDropdown: React.FC<PropertyFilterDropdownProps> = ({
  selectedProperty,
  onPropertyChange,
  properties,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleSelect = (propertyId: number | null) => {
    onPropertyChange(propertyId);
    setIsOpen(false);
  };

  const selectedPropertyName = selectedProperty
    ? properties.find((p) => p.id === selectedProperty)?.name
    : 'All Properties';

  const isFiltered = selectedProperty !== null;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsOpen(!isOpen);
          } else if (e.key === 'Escape' && isOpen) {
            e.preventDefault();
            setIsOpen(false);
          }
        }}
        className={`inline-flex items-center px-4 py-2 border rounded-lg shadow-sm text-sm font-medium transition-colors duration-300 ${
          isFiltered
            ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-600'
            : 'text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600'
        } hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
      >
        <i className="fas fa-building mr-2"></i>
        <span className="truncate max-w-[200px]">{selectedPropertyName}</span>
        <i
          className={`fas fa-chevron-down ml-2 transition-transform duration-200 ${
            isOpen ? 'rotate-180' : ''
          }`}
        ></i>
      </button>

      {isOpen && (
        <div className="origin-top-right absolute left-0 mt-2 w-72 rounded-md shadow-lg bg-white dark:bg-gray-800 ring-1 ring-black dark:ring-gray-600 ring-opacity-5 focus:outline-none z-50 transition-colors duration-300 max-h-96 overflow-y-auto">
          <div className="py-1">
            {/* All Properties Option */}
            <button
              type="button"
              onClick={() => handleSelect(null)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleSelect(null);
                } else if (e.key === 'Escape') {
                  e.preventDefault();
                  setIsOpen(false);
                }
              }}
              className={`group flex items-center w-full px-4 py-3 text-sm transition-colors duration-300 ${
                selectedProperty === null
                  ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              {selectedProperty === null && (
                <svg
                  className="mr-3 h-5 w-5 text-blue-500 dark:text-blue-400"
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
                <span className="font-medium">All Properties</span>
              </div>
            </button>

            {properties.length > 0 && (
              <div className="border-t border-gray-100 dark:border-gray-700 my-1"></div>
            )}

            {/* Individual Properties */}
            {properties.length === 0 ? (
              <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 text-center">
                No properties found
              </div>
            ) : (
              properties.map((property) => (
                <button
                  key={property.id}
                  type="button"
                  onClick={() => handleSelect(property.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleSelect(property.id);
                    } else if (e.key === 'Escape') {
                      e.preventDefault();
                      setIsOpen(false);
                    }
                  }}
                  className={`group flex items-center w-full px-4 py-3 text-sm transition-colors duration-300 ${
                    selectedProperty === property.id
                      ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  {selectedProperty === property.id && (
                    <svg
                      className="mr-3 h-5 w-5 text-blue-500 dark:text-blue-400"
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
                  <div className="flex flex-col items-start flex-1">
                    <span className="font-medium truncate max-w-full">
                      {property.name}
                    </span>
                    {property.address && (
                      <span className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-full">
                        {property.address}
                      </span>
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default PropertyFilterDropdown;

