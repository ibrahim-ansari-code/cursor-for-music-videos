import React from 'react';

/**
 * Type definitions for industrial unit details
 *
 * Note: Ownership entity is now tracked at the property level, not the unit level.
 */
interface IndustrialUnitTypeDetails {
  unit_type?: 'Industrial';
  additional_rent?: number | string;
  security_deposit?: number | string;
  parking_fee?: number | string;
  storage_fee?: number | string;
  additional_fees?: number | string;
  lease_structure?: string;
  use_type?: string;
  loading_dock_access?: boolean;
  drive_in_door_access?: boolean;
  has_separate_utilities?: boolean;
  [key: string]: unknown;
}

interface UnitFormData {
  name: string;
  floor: string;
  monthly_rent: string;
  description: string;
  size: string;
  unit_type_details?: IndustrialUnitTypeDetails;
  [key: string]: unknown;
}

interface IndustrialUnitFieldsProps {
  formData: UnitFormData;
  setFormData: React.Dispatch<React.SetStateAction<UnitFormData>>;
  disabled?: boolean;
}

/**
 * Industrial Unit Fields Component
 *
 * Renders property-type-specific fields for industrial units.
 * Handles financial terms, lease structure, and specifications.
 *
 * Note: Ownership entity is managed at the property level.
 */
const IndustrialUnitFields: React.FC<IndustrialUnitFieldsProps> = ({
  formData,
  setFormData,
  disabled = false,
}) => {

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ): void => {
    const { name, value, type } = e.target;
    const checked = (e.target as HTMLInputElement).checked;

    // Handle checkbox separately
    if (type === 'checkbox') {
      setFormData(prev => ({
        ...prev,
        unit_type_details: {
          ...(prev.unit_type_details || {}),
          unit_type: 'Industrial' as const,
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
        unit_type: 'Industrial' as const,
        [name]: value
      }
    }));
  };

  const unitTypeDetails = formData.unit_type_details || {};

  return (
    <div className="space-y-4">
      <div className="border-t pt-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-3">Industrial Details</h4>

        {/* Financial Terms */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label htmlFor="additional_rent" className="block text-sm font-medium text-gray-700 mb-1">
              Additional Rent
            </label>
            <div className="relative">
              <span className="absolute left-3 top-2 text-gray-500">$</span>
              <input
                type="number"
                id="additional_rent"
                name="additional_rent"
                value={unitTypeDetails.additional_rent || ''}
                onChange={handleChange}
                min="0"
                step="0.01"
                disabled={disabled}
                className="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                placeholder="0.00"
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">CAM charges, utilities, taxes, etc.</p>
          </div>

          <div>
            <label htmlFor="security_deposit" className="block text-sm font-medium text-gray-700 mb-1">
              Security Deposit
            </label>
            <div className="relative">
              <span className="absolute left-3 top-2 text-gray-500">$</span>
              <input
                type="number"
                id="security_deposit"
                name="security_deposit"
                value={unitTypeDetails.security_deposit || ''}
                onChange={handleChange}
                min="0"
                step="0.01"
                disabled={disabled}
                className="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                placeholder="0.00"
              />
            </div>
          </div>
        </div>

        {/* Additional Fees */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label htmlFor="parking_fee" className="block text-sm font-medium text-gray-700 mb-1">
              Parking Fee
            </label>
            <div className="relative">
              <span className="absolute left-3 top-2 text-gray-500">$</span>
              <input
                type="number"
                id="parking_fee"
                name="parking_fee"
                value={unitTypeDetails.parking_fee || ''}
                onChange={handleChange}
                min="0"
                step="0.01"
                disabled={disabled}
                className="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                placeholder="0.00"
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">Monthly parking charges</p>
          </div>

          <div>
            <label htmlFor="storage_fee" className="block text-sm font-medium text-gray-700 mb-1">
              Storage Fee
            </label>
            <div className="relative">
              <span className="absolute left-3 top-2 text-gray-500">$</span>
              <input
                type="number"
                id="storage_fee"
                name="storage_fee"
                value={unitTypeDetails.storage_fee || ''}
                onChange={handleChange}
                min="0"
                step="0.01"
                disabled={disabled}
                className="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                placeholder="0.00"
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">Storage space charges</p>
          </div>
        </div>

        <div className="mb-4">
          <label htmlFor="additional_fees" className="block text-sm font-medium text-gray-700 mb-1">
            Additional Fees
          </label>
          <div className="relative">
            <span className="absolute left-3 top-2 text-gray-500">$</span>
            <input
              type="number"
              id="additional_fees"
              name="additional_fees"
              value={unitTypeDetails.additional_fees || ''}
              onChange={handleChange}
              min="0"
              step="0.01"
              disabled={disabled}
              className="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              placeholder="0.00"
            />
          </div>
          <p className="text-xs text-gray-500 mt-1">Other miscellaneous fees</p>
        </div>

        {/* Lease Structure */}
        <div className="mb-4">
          <label htmlFor="lease_structure" className="block text-sm font-medium text-gray-700 mb-1">
            Lease Structure
          </label>
          <select
            id="lease_structure"
            name="lease_structure"
            value={unitTypeDetails.lease_structure || ''}
            onChange={handleChange}
            disabled={disabled}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          >
            <option value="">Select lease structure...</option>
            <option value="NNN">NNN (Triple Net)</option>
            <option value="Gross">Gross</option>
            <option value="Modified Gross">Modified Gross</option>
            <option value="Full Service">Full Service</option>
          </select>
        </div>

        {/* Use Type */}
        <div className="mb-4">
          <label htmlFor="use_type" className="block text-sm font-medium text-gray-700 mb-1">
            Use Type
          </label>
          <select
            id="use_type"
            name="use_type"
            value={unitTypeDetails.use_type || ''}
            onChange={handleChange}
            disabled={disabled}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          >
            <option value="">Select use type...</option>
            <option value="warehouse">Warehouse</option>
            <option value="office">Office</option>
            <option value="manufacturing">Manufacturing</option>
            <option value="flex_space">Flex Space</option>
            <option value="distribution">Distribution</option>
            <option value="cold_storage">Cold Storage</option>
            <option value="research_development">Research &amp; Development</option>
          </select>
        </div>

        {/* Loading & Access */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Loading &amp; Access
          </label>
          <div className="space-y-2">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="loading_dock_access"
                name="loading_dock_access"
                checked={unitTypeDetails.loading_dock_access || false}
                onChange={handleChange}
                disabled={disabled}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:bg-gray-100"
              />
              <label htmlFor="loading_dock_access" className="ml-2 text-sm text-gray-700">
                Loading Dock Access
              </label>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="drive_in_door_access"
                name="drive_in_door_access"
                checked={unitTypeDetails.drive_in_door_access || false}
                onChange={handleChange}
                disabled={disabled}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:bg-gray-100"
              />
              <label htmlFor="drive_in_door_access" className="ml-2 text-sm text-gray-700">
                Drive-In Door Access
              </label>
            </div>
          </div>
        </div>

        {/* Infrastructure */}
        <div className="mb-4">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="has_separate_utilities"
              name="has_separate_utilities"
              checked={unitTypeDetails.has_separate_utilities || false}
              onChange={handleChange}
              disabled={disabled}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:bg-gray-100"
            />
            <label htmlFor="has_separate_utilities" className="ml-2 text-sm text-gray-700">
              Separately Metered Utilities
            </label>
          </div>
        </div>
      </div>
    </div>
  );
};

export default IndustrialUnitFields;
