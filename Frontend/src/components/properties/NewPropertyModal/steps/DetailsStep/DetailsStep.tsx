import React, { useMemo, useState, useCallback } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData, PropertyType, PropertyStatus } from '@/types/property';
import { 
  Building2, Home, Store, Factory, Building, CheckCircle, Shield, Wrench,
  Info, FileText, Calendar, MapPin
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Import type-specific forms
import ResidentialForm from './typeSpecificForms/ResidentialForm';
import CommercialForm from './typeSpecificForms/CommercialForm';
import ApartmentComplexForm from './typeSpecificForms/ApartmentComplexForm';
import IndustrialForm from './typeSpecificForms/IndustrialForm';
import MixedUseForm from './typeSpecificForms/MixedUseForm';

export interface DetailsStepRef {
  switchToSpecificTab: () => void;
  switchToBasicTab: () => void;
  getCurrentTab: () => 'basic' | 'specific';
  canSwitchToSpecific: () => boolean;
}

interface DetailsStepProps {
  onNext?: () => void;
}

// Color mapping for Tailwind CSS production safety
const colorClassMap = {
  emerald: {
    gradient: 'from-emerald-400 to-emerald-600',
    lightGradient: 'from-emerald-50 to-emerald-100',
    border: 'border-emerald-200',
    text: 'text-emerald-600'
  },
  blue: {
    gradient: 'from-blue-400 to-blue-600',
    lightGradient: 'from-blue-50 to-blue-100',
    border: 'border-blue-200',
    text: 'text-blue-600'
  },
  orange: {
    gradient: 'from-orange-400 to-orange-600',
    lightGradient: 'from-orange-50 to-orange-100',
    border: 'border-orange-200',
    text: 'text-orange-600'
  },
  purple: {
    gradient: 'from-purple-400 to-purple-600',
    lightGradient: 'from-purple-50 to-purple-100',
    border: 'border-purple-200',
    text: 'text-purple-600'
  },
  red: {
    gradient: 'from-red-400 to-red-600',
    lightGradient: 'from-red-50 to-red-100',
    border: 'border-red-200',
    text: 'text-red-600'
  }
};

// Property type configurations
const propertyTypes = [
  { 
    value: PropertyType.RESIDENTIAL, 
    label: 'Residential', 
    icon: Home,
    color: 'emerald' as keyof typeof colorClassMap,
    description: 'Single family home'
  },
  { 
    value: PropertyType.APARTMENT_COMPLEX, 
    label: 'Apartments', 
    icon: Building2,
    color: 'blue' as keyof typeof colorClassMap,
    description: 'Multi-unit building'
  },
  { 
    value: PropertyType.COMMERCIAL, 
    label: 'Commercial', 
    icon: Store,
    color: 'orange' as keyof typeof colorClassMap,
    description: 'Retail or office'
  },
  { 
    value: PropertyType.MIXED_USE, 
    label: 'Mixed Use', 
    icon: Building,
    color: 'purple' as keyof typeof colorClassMap,
    description: 'Combined use'
  },
  { 
    value: PropertyType.INDUSTRIAL, 
    label: 'Industrial', 
    icon: Factory,
    color: 'red' as keyof typeof colorClassMap,
    description: 'Warehouse space'
  },
];

const statusOptions = [
  { value: PropertyStatus.ACTIVE, label: 'Active', icon: CheckCircle, color: 'green' },
  { value: PropertyStatus.INACTIVE, label: 'Inactive', icon: Shield, color: 'gray' },
  { value: PropertyStatus.MAINTENANCE, label: 'Maintenance', icon: Wrench, color: 'orange' },
];

const DetailsStep = React.forwardRef<DetailsStepRef, DetailsStepProps>((_props, ref) => {
  const { register, watch, setValue, formState: { errors } } = useFormContext<PropertyFormData>();
  const [activeTab, setActiveTab] = useState<'basic' | 'specific'>('basic');
  
  const propertyType = watch('property_type');
  const propertyName = watch('name');
  const yearBuilt = watch('year_built');
  const status = watch('status') || PropertyStatus.ACTIVE;
  const description = watch('description');
  
  const selectedType = useMemo(
    () => propertyTypes.find(t => t.value === propertyType),
    [propertyType]
  );
  
  
  // Set defaults - status is already handled with fallback in watch

  // Expose methods to parent
  React.useImperativeHandle(ref, () => ({
      switchToSpecificTab: () => {
        if (propertyType && activeTab === 'basic') {
          setActiveTab('specific');
        }
      },
      switchToBasicTab: () => {
        setActiveTab('basic');
      },
      getCurrentTab: () => activeTab,
      canSwitchToSpecific: () => !!propertyType
    }), [activeTab, propertyType]);

  // Render type-specific fields based on property type
  const renderTypeSpecificFields = useCallback(() => {
    if (!propertyType) return null;

    switch (propertyType) {
      case PropertyType.RESIDENTIAL:
        return <ResidentialForm />;
      case PropertyType.APARTMENT_COMPLEX:
        return <ApartmentComplexForm />;
      case PropertyType.COMMERCIAL:
        return <CommercialForm />;
      case PropertyType.INDUSTRIAL:
        return <IndustrialForm />;
      case PropertyType.MIXED_USE:
        return <MixedUseForm />;
      default:
        return null;
    }
  }, [propertyType]);

  return (
    <div className="flex flex-col h-full">
      {/* Tab Navigation - Only show when property type is selected */}
      {propertyType && (
        <div className="relative mb-4">
          <div className="flex p-1 bg-gray-100 rounded-lg">
            <button
              type="button"
              onClick={() => setActiveTab('basic')}
              className={`relative flex-1 px-4 py-2.5 text-sm font-medium rounded-md transition-all duration-200 ${
                activeTab === 'basic'
                  ? 'text-blue-700 bg-white shadow-sm'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <FileText className="h-3.5 w-3.5 inline mr-1.5 mb-0.5" />
              Basic Info
            </button>
            <button
              type="button"
              onClick={() => {
                // Only allow switching to specific tab if basic info is complete
                if (propertyName && propertyType) {
                  setActiveTab('specific');
                }
              }}
              disabled={!propertyName}
              className={`relative flex-1 px-4 py-2.5 text-sm font-medium rounded-md transition-all duration-200 ${
                activeTab === 'specific'
                  ? 'text-blue-700 bg-white shadow-sm'
                  : !propertyName
                  ? 'text-gray-400 cursor-not-allowed opacity-60'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
              title={!propertyName ? 'Please complete basic information first' : undefined}
            >
              <Building2 className="h-3.5 w-3.5 inline mr-1.5 mb-0.5" />
              {selectedType?.label} Information
            </button>
          </div>
        </div>
      )}

      {/* Content Area with smooth transitions */}
      <div className="flex-1 relative overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: activeTab === 'specific' ? 40 : -40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: activeTab === 'specific' ? -40 : 40 }}
            transition={{ 
              duration: 0.3, 
              ease: [0.4, 0.0, 0.2, 1],
              opacity: { duration: 0.2 }
            }}
            className="h-full"
          >
        {(!propertyType || activeTab === 'basic') && (
          <div className="h-full">
              <div className="grid grid-cols-12 gap-6 h-full">
                {/* Left Section - Form Fields (7 columns) */}
                <div className="col-span-7 flex flex-col space-y-5">
                  {/* Name and Year/Status Row */}
                  <div className="flex gap-3">
                    <div className="flex-1">
                      <label className="text-xs font-semibold text-gray-700 mb-1.5 block">
                        Property Name *
                      </label>
                      <input
                        {...register('name', { 
                          required: 'Property name is required',
                          minLength: { value: 3, message: 'At least 3 characters' }
                        })}
                        type="text"
                        className={`w-full px-3 py-2.5 text-sm font-medium border-2 rounded-xl transition-all
                          ${errors.name 
                            ? 'border-red-300 focus:border-red-400 focus:ring-4 focus:ring-red-100' 
                            : 'border-gray-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-100'
                          }`}
                        placeholder="e.g., Maple Ridge Apartments"
                      />
                      {errors.name && (
                        <p className="mt-1 text-xs text-red-600">
                          {errors.name.message}
                        </p>
                      )}
                    </div>

                    <div className="w-32">
                      <label className="text-xs font-semibold text-gray-700 mb-1.5 block">
                        Year Built
                      </label>
                      <div className="relative">
                        <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400 pointer-events-none" />
                        <input
                          {...register('year_built')}
                          type="number"
                          min="1800"
                          max="2025"
                          className={`w-full pl-8 pr-2 py-2.5 text-sm font-medium border-2 rounded-xl transition-all
                            ${errors.year_built 
                              ? 'border-red-300 focus:border-red-400 focus:ring-4 focus:ring-red-100' 
                              : 'border-gray-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-100'
                            }`}
                          placeholder=""
                        />
                      </div>
                      <div className="h-4 mt-1">
                        {errors.year_built && (
                          <p className="text-xs text-red-600">
                            {errors.year_built.message}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="w-36">
                      <label className="text-xs font-semibold text-gray-700 mb-1.5 block">
                        Status
                      </label>
                      <select
                        {...register('status')}
                        className="w-full px-3 py-2.5 text-sm font-medium border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-100 bg-white appearance-none cursor-pointer"
                      >
                        {statusOptions.map(option => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Property Type Selection */}
                  <div>
                    <label className="text-xs font-semibold text-gray-700 mb-3 block">
                      Property Type *
                    </label>
                    <div className="grid grid-cols-5 gap-3 p-2">
                      {propertyTypes.map((type) => {
                        const Icon = type.icon;
                        const isSelected = propertyType === type.value;
                        return (
                          <motion.button
                            key={type.value}
                            type="button"
                            onClick={() => setValue('property_type', type.value)}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            className={`relative group overflow-hidden rounded-xl transition-all duration-200 ${
                              isSelected 
                                ? 'ring-2 ring-offset-1 ring-blue-500 shadow-lg' 
                                : 'hover:shadow-md'
                            }`}
                          >
                            <div className={`absolute inset-0 bg-gradient-to-br ${
                              isSelected ? colorClassMap[type.color].gradient : 'from-gray-50 to-gray-100'
                            } opacity-100`} />
                            
                            <div className="relative px-3 py-4 flex flex-col items-center justify-center space-y-2 min-h-[80px]">
                              <Icon className={`h-7 w-7 ${
                                isSelected ? 'text-white' : 'text-gray-600 group-hover:text-gray-800'
                              } transition-colors flex-shrink-0`} />
                              <span className={`text-[10px] font-semibold text-center leading-tight ${
                                isSelected ? 'text-white' : 'text-gray-700'
                              }`}>
                                {type.label}
                              </span>
                            </div>
                            
                            {isSelected && (
                              <div className="absolute top-1 right-1">
                                <div className="bg-white rounded-full p-0.5">
                                  <CheckCircle className="h-3.5 w-3.5 text-blue-600" />
                                </div>
                              </div>
                            )}
                          </motion.button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Description with internal counter */}
                  <div className="flex-1 flex flex-col">
                    <label className="text-xs font-semibold text-gray-700 mb-1.5 block">
                      Description <span className="text-gray-400 font-normal">(Optional)</span>
                    </label>
                    <div className="relative flex-1">
                      <textarea
                        {...register('description')}
                        rows={3}
                        maxLength={500}
                        className="w-full h-full px-3 py-2.5 pb-6 text-sm border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-100 resize-none transition-all"
                        placeholder="Brief description of your property..."
                      />
                      <div className="absolute bottom-1.5 right-2.5 text-[10px] text-gray-400">
                        {description?.length || 0}/500
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Section - Preview & Tips (5 columns) */}
                <div className="col-span-5 flex flex-col space-y-4">
                  {/* Modern Property Preview Card */}
                  <motion.div 
                    className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-white to-gray-50 border border-gray-200 shadow-sm hover:shadow-md transition-shadow"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                  >
                    {selectedType && (
                      <div className={`absolute top-0 right-0 w-32 h-32 opacity-10 blur-3xl ${
                        selectedType.color === 'emerald' ? 'bg-gradient-to-br from-emerald-400 to-emerald-600' :
                        selectedType.color === 'blue' ? 'bg-gradient-to-br from-blue-400 to-blue-600' :
                        selectedType.color === 'orange' ? 'bg-gradient-to-br from-orange-400 to-orange-600' :
                        selectedType.color === 'purple' ? 'bg-gradient-to-br from-purple-400 to-purple-600' :
                        selectedType.color === 'red' ? 'bg-gradient-to-br from-red-400 to-red-600' :
                        'bg-gradient-to-br from-gray-400 to-gray-600'
                      }`} />
                    )}
                    
                    <div className="relative px-4 py-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          {selectedType ? (
                            <div className={`p-2 rounded-xl ${
                              selectedType.color === 'emerald' ? 'bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-200' :
                              selectedType.color === 'blue' ? 'bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200' :
                              selectedType.color === 'orange' ? 'bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200' :
                              selectedType.color === 'purple' ? 'bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200' :
                              selectedType.color === 'red' ? 'bg-gradient-to-br from-red-50 to-red-100 border-red-200' :
                              'bg-gradient-to-br from-gray-50 to-gray-100 border-gray-200'
                            }`}>
                              <selectedType.icon className={`h-5 w-5 ${
                                selectedType.color === 'emerald' ? 'text-emerald-600' :
                                selectedType.color === 'blue' ? 'text-blue-600' :
                                selectedType.color === 'orange' ? 'text-orange-600' :
                                selectedType.color === 'purple' ? 'text-purple-600' :
                                selectedType.color === 'red' ? 'text-red-600' :
                                'text-gray-600'
                              }`} />
                            </div>
                          ) : (
                            <div className="p-2 rounded-xl bg-gradient-to-br from-gray-100 to-gray-200 border border-gray-300">
                              <Home className="h-5 w-5 text-gray-500" />
                            </div>
                          )}
                          <div>
                            <h4 className="font-bold text-gray-900 text-base">
                              {propertyName || 'Your Property'}
                            </h4>
                            <p className="text-xs text-gray-500 flex items-center mt-0.5">
                              <MapPin className="h-3 w-3 mr-1" />
                              {selectedType?.label || 'Select type'}{yearBuilt ? ` • ${yearBuilt}` : ''}
                            </p>
                          </div>
                        </div>
                        
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold
                          ${status === PropertyStatus.ACTIVE 
                            ? 'bg-gradient-to-r from-green-50 to-emerald-50 text-green-700 border border-green-200' 
                            : status === PropertyStatus.MAINTENANCE 
                            ? 'bg-gradient-to-r from-orange-50 to-amber-50 text-orange-700 border border-orange-200' 
                            : 'bg-gradient-to-r from-gray-50 to-slate-50 text-gray-700 border border-gray-200'
                          }`}>
                          <span className={`w-1.5 h-1.5 rounded-full mr-2 ${
                            status === PropertyStatus.ACTIVE ? 'bg-green-500' :
                            status === PropertyStatus.MAINTENANCE ? 'bg-orange-500' : 'bg-gray-500'
                          }`} />
                          {statusOptions.find(s => s.value === status)?.label || 'Active'}
                        </span>
                      </div>
                    </div>
                  </motion.div>

                  {/* Compact Quick Tips */}
                  <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-4 border border-blue-100 flex-1 flex flex-col">
                    <div className="flex items-center mb-4">
                      <div className="p-1.5 bg-blue-100 rounded-lg mr-2.5">
                        <Info className="h-4 w-4 text-blue-600" />
                      </div>
                      <p className="font-semibold text-sm text-blue-900">Quick Tips</p>
                    </div>
                    <div className="flex flex-col justify-between flex-1">
                      <div className="flex items-center">
                        <span className="inline-flex w-1.5 h-1.5 rounded-full bg-blue-500 mr-3 flex-shrink-0"></span>
                        <span className="text-xs text-blue-700 leading-relaxed">Choose the property type that best matches your building structure</span>
                      </div>
                      {propertyType && (
                        <div className="flex items-center">
                          <span className="inline-flex w-1.5 h-1.5 rounded-full bg-blue-500 mr-3 flex-shrink-0"></span>
                          <span className="text-xs text-blue-700 leading-relaxed">Enter {selectedType?.label.toLowerCase()} specific details in the next tab</span>
                        </div>
                      )}
                      <div className="flex items-center">
                        <span className="inline-flex w-1.5 h-1.5 rounded-full bg-blue-500 mr-3 flex-shrink-0"></span>
                        <span className="text-xs text-blue-700 leading-relaxed">Units will be configured in the next step</span>
                      </div>
                      <div className="flex items-center">
                        <span className="inline-flex w-1.5 h-1.5 rounded-full bg-blue-500 mr-3 flex-shrink-0"></span>
                        <span className="text-xs text-blue-700 leading-relaxed">Complete details improve your Brikli experience</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
          </div>
        )}

        {propertyType && activeTab === 'specific' && (
          <div className="h-full min-h-[400px] overflow-y-auto">
            {renderTypeSpecificFields()}
          </div>
        )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
});





DetailsStep.displayName = 'DetailsStep';

export default React.memo(DetailsStep);