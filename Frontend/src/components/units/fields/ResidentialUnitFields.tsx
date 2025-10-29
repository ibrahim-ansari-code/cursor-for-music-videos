import React from 'react';

/**
 * Type definitions for residential unit details
 */
interface ResidentialUnitTypeDetails {
  unit_type?: 'Residential';
  bedrooms?: number | string;
  bathrooms?: number | string;
  parking_spot_number?: string;
  has_balcony?: boolean;
  balcony_size_sqft?: number | string;
  pet_friendly?: boolean;
  pet_deposit?: number | string;
  appliances?: string[];
  [key: string]: unknown;
}

interface UnitFormData {
  name: string;
  floor: string;
  monthly_rent: string;
  description: string;
  size: string;
  unit_type_details?: ResidentialUnitTypeDetails;
  [key: string]: unknown;
}

interface ResidentialUnitFieldsProps {
  formData: UnitFormData;
  setFormData: React.Dispatch<React.SetStateAction<UnitFormData>>;
  disabled?: boolean;
}

const APPLIANCES = [
  'washer',
  'dryer',
  'dishwasher',
  'refrigerator',
  'stove',
  'microwave'
] as const;

/**
 * Residential Unit Fields Component
 *
 * Renders property-type-specific fields for residential units.
 * Handles bedrooms, bathrooms, appliances, parking, balcony, and pet information.
 */
const ResidentialUnitFields: React.FC<ResidentialUnitFieldsProps> = ({
  formData,
  setFormData,
  disabled = false
}) => {
  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement>
  ): void => {
    const { name, value, type, checked } = e.target;

    // Handle checkbox separately
    if (type === 'checkbox') {
      setFormData(prev => ({
        ...prev,
        unit_type_details: {
          ...(prev.unit_type_details || {}),
          [name]: checked
        }
      }));
      return;
    }

    // For regular inputs, update the nested unit_type_details
    setFormData(prev => ({
      ...prev,
      unit_type_details: {
        ...(prev.unit_type_details || {}),
        unit_type: 'Residential' as const,
        [name]: value
      }
    }));
  };

  const handleApplianceChange = (
    appliance: string,
    checked: boolean
  ): void => {
    const currentAppliances = (formData.unit_type_details?.appliances || []) as string[];
    const newAppliances = checked
      ? [...currentAppliances, appliance]
      : currentAppliances.filter(a => a !== appliance);

    setFormData(prev => ({
      ...prev,
      unit_type_details: {
        ...(prev.unit_type_details || {}),
        unit_type: 'Residential' as const,
        appliances: newAppliances
      }
    }));
  };

  const unitTypeDetails = formData.unit_type_details || {};

  return (
    <div className="space-y-4">
      <div className="border-t pt-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-3">Residential Details</h4>

        {/* Bedrooms and Bathrooms */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label htmlFor="bedrooms" className="block text-sm font-medium text-gray-700 mb-1">
              Bedrooms <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              id="bedrooms"
              name="bedrooms"
              value={unitTypeDetails.bedrooms || ''}
              onChange={handleChange}
              min="0"
              max="20"
              disabled={disabled}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              placeholder="e.g., 2"
            />
          </div>

          <div>
            <label htmlFor="bathrooms" className="block text-sm font-medium text-gray-700 mb-1">
              Bathrooms <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              id="bathrooms"
              name="bathrooms"
              value={unitTypeDetails.bathrooms || ''}
              onChange={handleChange}
              min="0"
              max="20"
              step="0.5"
              disabled={disabled}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              placeholder="e.g., 1.5"
            />
            <p className="text-xs text-gray-500 mt-1">Use 0.5 increments (e.g., 1.5, 2.5)</p>
          </div>
        </div>

        {/* Parking */}
        <div className="mb-4">
          <label htmlFor="parking_spot_number" className="block text-sm font-medium text-gray-700 mb-1">
            Parking Spot Number
          </label>
          <input
            type="text"
            id="parking_spot_number"
            name="parking_spot_number"
            value={unitTypeDetails.parking_spot_number || ''}
            onChange={handleChange}
            maxLength={50}
            disabled={disabled}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            placeholder="e.g., A-12"
          />
        </div>

        {/* Balcony */}
        <div className="mb-4">
          <div className="flex items-center mb-2">
            <input
              type="checkbox"
              id="has_balcony"
              name="has_balcony"
              checked={unitTypeDetails.has_balcony || false}
              onChange={handleChange}
              disabled={disabled}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:bg-gray-100"
            />
            <label htmlFor="has_balcony" className="ml-2 text-sm font-medium text-gray-700">
              Has Balcony/Patio
            </label>
          </div>

          {unitTypeDetails.has_balcony && (
            <div className="ml-6">
              <label htmlFor="balcony_size_sqft" className="block text-sm font-medium text-gray-700 mb-1">
                Balcony Size (sq ft)
              </label>
              <input
                type="number"
                id="balcony_size_sqft"
                name="balcony_size_sqft"
                value={unitTypeDetails.balcony_size_sqft || ''}
                onChange={handleChange}
                min="0"
                max="1000"
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                placeholder="e.g., 80"
              />
            </div>
          )}
        </div>

        {/* Pet Policy */}
        <div className="mb-4">
          <div className="flex items-center mb-2">
            <input
              type="checkbox"
              id="pet_friendly"
              name="pet_friendly"
              checked={unitTypeDetails.pet_friendly || false}
              onChange={handleChange}
              disabled={disabled}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:bg-gray-100"
            />
            <label htmlFor="pet_friendly" className="ml-2 text-sm font-medium text-gray-700">
              Pet Friendly
            </label>
          </div>

          {unitTypeDetails.pet_friendly && (
            <div className="ml-6">
              <label htmlFor="pet_deposit" className="block text-sm font-medium text-gray-700 mb-1">
                Pet Deposit
              </label>
              <div className="relative">
                <span className="absolute left-3 top-2 text-gray-500">$</span>
                <input
                  type="number"
                  id="pet_deposit"
                  name="pet_deposit"
                  value={unitTypeDetails.pet_deposit || ''}
                  onChange={handleChange}
                  min="0"
                  step="0.01"
                  disabled={disabled}
                  className="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                  placeholder="0.00"
                />
              </div>
            </div>
          )}
        </div>

        {/* Appliances */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Included Appliances
          </label>
          <div className="grid grid-cols-2 gap-2">
            {APPLIANCES.map((appliance) => (
              <div key={appliance} className="flex items-center">
                <input
                  type="checkbox"
                  id={`appliance-${appliance}`}
                  checked={(unitTypeDetails.appliances || []).includes(appliance)}
                  onChange={(e) => handleApplianceChange(appliance, e.target.checked)}
                  disabled={disabled}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:bg-gray-100"
                />
                <label htmlFor={`appliance-${appliance}`} className="ml-2 text-sm text-gray-700 capitalize">
                  {appliance}
                </label>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResidentialUnitFields;
