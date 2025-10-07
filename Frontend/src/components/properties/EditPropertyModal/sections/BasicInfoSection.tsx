import React from 'react';
import { useFormContext } from 'react-hook-form';
import { Building } from 'lucide-react';
import { PropertyStatus } from '../../../../types/property';
import { EditPropertyFormData } from '../validation/editPropertySchema';

export const BasicInfoSection: React.FC = () => {
  const {
    register,
    formState: { errors },
  } = useFormContext<EditPropertyFormData>();

  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-2 mb-4">
        <Building className="h-5 w-5 text-blue-600 dark:text-blue-400" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Basic Information</h3>
      </div>

      {/* Property Name */}
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Property Name <span className="text-red-500">*</span>
        </label>
        <input
          {...register('name')}
          type="text"
          id="name"
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 ${
            errors.name ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
          }`}
          placeholder="Enter property name"
        />
        {errors.name && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.name.message}</p>
        )}
      </div>

      {/* Status */}
      <div>
        <label htmlFor="status" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Status <span className="text-red-500">*</span>
        </label>
        <select
          {...register('status')}
          id="status"
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 ${
            errors.status ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
          }`}
        >
          <option value={PropertyStatus.ACTIVE}>Active</option>
          <option value={PropertyStatus.INACTIVE}>Inactive</option>
          <option value={PropertyStatus.VACANT}>Vacant</option>
          <option value={PropertyStatus.RENTED}>Rented</option>
          <option value={PropertyStatus.PARTIALLY_RENTED}>Partially Rented</option>
          <option value={PropertyStatus.DRAFT}>Draft</option>
          <option value={PropertyStatus.ARCHIVED}>Archived</option>
        </select>
        {errors.status && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.status.message}</p>
        )}
      </div>

      {/* Year Built */}
      <div>
        <label htmlFor="year_built" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Year Built
        </label>
        <input
          {...register('year_built', {
            setValueAs: (v) => v === '' || v === null ? null : parseInt(v, 10)
          })}
          type="number"
          id="year_built"
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 ${
            errors.year_built ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
          }`}
          placeholder="e.g., 2010"
          min="1800"
          max="2100"
        />
        {errors.year_built && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.year_built.message}</p>
        )}
      </div>

      {/* Description */}
      <div>
        <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Description
        </label>
        <textarea
          {...register('description')}
          id="description"
          rows={4}
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 resize-none ${
            errors.description ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
          }`}
          placeholder="Add a description of the property..."
          maxLength={2000}
        />
        {errors.description && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.description.message}</p>
        )}
      </div>
    </div>
  );
};
