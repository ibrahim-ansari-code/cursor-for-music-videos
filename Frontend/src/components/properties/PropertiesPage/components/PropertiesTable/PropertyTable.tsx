import React from 'react';
import { Property } from '../../../../../types/property';
import { PropertiesTableSkeleton } from '../../../../ui/skeletons';
import { PropertyRow } from './PropertyRow';

interface PropertyTableProps {
  properties: Property[];
  loading: boolean;
  error: string | null;
  onDelete: (propertyId: number) => void;
  onEdit: (propertyId: number) => void;
  onRetry?: () => void;
}

export const PropertyTable: React.FC<PropertyTableProps> = ({
  properties,
  loading,
  error,
  onDelete,
  onEdit,
  onRetry,
}) => {
  if (loading) return <PropertiesTableSkeleton rowCount={8} />;

  if (error) {
    return (
      <div className="p-8 text-center">
        <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 dark:border-red-400 p-4 mb-4 max-w-md mx-auto">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-400 dark:text-red-500"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm leading-5 text-red-700 dark:text-red-300">{error}</p>
            </div>
          </div>
        </div>
        <button
          onClick={() => onRetry?.()}
          className="mt-2 px-4 py-2 border border-transparent text-sm leading-5 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-500 dark:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:border-blue-700 focus:shadow-outline-blue active:bg-blue-700 transition ease-in-out duration-150"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (!properties || properties.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-gray-400">
        No properties found. Create your first property!
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="data-table min-w-full">
        <thead>
          <tr>
            <th scope="col" className="px-6 py-4 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800">Property</th>
            <th scope="col" className="px-6 py-4 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800">Type</th>
            <th scope="col" className="px-6 py-4 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800">Address</th>
            <th scope="col" className="px-6 py-4 text-center font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800">Status</th>
            <th scope="col" className="px-6 py-4 text-right font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800">Added</th>
            <th scope="col" className="px-6 py-4 text-center font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800">Actions</th>
          </tr>
        </thead>
        <tbody>
          {properties.map((property, index) => (
            <PropertyRow
              key={property.id}
              property={property}
              onEdit={onEdit}
              onDelete={onDelete}
              index={index}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
};