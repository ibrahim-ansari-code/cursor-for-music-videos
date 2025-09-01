import React, { useEffect, useState } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData } from '@/types/property';
import { 
  Square, Truck, Zap, AlertCircle,
  Ruler, Package, Train, Shield, Warehouse,
  Building, Gauge, Factory,
  Droplets, MapPin, CheckCircle, Calculator, Info
} from 'lucide-react';

const IndustrialForm: React.FC = () => {
  const { register, watch, setValue, formState: { errors }, trigger, clearErrors } = useFormContext<PropertyFormData>();
  
  // Watch relevant fields - aligned with backend schema
  const typeDetails = watch('type_specific_details') || {};
  
  // Core space metrics - matching backend exactly
  const totalSquareFeet = Number(typeDetails.total_square_feet) || 0;
  const warehouseSquareFeet = Number(typeDetails.warehouse_square_feet) || 0;
  const officeSquareFeet = Number(typeDetails.office_square_feet) || 0;
  const manufacturingSquareFeet = Number(typeDetails.manufacturing_square_feet) || 0;
  
  // Building specifications
  const clearHeight = Number(typeDetails.clear_height) || 0;
  const loadingDocksCount = Number(typeDetails.loading_docks_count) || 0;
  const driveInDoorsCount = Number(typeDetails.drive_in_doors_count) || 0;
  
  // Boolean features
  const railAccess = typeDetails.rail_access;
  const hasCrane = typeDetails.has_crane;
  
  // Industrial type selection
  const industrialType = typeDetails.industrial_type;
  
  // Arrays
  const permittedUses = typeDetails.permitted_uses || [];
  
  // State for auto-calculation
  const [autoCalculateMode, setAutoCalculateMode] = useState<'warehouse' | 'office' | 'manufacturing' | null>(null);
  
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

  // Calculate totals and validation
  const calculatedTotal = warehouseSquareFeet + officeSquareFeet + manufacturingSquareFeet;
  const remainingSquareFeet = totalSquareFeet - calculatedTotal;
  const isValidDistribution = totalSquareFeet > 0 && calculatedTotal === totalSquareFeet;
  const hasDistributionError = totalSquareFeet > 0 && calculatedTotal > 0 && !isValidDistribution;
  
  // Track required fields completeness
  const hasRequiredFields = industrialType && totalSquareFeet > 0 && isValidDistribution;
  
  // Auto-calculate remaining space when one field is set to auto
  useEffect(() => {
    if (autoCalculateMode && totalSquareFeet > 0) {
      const otherFieldsTotal = 
        (autoCalculateMode !== 'warehouse' ? warehouseSquareFeet : 0) +
        (autoCalculateMode !== 'office' ? officeSquareFeet : 0) +
        (autoCalculateMode !== 'manufacturing' ? manufacturingSquareFeet : 0);
      
      const autoValue = Math.max(0, totalSquareFeet - otherFieldsTotal);
      
      if (autoCalculateMode === 'warehouse') {
        setValue('type_specific_details.warehouse_square_feet', autoValue);
      } else if (autoCalculateMode === 'office') {
        setValue('type_specific_details.office_square_feet', autoValue);
      } else if (autoCalculateMode === 'manufacturing') {
        setValue('type_specific_details.manufacturing_square_feet', autoValue);
      }
    }
  }, [totalSquareFeet, warehouseSquareFeet, officeSquareFeet, manufacturingSquareFeet, autoCalculateMode, setValue]);

  // Industrial type configurations - 8 types for even grid
  const industrialTypes = [
    { value: 'warehouse', label: 'Warehouse', icon: '📦' },
    { value: 'distribution', label: 'Distribution', icon: '🚚' },
    { value: 'manufacturing', label: 'Manufacturing', icon: '🏭' },
    { value: 'flex', label: 'Flex Space', icon: '🔄' },
    { value: 'cold_storage', label: 'Cold Storage', icon: '❄️' },
    { value: 'data_center', label: 'Data Center', icon: '🖥️' },
    { value: 'light_industrial', label: 'Light Industrial', icon: '💡' },
    { value: 'rd_tech', label: 'R&D/Tech', icon: '🔬' }
  ];

  // Handle quick fill based on industrial type
  const handleQuickFill = () => {
    if (!industrialType || !totalSquareFeet) return;
    
    const distributions: { [key: string]: { warehouse: number, office: number, manufacturing: number } } = {
      warehouse: { warehouse: 0.85, office: 0.15, manufacturing: 0 },
      distribution: { warehouse: 0.80, office: 0.20, manufacturing: 0 },
      manufacturing: { warehouse: 0.30, office: 0.10, manufacturing: 0.60 },
      flex: { warehouse: 0.40, office: 0.30, manufacturing: 0.30 },
      cold_storage: { warehouse: 0.90, office: 0.10, manufacturing: 0 },
      data_center: { warehouse: 0, office: 0.20, manufacturing: 0.80 },
      light_industrial: { warehouse: 0.50, office: 0.20, manufacturing: 0.30 },
      rd_tech: { warehouse: 0.20, office: 0.50, manufacturing: 0.30 }
    };
    
    const dist = distributions[industrialType];
    if (dist) {
      // Use remainder allocation strategy to ensure perfect totals
      const warehouseFeet = Math.floor(totalSquareFeet * dist.warehouse);
      const officeFeet = Math.floor(totalSquareFeet * dist.office);
      const manufacturingFeet = Math.floor(totalSquareFeet * dist.manufacturing);
      
      // Calculate remainder and allocate to largest component
      const remainder = totalSquareFeet - (warehouseFeet + officeFeet + manufacturingFeet);
      const components = [
        { key: 'warehouse', value: warehouseFeet, ratio: dist.warehouse },
        { key: 'office', value: officeFeet, ratio: dist.office },
        { key: 'manufacturing', value: manufacturingFeet, ratio: dist.manufacturing }
      ].sort((a, b) => b.ratio - a.ratio);
      
      // Add remainder to the largest component
      components[0].value += remainder;
      
      setValue('type_specific_details.warehouse_square_feet', components.find(c => c.key === 'warehouse')?.value || 0);
      setValue('type_specific_details.office_square_feet', components.find(c => c.key === 'office')?.value || 0);
      setValue('type_specific_details.manufacturing_square_feet', components.find(c => c.key === 'manufacturing')?.value || 0);
      setAutoCalculateMode(null);
      trigger('type_specific_details');
    }
  };

  return (
    <div className="space-y-5">
      {/* Industrial Type Selection */}
      <div>
        <label className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2.5 block">
          Facility Type <span className="text-red-500">*</span>
        </label>
        <div className="grid grid-cols-4 gap-2 p-1">
          {industrialTypes.map((type) => (
            <button
              key={type.value}
              type="button"
              onClick={() => {
                setValue('type_specific_details.industrial_type', type.value);
                if (getFieldError('industrial_type')) {
                  clearErrors('type_specific_details.industrial_type');
                }
              }}
              className={`
                relative p-3 rounded-xl border-2 transition-all duration-200 group
                ${industrialType === type.value 
                  ? 'border-orange-500 bg-gradient-to-br from-orange-50 to-amber-50 shadow-md' 
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                }
              `}
            >
              <div className="text-lg mb-1">{type.icon}</div>
              <div className={`text-xs font-medium ${
                industrialType === type.value ? 'text-orange-700' : 'text-gray-700'
              }`}>
                {type.label}
              </div>
              {industrialType === type.value && (
                <div className="absolute top-1 right-1">
                  <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse"></div>
                </div>
              )}
            </button>
          ))}
        </div>
        {getFieldError('industrial_type') && (
          <p className="mt-2 text-xs text-red-500 flex items-center">
            <AlertCircle className="h-3.5 w-3.5 mr-1" />
            {getFieldError('industrial_type')?.message || 'Please select a facility type'}
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
        
        {/* Total Square Feet - Required */}
        <div className="bg-white rounded-lg p-3 border border-gray-200 hover:border-orange-300 transition-colors group mb-3">
          <label className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-gray-600 group-hover:text-gray-900 transition-colors">
              <Square className="h-3.5 w-3.5 inline mr-1.5 text-orange-500" />
              Total Square Feet *
            </span>
            {totalSquareFeet > 0 && (
              <span className="text-xs text-orange-600 font-semibold">{totalSquareFeet.toLocaleString()} SF</span>
            )}
          </label>
          <input
            {...register('type_specific_details.total_square_feet', {
              required: 'Total square feet is required',
              min: { value: 1000, message: 'Min 1,000 SF' },
              max: { value: 5000000, message: 'Max 5,000,000 SF' },
              valueAsNumber: true
            })}
            type="number"
            className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all"
            placeholder="100000"
          />
          {getFieldError('total_square_feet') && (
            <p className="mt-1 text-[10px] text-red-500 flex items-center">
              <AlertCircle className="h-3 w-3 mr-0.5" />
              {getFieldError('total_square_feet')?.message}
            </p>
          )}
        </div>

        {/* Validation Status */}
        {totalSquareFeet > 0 && (
          <div className={`mb-3 p-2.5 rounded-lg border transition-all ${
            isValidDistribution 
              ? 'bg-green-50 border-green-200' 
              : hasDistributionError
              ? 'bg-red-50 border-red-200'
              : 'bg-blue-50 border-blue-200'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {isValidDistribution ? (
                  <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0" />
                ) : hasDistributionError ? (
                  <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0" />
                ) : (
                  <Info className="h-4 w-4 text-blue-600 flex-shrink-0" />
                )}
                <span className={`text-xs font-medium ${
                  isValidDistribution 
                    ? 'text-green-900' 
                    : hasDistributionError
                    ? 'text-red-900'
                    : 'text-blue-900'
                }`}>
                  {isValidDistribution 
                    ? 'Space distribution complete' 
                    : hasDistributionError
                    ? `${Math.abs(remainingSquareFeet).toLocaleString()} SF ${remainingSquareFeet > 0 ? 'unallocated' : 'over-allocated'} (Required)`
                    : 'Allocate space by type below (Required)'
                  }
                </span>
              </div>
              {industrialType && totalSquareFeet > 0 && !isValidDistribution && (
                <button
                  type="button"
                  onClick={handleQuickFill}
                  className="px-2 py-1 text-xs font-medium bg-white text-blue-600 border border-blue-200 rounded-md hover:bg-blue-50 transition-colors flex items-center gap-1"
                >
                  <Calculator className="h-3 w-3" />
                  Auto-fill
                </button>
              )}
            </div>
            {hasDistributionError && (
              <div className="mt-2 text-xs text-gray-600">
                <span className="font-medium">Total: </span>{totalSquareFeet.toLocaleString()} SF • 
                <span className="font-medium ml-2">Allocated: </span>{calculatedTotal.toLocaleString()} SF
              </div>
            )}
          </div>
        )}

        {/* Space Distribution */}
        <div>
          <label className="text-xs font-medium text-gray-600 mb-2 block">
            Space Distribution <span className="text-red-500">*</span>
            {totalSquareFeet > 0 && (
              <span className="text-gray-500 ml-2">
                (Must total {totalSquareFeet.toLocaleString()} SF)
              </span>
            )}
          </label>
          <div className="grid grid-cols-3 gap-2">
          {/* Warehouse SF */}
          <div className={`bg-white rounded-md p-2.5 border transition-all ${
            autoCalculateMode === 'warehouse' 
              ? 'border-blue-400 ring-2 ring-blue-200' 
              : 'border-gray-200'
          }`}>
            <label className="text-[10px] font-medium text-gray-600 flex items-center justify-between mb-1">
              <span>
                <Warehouse className="h-3 w-3 inline mr-1 text-blue-500" />
                Warehouse SF
              </span>
              <button
                type="button"
                onClick={() => setAutoCalculateMode(autoCalculateMode === 'warehouse' ? null : 'warehouse')}
                className={`px-1.5 py-0.5 text-[9px] font-medium rounded transition-all ${
                  autoCalculateMode === 'warehouse'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {autoCalculateMode === 'warehouse' ? 'AUTO' : 'Auto'}
              </button>
            </label>
            <input
              {...register('type_specific_details.warehouse_square_feet', {
                min: { value: 0, message: 'Min 0' },
                valueAsNumber: true,
                validate: (_, formValues) => {
                  const currentTotalSquareFeet = 
                    Number(formValues.type_specific_details?.total_square_feet) || 0;
                  const currentWarehouseSquareFeet = 
                    Number(formValues.type_specific_details?.warehouse_square_feet) || 0;
                  const currentOfficeSquareFeet = 
                    Number(formValues.type_specific_details?.office_square_feet) || 0;
                  const currentManufacturingSquareFeet = 
                    Number(formValues.type_specific_details?.manufacturing_square_feet) || 0;
                    
                  const currentCalculatedTotal = currentWarehouseSquareFeet + 
                    currentOfficeSquareFeet + currentManufacturingSquareFeet;
                  
                  if (currentTotalSquareFeet > 0 && currentCalculatedTotal > currentTotalSquareFeet) {
                    return 'Total exceeds property size';
                  }
                  return true;
                }
              })}
              type="number"
              disabled={autoCalculateMode === 'warehouse'}
              className={`w-full px-2 py-1 text-xs border rounded transition-all ${
                autoCalculateMode === 'warehouse'
                  ? 'bg-blue-50 border-blue-200 text-blue-700 font-medium'
                  : 'border-gray-200 focus:ring-1 focus:ring-blue-500'
              }`}
              placeholder="85000"
            />
            {warehouseSquareFeet > 0 && totalSquareFeet > 0 && (
              <div className="mt-1 text-[9px] text-gray-500 font-medium">
                {Math.round((warehouseSquareFeet / totalSquareFeet) * 100)}% of total
              </div>
            )}
          </div>
          
          {/* Office SF */}
          <div className={`bg-white rounded-md p-2.5 border transition-all ${
            autoCalculateMode === 'office' 
              ? 'border-indigo-400 ring-2 ring-indigo-200' 
              : 'border-gray-200'
          }`}>
            <label className="text-[10px] font-medium text-gray-600 flex items-center justify-between mb-1">
              <span>
                <Building className="h-3 w-3 inline mr-1 text-indigo-500" />
                Office SF
              </span>
              <button
                type="button"
                onClick={() => setAutoCalculateMode(autoCalculateMode === 'office' ? null : 'office')}
                className={`px-1.5 py-0.5 text-[9px] font-medium rounded transition-all ${
                  autoCalculateMode === 'office'
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {autoCalculateMode === 'office' ? 'AUTO' : 'Auto'}
              </button>
            </label>
            <input
              {...register('type_specific_details.office_square_feet', {
                min: { value: 0, message: 'Min 0' },
                valueAsNumber: true,
                validate: (_, formValues) => {
                  const currentTotalSquareFeet = 
                    Number(formValues.type_specific_details?.total_square_feet) || 0;
                  const currentWarehouseSquareFeet = 
                    Number(formValues.type_specific_details?.warehouse_square_feet) || 0;
                  const currentOfficeSquareFeet = 
                    Number(formValues.type_specific_details?.office_square_feet) || 0;
                  const currentManufacturingSquareFeet = 
                    Number(formValues.type_specific_details?.manufacturing_square_feet) || 0;
                    
                  const currentCalculatedTotal = currentWarehouseSquareFeet + 
                    currentOfficeSquareFeet + currentManufacturingSquareFeet;
                  
                  if (currentTotalSquareFeet > 0 && currentCalculatedTotal > currentTotalSquareFeet) {
                    return 'Total exceeds property size';
                  }
                  return true;
                }
              })}
              type="number"
              disabled={autoCalculateMode === 'office'}
              className={`w-full px-2 py-1 text-xs border rounded transition-all ${
                autoCalculateMode === 'office'
                  ? 'bg-indigo-50 border-indigo-200 text-indigo-700 font-medium'
                  : 'border-gray-200 focus:ring-1 focus:ring-indigo-500'
              }`}
              placeholder="5000"
            />
            {officeSquareFeet > 0 && totalSquareFeet > 0 && (
              <div className="mt-1 text-[9px] text-gray-500 font-medium">
                {Math.round((officeSquareFeet / totalSquareFeet) * 100)}% of total
              </div>
            )}
          </div>
          
          {/* Manufacturing SF */}
          <div className={`bg-white rounded-md p-2.5 border transition-all ${
            autoCalculateMode === 'manufacturing' 
              ? 'border-purple-400 ring-2 ring-purple-200' 
              : 'border-gray-200'
          }`}>
            <label className="text-[10px] font-medium text-gray-600 flex items-center justify-between mb-1">
              <span>
                <Factory className="h-3 w-3 inline mr-1 text-purple-500" />
                Manufacturing SF
              </span>
              <button
                type="button"
                onClick={() => setAutoCalculateMode(autoCalculateMode === 'manufacturing' ? null : 'manufacturing')}
                className={`px-1.5 py-0.5 text-[9px] font-medium rounded transition-all ${
                  autoCalculateMode === 'manufacturing'
                    ? 'bg-purple-100 text-purple-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {autoCalculateMode === 'manufacturing' ? 'AUTO' : 'Auto'}
              </button>
            </label>
            <input
              {...register('type_specific_details.manufacturing_square_feet', {
                min: { value: 0, message: 'Min 0' },
                valueAsNumber: true,
                validate: (_, formValues) => {
                  const currentTotalSquareFeet = 
                    Number(formValues.type_specific_details?.total_square_feet) || 0;
                  const currentWarehouseSquareFeet = 
                    Number(formValues.type_specific_details?.warehouse_square_feet) || 0;
                  const currentOfficeSquareFeet = 
                    Number(formValues.type_specific_details?.office_square_feet) || 0;
                  const currentManufacturingSquareFeet = 
                    Number(formValues.type_specific_details?.manufacturing_square_feet) || 0;
                    
                  const currentCalculatedTotal = currentWarehouseSquareFeet + 
                    currentOfficeSquareFeet + currentManufacturingSquareFeet;
                  
                  if (currentTotalSquareFeet > 0 && currentCalculatedTotal > currentTotalSquareFeet) {
                    return 'Total exceeds property size';
                  }
                  return true;
                }
              })}
              type="number"
              disabled={autoCalculateMode === 'manufacturing'}
              className={`w-full px-2 py-1 text-xs border rounded transition-all ${
                autoCalculateMode === 'manufacturing'
                  ? 'bg-purple-50 border-purple-200 text-purple-700 font-medium'
                  : 'border-gray-200 focus:ring-1 focus:ring-purple-500'
              }`}
              placeholder="10000"
            />
            {manufacturingSquareFeet > 0 && totalSquareFeet > 0 && (
              <div className="mt-1 text-[9px] text-gray-500 font-medium">
                {Math.round((manufacturingSquareFeet / totalSquareFeet) * 100)}% of total
              </div>
            )}
            </div>
          </div>
        </div>
      </div>

      {/* Building Specifications */}
      <div className="bg-white rounded-xl p-3.5 border border-gray-200 hover:shadow-sm transition-all">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            <Ruler className="h-3.5 w-3.5 inline mr-1.5 text-blue-600" />
            Building Specifications
          </span>
        </div>
        
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-lg p-2.5 border border-gray-200">
            <label className="text-xs font-medium text-gray-600 block mb-1">
              Clear Height (feet)
            </label>
            <input
              {...register('type_specific_details.clear_height', {
                min: { value: 0, message: 'Min 0' },
                max: { value: 100, message: 'Max 100 ft' },
                valueAsNumber: true
              })}
              type="number"
              step="0.5"
              className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:ring-1 focus:ring-blue-500"
              placeholder="32"
            />
          </div>
          
          <div className="bg-white rounded-lg p-2.5 border border-gray-200">
            <label className="text-xs font-medium text-gray-600 block mb-1">
              <Square className="h-3 w-3 inline mr-1 text-amber-500" />
              Truck Court SF
            </label>
            <input
              {...register('type_specific_details.truck_court_size', {
                min: { value: 0, message: 'Min 0' },
                valueAsNumber: true
              })}
              type="number"
              className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:ring-1 focus:ring-amber-500"
              placeholder="15000"
            />
          </div>
        </div>
      </div>

      {/* Loading & Access Configuration */}
      <div className="bg-gradient-to-br from-stone-50/40 to-gray-50/30 rounded-xl p-3.5 border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            <Truck className="h-3.5 w-3.5 inline mr-1.5 text-amber-600" />
            Loading & Access
          </span>
        </div>
        
        {/* Loading Doors Grid */}
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div className="bg-white rounded-md p-2.5 border border-gray-200">
            <label className="text-xs font-medium text-gray-600 block mb-1">
              Loading Docks
            </label>
            <input
              {...register('type_specific_details.loading_docks_count', {
                min: { value: 0, message: 'Min 0' },
                max: { value: 100, message: 'Max 100' },
                valueAsNumber: true
              })}
              type="number"
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded focus:ring-1 focus:ring-amber-500"
              placeholder="10"
            />
          </div>
          <div className="bg-white rounded-md p-2.5 border border-gray-200">
            <label className="text-xs font-medium text-gray-600 block mb-1">
              Drive-In Doors
            </label>
            <input
              {...register('type_specific_details.drive_in_doors_count', {
                min: { value: 0, message: 'Min 0' },
                max: { value: 50, message: 'Max 50' },
                valueAsNumber: true
              })}
              type="number"
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded focus:ring-1 focus:ring-amber-500"
              placeholder="2"
            />
          </div>
        </div>

        {/* Rail Access */}
        <label className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200 hover:border-amber-300 cursor-pointer transition-all">
          <span className="text-xs font-medium text-gray-700">
            <Train className="h-3.5 w-3.5 inline mr-1.5 text-gray-500" />
            Rail Spur Access
          </span>
          <input
            type="checkbox"
            {...register('type_specific_details.rail_access')}
            className="rounded text-amber-600 focus:ring-amber-500"
          />
        </label>
      </div>

      {/* Power & Infrastructure */}
      <div className="bg-gradient-to-br from-slate-50/50 to-gray-50/30 rounded-xl p-3.5 border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            <Zap className="h-3.5 w-3.5 inline mr-1.5 text-yellow-600" />
            Power & Infrastructure
          </span>
        </div>
        
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div className="bg-white rounded-lg p-2.5 border border-gray-200">
            <label className="text-xs font-medium text-gray-600 block mb-1">
              <Gauge className="h-3 w-3 inline mr-1 text-yellow-500" />
              Power Capacity
            </label>
            <input
              {...register('type_specific_details.power_capacity')}
              type="text"
              maxLength={50}
              className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:ring-1 focus:ring-yellow-500"
              placeholder="2000 amps"
            />
          </div>
          
          <div className="bg-white rounded-lg p-2.5 border border-gray-200">
            <label className="text-xs font-medium text-gray-600 block mb-1">
              <Zap className="h-3 w-3 inline mr-1 text-yellow-500" />
              Power Voltage
            </label>
            <input
              {...register('type_specific_details.power_voltage')}
              type="text"
              maxLength={50}
              className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:ring-1 focus:ring-yellow-500"
              placeholder="480V 3-phase"
            />
          </div>
        </div>

        {/* Crane System */}
        <div className="bg-white rounded-lg p-2.5 border border-gray-200">
          <label className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-700">
              <Package className="h-3.5 w-3.5 inline mr-1.5 text-purple-500" />
              Overhead Crane System
            </span>
            <input
              type="checkbox"
              {...register('type_specific_details.has_crane')}
              className="rounded text-purple-600 focus:ring-purple-500"
            />
          </label>
          {hasCrane && (
            <input
              {...register('type_specific_details.crane_capacity')}
              type="text"
              maxLength={50}
              className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:ring-1 focus:ring-purple-500"
              placeholder="Crane capacity (e.g., 10 ton)"
            />
          )}
        </div>

        {/* Sprinkler System */}
        <div className="bg-white rounded-lg p-2.5 border border-gray-200 mt-3">
          <label className="text-xs font-medium text-gray-600 block mb-1">
            <Droplets className="h-3 w-3 inline mr-1 text-blue-500" />
            Sprinkler System Type
          </label>
          <select
            {...register('type_specific_details.sprinkler_system_type')}
            className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:ring-1 focus:ring-blue-500"
          >
            <option value="">Select...</option>
            <option value="esfr">ESFR</option>
            <option value="wet">Wet System</option>
            <option value="dry">Dry System</option>
            <option value="pre_action">Pre-Action</option>
            <option value="deluge">Deluge</option>
            <option value="none">None</option>
          </select>
        </div>
      </div>

      {/* Environmental & Compliance */}
      <div className="bg-gradient-to-br from-gray-50/50 to-stone-50/30 rounded-xl p-3.5 border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            <Shield className="h-3.5 w-3.5 inline mr-1.5 text-green-600" />
            Environmental & Compliance
          </span>
        </div>
        
        {/* Hazmat Storage */}
        <label className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200 hover:border-yellow-300 cursor-pointer transition-all mb-3">
          <span className="text-xs font-medium text-gray-700">
            <Shield className="h-3.5 w-3.5 inline mr-1.5 text-yellow-500" />
            Hazardous Materials Storage Permitted
          </span>
          <input
            type="checkbox"
            {...register('type_specific_details.hazmat_storage_permitted')}
            className="rounded text-yellow-600 focus:ring-yellow-500"
          />
        </label>

        {/* Environmental Compliance */}
        <div className="bg-white rounded-lg p-3 border border-gray-200 mb-3">
          <label className="text-xs font-medium text-gray-600 block mb-2">
            Environmental Compliance
          </label>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Phase I ESA Date</label>
              <input
                {...register('type_specific_details.environmental_compliance.phase_1_esa')}
                type="date"
                className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded focus:ring-1 focus:ring-green-500"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Phase II ESA Date</label>
              <input
                {...register('type_specific_details.environmental_compliance.phase_2_esa')}
                type="date"
                className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded focus:ring-1 focus:ring-green-500"
              />
            </div>
          </div>
          
          <div className="mb-3">
            <label className="text-xs text-gray-500 block mb-1">Permits (comma-separated)</label>
            <input
              {...register('type_specific_details.environmental_compliance.permits')}
              type="text"
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded focus:ring-1 focus:ring-green-500"
              placeholder="air_quality, wastewater, hazmat"
            />
          </div>
          
          <div className="mb-3">
            <label className="text-xs text-gray-500 block mb-1">Certifications (comma-separated)</label>
            <input
              {...register('type_specific_details.environmental_compliance.certifications')}
              type="text"
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded focus:ring-1 focus:ring-green-500"
              placeholder="ISO_14001, LEED_Silver"
            />
          </div>
          
          <div>
            <label className="text-xs text-gray-500 block mb-1">Additional Notes</label>
            <textarea
              {...register('type_specific_details.environmental_compliance.notes')}
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded focus:ring-1 focus:ring-green-500"
              rows={2}
              placeholder="Additional compliance notes and details"
            />
          </div>
        </div>

        {/* Zoning */}
        <div className="bg-white rounded-lg p-3 border border-gray-200">
          <label className="text-xs font-medium text-gray-600 block mb-1">
            <MapPin className="h-3 w-3 inline mr-1 text-gray-500" />
            Zoning Classification
          </label>
          <input
            {...register('type_specific_details.zoning_classification')}
            type="text"
            maxLength={50}
            className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded focus:ring-1 focus:ring-gray-500"
            placeholder="e.g., M-1, M-2, I-1"
          />
        </div>
      </div>

      {/* Permitted Uses */}
      <div className="bg-gradient-to-br from-neutral-50/50 to-gray-50/40 rounded-xl p-3.5 border border-gray-200">
        <label className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-3 block">
          Permitted Industrial Uses
        </label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { value: 'warehouse', label: 'Warehouse/Storage' },
            { value: 'distribution', label: 'Distribution' },
            { value: 'manufacturing', label: 'Manufacturing' },
            { value: 'assembly', label: 'Assembly' },
            { value: 'light_industrial', label: 'Light Industrial' },
            { value: 'heavy_industrial', label: 'Heavy Industrial' },
            { value: 'flex_space', label: 'Flex Space' },
            { value: 'research_development', label: 'R&D' },
            { value: 'cold_storage', label: 'Cold Storage' },
            { value: 'data_center', label: 'Data Center' },
            { value: 'logistics', label: 'Logistics Hub' },
            { value: 'fulfillment', label: 'E-Commerce Fulfillment' }
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
      {(totalSquareFeet > 0 || clearHeight > 0 || loadingDocksCount > 0) && (
        <div className={`rounded-xl p-4 shadow-lg transition-all ${
          hasRequiredFields 
            ? 'bg-gradient-to-br from-green-500 to-emerald-600 text-white'
            : 'bg-gradient-to-br from-orange-500 to-amber-600 text-white'
        }`}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-bold mb-2 flex items-center gap-2">
                Industrial Facility Summary
                {hasRequiredFields && (
                  <CheckCircle className="h-4 w-4" />
                )}
              </p>
              <div className="space-y-1 text-xs">
                {totalSquareFeet > 0 && (
                  <p className="flex items-center opacity-90">
                    <Square className="h-3.5 w-3.5 mr-1.5" />
                    <span className="font-medium">{totalSquareFeet.toLocaleString()} SF Total</span>
                    {warehouseSquareFeet > 0 && <span className="ml-1">({Math.round(warehouseSquareFeet/totalSquareFeet*100)}% Warehouse)</span>}
                  </p>
                )}
                {!hasRequiredFields && (
                  <p className="flex items-center text-yellow-200 mt-2">
                    <AlertCircle className="h-3.5 w-3.5 mr-1.5" />
                    <span className="font-medium">
                      {!industrialType ? 'Select facility type' : 
                       !totalSquareFeet ? 'Enter total square feet' :
                       !isValidDistribution ? 'Complete space distribution' : 'Required fields missing'}
                    </span>
                  </p>
                )}
                {clearHeight > 0 && (
                  <p className="flex items-center opacity-90">
                    <Ruler className="h-3.5 w-3.5 mr-1.5" />
                    <span className="font-medium">{clearHeight}'</span> Clear Height
                  </p>
                )}
                {loadingDocksCount > 0 && (
                  <p className="flex items-center opacity-90">
                    <Truck className="h-3.5 w-3.5 mr-1.5" />
                    <span className="font-medium">{loadingDocksCount}</span> Loading Docks
                    {driveInDoorsCount > 0 && ` + ${driveInDoorsCount} drive-in doors`}
                  </p>
                )}
                {railAccess && (
                  <p className="flex items-center opacity-90">
                    <Train className="h-3.5 w-3.5 mr-1.5" />
                    Rail Spur Access
                  </p>
                )}
                {hasCrane && (
                  <p className="flex items-center opacity-90">
                    <Package className="h-3.5 w-3.5 mr-1.5" />
                    Overhead Crane System
                  </p>
                )}
                {industrialType && (
                  <p className="flex items-center opacity-90">
                    <Factory className="h-3.5 w-3.5 mr-1.5" />
                    {industrialType.charAt(0).toUpperCase() + industrialType.slice(1).replace(/_/g, ' ')} facility
                  </p>
                )}
              </div>
            </div>
            <div className="text-3xl">🏭</div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IndustrialForm;