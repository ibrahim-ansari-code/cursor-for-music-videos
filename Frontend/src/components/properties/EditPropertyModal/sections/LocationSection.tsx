import React from 'react';
import { useFormContext } from 'react-hook-form';
import { MapPin } from 'lucide-react';
import { EditPropertyFormData } from '../validation/editPropertySchema';
import { validProvinces } from '../validation/editPropertySchema';

export const LocationSection: React.FC = () => {
  const {
    register,
    watch,
    formState: { errors },
  } = useFormContext<EditPropertyFormData>();

  const latitude = watch('latitude');
  const longitude = watch('longitude');
  const hasCoordinates = latitude !== null && longitude !== null;

  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-2 mb-4">
        <MapPin className="h-5 w-5 text-blue-600 dark:text-blue-400" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Location</h3>
      </div>

      {/* Address */}
      <div>
        <label htmlFor="address" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Street Address <span className="text-red-500">*</span>
        </label>
        <input
          {...register('address')}
          type="text"
          id="address"
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 ${
            errors.address ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
          }`}
          placeholder="123 Main Street"
        />
        {errors.address && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.address.message}</p>
        )}
      </div>

      {/* City and Province */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="city" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            City <span className="text-red-500">*</span>
          </label>
          <input
            {...register('city')}
            type="text"
            id="city"
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 ${
              errors.city ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
            }`}
            placeholder="Toronto"
          />
          {errors.city && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.city.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="province" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Province <span className="text-red-500">*</span>
          </label>
          <select
            {...register('province')}
            id="province"
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 ${
              errors.province ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
            }`}
          >
            <option value="">Select province</option>
            {validProvinces.map((province) => (
              <option key={province} value={province}>
                {province}
              </option>
            ))}
          </select>
          {errors.province && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.province.message}</p>
          )}
        </div>
      </div>

      {/* Postal Code */}
      <div>
        <label htmlFor="postal_code" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Postal Code <span className="text-red-500">*</span>
        </label>
        <input
          {...register('postal_code')}
          type="text"
          id="postal_code"
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 ${
            errors.postal_code ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
          }`}
          placeholder="M5V 3A8"
        />
        {errors.postal_code && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.postal_code.message}</p>
        )}
      </div>

      {/* Map Preview */}
      {hasCoordinates && (
        <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Location Coordinates</p>
          <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
            <p>Latitude: {latitude?.toFixed(6)}</p>
            <p>Longitude: {longitude?.toFixed(6)}</p>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
            Note: To update coordinates, please create a new property or contact support
          </p>
        </div>
      )}
    </div>
  );
};
