import React from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData } from '@/types/property';
import { 
  Square, Building, Users, 
  TrendingUp, Layers, Shield, AlertCircle, MapPin, Truck, Eye, Wrench,
  DollarSign, FileText, Ruler
} from 'lucide-react';

const CommercialForm: React.FC = () => {
  const { register, watch, setValue, formState: { errors } } = useFormContext<PropertyFormData>();
  
  // Watch relevant fields - aligned with backend schema
  const typeDetails = watch('type_specific_details') || {};
  
  // Core metrics from backend schema - REQUIRED fields
  const spaceType = typeDetails.space_type;
  const usableSquareFeet = Number(typeDetails.usable_square_feet) || 0;
  const rentableSquareFeet = Number(typeDetails.rentable_square_feet) || 0;
  const leaseType = typeDetails.lease_type;
  const floorCount = typeDetails.floor_count;
  const floorCountInput = typeDetails.floor_count_custom;
  
  // Optional but important fields
  
  // Boolean fields
  const hasLoadingArea = typeDetails.has_loading_area;
  const signageRights = typeDetails.signage_rights;
  
  // Arrays
  const permittedUses = typeDetails.permitted_uses || [];
  

  // Helper to safely access nested errors
  const getFieldError = (fieldName: string) => {
    if (!errors.type_specific_details) return null;
    const nestedErrors = errors.type_specific_details;
    if (typeof nestedErrors !== 'object' || nestedErrors === null) return null;
    return (nestedErrors as Record<string, any>)[fieldName];
  };

  // Handle array checkbox changes
  const handleArrayCheckbox = (fieldName: string, value: string, checked: boolean) => {
    const currentValues = watch(`type_specific_details.${fieldName}`) || [];
    if (checked) {
      setValue(`type_specific_details.${fieldName}`, [...currentValues, value]);
    } else {
      setValue(`type_specific_details.${fieldName}`, currentValues.filter((v: string) => v !== value));
    }
  };

  // Space type configurations - matching backend exactly
  const spaceTypes = [
    { value: 'retail', label: 'Retail', icon: '🛍️' },
    { value: 'office', label: 'Office', icon: '🏢' },
    { value: 'medical', label: 'Medical', icon: '🏥' },
    { value: 'restaurant', label: 'Restaurant', icon: '🍽️' },
    { value: 'hotel_motel', label: 'Hotel/Motel', icon: '🏨' },
    { value: 'mixed', label: 'Mixed/Multi-Tenant', icon: '🏬' }
  ];

  // Lease type options - matching backend exactly
  const leaseTypes = [
    { value: 'gross', label: 'Gross', description: 'Tenant pays rent only' },
    { value: 'triple_net', label: 'Triple Net (NNN)', description: 'Tenant pays rent + expenses' },
    { value: 'modified_gross', label: 'Modified Gross', description: 'Shared expenses' },
    { value: 'percentage', label: 'Percentage Lease', description: 'Base rent + % of sales' },
    { value: 'other', label: 'Other', description: 'Custom lease structure' }
  ];

  return (
    <div className="space-y-5">
      {/* Space Type Selection - Required */}
      <div>
        <label className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2.5 block">
          Commercial Space Type *
        </label>
        <div className="grid grid-cols-3 gap-2 p-1">
          {spaceTypes.map((type) => (
            <button
              key={type.value}
              type="button"
              onClick={() => setValue('type_specific_details.space_type', type.value)}
              className={`
                relative p-3 rounded-xl border-2 transition-all duration-200 group
                ${spaceType === type.value 
                  ? 'border-green-500 bg-gradient-to-br from-green-50 to-emerald-50 shadow-md' 
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                }
              `}
            >
              <div className="text-lg mb-1">{type.icon}</div>
              <div className={`text-xs font-medium ${
                spaceType === type.value ? 'text-green-700' : 'text-gray-700'
              }`}>
                {type.label}
              </div>
              {spaceType === type.value && (
                <div className="absolute top-1 right-1">
                  <div className={`w-2 h-2 bg-green-500 rounded-full animate-pulse`}></div>
                </div>
              )}
            </button>
          ))}
        </div>
        {getFieldError('space_type') && (
          <p className="mt-1 text-xs text-red-500 flex items-center">
            <AlertCircle className="h-3 w-3 mr-1" />
            {getFieldError('space_type')?.message}
          </p>
        )}
      </div>

      {/* Core Space Configuration - Required */}
      <div className="bg-gradient-to-br from-gray-50 to-gray-100/50 rounded-xl p-4 border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            Essential Details
          </span>
          <span className="text-xs text-gray-500">* Required</span>
        </div>
        
        <div className="grid grid-cols-2 gap-3 mb-3">
          {/* Usable Square Feet - Required */}
          <div className="bg-white rounded-lg p-3 border border-gray-200 hover:border-indigo-300 transition-colors group">
            <label className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 group-hover:text-gray-900 transition-colors">
                <Square className="h-3.5 w-3.5 inline mr-1.5 text-indigo-500" />
                Usable SF *
              </span>
              {usableSquareFeet > 0 && (
                <span className="text-xs text-indigo-600 font-semibold">{usableSquareFeet.toLocaleString()} ft²</span>
              )}
            </label>
            <input
              {...register('type_specific_details.usable_square_feet', {
                required: 'Usable square feet is required',
                min: { value: 100, message: 'Min 100 SF' },
                valueAsNumber: true
              })}
              type="number"
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
              placeholder="5000"
            />
            {getFieldError('usable_square_feet') && (
              <p className="mt-1 text-[10px] text-red-500">
                {getFieldError('usable_square_feet')?.message}
              </p>
            )}
          </div>

          {/* Rentable Square Feet - Required */}
          <div className="bg-white rounded-lg p-3 border border-gray-200 hover:border-purple-300 transition-colors group">
            <label className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 group-hover:text-gray-900 transition-colors">
                <TrendingUp className="h-3.5 w-3.5 inline mr-1.5 text-purple-500" />
                Rentable SF *
              </span>
              {rentableSquareFeet > 0 && (
                <span className="text-xs text-purple-600 font-semibold">{rentableSquareFeet.toLocaleString()} ft²</span>
              )}
            </label>
            <input
              {...register('type_specific_details.rentable_square_feet', {
                required: 'Rentable square feet is required',
                min: { value: 100, message: 'Min 100 SF' },
                valueAsNumber: true
              })}
              type="number"
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
              placeholder="5500"
            />
            {getFieldError('rentable_square_feet') && (
              <p className="mt-1 text-[10px] text-red-500">
                {getFieldError('rentable_square_feet')?.message}
              </p>
            )}
          </div>
        </div>

        {/* Common Area Factor & Ceiling Height */}
        <div className="grid grid-cols-2 gap-3">
          {/* Common Area Factor (computed, read-only) */}
          <div className="bg-white rounded-lg p-3 border border-gray-200 hover:border-purple-300 transition-colors group">
            <label className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 group-hover:text-gray-900 transition-colors">
                <Users className="h-3.5 w-3.5 inline mr-1 text-purple-500" />
                CAF (%)
              </span>
              <span className="text-xs text-purple-500 font-medium">Auto</span>
            </label>
            <input
              type="text"
              value={usableSquareFeet > 0 && rentableSquareFeet > 0 
                ? `${(((rentableSquareFeet - usableSquareFeet) / usableSquareFeet) * 100).toFixed(2)}%`
                : ''
              }
              readOnly
              className={`
                w-full px-2.5 py-1.5 text-sm font-semibold border border-gray-200 rounded-md 
                bg-gradient-to-r from-purple-50 to-indigo-50 
                transition-all duration-200
                ${usableSquareFeet > 0 && rentableSquareFeet > 0 
                  ? 'text-purple-700 border-purple-200' 
                  : 'text-gray-400 border-gray-200'
                }
              `}
              placeholder="Auto-calculated"
            />
            {getFieldError('common_area_factor') && (
              <p className="mt-1 text-[10px] text-red-500">
                {getFieldError('common_area_factor')?.message}
              </p>
            )}
          </div>

          {/* Ceiling Height */}
          <div className="bg-white rounded-lg p-3 border border-gray-200 hover:border-indigo-300 transition-colors group">
            <label className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 group-hover:text-gray-900 transition-colors">
                <Ruler className="h-3.5 w-3.5 inline mr-1.5 text-indigo-500" />
                Ceiling Height
              </span>
              {typeDetails.ceiling_height > 0 && (
                <span className="text-xs text-indigo-600 font-semibold">{typeDetails.ceiling_height} ft</span>
              )}
            </label>
            <input
              {...register('type_specific_details.ceiling_height', {
                min: { value: 0, message: 'Min 0' },
                valueAsNumber: true
              })}
              type="number"
              step="0.5"
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
              placeholder="12"
            />
            {getFieldError('ceiling_height') && (
              <p className="mt-1 text-[10px] text-red-500">
                {getFieldError('ceiling_height')?.message}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Floor Count - Standalone Section */}
      <div className="bg-gradient-to-br from-blue-50/30 to-indigo-50/20 rounded-xl p-3.5 border border-gray-200">
        <label className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2.5 block">
          <Layers className="h-3.5 w-3.5 inline mr-1.5 text-blue-500" />
          Floor Count
        </label>
        <div className="flex gap-2">
          {[1, 2, 3].map((num) => (
            <button
              key={num}
              type="button"
              onClick={() => {
                setValue('type_specific_details.floor_count', num);
                setValue('type_specific_details.floor_count_custom', undefined);
              }}
              className={`
                flex-1 py-2 px-3 rounded-lg font-medium text-sm transition-all
                ${floorCount === num && !floorCountInput
                  ? 'bg-gradient-to-r from-purple-500 to-indigo-500 text-white shadow-md' 
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }
              `}
            >
              {num}
            </button>
          ))}
          <input
            {...register('type_specific_details.floor_count_custom', {
              onChange: (e) => {
                const value = parseInt(e.target.value);
                if (value >= 4) {
                  setValue('type_specific_details.floor_count', value);
                } else if (!e.target.value) {
                  setValue('type_specific_details.floor_count', undefined);
                }
              }
            })}
            type="number"
            min="4"
            max="100"
            className="w-16 px-2 py-2 text-sm font-medium border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-center"
            placeholder="4+"
          />
        </div>
      </div>

      {/* Lease Structure - Required */}
      <div className="bg-white rounded-xl p-3.5 border border-gray-200 hover:shadow-sm transition-all">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            <FileText className="h-3.5 w-3.5 inline mr-1.5 text-green-600" />
            Lease Structure *
          </span>
        </div>
        
        <div className="space-y-2">
          {leaseTypes.map((lease) => (
            <button
              key={lease.value}
              type="button"
              onClick={() => setValue('type_specific_details.lease_type', lease.value)}
              className={`
                w-full p-3 rounded-lg border-2 text-left transition-all duration-200
                ${leaseType === lease.value 
                  ? 'border-green-500 bg-green-50' 
                  : 'border-gray-200 bg-white hover:border-gray-300'
                }
              `}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className={`text-sm font-medium ${
                    leaseType === lease.value ? 'text-green-700' : 'text-gray-700'
                  }`}>
                    {lease.label}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">{lease.description}</div>
                </div>
                {leaseType === lease.value && (
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                )}
              </div>
            </button>
          ))}
        </div>
        {getFieldError('lease_type') && (
          <p className="mt-2 text-xs text-red-500 flex items-center">
            <AlertCircle className="h-3 w-3 mr-1" />
            {getFieldError('lease_type')?.message}
          </p>
        )}
      </div>

      {/* Loading & Signage */}
      <div className="bg-gradient-to-br from-slate-50/50 to-gray-50/30 rounded-xl p-3.5 border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            Loading & Signage
          </span>
        </div>
        
        <div className="grid grid-cols-2 gap-3 mb-3">
          <label className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200 hover:border-amber-300 cursor-pointer transition-all">
            <span className="text-xs font-medium text-gray-700">
              <Truck className="h-3.5 w-3.5 inline mr-1.5 text-amber-500" />
              Has Loading Area
            </span>
            <input
              type="checkbox"
              {...register('type_specific_details.has_loading_area')}
              className="rounded text-amber-600 focus:ring-amber-500"
            />
          </label>
          
          <label className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-300 cursor-pointer transition-all">
            <span className="text-xs font-medium text-gray-700">
              <Eye className="h-3.5 w-3.5 inline mr-1.5 text-blue-500" />
              Signage Rights
            </span>
            <input
              type="checkbox"
              {...register('type_specific_details.signage_rights')}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
          </label>
        </div>

        {hasLoadingArea && (
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white rounded-md p-2.5 border border-gray-200">
              <label className="text-xs font-medium text-gray-600 block mb-1">
                Loading Docks Count
              </label>
              <input
                {...register('type_specific_details.loading_docks_count', {
                  min: { value: 0, message: 'Min 0' },
                  valueAsNumber: true
                })}
                type="number"
                className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:ring-1 focus:ring-amber-500"
                placeholder="2"
                defaultValue={0}
              />
            </div>
            
            <div className="bg-white rounded-md p-2.5 border border-gray-200">
              <label className="text-xs font-medium text-gray-600 block mb-1">
                Loading Area Details
              </label>
              <input
                {...register('type_specific_details.loading_area_details')}
                type="text"
                className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:ring-1 focus:ring-amber-500"
                placeholder="Rear loading, 2 bays"
              />
            </div>
          </div>
        )}

        {signageRights && (
          <div className="bg-white rounded-md p-2.5 border border-gray-200 mt-3">
            <label className="text-xs font-medium text-gray-600 block mb-1">
              Signage Restrictions
            </label>
            <textarea
              {...register('type_specific_details.signage_restrictions')}
              className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:ring-1 focus:ring-blue-500"
              rows={2}
              placeholder="Describe any signage restrictions or requirements"
            />
          </div>
        )}
      </div>

      {/* Compliance & Zoning */}
      <div className="bg-gradient-to-br from-gray-50/50 to-stone-50/30 rounded-xl p-3.5 border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            <Shield className="h-3.5 w-3.5 inline mr-1.5 text-green-600" />
            Compliance & Management
          </span>
        </div>
        
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div className="bg-white rounded-lg p-2.5 border border-gray-200">
            <label className="text-xs font-medium text-gray-600 block mb-1">
              <MapPin className="h-3 w-3 inline mr-1 text-gray-500" />
              Zoning Code
            </label>
            <input
              {...register('type_specific_details.zoning_code')}
              type="text"
              maxLength={50}
              className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:ring-1 focus:ring-gray-500"
              placeholder="C-2, B-1, etc."
            />
          </div>
          
          <div className="bg-white rounded-lg p-2.5 border border-gray-200">
            <label className="text-xs font-medium text-gray-600 block mb-1">
              <DollarSign className="h-3 w-3 inline mr-1 text-green-500" />
              CAM Fee (Monthly)
            </label>
            <input
              {...register('type_specific_details.common_area_maintenance_fee', {
                min: { value: 0, message: 'Min 0' },
                valueAsNumber: true
              })}
              type="number"
              step="0.01"
              className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:ring-1 focus:ring-green-500"
              placeholder="500"
            />
          </div>
        </div>

        <label className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200 hover:border-green-300 cursor-pointer transition-all">
          <span className="text-xs font-medium text-gray-700">
            <Wrench className="h-3.5 w-3.5 inline mr-1.5 text-gray-500" />
            On-Site Maintenance
          </span>
          <input
            type="checkbox"
            {...register('type_specific_details.on_site_maintenance')}
            className="rounded text-green-600 focus:ring-green-500"
          />
        </label>
      </div>

      {/* Permitted Uses */}
      <div className="bg-gradient-to-br from-neutral-50/50 to-gray-50/40 rounded-xl p-3.5 border border-gray-200">
        <label className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-3 block">
          Permitted Uses
        </label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { value: 'retail', label: 'Retail' },
            { value: 'office', label: 'Office' },
            { value: 'medical', label: 'Medical/Healthcare' },
            { value: 'restaurant', label: 'Restaurant/Food' },
            { value: 'fitness', label: 'Fitness/Gym' },
            { value: 'entertainment', label: 'Entertainment' },
            { value: 'educational', label: 'Educational' },
            { value: 'professional', label: 'Professional Services' },
            { value: 'personal_services', label: 'Personal Services' }
          ].map((use) => (
            <label key={use.value} className="flex items-center px-3 py-1.5 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors">
              <input
                type="checkbox"
                checked={permittedUses.includes(use.value)}
                onChange={(e) => handleArrayCheckbox('permitted_uses', use.value, e.target.checked)}
                className="mr-2 h-3.5 w-3.5 text-green-600 rounded focus:ring-green-500"
              />
              <span className="text-xs font-medium text-gray-700">{use.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Dynamic Summary Card */}
      {(usableSquareFeet > 0 || rentableSquareFeet > 0 || spaceType) && (
        <div className="bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl p-4 text-white shadow-lg">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-bold mb-2">
                Commercial Summary
              </p>
              <div className="space-y-1 text-xs">
                {spaceType && (
                  <p className="flex items-center opacity-90">
                    <Building className="h-3.5 w-3.5 mr-1.5" />
                    {spaceType.charAt(0).toUpperCase() + spaceType.slice(1).replace(/_/g, ' ')} space
                  </p>
                )}
                {usableSquareFeet > 0 && (
                  <p className="flex items-center opacity-90">
                    <Square className="h-3.5 w-3.5 mr-1.5" />
                    <span className="font-medium">{usableSquareFeet.toLocaleString()} SF Usable</span> 
                  </p>
                )}
                {rentableSquareFeet > 0 && usableSquareFeet > 0 && (
                  <p className="flex items-center opacity-90">
                    <TrendingUp className="h-3.5 w-3.5 mr-1.5" />
                    <span className="font-medium">{((rentableSquareFeet/usableSquareFeet - 1) * 100).toFixed(1)}% Load Factor</span> 
                  </p>
                )}
                {leaseType && (
                  <p className="flex items-center opacity-90">
                    <FileText className="h-3.5 w-3.5 mr-1.5" />
                    {leaseType.replace(/_/g, ' ').charAt(0).toUpperCase() + leaseType.slice(1).replace(/_/g, ' ')} Lease
                  </p>
                )}
              </div>
            </div>
            <div className="text-3xl">🏢</div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CommercialForm;