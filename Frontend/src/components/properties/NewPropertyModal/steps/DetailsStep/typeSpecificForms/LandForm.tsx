import React, { useEffect } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData } from '@/types/property';
import { 
  MapPin, Ruler, FileText, Scale, Shield,
  AlertTriangle, FileCheck, Trees, Mountain, Zap, Waves,
  Building, DollarSign, Upload
} from 'lucide-react';

const LandForm: React.FC = () => {
  const { register, watch, setValue } = useFormContext<PropertyFormData>();
  
  // Watch relevant fields
  const typeDetails = watch('type_specific_details') || {};
  const totalAreaSqft = Number(watch('type_specific_details.total_area_sqft')) || 0;
  const totalAcres = totalAreaSqft > 0 ? (totalAreaSqft / 43560).toFixed(4) : '0';
  const leasedPortionSqft = Number(watch('type_specific_details.leased_portion_sqft')) || 0;
  const leaseStructure = typeDetails.lease_structure;
  const allowsStructures = typeDetails.allows_structures;
  const utilitiesStatus = typeDetails.utilities_status || {};

  // Auto-calculate and save total_acres and leased_portion_percentage to form state
  useEffect(() => {
    if (totalAreaSqft > 0) {
      const acres = parseFloat((totalAreaSqft / 43560).toFixed(4));
      setValue('type_specific_details.total_acres', acres, { shouldDirty: true });

      if (leasedPortionSqft > 0) {
        const percentage = parseFloat(((leasedPortionSqft / totalAreaSqft) * 100).toFixed(2));
        setValue('type_specific_details.leased_portion_percentage', percentage, { shouldDirty: true });
      } else {
        setValue('type_specific_details.leased_portion_percentage', null);
      }
    } else {
      setValue('type_specific_details.total_acres', null);
      setValue('type_specific_details.leased_portion_percentage', null);
    }
  }, [totalAreaSqft, leasedPortionSqft, setValue]);

  // Handle utility checkboxes
  const handleUtilityChange = (utility: string, status: string) => {
    const current = watch('type_specific_details.utilities_status') || {};
    setValue('type_specific_details.utilities_status', {
      ...current,
      [utility]: status
    }, { shouldDirty: true });
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

  const leaseStructureTypes = [
    { value: 'ground_lease', label: 'Ground Lease', description: 'Lease land for tenant development' },
    { value: 'air_rights', label: 'Air Rights', description: 'Rights to build above property' },
    { value: 'agricultural', label: 'Agricultural', description: 'Farming or agriculture use' },
    { value: 'mineral_rights', label: 'Mineral Rights', description: 'Subsurface rights' },
    { value: 'mixed', label: 'Mixed Use', description: 'Combined usage rights' }
  ];

  const permittedUseOptions = [
    'retail', 'restaurant', 'office', 'industrial', 'agricultural',
    'residential_development', 'parking', 'storage', 'recreational'
  ];

  return (
    <div className="space-y-5">
      {/* Land Measurements */}
      <div className="bg-gradient-to-br from-green-50 to-emerald-50/30 dark:from-green-900/30 dark:to-emerald-900/20 rounded-xl p-4 border border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
            <Ruler className="h-3.5 w-3.5 inline mr-1.5 text-green-600 dark:text-green-400" />
            Land Measurements
          </span>
        </div>
        
        <div className="grid grid-cols-2 gap-3 mb-3">
          {/* Total Area (sq ft) */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-600 hover:border-green-300 dark:hover:border-green-500 transition-colors">
            <label className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                Total Area (sq ft)
              </span>
              {totalAreaSqft > 0 && (
                <span className="text-xs text-green-600 dark:text-green-400 font-semibold">{totalAreaSqft.toLocaleString()} ft²</span>
              )}
            </label>
            <input
              {...register('type_specific_details.total_area_sqft', {
                min: { value: 1, message: 'Min 1 sq ft' },
                valueAsNumber: true
              })}
              type="number"
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-green-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="43560"
            />
          </div>

          {/* Total Acres (auto-calculated) */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-600">
            <label className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                <Trees className="h-3 w-3 inline mr-1 text-green-500 dark:text-green-400" />
                Total Acres
              </span>
              <span className="text-xs text-green-500 dark:text-green-400 font-medium">Auto</span>
            </label>
            <input
              type="text"
              value={totalAcres !== '0' ? `${totalAcres} acres` : ''}
              readOnly
              className="w-full px-2.5 py-1.5 text-sm font-semibold border border-gray-200 dark:border-gray-600 rounded-md bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900 dark:to-emerald-900 text-green-700 dark:text-green-300 cursor-not-allowed"
              placeholder="Auto-calculated"
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 mb-3">
          {/* Frontage */}
          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Frontage (m)
            </label>
            <input
              {...register('type_specific_details.frontage_meters', { valueAsNumber: true })}
              type="number"
              step="0.01"
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-green-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="30.5"
            />
          </div>

          {/* Depth */}
          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Depth (m)
            </label>
            <input
              {...register('type_specific_details.depth_meters', { valueAsNumber: true })}
              type="number"
              step="0.01"
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-green-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="45.7"
            />
          </div>

          {/* Survey Date */}
          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Survey Date
            </label>
            <input
              {...register('type_specific_details.survey_date')}
              type="date"
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-green-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {/* Survey Reference */}
          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Survey Plan No.
            </label>
            <input
              {...register('type_specific_details.survey_reference')}
              type="text"
              maxLength={200}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-green-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="Plan 67M-215"
            />
          </div>

          {/* Lot Numbers */}
          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Lot/Cadastre Numbers
            </label>
            <input
              {...register('type_specific_details.lot_numbers')}
              type="text"
              maxLength={200}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-green-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="Lot 4 179 709"
            />
          </div>
        </div>

        {/* Leased Portion (for partial leases) */}
        {leasedPortionSqft > 0 && (
          <div className="mt-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 border border-blue-200 dark:border-blue-700">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Leased Portion (sq ft) - Partial Land Lease
            </label>
            <input
              {...register('type_specific_details.leased_portion_sqft', { valueAsNumber: true })}
              type="number"
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="10000"
            />
            {totalAreaSqft > 0 && leasedPortionSqft > 0 && (
              <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                {((leasedPortionSqft / totalAreaSqft) * 100).toFixed(2)}% of total land
              </p>
            )}
          </div>
        )}
      </div>

      {/* Land Use & Zoning */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
            <MapPin className="h-3.5 w-3.5 inline mr-1.5 text-blue-600 dark:text-blue-400" />
            Land Use & Zoning
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-3">
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-md p-2.5">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Municipality
            </label>
            <input
              {...register('type_specific_details.municipality')}
              type="text"
              maxLength={200}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="City of Laval"
            />
          </div>

          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-md p-2.5">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Zoning Code
            </label>
            <input
              {...register('type_specific_details.zoning_code')}
              type="text"
              maxLength={100}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="C-2, A-1, etc."
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-3">
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-md p-2.5">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Official Plan Designation
            </label>
            <select
              {...register('type_specific_details.official_plan_designation')}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="">Select...</option>
              <option value="residential">Residential</option>
              <option value="commercial">Commercial</option>
              <option value="industrial">Industrial</option>
              <option value="agricultural">Agricultural</option>
              <option value="mixed_use">Mixed Use</option>
              <option value="institutional">Institutional</option>
              <option value="open_space">Open Space</option>
            </select>
          </div>

          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-md p-2.5">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Site Plan Status
            </label>
            <select
              {...register('type_specific_details.site_plan_status')}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="">Select...</option>
              <option value="approved">Approved</option>
              <option value="pending">Pending</option>
              <option value="not_submitted">Not Submitted</option>
            </select>
          </div>
        </div>

        {/* Overlays & Restrictions */}
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-md p-2.5">
          <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
            Zoning Overlays & Restrictions
          </label>
          <textarea
            {...register('type_specific_details.overlays_restrictions')}
            rows={2}
            className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            placeholder="E.g., Greenbelt (ON), Agricultural Land Reserve (BC), Conservation Authority, Heritage overlay"
          />
        </div>

        {/* Permitted Uses */}
        <div className="mt-3">
          <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-2">
            Permitted Uses
          </label>
          <div className="grid grid-cols-3 gap-2">
            {permittedUseOptions.map((use) => (
              <label key={use} className="flex items-center px-2 py-1.5 bg-gray-50 dark:bg-gray-700/50 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors">
                <input
                  type="checkbox"
                  checked={(typeDetails.permitted_uses || []).includes(use)}
                  onChange={(e) => handleArrayCheckbox('permitted_uses', use, e.target.checked)}
                  className="mr-2 h-3 w-3 text-green-600 dark:text-green-500 rounded focus:ring-green-500"
                />
                <span className="text-xs text-gray-700 dark:text-gray-300 capitalize">{use.replace(/_/g, ' ')}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Ground Lease Specifics */}
      <div className="bg-gradient-to-br from-purple-50/50 to-indigo-50/30 dark:from-purple-900/30 dark:to-indigo-900/20 rounded-xl p-4 border border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
            <FileText className="h-3.5 w-3.5 inline mr-1.5 text-purple-600 dark:text-purple-400" />
            Ground Lease Structure
          </span>
        </div>

        {/* Lease Structure Type */}
        <div className="space-y-2 mb-3">
          {leaseStructureTypes.map((type) => (
            <button
              key={type.value}
              type="button"
              onClick={() => setValue('type_specific_details.lease_structure', type.value, { shouldDirty: true })}
              className={`w-full p-2.5 rounded-lg border-2 text-left transition-all ${
                leaseStructure === type.value 
                  ? 'border-purple-500 dark:border-purple-400 bg-purple-50 dark:bg-purple-900/30' 
                  : 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-500'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className={`text-xs font-medium ${leaseStructure === type.value ? 'text-purple-700 dark:text-purple-300' : 'text-gray-700 dark:text-gray-300'}`}>
                    {type.label}
                  </div>
                  <div className="text-[10px] text-gray-500 dark:text-gray-400">{type.description}</div>
                </div>
                {leaseStructure === type.value && (
                  <div className="w-2 h-2 bg-purple-500 dark:bg-purple-400 rounded-full"></div>
                )}
              </div>
            </button>
          ))}
        </div>

        {/* Development & Usage Rights */}
        <div className="grid grid-cols-2 gap-2">
          <label className="flex items-center justify-between p-2.5 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 cursor-pointer hover:border-purple-300 dark:hover:border-purple-500 transition-colors">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              <Building className="h-3 w-3 inline mr-1 text-purple-500 dark:text-purple-400" />
              Allows Structures
            </span>
            <input
              type="checkbox"
              {...register('type_specific_details.allows_structures')}
              className="rounded text-purple-600 dark:text-purple-500 focus:ring-purple-500"
            />
          </label>

          <label className="flex items-center justify-between p-2.5 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 cursor-pointer hover:border-blue-300 dark:hover:border-blue-500 transition-colors">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              Signage Rights
            </span>
            <input
              type="checkbox"
              {...register('type_specific_details.signage_rights')}
              className="rounded text-blue-600 dark:text-blue-500 focus:ring-blue-500"
            />
          </label>

          <label className="flex items-center justify-between p-2.5 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 cursor-pointer hover:border-green-300 dark:hover:border-green-500 transition-colors">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              Subletting Allowed
            </span>
            <input
              type="checkbox"
              {...register('type_specific_details.subletting_allowed')}
              className="rounded text-green-600 dark:text-green-500 focus:ring-green-500"
            />
          </label>

          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              <DollarSign className="h-3 w-3 inline mr-1 text-green-500 dark:text-green-400" />
              Revenue Share (%)
            </label>
            <input
              {...register('type_specific_details.revenue_share_percentage', { valueAsNumber: true })}
              type="number"
              step="0.01"
              min="0"
              max="100"
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-green-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="5.0"
            />
          </div>
        </div>

        {/* Development Rights */}
        {allowsStructures && (
          <div className="mt-3 bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Development Rights & Restrictions
            </label>
            <textarea
              {...register('type_specific_details.development_rights')}
              rows={2}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-purple-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="Describe permitted development, height limits, coverage ratio, etc."
            />
          </div>
        )}
      </div>

      {/* Physical Features */}
      <div className="bg-gradient-to-br from-amber-50/40 to-yellow-50/20 dark:from-amber-900/20 dark:to-yellow-900/10 rounded-xl p-4 border border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
            <Mountain className="h-3.5 w-3.5 inline mr-1.5 text-amber-600 dark:text-amber-400" />
            Physical Features
          </span>
        </div>

        <div className="grid grid-cols-3 gap-3 mb-3">
          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Topography
            </label>
            <select
              {...register('type_specific_details.topography')}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-amber-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="">Select...</option>
              <option value="flat">Flat</option>
              <option value="sloped">Sloped</option>
              <option value="hilly">Hilly</option>
              <option value="mixed">Mixed</option>
            </select>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Soil Type
            </label>
            <input
              {...register('type_specific_details.soil_type')}
              type="text"
              maxLength={100}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-amber-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="Clay, sandy, loam, etc."
            />
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Drainage
            </label>
            <input
              {...register('type_specific_details.drainage')}
              type="text"
              maxLength={100}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-amber-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="Good, poor, moderate"
            />
          </div>
        </div>

        {/* Environmental Indicators */}
        <div className="grid grid-cols-3 gap-2">
          <label className="flex items-center justify-between p-2.5 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 cursor-pointer hover:border-blue-300 dark:hover:border-blue-500 transition-colors">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              <Waves className="h-3 w-3 inline mr-1 text-blue-500 dark:text-blue-400" />
              Floodplain
            </span>
            <input
              type="checkbox"
              {...register('type_specific_details.floodplain_indicator')}
              className="rounded text-blue-600 dark:text-blue-500 focus:ring-blue-500"
            />
          </label>

          <label className="flex items-center justify-between p-2.5 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 cursor-pointer hover:border-orange-300 dark:hover:border-orange-500 transition-colors">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              <AlertTriangle className="h-3 w-3 inline mr-1 text-orange-500 dark:text-orange-400" />
              Brownfield
            </span>
            <input
              type="checkbox"
              {...register('type_specific_details.brownfield_indicator')}
              className="rounded text-orange-600 dark:text-orange-500 focus:ring-orange-500"
            />
          </label>

          <label className="flex items-center justify-between p-2.5 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 cursor-pointer hover:border-green-300 dark:hover:border-green-500 transition-colors">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              <Trees className="h-3 w-3 inline mr-1 text-green-500 dark:text-green-400" />
              Conservation Area
            </span>
            <input
              type="checkbox"
              {...register('type_specific_details.conservation_area')}
              className="rounded text-green-600 dark:text-green-500 focus:ring-green-500"
            />
          </label>
        </div>
      </div>

      {/* Utilities & Infrastructure */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
            <Zap className="h-3.5 w-3.5 inline mr-1.5 text-yellow-600 dark:text-yellow-400" />
            Utilities & Infrastructure
          </span>
        </div>

        <div className="space-y-2 mb-3">
          {['water', 'sewer', 'electricity', 'natural_gas', 'fiber'].map((utility) => (
            <div key={utility} className="bg-gray-50 dark:bg-gray-700/50 rounded-md p-2.5">
              <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1.5 capitalize">
                {utility.replace(/_/g, ' ')}
              </label>
              <div className="flex gap-2">
                {['connected', 'available', 'not_available'].map((status) => (
                  <button
                    key={status}
                    type="button"
                    onClick={() => handleUtilityChange(utility, status)}
                    className={`flex-1 py-1.5 px-2 rounded text-xs font-medium transition-all ${
                      utilitiesStatus[utility] === status
                        ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white shadow-sm'
                        : 'bg-gray-100 dark:bg-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-500'
                    }`}
                  >
                    {status === 'not_available' ? 'N/A' : status.charAt(0).toUpperCase() + status.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-md p-2.5">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Road Access
            </label>
            <input
              {...register('type_specific_details.road_access')}
              type="text"
              maxLength={200}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="Paved road, direct access"
            />
          </div>

          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-md p-2.5">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Parking Spaces
            </label>
            <input
              {...register('type_specific_details.parking_spaces', { valueAsNumber: true })}
              type="number"
              min="0"
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="50"
            />
          </div>
        </div>
      </div>

      {/* Legal & Financial */}
      <div className="bg-gradient-to-br from-slate-50/50 to-gray-50/30 dark:from-slate-800/50 dark:to-gray-800/30 rounded-xl p-4 border border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
            <Scale className="h-3.5 w-3.5 inline mr-1.5 text-slate-600 dark:text-slate-400" />
            Legal & Financial
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-3">
          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Title Registration Province
            </label>
            <input
              {...register('type_specific_details.title_registration_province')}
              type="text"
              maxLength={100}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-slate-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="Québec, Ontario, etc."
            />
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Title Registration Number
            </label>
            <input
              {...register('type_specific_details.title_registration_number')}
              type="text"
              maxLength={200}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-slate-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="PIN or lot number"
            />
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Assessment Roll Number
            </label>
            <input
              {...register('type_specific_details.assessment_roll_number')}
              type="text"
              maxLength={100}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-slate-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="MPAC roll number"
            />
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Insurance Responsibility
            </label>
            <select
              {...register('type_specific_details.insurance_responsibility')}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-slate-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="">Select...</option>
              <option value="landlord">Landlord</option>
              <option value="tenant">Tenant</option>
              <option value="shared">Shared</option>
            </select>
          </div>
        </div>

        {/* Easements & Covenants */}
        <div className="space-y-2">
          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Easements & Rights of Way
            </label>
            <textarea
              {...register('type_specific_details.easements')}
              rows={2}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-slate-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="Describe any easements, rights of way, or access restrictions"
            />
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
              Registered Covenants
            </label>
            <textarea
              {...register('type_specific_details.registered_covenants')}
              rows={2}
              className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-slate-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="Registered covenants and encroachments"
            />
          </div>
        </div>
      </div>

      {/* Environmental Assessments */}
      <div className="bg-gradient-to-br from-emerald-50/40 to-green-50/20 dark:from-emerald-900/20 dark:to-green-900/10 rounded-xl p-4 border border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
            <Shield className="h-3.5 w-3.5 inline mr-1.5 text-emerald-600 dark:text-emerald-400" />
            Environmental Assessments
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 mb-3">
          <label className="flex items-center justify-between p-2.5 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 cursor-pointer hover:border-emerald-300 dark:hover:border-emerald-500 transition-colors">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              <FileCheck className="h-3 w-3 inline mr-1 text-emerald-500 dark:text-emerald-400" />
              Phase I ESA Complete
            </span>
            <input
              type="checkbox"
              {...register('type_specific_details.environmental_assessment_phase1')}
              className="rounded text-emerald-600 dark:text-emerald-500 focus:ring-emerald-500"
            />
          </label>

          <label className="flex items-center justify-between p-2.5 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 cursor-pointer hover:border-emerald-300 dark:hover:border-emerald-500 transition-colors">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              <FileCheck className="h-3 w-3 inline mr-1 text-emerald-500 dark:text-emerald-400" />
              Phase II ESA Complete
            </span>
            <input
              type="checkbox"
              {...register('type_specific_details.environmental_assessment_phase2')}
              className="rounded text-emerald-600 dark:text-emerald-500 focus:ring-emerald-500"
            />
          </label>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-md p-2.5 border border-gray-200 dark:border-gray-600">
          <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1">
            Environmental Restrictions
          </label>
          <textarea
            {...register('type_specific_details.environmental_restrictions')}
            rows={2}
            className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-emerald-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            placeholder="Environmental restrictions and requirements"
          />
        </div>
      </div>

      {/* Documentation Notes */}
      <div className="bg-gradient-to-br from-blue-50/30 to-indigo-50/20 dark:from-blue-900/20 dark:to-indigo-900/10 rounded-xl p-4 border border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
            <Upload className="h-3.5 w-3.5 inline mr-1.5 text-blue-600 dark:text-blue-400" />
            Documentation (Upload in Media Step)
          </span>
        </div>

        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 border border-blue-200 dark:border-blue-700">
          <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
            Documents to prepare for upload in the Photos & Media step:
          </p>
          <ul className="text-xs text-gray-600 dark:text-gray-400 space-y-1 list-disc list-inside">
            <li>Survey plan (PDF or GeoTIFF)</li>
            <li>Zoning certificate/confirmation</li>
            <li>Site plan approval documents</li>
            <li>Environmental assessment reports (Phase I/II)</li>
            <li>Parcel map or GIS overlay</li>
            <li>Aerial/drone photographs</li>
          </ul>
        </div>
      </div>

      {/* Summary Card */}
      {totalAreaSqft > 0 && (
        <div className="bg-gradient-to-br from-green-500 to-emerald-600 dark:from-green-600 dark:to-emerald-700 rounded-xl p-4 text-white shadow-lg">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-bold mb-2">Land Summary</p>
              <div className="space-y-1 text-xs">
                <p className="flex items-center opacity-90">
                  <MapPin className="h-3.5 w-3.5 mr-1.5" />
                  {totalAreaSqft.toLocaleString()} sq ft ({totalAcres} acres)
                </p>
                {leaseStructure && (
                  <p className="flex items-center opacity-90">
                    <FileText className="h-3.5 w-3.5 mr-1.5" />
                    {leaseStructure.replace(/_/g, ' ').toUpperCase()}
                  </p>
                )}
                {leasedPortionSqft > 0 && (
                  <p className="flex items-center opacity-90">
                    <Scale className="h-3.5 w-3.5 mr-1.5" />
                    Partial Lease: {leasedPortionSqft.toLocaleString()} sq ft
                  </p>
                )}
                {allowsStructures && (
                  <p className="flex items-center opacity-90">
                    <Building className="h-3.5 w-3.5 mr-1.5" />
                    Development Allowed
                  </p>
                )}
              </div>
            </div>
            <div className="text-3xl">🏞️</div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LandForm;

