import React, { useMemo } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData } from '@/types/property';
import { 
  Home, Store, Car, 
  Users, Layers, AlertCircle,
  Building2, MapPin, Briefcase, Info
} from 'lucide-react';

const MixedUseForm: React.FC = () => {
  const { register, watch, setValue, formState: { errors }, trigger } = useFormContext<PropertyFormData>();
  
  // Watch relevant fields - aligned with backend schema
  const typeDetails = watch('type_specific_details') || {};
  
  // Core metrics from backend schema
  const residentialSquareFeet = Number(typeDetails.residential_square_feet) || 0;
  const commercialSquareFeet = Number(typeDetails.commercial_square_feet) || 0;
  const residentialUnitsCount = Number(typeDetails.residential_units_count) || 0;
  const commercialUnitsCount = Number(typeDetails.commercial_units_count) || 0;
  const parkingSpacesTotal = Number(typeDetails.parking_spaces_total) || 0;
  
  // Unit types and space types
  const commercialSpaceTypes = typeDetails.commercial_space_types || [];
  const sharedAmenities = typeDetails.shared_amenities || [];
  
  // Mixed-use type selection
  const mixedUseType = typeDetails.mixed_use_type;
  
  // Calculate residential unit mix total for real-time feedback - watch individual fields
  const studioCount = watch('type_specific_details.residential_unit_types.studio') || 0;
  const br1Count = watch('type_specific_details.residential_unit_types.1br') || 0;
  const br2Count = watch('type_specific_details.residential_unit_types.2br') || 0;
  const br3Count = watch('type_specific_details.residential_unit_types.3br') || 0;
  const br4Count = watch('type_specific_details.residential_unit_types.4br') || 0;
  const penthouseCount = watch('type_specific_details.residential_unit_types.penthouse') || 0;
  
  const residentialUnitMixTotal = useMemo(() => {
    return Number(studioCount) + Number(br1Count) + Number(br2Count) + 
           Number(br3Count) + Number(br4Count) + Number(penthouseCount);
  }, [studioCount, br1Count, br2Count, br3Count, br4Count, penthouseCount]);

  // Check if residential unit mix is valid for UI feedback
  const isResidentialUnitMixValid = useMemo(() => {
    if (residentialUnitsCount === 0) return true; // No validation needed if no total units
    if (residentialUnitMixTotal === 0) return false; // Need to distribute units
    return residentialUnitMixTotal === residentialUnitsCount; // Must equal total
  }, [residentialUnitMixTotal, residentialUnitsCount]);
  
  // Boolean fields
  
  // Helper to safely access nested errors
  const getFieldError = (fieldName: string) => {
    if (!errors.type_specific_details) return null;
    const nestedErrors = errors.type_specific_details;
    if (typeof nestedErrors === 'object' && nestedErrors !== null && fieldName in nestedErrors) {
      return (nestedErrors as Record<string, any>)[fieldName];
    }
    return null;
  };

  // Handle array checkbox changes
  const handleArrayCheckbox = (fieldName: string, value: string, checked: boolean) => {
    const currentValues = watch(`type_specific_details.${fieldName}`) || [];
    if (checked) {
      setValue(`type_specific_details.${fieldName}`, [...currentValues, value], { shouldDirty: true });
    } else {
      setValue(`type_specific_details.${fieldName}`, currentValues.filter((v: string) => v !== value), { shouldDirty: true });
    }
  };

  // Mixed-use type configurations
  const mixedUseTypes = [
    { value: 'live_work', label: 'Live/Work', icon: '🏠' },
    { value: 'retail_residential', label: 'Retail + Residential', icon: '🛍️' },
    { value: 'office_residential', label: 'Office + Residential', icon: '🏢' },
    { value: 'hotel_retail', label: 'Hotel + Retail', icon: '🏨' },
    { value: 'vertical_mixed', label: 'Vertical Mixed', icon: '🏗️' },
    { value: 'horizontal_mixed', label: 'Horizontal Mixed', icon: '🏘️' }
  ];

  return (
    <div className="space-y-5">
      {/* Mixed-Use Type Selection */}
      <div>
        <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-2.5 block transition-colors duration-300">
          Development Type
        </label>
        <div className="grid grid-cols-3 gap-2 p-1">
          {mixedUseTypes.map((type) => (
            <button
              key={type.value}
              type="button"
              onClick={() => setValue('type_specific_details.mixed_use_type', type.value, { shouldDirty: true })}
              className={`
                relative p-3 rounded-xl border-2 transition-all duration-200 group
                ${mixedUseType === type.value 
                  ? 'border-indigo-500 dark:border-indigo-400 bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-900/40 dark:to-purple-900/40 shadow-md' 
                  : 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-500 hover:shadow-sm'
                }
              `}
            >
              <div className="text-lg mb-1">{type.icon}</div>
              <div className={`text-xs font-medium transition-colors duration-300 ${
                mixedUseType === type.value ? 'text-indigo-700 dark:text-indigo-300' : 'text-gray-700 dark:text-gray-300'
              }`}>
                {type.label}
              </div>
              {mixedUseType === type.value && (
                <div className="absolute top-1 right-1">
                  <div className="w-2 h-2 bg-indigo-500 dark:bg-indigo-400 rounded-full animate-pulse"></div>
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Space Distribution - Primary Section */}
      <div className="bg-gradient-to-br from-gray-50 to-gray-100/50 dark:from-gray-800/50 dark:to-gray-900/50 rounded-xl p-4 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            Essential Details
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400 transition-colors duration-300">* Required</span>
        </div>
        
        <div className="grid grid-cols-2 gap-3 mb-3">
          {/* Residential Square Feet */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-600 hover:border-green-300 dark:hover:border-green-500 transition-colors group">
            <label className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors">
                <Home className="h-3.5 w-3.5 inline mr-1.5 text-green-500 dark:text-green-400" />
                Residential SF <span className="text-red-500">*</span>
              </span>
              {residentialSquareFeet > 0 && (
                <span className="text-xs text-green-600 dark:text-green-400 font-semibold transition-colors duration-300">{residentialSquareFeet.toLocaleString()}</span>
              )}
            </label>
            <input
              {...register('type_specific_details.residential_square_feet', {
                required: 'Residential square feet is required for mixed-use properties',
                min: { value: 1, message: 'Must be at least 1 square foot' },
                valueAsNumber: true
              })}
              type="number"
              className={`w-full px-2.5 py-1.5 text-sm border rounded-md focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 border-gray-200 dark:border-gray-600 ${
                getFieldError('residential_square_feet') ? 'border-red-300 dark:border-red-500' : ''
              }`}
              placeholder="50000"
            />
            {getFieldError('residential_square_feet') && (
              <p className="mt-1 text-[10px] text-red-500 flex items-center">
                <AlertCircle className="h-3 w-3 mr-0.5" />
                {getFieldError('residential_square_feet')?.message}
              </p>
            )}
          </div>

          {/* Commercial Square Feet */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-600 hover:border-purple-300 dark:hover:border-purple-500 transition-colors group">
            <label className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors">
                <Store className="h-3.5 w-3.5 inline mr-1.5 text-purple-500 dark:text-purple-400" />
                Commercial SF <span className="text-red-500">*</span>
              </span>
              {commercialSquareFeet > 0 && (
                <span className="text-xs text-purple-600 dark:text-purple-400 font-semibold transition-colors duration-300">{commercialSquareFeet.toLocaleString()}</span>
              )}
            </label>
            <input
              {...register('type_specific_details.commercial_square_feet', {
                required: 'Commercial square feet is required for mixed-use properties',
                min: { value: 1, message: 'Must be at least 1 square foot' },
                valueAsNumber: true
              })}
              type="number"
              className={`w-full px-2.5 py-1.5 text-sm border rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 border-gray-200 dark:border-gray-600 ${
                getFieldError('commercial_square_feet') ? 'border-red-300 dark:border-red-500' : ''
              }`}
              placeholder="15000"
            />
            {getFieldError('commercial_square_feet') && (
              <p className="mt-1 text-[10px] text-red-500 flex items-center">
                <AlertCircle className="h-3 w-3 mr-0.5" />
                {getFieldError('commercial_square_feet')?.message}
              </p>
            )}
          </div>
        </div>

        {/* Unit Counts */}
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-700 transition-colors duration-300">
            <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400 block mb-1 transition-colors duration-300">
              <Users className="h-3 w-3 inline mr-1 text-green-500 dark:text-green-400" />
              Residential Units
            </label>
            <input
              {...register('type_specific_details.residential_units_count', {
                min: { value: 0, message: 'Min 0' },
                valueAsNumber: true
              })}
              type="number"
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-green-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition-colors duration-300"
              placeholder="40"
            />
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
            <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400 block mb-1 transition-colors duration-300">
              <Briefcase className="h-3 w-3 inline mr-1 text-purple-500 dark:text-purple-400" />
              Commercial Units
            </label>
            <input
              {...register('type_specific_details.commercial_units_count', {
                min: { value: 0, message: 'Min 0' },
                valueAsNumber: true
              })}
              type="number"
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-purple-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition-colors duration-300"
              placeholder="5"
            />
          </div>
        </div>
      </div>

      {/* Unit Types Configuration */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-3.5 border border-gray-200 dark:border-gray-600 hover:shadow-sm transition-all">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider transition-colors duration-300">
            Unit Types & Mix
          </span>
        </div>
        
        {/* Residential Unit Types */}
        <div className={`bg-white dark:bg-gray-700 rounded-lg p-3 border mb-3 transition-all ${
          !isResidentialUnitMixValid && residentialUnitsCount > 0 ? 'border-red-300 dark:border-red-500 shadow-sm' : 'border-gray-200 dark:border-gray-600'
        }`}>
          <label className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center justify-between transition-colors duration-300">
            <span>Residential Unit Mix</span>
            {residentialUnitsCount > 0 && (
              <span className={`text-xs font-medium ${
                isResidentialUnitMixValid ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
              } transition-colors duration-300`}>
                {residentialUnitMixTotal} / {residentialUnitsCount} units
                {isResidentialUnitMixValid && ' ✓'}
              </span>
            )}
          </label>
          
          {residentialUnitsCount > 0 && residentialUnitMixTotal === 0 && (
            <div className="mb-3 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
              <p className="text-xs text-blue-700 dark:text-blue-300 flex items-center transition-colors duration-300">
                <Info className="h-3.5 w-3.5 mr-1 flex-shrink-0" />
                Distribute your {residentialUnitsCount} residential units across bedroom types below
              </p>
            </div>
          )}
          <div className="grid grid-cols-6 gap-2">
            {[
              { key: 'studio', label: 'Studio' },
              { key: '1br', label: '1BR' },
              { key: '2br', label: '2BR' },
              { key: '3br', label: '3BR' },
              { key: '4br', label: '4BR+' },
              { key: 'penthouse', label: 'Penthouse' }
            ].map((unit) => (
              <div key={unit.key} className={`bg-gray-50 dark:bg-gray-600 rounded-md p-2 border transition-colors duration-300 ${
                !isResidentialUnitMixValid && residentialUnitsCount > 0 ? 'border-red-200 dark:border-red-400' : 'border-gray-200 dark:border-gray-500'
              }`}>
                <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400 block mb-1 transition-colors duration-300">
                  {unit.label}
                </label>
                <input
                  {...register(`type_specific_details.residential_unit_types.${unit.key}` as const, {
                    min: { value: 0, message: 'Min 0' },
                    valueAsNumber: true,
                    onChange: () => {
                      // Trigger validation after input change for real-time feedback
                      setTimeout(() => {
                        trigger('type_specific_details.residential_unit_types');
                        trigger('type_specific_details.residential_units_count');
                      }, 0);
                    }
                  })}
                  type="number"
                  className={`w-full px-1.5 py-1 text-xs border rounded focus:ring-1 focus:ring-green-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition-colors duration-300 ${
                    !isResidentialUnitMixValid && residentialUnitsCount > 0 ? 'border-red-200 dark:border-red-400' : 'border-gray-200 dark:border-gray-600'
                  }`}
                  placeholder="0"
                />
              </div>
            ))}
          </div>
          
          {!isResidentialUnitMixValid && residentialUnitsCount > 0 && residentialUnitMixTotal > 0 && (
            <div className="mt-3 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg">
              <p className="text-xs text-red-600 dark:text-red-400 flex items-center transition-colors duration-300">
                <AlertCircle className="h-3.5 w-3.5 mr-1 flex-shrink-0" />
                Residential unit distribution ({residentialUnitMixTotal}) must equal total residential units ({residentialUnitsCount})
              </p>
            </div>
          )}
        </div>

        {/* Commercial Space Types */}
        <div className="bg-white dark:bg-gray-700 rounded-lg p-3 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
          <label className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2 block transition-colors duration-300">
            Commercial Space Types
          </label>
          <div className="grid grid-cols-3 gap-2">
            {[
              { value: 'retail', label: 'Retail', icon: '🛍️' },
              { value: 'office', label: 'Office', icon: '💼' },
              { value: 'restaurant', label: 'Restaurant', icon: '🍽️' },
              { value: 'cafe', label: 'Cafe', icon: '☕' },
              { value: 'service', label: 'Service', icon: '🔧' },
              { value: 'medical', label: 'Medical', icon: '🏥' },
              { value: 'fitness', label: 'Fitness/Gym', icon: '💪' },
              { value: 'bank', label: 'Bank/Financial', icon: '🏦' },
              { value: 'entertainment', label: 'Entertainment', icon: '🎭' }
            ].map((type) => (
              <label key={type.value} className="flex items-center px-3 py-1.5 bg-gray-50 dark:bg-gray-600 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-500 transition-colors">
                <input
                  type="checkbox"
                  checked={commercialSpaceTypes.includes(type.value)}
                  onChange={(e) => handleArrayCheckbox('commercial_space_types', type.value, e.target.checked)}
                  className="mr-2 h-3.5 w-3.5 text-purple-600 rounded focus:ring-purple-500"
                />
                <span className="text-sm">{type.icon}</span>
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300 transition-colors duration-300">{type.label}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Shared Facilities & Management */}
      <div className="bg-gradient-to-br from-slate-50/50 to-gray-50/30 dark:from-gray-800/50 dark:to-gray-900/30 rounded-xl p-3.5 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider transition-colors duration-300">
            Shared Facilities & Management
          </span>
        </div>
        
        {/* Configuration Options */}
        <div className="grid grid-cols-2 gap-3 mb-3">
          <label className="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-500 cursor-pointer transition-all">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300 transition-colors duration-300">Separate Entrances</span>
            <input
              type="checkbox"
              {...register('type_specific_details.separate_entrances')}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
          </label>
          
          <label className="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-500 cursor-pointer transition-all">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300 transition-colors duration-300">Shared Parking</span>
            <input
              type="checkbox"
              {...register('type_specific_details.shared_parking')}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
          </label>
        </div>

        {/* Parking Spaces */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-600 mb-3 transition-colors duration-300">
          <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1 transition-colors duration-300">
            <Car className="h-3.5 w-3.5 inline mr-1.5 text-amber-500 dark:text-amber-400" />
            Total Parking Spaces
          </label>
          <input
            {...register('type_specific_details.parking_spaces_total', {
              min: { value: 0, message: 'Min 0' },
              valueAsNumber: true
            })}
            type="number"
            className="w-full px-2.5 py-1.5 text-sm border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-amber-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition-colors duration-300"
            placeholder="60"
          />
        </div>

        {/* Shared Amenities */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
          <label className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2 block transition-colors duration-300">
            Shared Amenities
          </label>
          <div className="grid grid-cols-3 gap-2">
            {[
              { value: 'lobby', label: 'Lobby' },
              { value: 'parking_garage', label: 'Parking Garage' },
              { value: 'rooftop_deck', label: 'Rooftop Deck' },
              { value: 'gym', label: 'Fitness Center' },
              { value: 'pool', label: 'Pool' },
              { value: 'courtyard', label: 'Courtyard' },
              { value: 'concierge', label: 'Concierge' },
              { value: 'business_center', label: 'Business Center' },
              { value: 'lounge', label: 'Lounge' }
            ].map((amenity) => (
              <label key={amenity.value} className="flex items-center px-3 py-1.5 bg-gray-50 dark:bg-gray-600 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-500 transition-colors">
                <input
                  type="checkbox"
                  checked={sharedAmenities.includes(amenity.value)}
                  onChange={(e) => handleArrayCheckbox('shared_amenities', amenity.value, e.target.checked)}
                  className="mr-2 h-3.5 w-3.5 text-green-600 rounded focus:ring-green-500"
                />
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300 transition-colors duration-300">{amenity.label}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Management Structure */}
      <div className="bg-gradient-to-br from-stone-50/40 to-gray-50/30 dark:from-gray-800/40 dark:to-gray-900/30 rounded-xl p-3.5 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider transition-colors duration-300">
            Management & Zoning
          </span>
        </div>
        
        <div className="space-y-3">
          <label className="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-indigo-300 dark:hover:border-indigo-500 cursor-pointer transition-all">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300 transition-colors duration-300">Single Management Company</span>
            <input
              type="checkbox"
              {...register('type_specific_details.single_management_company')}
              className="rounded text-indigo-600 focus:ring-indigo-500"
            />
          </label>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1 transition-colors duration-300">
              Management Structure
            </label>
            <textarea
              {...register('type_specific_details.management_structure')}
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition-colors duration-300"
              rows={2}
              placeholder="Describe management structure (e.g., Single company manages both residential and commercial)"
            />
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1 transition-colors duration-300">
              <MapPin className="h-3 w-3 inline mr-1 text-gray-500 dark:text-gray-400" />
              Zoning Designation
            </label>
            <input
              {...register('type_specific_details.zoning_designation')}
              type="text"
              maxLength={50}
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-gray-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition-colors duration-300"
              placeholder="e.g., MU-2, C-MU, TOD"
            />
          </div>
        </div>
      </div>

      {/* Dynamic Summary Card */}
      {(residentialSquareFeet > 0 || commercialSquareFeet > 0 || residentialUnitsCount > 0 || commercialUnitsCount > 0) && (
        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl p-4 text-white shadow-lg">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-bold mb-2">
                Mixed-Use Summary
              </p>
              <div className="space-y-1 text-xs">
                {(residentialSquareFeet > 0 || commercialSquareFeet > 0) && (
                  <p className="flex items-center opacity-90">
                    <Layers className="h-3.5 w-3.5 mr-1.5" />
                    <span className="font-medium">
                      {(residentialSquareFeet + commercialSquareFeet).toLocaleString()} SF
                    </span> total
                    {residentialSquareFeet > 0 && commercialSquareFeet > 0 && (
                      <span className="ml-1">
                        {(() => {
                          const totalSquareFeet = residentialSquareFeet + commercialSquareFeet;
                          if (totalSquareFeet === 0) return '(0% res / 0% com)';
                          
                          const resPercentage = Math.round(residentialSquareFeet / totalSquareFeet * 100);
                          const comPercentage = Math.round(commercialSquareFeet / totalSquareFeet * 100);
                          return `(${resPercentage}% res / ${comPercentage}% com)`;
                        })()}
                      </span>
                    )}
                  </p>
                )}
                {residentialUnitsCount > 0 && (
                  <p className="flex items-center opacity-90">
                    <Home className="h-3.5 w-3.5 mr-1.5" />
                    <span className="font-medium">{residentialUnitsCount}</span> residential units
                  </p>
                )}
                {commercialUnitsCount > 0 && (
                  <p className="flex items-center opacity-90">
                    <Store className="h-3.5 w-3.5 mr-1.5" />
                    <span className="font-medium">{commercialUnitsCount}</span> commercial spaces
                  </p>
                )}
                {parkingSpacesTotal > 0 && (
                  <p className="flex items-center opacity-90">
                    <Car className="h-3.5 w-3.5 mr-1.5" />
                    <span className="font-medium">{parkingSpacesTotal}</span> parking spaces
                  </p>
                )}
                {commercialSpaceTypes.length > 0 && (
                  <p className="flex items-center opacity-90">
                    <Building2 className="h-3.5 w-3.5 mr-1.5" />
                    {commercialSpaceTypes.join(', ')}
                  </p>
                )}
              </div>
            </div>
            <div className="text-3xl">🏙️</div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MixedUseForm;