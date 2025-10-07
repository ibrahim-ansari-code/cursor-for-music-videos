import React from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData } from '@/types/property';
import { 
  Bed, Bath, Square, Car, Trees, Droplets,
  Wind, Flame, Building2, Layers, Zap, Shield,
  AlertCircle
} from 'lucide-react';

const ResidentialForm: React.FC = () => {
  const { register, watch, setValue, formState: { errors } } = useFormContext<PropertyFormData>();
  
  // Watch relevant fields with safe defaults
  const typeDetails = watch('type_specific_details') || {};
  const bedrooms = Number(typeDetails.bedrooms) || 0;
  const bathrooms = Number(typeDetails.bathrooms) || 0;
  const squareFeet = Number(typeDetails.square_feet) || 0;
  const lotSize = Number(typeDetails.lot_size) || 0;
  const stories = typeDetails.stories;
  const storiesInput = typeDetails.stories_custom;
  const garageSpaces = Number(typeDetails.garage_spaces) || 0;
  
  const propertySubtype = typeDetails.property_subtype;

  // Helper to safely access nested errors
  const getFieldError = (fieldName: string): { message: string } | null => {
    if (!errors.type_specific_details) return null;
    const nestedErrors = errors.type_specific_details;
    if (typeof nestedErrors !== 'object' || nestedErrors === null) return null;
    if (fieldName in nestedErrors) {
      const error = nestedErrors[fieldName as keyof typeof nestedErrors];
      // Return only if it's a FieldError object with a message property
      if (error && typeof error === 'object' && 'message' in error) {
        return error as { message: string };
      }
    }
    return null;
  };

  // Property subtype configurations
  const propertySubtypes = [
    { value: 'single_family', label: 'Single Family', icon: '🏡' },
    { value: 'townhouse', label: 'Townhouse', icon: '🏘️' },
    { value: 'condo', label: 'Condo', icon: '🏢' },
    { value: 'duplex', label: 'Duplex', icon: '👥' },
    { value: 'manufactured', label: 'Manufactured', icon: '🏗️' },
    { value: 'mobile_home', label: 'Mobile Home', icon: '🚐' }
  ];

  return (
    <div className="space-y-5">
      {/* Property Subtype - Enhanced Card Selection */}
      <div>
        <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-2.5 block transition-colors duration-300">
          Property Type
        </label>
        <div className="grid grid-cols-3 gap-2 p-1">
          {propertySubtypes.map((type) => (
            <button
              key={type.value}
              type="button"
              onClick={() => setValue('type_specific_details.property_subtype', type.value, { shouldDirty: true })}
              className={`
                relative p-3 rounded-xl border-2 transition-all duration-200 group
                ${propertySubtype === type.value 
                  ? 'border-green-500 dark:border-green-400 bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900 dark:to-emerald-900 shadow-md' 
                  : 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-500 hover:shadow-sm'
                }
              `}
            >
              <div className="text-lg mb-1">{type.icon}</div>
              <div className={`text-xs font-medium ${
                propertySubtype === type.value ? 'text-green-700 dark:text-green-300' : 'text-gray-700 dark:text-gray-300'
              }`}>
                {type.label}
              </div>
              {propertySubtype === type.value && (
                <div className="absolute top-1 right-1">
                  <div className="w-2 h-2 bg-green-500 dark:bg-green-400 rounded-full animate-pulse"></div>
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Core Property Details - Modern Card Layout */}
      <div className="bg-gradient-to-br from-gray-50 to-gray-100/50 dark:from-gray-800/50 dark:to-gray-900/50 rounded-xl p-4 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
            Essential Details
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400 transition-colors duration-300">* Required</span>
        </div>
        
        <div className="grid grid-cols-2 gap-3">
          {/* Bedrooms */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-500 transition-colors group">
            <label className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors">
                <Bed className="h-3.5 w-3.5 inline mr-1 text-blue-500 dark:text-blue-400" />
                Bedrooms *
              </span>
              {bedrooms > 0 && (
                <span className="text-xs text-blue-600 dark:text-blue-400 font-semibold">{bedrooms} {bedrooms === 1 ? 'bed' : 'beds'}</span>
              )}
            </label>
            <input
              {...register('type_specific_details.bedrooms', {
                required: 'Required',
                min: { value: 0, message: 'Min 0' },
                max: { value: 20, message: 'Max 20' },
                valueAsNumber: true
              })}
              type="number"
              className="w-full px-2.5 py-1.5 text-sm font-medium border border-gray-200 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="3"
            />
            {getFieldError('bedrooms') && (
              <p className="mt-1 text-xs text-red-500 dark:text-red-400">{getFieldError('bedrooms')?.message}</p>
            )}
          </div>

          {/* Bathrooms */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-500 transition-colors group">
            <label className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors">
                <Bath className="h-3.5 w-3.5 inline mr-1 text-blue-500 dark:text-blue-400" />
                Bathrooms *
              </span>
              {bathrooms > 0 && (
                <span className="text-xs text-blue-600 dark:text-blue-400 font-semibold">{bathrooms} {bathrooms === 1 ? 'bath' : 'baths'}</span>
              )}
            </label>
            <input
              {...register('type_specific_details.bathrooms', {
                required: 'Required',
                min: { value: 0, message: 'Min 0' },
                valueAsNumber: true
              })}
              type="number"
              step="0.5"
              className="w-full px-2.5 py-1.5 text-sm font-medium border border-gray-200 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="2.5"
            />
            {getFieldError('bathrooms') && (
              <p className="mt-1 text-xs text-red-500 dark:text-red-400">{getFieldError('bathrooms')?.message}</p>
            )}
          </div>

          {/* Square Feet */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-500 transition-colors group">
            <label className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors">
                <Square className="h-3.5 w-3.5 inline mr-1 text-indigo-500 dark:text-indigo-400" />
                Living Area
              </span>
              {squareFeet > 0 && (
                <span className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold">{squareFeet.toLocaleString()} ft²</span>
              )}
            </label>
            <input
              {...register('type_specific_details.square_feet', {
                min: { value: 0, message: 'Min 0' },
                validate: (value) => {
                  const lotSizeValue = watch('type_specific_details.lot_size');
                  if (value && lotSizeValue && Number(value) >= Number(lotSizeValue)) {
                    return 'Living area must be less than lot size';
                  }
                  return true;
                },
                valueAsNumber: true
              })}
              type="number"
              className="w-full px-2.5 py-1.5 text-sm font-medium border border-gray-200 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="2000"
            />
            {getFieldError('square_feet') && (
              <p className="mt-1 text-xs text-red-500 dark:text-red-400">{getFieldError('square_feet')?.message}</p>
            )}
          </div>

          {/* Lot Size */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-500 transition-colors group">
            <label className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors">
                <Trees className="h-3.5 w-3.5 inline mr-1 text-green-500 dark:text-green-400" />
                Lot Size
              </span>
              {lotSize > 0 && (
                <span className="text-xs text-green-600 dark:text-green-400 font-semibold">{lotSize.toLocaleString()} ft²</span>
              )}
            </label>
            <input
              {...register('type_specific_details.lot_size', {
                min: { value: 0, message: 'Min 0' },
                validate: (value) => {
                  const squareFeetValue = watch('type_specific_details.square_feet');
                  if (value && squareFeetValue && Number(value) <= Number(squareFeetValue)) {
                    return 'Lot size must be greater than living area';
                  }
                  return true;
                },
                valueAsNumber: true
              })}
              type="number"
              className="w-full px-2.5 py-1.5 text-sm font-medium border border-gray-200 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="5000"
            />
            {getFieldError('lot_size') && (
              <p className="mt-1 text-xs text-red-500">{getFieldError('lot_size')?.message}</p>
            )}
          </div>
        </div>
        
        {/* Coverage Ratio Validator - Visual feedback for Living Area vs Lot Size */}
        {(squareFeet > 0 || lotSize > 0) && (
          <div className="mt-3">
            <div className={`bg-white rounded-lg p-3 border-2 transition-all ${
              squareFeet > 0 && lotSize > 0 && squareFeet >= lotSize
                ? 'border-red-300 bg-red-50'
                : squareFeet > 0 && lotSize > 0
                ? 'border-green-200 bg-gradient-to-r from-green-50 to-emerald-50'
                : 'border-gray-200'
            }`}>
              <label className="flex items-center justify-between mb-1.5">
                <span className={`text-xs font-medium transition-colors ${
                  squareFeet > 0 && lotSize > 0 && squareFeet >= lotSize
                    ? 'text-red-700'
                    : 'text-gray-600'
                }`}>
                  <Building2 className="h-3.5 w-3.5 inline mr-1 text-purple-500" />
                  Coverage Ratio
                </span>
                <span className="text-xs text-purple-500 font-medium">Auto</span>
              </label>
              <input
                type="text"
                value={squareFeet > 0 && lotSize > 0 
                  ? `${((squareFeet / lotSize) * 100).toFixed(1)}%`
                  : ''
                }
                readOnly
                className={`
                  w-full px-2.5 py-1.5 text-sm font-semibold border rounded-md 
                  transition-all duration-200 cursor-not-allowed
                  ${squareFeet > 0 && lotSize > 0 && squareFeet >= lotSize
                    ? 'border-red-300 bg-red-100 text-red-700'
                    : squareFeet > 0 && lotSize > 0 
                    ? 'border-purple-200 bg-gradient-to-r from-purple-50 to-indigo-50 text-purple-700' 
                    : 'border-gray-200 bg-gray-50 text-gray-400'
                  }
                `}
                placeholder="Auto-calculated"
              />
              {squareFeet > 0 && lotSize > 0 && squareFeet >= lotSize && (
                <p className="mt-1.5 text-xs text-red-600 flex items-center">
                  <AlertCircle className="h-3 w-3 mr-1" />
                  Living area cannot exceed lot size
                </p>
              )}
              {squareFeet > 0 && lotSize > 0 && squareFeet < lotSize && (
                <p className="mt-1 text-[10px] text-gray-500">
                  {(lotSize - squareFeet).toLocaleString()} ft² available for outdoor space
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Layout - Building Stories */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-3.5 border border-gray-200 dark:border-gray-600 hover:shadow-sm transition-all">
        <label className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center">
          <Layers className="h-3.5 w-3.5 mr-1.5 text-purple-500" />
          Building Stories
        </label>
        <div className="flex gap-1.5">
          {[1, 2, 3].map((num) => (
            <button
              key={num}
              type="button"
              onClick={() => {
                setValue('type_specific_details.stories', num, { shouldDirty: true });
                setValue('type_specific_details.stories_custom', undefined, { shouldDirty: true });
              }}
              className={`
                flex-1 py-2 px-3 rounded-lg font-medium text-sm transition-all
                ${stories === num && !storiesInput
                  ? 'bg-gradient-to-r from-purple-500 to-indigo-500 text-white shadow-md' 
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }
              `}
            >
              {num}
            </button>
          ))}
          <input
            {...register('type_specific_details.stories_custom', {
              onChange: (e) => {
                const value = parseInt(e.target.value);
                if (value >= 4) {
                  setValue('type_specific_details.stories', value, { shouldDirty: true });
                } else if (!e.target.value) {
                  setValue('type_specific_details.stories', undefined, { shouldDirty: true });
                } else if (value < 4) {
                  // Clear stories field if custom value is invalid but keep custom input
                  setValue('type_specific_details.stories', undefined, { shouldDirty: true });
                }
              }
            })}
            type="number"
            min="4"
            max="10"
            className="w-16 px-2 py-2 text-sm font-medium border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-center bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition-colors duration-300"
            placeholder="4+"
          />
        </div>
      </div>

      {/* Parking & Garage - Combined Section */}
      <div className="bg-gradient-to-br from-stone-50/40 to-gray-50/30 dark:from-gray-800/40 dark:to-gray-900/30 rounded-xl p-3.5 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
        <label className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2.5 block">
          Parking & Garage
        </label>
        
        {/* Garage Spaces */}
        <div className="mb-3">
          <label className="text-xs font-medium text-gray-700 mb-2 flex items-center">
            <Car className="h-3.5 w-3.5 mr-1.5 text-orange-500" />
            Garage Spaces
          </label>
          <div className="flex gap-1.5">
            {[0, 1, 2, 3].map((num) => (
              <button
                key={num}
                type="button"
                onClick={() => setValue('type_specific_details.garage_spaces', num, { shouldDirty: true })}
                className={`
                  flex-1 py-2 px-2 rounded-lg font-medium text-sm transition-all
                  ${garageSpaces === num 
                    ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white shadow-md' 
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }
                `}
              >
                {num}
              </button>
            ))}
          </div>
        </div>

        {/* Additional Parking Options */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block transition-colors duration-300">Additional Options</label>
          <div className="flex gap-2">
            <label className="flex items-center px-3 py-1.5 bg-gray-50 dark:bg-gray-700/50 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600/50 transition-colors">
              <input
                type="checkbox"
                {...register('type_specific_details.has_driveway')}
                className="mr-2 h-3.5 w-3.5 text-blue-600 rounded focus:ring-blue-500"
              />
              <span className="text-xs font-medium text-gray-700 dark:text-gray-300 transition-colors duration-300">Driveway</span>
            </label>
            
            <label className="flex items-center px-3 py-1.5 bg-gray-50 dark:bg-gray-700/50 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600/50 transition-colors">
              <input
                type="checkbox"
                {...register('type_specific_details.street_parking')}
                className="mr-2 h-3.5 w-3.5 text-blue-600 rounded focus:ring-blue-500"
              />
              <span className="text-xs font-medium text-gray-700 dark:text-gray-300 transition-colors duration-300">Street Parking</span>
            </label>
          </div>
        </div>
      </div>


      {/* Systems - Modern Dropdown Cards */}
      <div className="bg-gradient-to-br from-slate-50/50 to-gray-50/30 dark:from-gray-800/50 dark:to-gray-900/30 rounded-xl p-3.5 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
          <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-2.5 block transition-colors duration-300">
            Systems
          </label>
          <div className="space-y-2.5">
            {/* Heating */}
            <div className="group">
              <label className="text-xs font-medium text-gray-600 mb-1 flex items-center">
                <Flame className="h-3 w-3 mr-1 text-orange-500" />
                Heating
              </label>
              <select
                {...register('type_specific_details.heating_type')}
                className="w-full text-xs px-2.5 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent group-hover:bg-white dark:group-hover:bg-gray-600 transition-colors text-gray-900 dark:text-gray-100"
              >
                <option value="">Select type...</option>
                <option value="forced_air">Forced Air</option>
                <option value="radiant">Radiant</option>
                <option value="heat_pump">Heat Pump</option>
                <option value="baseboard">Baseboard</option>
                <option value="electric">Electric</option>
                <option value="gas">Gas</option>
                <option value="other">Other</option>
              </select>
            </div>

            {/* Cooling */}
            <div className="group">
              <label className="text-xs font-medium text-gray-600 mb-1 flex items-center">
                <Wind className="h-3 w-3 mr-1 text-cyan-500" />
                Cooling
              </label>
              <select
                {...register('type_specific_details.cooling_type')}
                className="w-full text-xs px-2.5 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent group-hover:bg-white dark:group-hover:bg-gray-600 transition-colors text-gray-900 dark:text-gray-100"
              >
                <option value="">Select type...</option>
                <option value="central_air">Central Air</option>
                <option value="window_units">Window Units</option>
                <option value="mini_split">Mini Split</option>
                <option value="none">None</option>
                <option value="other">Other</option>
              </select>
            </div>

            {/* Water Heater */}
            <div className="group">
              <label className="text-xs font-medium text-gray-600 mb-1 flex items-center">
                <Droplets className="h-3 w-3 mr-1 text-blue-500" />
                Water Heater
              </label>
              <select
                {...register('type_specific_details.water_heater_type')}
                className="w-full text-xs px-2.5 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent group-hover:bg-white dark:group-hover:bg-gray-600 transition-colors text-gray-900 dark:text-gray-100"
              >
                <option value="">Select type...</option>
                <option value="tank">Tank</option>
                <option value="tankless">Tankless</option>
                <option value="solar">Solar</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
        </div>

      {/* Additional Details - Compact Grid */}
      <div className="bg-gradient-to-br from-gray-50 to-gray-100/50 dark:from-gray-800/50 dark:to-gray-900/50 rounded-xl p-3.5 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
        <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-2.5 block transition-colors duration-300">
          Property Details
        </label>
        <div className="grid grid-cols-2 gap-2.5">
          {/* Roof Type */}
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 flex items-center">
              <Shield className="h-3 w-3 mr-1 text-gray-500" />
              Roof Type
            </label>
            <select
              {...register('type_specific_details.roof_type')}
              className="w-full text-xs px-2 py-1.5 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-md focus:ring-1 focus:ring-blue-500 text-gray-900 dark:text-gray-100 transition-colors duration-300"
            >
              <option value="">Select...</option>
              <option value="shingle">Shingle</option>
              <option value="tile">Tile</option>
              <option value="metal">Metal</option>
              <option value="flat">Flat</option>
              <option value="other">Other</option>
            </select>
          </div>

          {/* Exterior Material */}
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 flex items-center">
              <Building2 className="h-3 w-3 mr-1 text-gray-500" />
              Exterior
            </label>
            <select
              {...register('type_specific_details.exterior_material')}
              className="w-full text-xs px-2 py-1.5 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-md focus:ring-1 focus:ring-blue-500 text-gray-900 dark:text-gray-100 transition-colors duration-300"
            >
              <option value="">Select...</option>
              <option value="brick">Brick</option>
              <option value="vinyl_siding">Vinyl Siding</option>
              <option value="wood">Wood</option>
              <option value="stucco">Stucco</option>
              <option value="stone">Stone</option>
              <option value="fiber_cement">Fiber Cement</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>
      </div>


      {/* Property Summary - if data exists */}
      {(bedrooms > 0 || bathrooms > 0 || squareFeet > 0) && (
        <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl p-4 text-white shadow-lg">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-bold">Quick Summary</h4>
            <Zap className="h-4 w-4" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            {bedrooms > 0 && (
              <div className="text-center">
                <div className="text-2xl font-bold">{bedrooms}</div>
                <div className="text-xs opacity-90">Bedroom{bedrooms !== 1 ? 's' : ''}</div>
              </div>
            )}
            {bathrooms > 0 && (
              <div className="text-center">
                <div className="text-2xl font-bold">{bathrooms}</div>
                <div className="text-xs opacity-90">Bathroom{bathrooms !== 1 ? 's' : ''}</div>
              </div>
            )}
            {squareFeet > 0 && (
              <div className="text-center">
                <div className="text-2xl font-bold">{(squareFeet/1000).toFixed(1)}k</div>
                <div className="text-xs opacity-90">Sq Ft</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ResidentialForm;