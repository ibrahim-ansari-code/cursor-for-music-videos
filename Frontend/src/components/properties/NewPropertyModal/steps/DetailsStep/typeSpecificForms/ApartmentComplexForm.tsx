import React, { useEffect, useMemo, useCallback } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData } from '@/types/property';
import { 
  ApartmentComplexDetails, 
  ComplexStyle, 
  SharedAmenity
} from '@/types/apartmentComplex';
import { useFormFieldDebounce } from '@/hooks/useDebounce.ts';
import { 
  Building, Users, Car, Shield, Trash2,
  Phone, Mail, MapPin, AlertCircle,
  Sparkles, Zap, CheckCircle, Info,
  UserCheck, Building2, Layers
} from 'lucide-react';

/**
 * Industry-standard ApartmentComplexForm component
 * - Proper TypeScript types
 * - Optimized debouncing with conflict resolution
 * - Memory leak prevention
 * - Accessibility compliant
 * - YC-grade validation with Zod schema
 */
const ApartmentComplexForm: React.FC = React.memo(() => {
  const { register, watch, setValue, formState: { errors }, trigger } = useFormContext<PropertyFormData>();
  
  // Watch the entire type_specific_details object for proper reactivity
  const typeDetails = watch('type_specific_details') || {};
  const typedDetails = typeDetails as Partial<ApartmentComplexDetails>;
  
  // Extract fields with proper defaults
  const {
    complex_style,
    number_of_buildings = 0,
    total_units = 0,
    unit_mix = {},
    parking_spaces_total = 0,
    elevator_count = 0,
    floor_count,
    floor_count_custom,
    elevator_count_custom,
    on_site_management,
    trash_system_type,
    security_system_type,
    shared_amenities = []
  } = typedDetails;

  // Optimized debounced field updates with conflict resolution
  const floorCountDebouncer = useFormFieldDebounce(
    floor_count_custom,
    useCallback((value: number | string | undefined) => {
      if (!value || value === '') {
        setValue('type_specific_details.floor_count', undefined);
        return;
      }
      const numValue = parseInt(String(value));
      if (!isNaN(numValue) && numValue >= 4) {
        setValue('type_specific_details.floor_count', numValue);
      }
    }, [setValue]),
    300,
    // Conflict resolver: prefer the latest value
    (_current, incoming) => incoming
  );

  const elevatorCountDebouncer = useFormFieldDebounce(
    elevator_count_custom,
    useCallback((value: number | string | undefined) => {
      if (!value || value === '') {
        setValue('type_specific_details.elevator_count', undefined);
        return;
      }
      const numValue = parseInt(String(value));
      if (!isNaN(numValue) && numValue >= 5) {
        setValue('type_specific_details.elevator_count', numValue);
      }
    }, [setValue]),
    300,
    (_current, incoming) => incoming
  );

  // Sync form field changes with debounced updates
  useEffect(() => {
    floorCountDebouncer.updateValue(floor_count_custom);
  }, [floor_count_custom, floorCountDebouncer]);

  useEffect(() => {
    elevatorCountDebouncer.updateValue(elevator_count_custom);
  }, [elevator_count_custom, elevatorCountDebouncer]);

  // Cleanup debounced operations on unmount
  useEffect(() => {
    return () => {
      floorCountDebouncer.cancel();
      elevatorCountDebouncer.cancel();
    };
  }, [floorCountDebouncer, elevatorCountDebouncer]);

  // Helper to safely access nested errors with proper typing
  const getFieldError = useCallback((fieldName: keyof ApartmentComplexDetails): string | undefined => {
    if (!errors.type_specific_details) return undefined;
    const nestedErrors = errors.type_specific_details;
    if (typeof nestedErrors !== 'object' || nestedErrors === null) return undefined;
    const error = (nestedErrors as Record<string, any>)[fieldName];
    return error?.message || undefined;
  }, [errors.type_specific_details]);

  // Optimized array checkbox handler with proper typing
  const handleArrayCheckbox = useCallback((
    fieldName: 'shared_amenities', 
    value: SharedAmenity, 
    checked: boolean
  ) => {
    const currentValues = (typedDetails[fieldName] as SharedAmenity[]) || [];
    const newValues = checked 
      ? [...currentValues, value]
      : currentValues.filter((v: SharedAmenity) => v !== value);
    
    setValue(`type_specific_details.${fieldName}`, newValues);
    // Trigger validation for this field
    trigger(`type_specific_details.${fieldName}`);
  }, [setValue, typedDetails, trigger]);

  // Calculate unit mix total for real-time feedback - watch individual fields for better reactivity
  const studioCount = watch('type_specific_details.unit_mix.studio') || 0;
  const br1Count = watch('type_specific_details.unit_mix.1br') || 0;
  const br2Count = watch('type_specific_details.unit_mix.2br') || 0;
  const br3Count = watch('type_specific_details.unit_mix.3br') || 0;
  const br4Count = watch('type_specific_details.unit_mix.4br') || 0;
  const penthouseCount = watch('type_specific_details.unit_mix.penthouse') || 0;
  
  const unitMixTotal = useMemo(() => {
    return Number(studioCount) + Number(br1Count) + Number(br2Count) + 
           Number(br3Count) + Number(br4Count) + Number(penthouseCount);
  }, [studioCount, br1Count, br2Count, br3Count, br4Count, penthouseCount]);

  // Check if unit mix is valid for UI feedback
  const isUnitMixValid = useMemo(() => {
    if (total_units === 0) return true; // No validation needed if no total units
    if (unitMixTotal === 0) return false; // Need to distribute units
    return unitMixTotal === total_units; // Must equal total
  }, [unitMixTotal, total_units]);

  // Trigger validation when unit mix or total units change
  useEffect(() => {
    if (total_units > 0) {
      trigger('type_specific_details.unit_mix');
    }
  }, [unitMixTotal, total_units, trigger]);

  // Memoized complex style configurations
  const complexStyles = useMemo(() => [
    { value: 'garden' as ComplexStyle, label: 'Garden Style', icon: '🌳', description: 'Low-rise with landscaping' },
    { value: 'highrise' as ComplexStyle, label: 'High-Rise', icon: '🏢', description: '15+ floors' },
    { value: 'midrise' as ComplexStyle, label: 'Mid-Rise', icon: '🏘️', description: '4-14 floors' },
    { value: 'townhome' as ComplexStyle, label: 'Townhome', icon: '🏡', description: 'Attached single-family style' },
    { value: 'luxury' as ComplexStyle, label: 'Luxury', icon: '💎', description: 'High-end amenities' },
    { value: 'student' as ComplexStyle, label: 'Student Housing', icon: '🎓', description: 'Near educational institutions' }
  ], []);

  // Stable event handlers to prevent re-renders
  const handleComplexStyleSelect = useCallback((style: ComplexStyle) => {
    setValue('type_specific_details.complex_style', style);
  }, [setValue]);

  const handleFloorCountSelect = useCallback((num: number) => {
    setValue('type_specific_details.floor_count', num);
    setValue('type_specific_details.floor_count_custom', undefined);
  }, [setValue]);

  const handleElevatorCountSelect = useCallback((num: number) => {
    setValue('type_specific_details.elevator_count', num);
    setValue('type_specific_details.elevator_count_custom', undefined);
  }, [setValue]);

  return (
    <div className="space-y-5" role="form" aria-label="Apartment Complex Details">
      {/* Complex Style Selection - Top Priority with improved accessibility */}
      <fieldset>
        <legend className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2.5">
          Complex Style <span className="text-red-500" aria-label="required">*</span>
        </legend>
        <div className="grid grid-cols-3 gap-2 p-1" role="radiogroup" aria-required="true">
          {complexStyles.map((style) => (
            <button
              key={style.value}
              type="button"
              role="radio"
              aria-checked={complex_style === style.value}
              aria-describedby={`${style.value}-description`}
              onClick={() => handleComplexStyleSelect(style.value)}
              className={`
                relative p-3 rounded-xl border-2 transition-all duration-200 group focus:outline-none focus:ring-2 focus:ring-purple-500
                ${complex_style === style.value 
                  ? 'border-purple-500 bg-gradient-to-br from-purple-50 to-indigo-50 shadow-md' 
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                }
              `}
            >
              <div className="text-lg mb-1" aria-hidden="true">{style.icon}</div>
              <div className={`text-xs font-medium ${
                complex_style === style.value ? 'text-purple-700' : 'text-gray-700'
              }`}>
                {style.label}
              </div>
              <div id={`${style.value}-description`} className="sr-only">
                {style.description}
              </div>
              {complex_style === style.value && (
                <div className="absolute top-1 right-1" aria-hidden="true">
                  <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></div>
                </div>
              )}
            </button>
          ))}
        </div>
        {getFieldError('complex_style') && (
          <p className="mt-2 text-xs text-red-500 flex items-center" role="alert">
            <AlertCircle className="h-3.5 w-3.5 mr-1" aria-hidden="true" />
            {getFieldError('complex_style')}
          </p>
        )}
      </fieldset>

      {/* Core Complex Details - Required Fields First */}
      <fieldset className="bg-gradient-to-br from-gray-50 to-gray-100/50 rounded-xl p-3.5 border border-gray-200">
        <legend className="mb-3">
          <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            Essential Details
          </span>
        </legend>
        
        <div className="grid grid-cols-3 gap-3">
          {/* Number of Buildings */}
          <div className="bg-white rounded-lg p-3 border border-gray-200 hover:border-blue-300 transition-colors group">
            <label className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 group-hover:text-gray-900 transition-colors">
                <Building className="h-3.5 w-3.5 inline mr-1 text-blue-500" aria-hidden="true" />
                Buildings <span className="text-red-500" aria-label="required">*</span>
              </span>
              {number_of_buildings > 0 && (
                <span className="text-xs text-blue-600 font-semibold" aria-label={`${number_of_buildings} buildings`}>
                  {number_of_buildings}
                </span>
              )}
            </label>
            <input
              {...register('type_specific_details.number_of_buildings', {
                required: 'Number of buildings is required',
                min: { value: 1, message: 'Must have at least 1 building' },
                max: { value: 100, message: 'Maximum 100 buildings' },
                valueAsNumber: true
              })}
              type="number"
              min="1"
              max="100"
              aria-invalid={!!getFieldError('number_of_buildings')}
              aria-describedby={getFieldError('number_of_buildings') ? 'buildings-error' : undefined}
              className={`w-full px-2.5 py-1.5 text-sm font-medium border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all ${
                getFieldError('number_of_buildings') ? 'border-red-300' : 'border-gray-200'
              }`}
              placeholder="3"
            />
            {getFieldError('number_of_buildings') && (
              <p id="buildings-error" className="mt-1 text-[10px] text-red-500 flex items-center" role="alert">
                <AlertCircle className="h-3 w-3 mr-0.5" aria-hidden="true" />
                {getFieldError('number_of_buildings')}
              </p>
            )}
          </div>

          {/* Total Units */}
          <div className="bg-white rounded-lg p-3 border border-gray-200 hover:border-purple-300 transition-colors group">
            <label className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 group-hover:text-gray-900 transition-colors">
                <Users className="h-3.5 w-3.5 inline mr-1 text-purple-500" aria-hidden="true" />
                Total Units <span className="text-red-500" aria-label="required">*</span>
              </span>
              {total_units > 0 && (
                <span className="text-xs text-purple-600 font-semibold" aria-label={`${total_units} units`}>
                  {total_units}
                </span>
              )}
            </label>
            <input
              {...register('type_specific_details.total_units', {
                required: 'Total units is required',
                min: { value: 1, message: 'Must have at least 1 unit' },
                max: { value: 10000, message: 'Maximum 10,000 units' },
                valueAsNumber: true
              })}
              type="number"
              min="1"
              max="10000"
              aria-invalid={!!getFieldError('total_units')}
              aria-describedby={getFieldError('total_units') ? 'units-error' : undefined}
              className={`w-full px-2.5 py-1.5 text-sm font-medium border rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all ${
                getFieldError('total_units') ? 'border-red-300' : 'border-gray-200'
              }`}
              placeholder="120"
            />
            {getFieldError('total_units') && (
              <p id="units-error" className="mt-1 text-[10px] text-red-500 flex items-center" role="alert">
                <AlertCircle className="h-3 w-3 mr-0.5" aria-hidden="true" />
                {getFieldError('total_units')}
              </p>
            )}
          </div>

          {/* Parking Spaces */}
          <div className="bg-white rounded-lg p-3 border border-gray-200 hover:border-amber-300 transition-colors group">
            <label className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 group-hover:text-gray-900 transition-colors">
                <Car className="h-3.5 w-3.5 inline mr-1 text-amber-500" aria-hidden="true" />
                Parking Spaces
              </span>
              {parking_spaces_total > 0 && (
                <span className="text-xs text-amber-600 font-semibold" aria-label={`${parking_spaces_total} parking spaces`}>
                  {parking_spaces_total}
                </span>
              )}
            </label>
            <input
              {...register('type_specific_details.parking_spaces_total', {
                min: { value: 0, message: 'Cannot be negative' },
                valueAsNumber: true
              })}
              type="number"
              min="0"
              className="w-full px-2.5 py-1.5 text-sm font-medium border border-gray-200 rounded-md focus:ring-2 focus:ring-amber-500 focus:border-transparent transition-all"
              placeholder="180"
            />
            {parking_spaces_total > 0 && total_units > 0 && (
              <div className="mt-1 text-[9px] text-gray-500 font-medium">
                {(parking_spaces_total/total_units).toFixed(1)} per unit
              </div>
            )}
          </div>
        </div>
      </fieldset>

      {/* Unit Mix Distribution - Required */}
      <fieldset className={`bg-white rounded-xl p-3.5 border transition-all ${
        !isUnitMixValid && total_units > 0 ? 'border-red-300 shadow-sm' : 'border-gray-200'
      }`}>
        <legend className="text-xs font-medium text-gray-700 mb-2 flex items-center">
          <Layers className="h-3.5 w-3.5 mr-1.5 text-indigo-500" aria-hidden="true" />
          Unit Mix Distribution <span className="text-red-500 ml-1" aria-label="required">*</span>
          {total_units > 0 && (
            <span className={`ml-auto text-xs font-medium ${
              isUnitMixValid ? 'text-green-600' : 'text-red-600'
            }`}>
              {unitMixTotal} / {total_units} units
              {isUnitMixValid && ' ✓'}
            </span>
          )}
        </legend>
        
        {total_units > 0 && unitMixTotal === 0 && (
          <div className="mb-3 p-2 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-xs text-blue-700 flex items-center">
              <Info className="h-3.5 w-3.5 mr-1 flex-shrink-0" aria-hidden="true" />
              Distribute your {total_units} units across bedroom types below
            </p>
          </div>
        )}
        
        <div className="grid grid-cols-3 gap-2" role="group" aria-label="Unit mix distribution">
          {[
            { key: 'studio', label: 'Studio', color: 'from-gray-400 to-gray-500' },
            { key: '1br', label: '1 BR', color: 'from-blue-400 to-blue-500' },
            { key: '2br', label: '2 BR', color: 'from-indigo-400 to-indigo-500' },
            { key: '3br', label: '3 BR', color: 'from-purple-400 to-purple-500' },
            { key: '4br', label: '4+ BR', color: 'from-pink-400 to-pink-500' },
            { key: 'penthouse', label: 'Penthouse', color: 'from-amber-400 to-amber-500' }
          ].map((unitType) => {
            const unitCount = (unit_mix as any)?.[unitType.key] || 0;
            return (
              <div key={unitType.key} className={`bg-gray-50 rounded-lg p-2 ${
                !isUnitMixValid && total_units > 0 ? 'border border-red-200' : ''
              }`}>
                <label className="text-[10px] font-medium text-gray-600 mb-1 block">
                  {unitType.label}
                </label>
                <input
                  {...register(`type_specific_details.unit_mix.${unitType.key}`, {
                    min: { value: 0, message: 'Cannot be negative' },
                    valueAsNumber: true,
                    onChange: () => {
                      // Trigger validation after input change for real-time feedback
                      setTimeout(() => {
                        trigger('type_specific_details.unit_mix');
                        trigger('type_specific_details.total_units');
                      }, 0);
                    }
                  })}
                  type="number"
                  min="0"
                  aria-label={`Number of ${unitType.label} units`}
                  className={`w-full px-2 py-1.5 text-xs font-medium border rounded focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${
                    !isUnitMixValid && total_units > 0 ? 'border-red-200' : 'border-gray-200'
                  }`}
                  placeholder="0"
                />
                {unitCount > 0 && total_units > 0 && (
                  <div className="mt-1">
                    <div className={`h-1 rounded-full bg-gradient-to-r ${unitType.color}`} 
                      style={{ width: `${Math.min((unitCount / total_units) * 100, 100)}%` }}
                      role="progressbar"
                      aria-valuenow={Math.round((unitCount / total_units) * 100)}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`${unitType.label} represents ${Math.round((unitCount / total_units) * 100)}% of total units`}
                    />
                    <div className="text-[9px] text-gray-500 mt-0.5">
                      {Math.round((unitCount / total_units) * 100)}%
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
        
        {!isUnitMixValid && total_units > 0 && unitMixTotal > 0 && (
          <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-xs text-red-600 flex items-center" role="alert">
              <AlertCircle className="h-3.5 w-3.5 mr-1 flex-shrink-0" aria-hidden="true" />
              Unit distribution ({unitMixTotal}) must equal total units ({total_units})
            </p>
          </div>
        )}
        
        {/* Remove duplicate error display - schema validation handles this */}
      </fieldset>

      {/* Floor Count - Optional but Important */}
      <fieldset className="bg-gradient-to-br from-blue-50/30 to-indigo-50/20 rounded-xl p-3.5 border border-gray-200">
        <legend className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2.5">
          <Layers className="h-3.5 w-3.5 inline mr-1.5 text-blue-500" aria-hidden="true" />
          Floor Count
        </legend>
        <div className="flex gap-2" role="group" aria-label="Floor count selection">
          {[1, 2, 3].map((num) => (
            <button
              key={num}
              type="button"
              onClick={() => handleFloorCountSelect(num)}
              aria-pressed={floor_count === num && !floor_count_custom}
              className={`
                flex-1 py-2 px-3 rounded-lg font-medium text-sm transition-all focus:outline-none focus:ring-2 focus:ring-purple-500
                ${floor_count === num && !floor_count_custom
                  ? 'bg-gradient-to-r from-purple-500 to-indigo-500 text-white shadow-md' 
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }
              `}
            >
              {num}
            </button>
          ))}
          <input
            {...register('type_specific_details.floor_count_custom')}
            type="number"
            min="4"
            max="100"
            aria-label="Custom floor count (4 or more)"
            className="w-16 px-2 py-2 text-sm font-medium border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-center"
            placeholder="4+"
          />
        </div>
      </fieldset>

      {/* Building Features - Elevator Count */}
      <fieldset className="bg-white rounded-xl p-3.5 border border-gray-200 hover:shadow-sm transition-all">
        <legend className="text-xs font-medium text-gray-700 mb-2 flex items-center">
          <Building2 className="h-3.5 w-3.5 mr-1.5 text-indigo-500" aria-hidden="true" />
          Elevator Count
        </legend>
        <div className="flex gap-1.5" role="group" aria-label="Elevator count selection">
          {[0, 1, 2, 3, 4].map((num) => (
            <button
              key={num}
              type="button"
              onClick={() => handleElevatorCountSelect(num)}
              aria-pressed={elevator_count === num}
              className={`
                flex-1 py-2 px-3 rounded-lg font-medium text-sm transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500
                ${elevator_count === num
                  ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-md' 
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }
              `}
            >
              {num}
            </button>
          ))}
          <input
            {...register('type_specific_details.elevator_count_custom')}
            type="number"
            min="5"
            max="20"
            aria-label="Custom elevator count (5 or more)"
            className="w-16 px-2 py-2 text-sm font-medium border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-center"
            placeholder="5+"
          />
        </div>
      </fieldset>

      {/* Management Information */}
      <fieldset className="bg-gradient-to-br from-gray-50 to-gray-100/50 rounded-xl p-3.5 border border-gray-200 hover:shadow-sm transition-all">
        <legend className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2.5">
          Management
        </legend>
        <div className="space-y-2.5">
          <div className="group">
            <label className="text-xs font-medium text-gray-600 mb-1 block flex items-center">
              <UserCheck className="h-3 w-3 mr-1 text-green-500" aria-hidden="true" />
              Property Manager
            </label>
            <input
              {...register('type_specific_details.assigned_property_manager')}
              type="text"
              maxLength={200}
              className="w-full text-xs px-2.5 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent group-hover:bg-white transition-colors"
              placeholder="John Smith"
            />
          </div>

          <div className="group">
            <label className="text-xs font-medium text-gray-600 mb-1 block">
              Management Company
            </label>
            <input
              {...register('type_specific_details.property_management_company')}
              type="text"
              maxLength={200}
              className="w-full text-xs px-2.5 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-500 focus:border-transparent group-hover:bg-white transition-colors"
              placeholder="ABC Property Management"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="group">
              <label className="text-xs font-medium text-gray-600 mb-1 block flex items-center">
                <Phone className="h-3 w-3 mr-1 text-gray-500" aria-hidden="true" />
                Phone
              </label>
              <input
                {...register('type_specific_details.management_contact_phone')}
                type="tel"
                maxLength={20}
                className="w-full text-xs px-2 py-1.5 bg-gray-50 border border-gray-200 rounded-md focus:ring-2 focus:ring-gray-500 focus:border-transparent group-hover:bg-white transition-colors"
                placeholder="555-0100"
              />
            </div>
            
            <div className="group">
              <label className="text-xs font-medium text-gray-600 mb-1 block flex items-center">
                <Mail className="h-3 w-3 mr-1 text-gray-500" aria-hidden="true" />
                Email
              </label>
              <input
                {...register('type_specific_details.management_contact_email')}
                type="email"
                maxLength={255}
                className="w-full text-xs px-2 py-1.5 bg-gray-50 border border-gray-200 rounded-md focus:ring-2 focus:ring-gray-500 focus:border-transparent group-hover:bg-white transition-colors"
                placeholder="manager@email.com"
              />
            </div>
          </div>

          <label className="flex items-center px-3 py-1.5 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors">
            <input
              type="checkbox"
              {...register('type_specific_details.on_site_management')}
              className="mr-2 h-3.5 w-3.5 text-green-600 rounded focus:ring-green-500"
            />
            <span className="text-xs font-medium text-gray-700">On-Site Management Office</span>
          </label>

          {on_site_management && (
            <div className="group">
              <label className="text-xs font-medium text-gray-600 mb-1 block flex items-center">
                <MapPin className="h-3 w-3 mr-1 text-gray-500" aria-hidden="true" />
                Office Location
              </label>
              <input
                {...register('type_specific_details.management_office_location')}
                type="text"
                maxLength={100}
                className="w-full text-xs px-2 py-1.5 bg-gray-50 border border-gray-200 rounded-md focus:ring-2 focus:ring-gray-500 focus:border-transparent group-hover:bg-white transition-colors"
                placeholder="Building A, Unit 101"
              />
            </div>
          )}
        </div>
      </fieldset>

      {/* Security & Systems */}
      <fieldset className="bg-gradient-to-br from-gray-50 to-gray-100/50 rounded-xl p-3.5 border border-gray-200 hover:shadow-sm transition-all">
        <legend className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2.5">
          Security & Systems
        </legend>
        <div className="space-y-2.5">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block flex items-center">
                <Shield className="h-3 w-3 mr-1 text-red-500" aria-hidden="true" />
                Security System
              </label>
              <select
                {...register('type_specific_details.security_system_type')}
                className="w-full text-xs px-2 py-1.5 bg-white border border-gray-200 rounded-md focus:ring-2 focus:ring-red-500 focus:border-transparent"
              >
                <option value="">Select...</option>
                <option value="cameras">Camera System</option>
                <option value="key_fob">Key Fob Access</option>
                <option value="doorman">Doorman/Concierge</option>
                <option value="gated">Gated Community</option>
                <option value="combination">Combination</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block flex items-center">
                <Trash2 className="h-3 w-3 mr-1 text-gray-500" aria-hidden="true" />
                Trash System
              </label>
              <select
                {...register('type_specific_details.trash_system_type')}
                className="w-full text-xs px-2 py-1.5 bg-white border border-gray-200 rounded-md focus:ring-2 focus:ring-gray-500 focus:border-transparent"
              >
                <option value="">Select...</option>
                <option value="chute">Trash Chute</option>
                <option value="compactor">Compactor</option>
                <option value="curbside">Curbside</option>
                <option value="valet">Valet Trash</option>
                <option value="dumpster">Dumpster</option>
              </select>
            </div>
          </div>

          {(security_system_type || trash_system_type) && (
            <div className="grid grid-cols-2 gap-2">
              {security_system_type && (
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">
                    Security Details
                  </label>
                  <input
                    {...register('type_specific_details.security_system_details')}
                    type="text"
                    className="w-full text-xs px-2 py-1.5 bg-white border border-gray-200 rounded-md focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    placeholder="24/7 monitoring, access codes"
                  />
                </div>
              )}

              {trash_system_type && (
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">
                    Collection Schedule
                  </label>
                  <input
                    {...register('type_specific_details.trash_collection_schedule')}
                    type="text"
                    maxLength={200}
                    className="w-full text-xs px-2 py-1.5 bg-white border border-gray-200 rounded-md focus:ring-2 focus:ring-gray-500 focus:border-transparent"
                    placeholder="Mon/Wed/Fri 8am"
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </fieldset>

      {/* Shared Amenities */}
      <fieldset className="bg-gradient-to-br from-gray-50 to-gray-100/50 rounded-xl p-3.5 border border-gray-200 hover:shadow-sm transition-all">
        <legend className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2.5">
          Shared Amenities
        </legend>
        
        <div className="grid grid-cols-3 gap-2" role="group" aria-label="Shared amenities">
          {[
            { value: 'gym' as SharedAmenity, label: 'Fitness Center', icon: '💪' },
            { value: 'pool' as SharedAmenity, label: 'Swimming Pool', icon: '🏊' },
            { value: 'parking_garage' as SharedAmenity, label: 'Parking Garage', icon: '🚗' },
            { value: 'clubhouse' as SharedAmenity, label: 'Clubhouse', icon: '🏛️' },
            { value: 'laundry' as SharedAmenity, label: 'Laundry Facility', icon: '🧺' },
            { value: 'playground' as SharedAmenity, label: 'Playground', icon: '🎮' },
            { value: 'business_center' as SharedAmenity, label: 'Business Center', icon: '💼' },
            { value: 'pet_area' as SharedAmenity, label: 'Pet Area', icon: '🐕' },
            { value: 'bbq_area' as SharedAmenity, label: 'BBQ/Picnic Area', icon: '🍖' },
            { value: 'tennis_court' as SharedAmenity, label: 'Tennis Court', icon: '🎾' },
            { value: 'basketball_court' as SharedAmenity, label: 'Basketball Court', icon: '🏀' },
            { value: 'storage' as SharedAmenity, label: 'Storage Units', icon: '📦' }
          ].map((amenity) => (
            <label key={amenity.value} className="flex items-center px-2 py-1.5 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors">
              <input
                type="checkbox"
                checked={(shared_amenities as SharedAmenity[]).includes(amenity.value)}
                onChange={(e) => handleArrayCheckbox('shared_amenities', amenity.value, e.target.checked)}
                className="mr-1.5 h-3.5 w-3.5 text-purple-600 rounded focus:ring-purple-500"
                aria-describedby={`${amenity.value}-desc`}
              />
              <span className="text-xs mr-1" aria-hidden="true">{amenity.icon}</span>
              <span id={`${amenity.value}-desc`} className="text-xs font-medium text-gray-700">
                {amenity.label}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {/* Property Summary */}
      {(number_of_buildings > 0 || total_units > 0 || parking_spaces_total > 0) && (
        <div className={`rounded-xl p-4 shadow-lg transition-all ${
          complex_style && number_of_buildings > 0 && total_units > 0 && isUnitMixValid
            ? 'bg-gradient-to-br from-green-500 to-emerald-600 text-white'
            : 'bg-gradient-to-br from-purple-500 to-indigo-600 text-white'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-bold flex items-center gap-2">
              Complex Summary
              {complex_style && number_of_buildings > 0 && total_units > 0 && isUnitMixValid && (
                <CheckCircle className="h-4 w-4" aria-label="Form is valid" />
              )}
            </h4>
            <Zap className="h-4 w-4" aria-hidden="true" />
          </div>
          {!(complex_style && number_of_buildings > 0 && total_units > 0 && isUnitMixValid) && (
            <div className="mb-3 p-2 bg-white/10 rounded-lg">
              <p className="text-xs text-yellow-200 flex items-center">
                <AlertCircle className="h-3.5 w-3.5 mr-1.5 flex-shrink-0" aria-hidden="true" />
                {!complex_style ? 'Select complex style' :
                 !number_of_buildings ? 'Enter number of buildings' :
                 !total_units ? 'Enter total units' :
                 !isUnitMixValid ? 'Complete unit mix distribution' : 'Required fields missing'}
              </p>
            </div>
          )}
          <div className="grid grid-cols-3 gap-3">
            {number_of_buildings > 0 && (
              <div className="text-center">
                <div className="text-2xl font-bold">{number_of_buildings}</div>
                <div className="text-xs opacity-90">Building{number_of_buildings !== 1 ? 's' : ''}</div>
              </div>
            )}
            {total_units > 0 && (
              <div className="text-center">
                <div className="text-2xl font-bold">{total_units}</div>
                <div className="text-xs opacity-90">Total Units</div>
              </div>
            )}
            {parking_spaces_total > 0 && total_units > 0 && (
              <div className="text-center">
                <div className="text-2xl font-bold">{(parking_spaces_total/total_units).toFixed(1)}</div>
                <div className="text-xs opacity-90">Parking Ratio</div>
              </div>
            )}
          </div>
          {(shared_amenities as SharedAmenity[]).length > 0 && (
            <div className="mt-3 pt-3 border-t border-white/20">
              <div className="flex items-center text-xs">
                <Sparkles className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
                <span className="font-medium">{(shared_amenities as SharedAmenity[]).length} amenities</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

ApartmentComplexForm.displayName = 'ApartmentComplexForm';

export default ApartmentComplexForm;