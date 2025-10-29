import React, { useMemo, useState, useCallback, useEffect } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData, PropertyType, PropertyStatus } from '@/types/property';
import {
  Building2, Home, Store, Factory, Building, CheckCircle, Shield,
  Info, FileText, Calendar, MapPin, Briefcase, ChevronDown, ArrowRight
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import * as Select from '@radix-ui/react-select';
import * as Sentry from '@sentry/react';
import {
  fetchOwnershipEntities,
  type OwnershipEntity
} from '../../../../../utils/api/ownershipEntities';
import NewOwnershipEntityModal from '../../../../ownership/NewOwnershipEntityModal';

// Constant for "no ownership entity" value - can't use empty string with Radix Select
const NO_OWNERSHIP_ENTITY = '__none__';

// Import type-specific forms
import ResidentialForm from './typeSpecificForms/ResidentialForm';
import CommercialForm from './typeSpecificForms/CommercialForm';
import ApartmentComplexForm from './typeSpecificForms/ApartmentComplexForm';
import IndustrialForm from './typeSpecificForms/IndustrialForm';
import MixedUseForm from './typeSpecificForms/MixedUseForm';
import SectionErrorBoundary from '../../components/SectionErrorBoundary';

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
  { value: PropertyStatus.RENTED, label: 'Rented', icon: CheckCircle, color: 'emerald' },
];

const DetailsStep = React.forwardRef<DetailsStepRef, DetailsStepProps>((_props, ref) => {
  const { register, watch, setValue, formState: { errors } } = useFormContext<PropertyFormData>();
  const [activeTab, setActiveTab] = useState<'basic' | 'specific'>('basic');
  const [ownershipEntities, setOwnershipEntities] = useState<OwnershipEntity[]>([]);
  const [loadingEntities, setLoadingEntities] = useState<boolean>(true);
  const [isCreateEntityModalOpen, setIsCreateEntityModalOpen] = useState(false);
  
  const propertyType = watch('property_type');
  const propertyName = watch('name');
  const yearBuilt = watch('year_built');
  const status = watch('status') || PropertyStatus.ACTIVE;
  const description = watch('description');
  const ownershipEntityId = watch('ownership_entity_id');
  
  const selectedType = useMemo(
    () => propertyTypes.find(t => t.value === propertyType),
    [propertyType]
  );
  
  // Load ownership entities on mount
  useEffect(() => {
    const loadOwnershipEntities = async () => {
      return Sentry.startSpan(
        {
          op: 'property.modal.load_entities',
          name: 'Load Ownership Entities',
        },
        async (span) => {
          try {
            setLoadingEntities(true);
            Sentry.logger.debug('Loading ownership entities for property form');
            const response = await fetchOwnershipEntities({ pageSize: 100 });
            setOwnershipEntities(response.entities || []);
            span.setAttribute('entityCount', response.entities?.length || 0);
            Sentry.logger.debug('Ownership entities loaded successfully', { count: response.entities?.length || 0 });
          } catch (error) {
            Sentry.logger.error('Failed to load ownership entities', { 
              error: error instanceof Error ? error.message : String(error) 
            });
            Sentry.captureException(error, {
              tags: {
                component: 'DetailsStep',
                action: 'load_entities',
                feature: 'property_modal',
              },
            });
          } finally {
            setLoadingEntities(false);
          }
        }
      );
    };

    loadOwnershipEntities();
  }, []);

  // Handle ownership entity creation
  const handleEntityCreated = useCallback((newEntity: OwnershipEntity) => {
    Sentry.logger.info('Ownership entity created from property modal', {
      entityId: newEntity.id,
      entityName: newEntity.name,
      entityType: newEntity.entity_type,
    });

    // Add to list using functional setState
    setOwnershipEntities(prev => [...prev, newEntity]);

    // Auto-select the newly created entity
    setValue('ownership_entity_id', newEntity.id);

    // Close modal
    setIsCreateEntityModalOpen(false);

    // Success toast is already shown by the modal component
  }, [setValue]);

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
        return (
          <SectionErrorBoundary sectionName="ResidentialForm">
            <ResidentialForm />
          </SectionErrorBoundary>
        );
      case PropertyType.APARTMENT_COMPLEX:
        return (
          <SectionErrorBoundary 
            sectionName="ApartmentComplexForm"
            onSectionError={(section, error) => {
              console.warn(`Section ${section} failed:`, error);
            }}
          >
            <ApartmentComplexForm />
          </SectionErrorBoundary>
        );
      case PropertyType.COMMERCIAL:
        return (
          <SectionErrorBoundary sectionName="CommercialForm">
            <CommercialForm />
          </SectionErrorBoundary>
        );
      case PropertyType.INDUSTRIAL:
        return (
          <SectionErrorBoundary sectionName="IndustrialForm">
            <IndustrialForm />
          </SectionErrorBoundary>
        );
      case PropertyType.MIXED_USE:
        return (
          <SectionErrorBoundary sectionName="MixedUseForm">
            <MixedUseForm />
          </SectionErrorBoundary>
        );
      default:
        return null;
    }
  }, [propertyType]);

  return (
    <div className="flex flex-col h-full">
      {/* Tab Navigation - Only show when property type is selected */}
      {propertyType && (
        <div className="relative mb-4">
          <div className="flex p-1 bg-gray-100 dark:bg-gray-700 rounded-lg">
            <button
              type="button"
              onClick={() => setActiveTab('basic')}
              className={`relative flex-1 px-4 py-2.5 text-sm font-medium rounded-md transition-all duration-200 ${
                activeTab === 'basic'
                  ? 'text-blue-700 dark:text-blue-300 bg-white dark:bg-gray-800 shadow-sm'
                  : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-600'
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
                  ? 'text-blue-700 dark:text-blue-300 bg-white dark:bg-gray-800 shadow-sm'
                  : !propertyName
                  ? 'text-gray-400 dark:text-gray-500 cursor-not-allowed opacity-60'
                  : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-600'
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
                <div className="col-span-7 flex flex-col space-y-5 pl-1">
                  {/* Name Row */}
                  <div>
                      <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 block">
                        Property Name *
                      </label>
                      <input
                        {...register('name', { 
                          required: 'Property name is required',
                          minLength: { value: 3, message: 'At least 3 characters' }
                        })}
                        type="text"
                        className={`w-full px-3 py-2.5 text-sm font-medium border-2 rounded-xl transition-all bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                          ${errors.name 
                            ? 'border-red-300 dark:border-red-500 focus:border-red-400 dark:focus:border-red-400 focus:ring-4 focus:ring-red-100 dark:focus:ring-red-900' 
                            : 'border-gray-200 dark:border-gray-600 focus:border-blue-500 dark:focus:border-blue-400 focus:ring-4 focus:ring-blue-100 dark:focus:ring-blue-900'
                          }`}
                        placeholder="e.g., Maple Ridge Apartments"
                      />
                      {errors.name && (
                        <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                          {errors.name.message}
                        </p>
                      )}
                    </div>

                  {/* Year/Status/Ownership Row */}
                  <div className="grid grid-cols-12 gap-3">
                    <div className="col-span-3">
                      <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 block">
                        Year Built
                      </label>
                      <div className="relative">
                        <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400 dark:text-gray-500 pointer-events-none" />
                        <input
                          {...register('year_built')}
                          type="number"
                          min="1800"
                          max="2025"
                          className={`w-full pl-8 pr-2 py-2.5 text-sm font-medium border-2 rounded-xl transition-all bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                            ${errors.year_built 
                              ? 'border-red-300 dark:border-red-500 focus:border-red-400 dark:focus:border-red-400 focus:ring-4 focus:ring-red-100 dark:focus:ring-red-900' 
                              : 'border-gray-200 dark:border-gray-600 focus:border-blue-500 dark:focus:border-blue-400 focus:ring-4 focus:ring-blue-100 dark:focus:ring-blue-900'
                            }`}
                          placeholder=""
                        />
                      </div>
                    </div>

                    <div className="col-span-3">
                      <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 block">
                        Status
                      </label>
                      <Select.Root 
                        value={status} 
                        onValueChange={(value) => {
                          Sentry.logger.trace('Property status changed', { status: value });
                          setValue('status', value as PropertyStatus);
                        }}
                      >
                        <Select.Trigger className="w-full px-3 py-2.5 text-sm font-medium border-2 border-gray-200 dark:border-gray-600 rounded-xl focus:border-blue-500 dark:focus:border-blue-400 focus:ring-4 focus:ring-blue-100 dark:focus:ring-blue-900 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 transition-all flex items-center justify-between hover:border-gray-300 dark:hover:border-gray-500">
                          <Select.Value />
                          <Select.Icon>
                            <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                          </Select.Icon>
                        </Select.Trigger>
                        <Select.Portal>
                          <Select.Content 
                            className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 shadow-lg z-50"
                            position="popper"
                            side="bottom"
                            align="start"
                            sideOffset={4}
                          >
                            <Select.Viewport className="p-1">
                              {statusOptions.map((option) => (
                                <Select.Item
                                  key={option.value}
                                  value={option.value}
                                  className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                                >
                                  <Select.ItemText>{option.label}</Select.ItemText>
                                  <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                                    <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                                  </Select.ItemIndicator>
                                </Select.Item>
                              ))}
                            </Select.Viewport>
                          </Select.Content>
                        </Select.Portal>
                      </Select.Root>
                    </div>

                    <div className="col-span-6">
                      <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 block">
                        <Briefcase className="h-3 w-3 inline mr-1 mb-0.5" />
                        Ownership Entity
                      </label>
                      {loadingEntities ? (
                        <div className="w-full px-3 py-2.5 text-xs border-2 border-gray-200 dark:border-gray-600 rounded-xl bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                          Loading...
                        </div>
                      ) : (
                        <Select.Root 
                          value={ownershipEntityId ?? NO_OWNERSHIP_ENTITY} 
                          onValueChange={(value) => {
                            Sentry.logger.trace('Ownership entity changed', { value, isNone: value === NO_OWNERSHIP_ENTITY });
                            setValue('ownership_entity_id', value === NO_OWNERSHIP_ENTITY ? null : value);
                          }}
                        >
                          <Select.Trigger className="w-full px-3 py-2.5 text-sm font-medium border-2 border-gray-200 dark:border-gray-600 rounded-xl focus:border-blue-500 dark:focus:border-blue-400 focus:ring-4 focus:ring-blue-100 dark:focus:ring-blue-900 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 transition-all flex items-center justify-between hover:border-gray-300 dark:hover:border-gray-500">
                            <Select.Value placeholder="None" />
                            <Select.Icon>
                              <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                            </Select.Icon>
                          </Select.Trigger>
                          <Select.Portal>
                            <Select.Content 
                              className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 shadow-lg z-50 max-h-[300px]"
                              position="popper"
                              side="bottom"
                              align="start"
                              sideOffset={4}
                            >
                              <Select.Viewport className="p-1">
                                <Select.Item
                                  value={NO_OWNERSHIP_ENTITY}
                                  className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                                >
                                  <Select.ItemText>None</Select.ItemText>
                                  <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                                    <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                                  </Select.ItemIndicator>
                                </Select.Item>
                                {ownershipEntities.map((entity) => (
                                  <Select.Item
                                    key={entity.id}
                                    value={entity.id}
                                    className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                                  >
                                    <Select.ItemText>{entity.name}</Select.ItemText>
                                    <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                                      <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                                    </Select.ItemIndicator>
                                  </Select.Item>
                                ))}
                              </Select.Viewport>
                            </Select.Content>
                          </Select.Portal>
                        </Select.Root>
                      )}
                      {!loadingEntities && (
                        <button
                          type="button"
                          onClick={() => setIsCreateEntityModalOpen(true)}
                          className="mt-2 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium transition-colors flex items-center gap-1"
                        >
                          <Briefcase className="h-3.5 w-3.5" />
                          Create New Ownership Entity
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Property Type Selection */}
                  <div>
                    <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-3 block">
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
                            onClick={() => {
                              Sentry.startSpan(
                                {
                                  op: 'ui.click',
                                  name: 'Select Property Type',
                                },
                                (span) => {
                                  span.setAttribute('propertyType', type.value);
                                  span.setAttribute('previousType', propertyType || 'none');
                                  Sentry.logger.debug('Property type selected', { type: type.value });
                                  setValue('property_type', type.value);
                                }
                              );
                            }}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            className={`relative group overflow-hidden rounded-xl transition-all duration-200 ${
                              isSelected 
                                ? 'ring-2 ring-offset-1 ring-blue-500 shadow-lg' 
                                : 'hover:shadow-md'
                            }`}
                          >
                            <div className={`absolute inset-0 bg-gradient-to-br transition-colors duration-300 ${
                              isSelected ? colorClassMap[type.color].gradient : 'from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-800'
                            } opacity-100`} />
                            
                            <div className="relative px-3 py-4 flex flex-col items-center justify-center space-y-2 min-h-[80px]">
                              <Icon className={`h-7 w-7 transition-colors duration-300 ${
                                isSelected ? 'text-white' : 'text-gray-600 dark:text-gray-400 group-hover:text-gray-800 dark:group-hover:text-gray-200'
                              } flex-shrink-0`} />
                              <span className={`text-[10px] font-semibold text-center leading-tight transition-colors duration-300 ${
                                isSelected ? 'text-white' : 'text-gray-700 dark:text-gray-300'
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
                    <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 block">
                      Description <span className="text-gray-400 dark:text-gray-500 font-normal">(Optional)</span>
                    </label>
                    <div className="relative flex-1">
                      <textarea
                        {...register('description')}
                        rows={3}
                        maxLength={500}
                        className="w-full h-full px-3 py-2.5 pb-6 text-sm border-2 border-gray-200 dark:border-gray-600 rounded-xl focus:border-blue-500 dark:focus:border-blue-400 focus:ring-4 focus:ring-blue-100 dark:focus:ring-blue-900 resize-none transition-all bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                        placeholder="Brief description of your property..."
                      />
                      <div className="absolute bottom-1.5 right-2.5 text-[10px] text-gray-400 dark:text-gray-500">
                        {description?.length || 0}/500
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Section - Preview & Tips (5 columns) */}
                <div className="col-span-5 flex flex-col space-y-4">
                  {/* Modern Property Preview Card */}
                  <motion.div 
                    className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow"
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
                            <h4 className="font-bold text-gray-900 dark:text-gray-100 text-base">
                              {propertyName || 'Your Property'}
                            </h4>
                            <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center mt-0.5">
                              <MapPin className="h-3 w-3 mr-1" />
                              {selectedType?.label || 'Select type'}{yearBuilt ? ` • ${yearBuilt}` : ''}
                            </p>
                          </div>
                        </div>
                        
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold
                          ${status === PropertyStatus.ACTIVE 
                            ? 'bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900 dark:to-emerald-900 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-700' 
                            : status === PropertyStatus.RENTED 
                            ? 'bg-gradient-to-r from-emerald-50 to-green-50 dark:from-emerald-900 dark:to-green-900 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-700' 
                            : 'bg-gradient-to-r from-gray-50 to-slate-50 dark:from-gray-800 dark:to-slate-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700'
                          }`}>
                          <span className={`w-1.5 h-1.5 rounded-full mr-2 ${
                            status === PropertyStatus.ACTIVE ? 'bg-green-500' :
                            status === PropertyStatus.RENTED ? 'bg-emerald-500' : 'bg-gray-500'
                          }`} />
                          {statusOptions.find(s => s.value === status)?.label || 'Active'}
                        </span>
                      </div>
                    </div>
                  </motion.div>

                  {/* Compact Quick Tips */}
                  <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900 dark:to-indigo-900 rounded-xl p-4 border border-blue-100 dark:border-blue-800">
                    <div className="flex items-center mb-3">
                      <div className="p-1.5 bg-blue-100 dark:bg-blue-800 rounded-lg mr-2.5">
                        <Info className="h-4 w-4 text-blue-600 dark:text-blue-300" />
                      </div>
                      <p className="font-semibold text-sm text-blue-900 dark:text-blue-100">Quick Tips</p>
                    </div>
                    <div className="space-y-2.5">
                      <div className="flex items-center">
                        <span className="inline-flex w-1.5 h-1.5 rounded-full bg-blue-500 mr-3 flex-shrink-0"></span>
                        <span className="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">Choose the property type that best matches your building structure</span>
                      </div>
                      {propertyType && (
                        <div className="flex items-center">
                          <span className="inline-flex w-1.5 h-1.5 rounded-full bg-blue-500 mr-3 flex-shrink-0"></span>
                          <span className="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">Enter {selectedType?.label.toLowerCase()} specific details in the next tab</span>
                        </div>
                      )}
                      <div className="flex items-center">
                        <span className="inline-flex w-1.5 h-1.5 rounded-full bg-blue-500 mr-3 flex-shrink-0"></span>
                        <span className="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">Units will be configured in the next step</span>
                      </div>
                      <div className="flex items-center">
                        <span className="inline-flex w-1.5 h-1.5 rounded-full bg-blue-500 mr-3 flex-shrink-0"></span>
                        <span className="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">Complete details improve your Brikli experience</span>
                      </div>
                    </div>
                  </div>

                  {/* What's Next Section */}
                  <div className="bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/20 rounded-xl p-4 border border-green-200 dark:border-green-700">
                    <div className="flex items-center mb-3">
                      <div className="p-1.5 bg-green-100 dark:bg-green-800 rounded-lg mr-2.5">
                        <ArrowRight className="h-4 w-4 text-green-600 dark:text-green-300" />
                      </div>
                      <p className="font-semibold text-sm text-green-900 dark:text-green-100">What's Next?</p>
                    </div>
                    <div className="space-y-3">
                      <div className="flex items-start gap-3">
                        <div className="flex-shrink-0 w-5 h-5 rounded-full bg-green-600 dark:bg-green-500 flex items-center justify-center text-[10px] font-bold text-white">
                          2
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-green-900 dark:text-green-100">Units Setup</p>
                          <p className="text-xs text-green-700 dark:text-green-300 mt-0.5">Configure rentable units for your property</p>
                        </div>
                      </div>
                      <div className="flex items-start gap-3">
                        <div className="flex-shrink-0 w-5 h-5 rounded-full bg-green-600 dark:bg-green-500 flex items-center justify-center text-[10px] font-bold text-white">
                          3
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-green-900 dark:text-green-100">Photos & Media</p>
                          <p className="text-xs text-green-700 dark:text-green-300 mt-0.5">Add images to showcase your property</p>
                        </div>
                      </div>
                      <div className="flex items-start gap-3">
                        <div className="flex-shrink-0 w-5 h-5 rounded-full bg-green-600 dark:bg-green-500 flex items-center justify-center text-[10px] font-bold text-white">
                          4
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-green-900 dark:text-green-100">Review & Submit</p>
                          <p className="text-xs text-green-700 dark:text-green-300 mt-0.5">Final check and create your property</p>
                        </div>
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

      {/* Ownership Entity Creation Modal */}
      <NewOwnershipEntityModal
        isOpen={isCreateEntityModalOpen}
        onClose={() => setIsCreateEntityModalOpen(false)}
        onSuccess={handleEntityCreated}
      />
    </div>
  );
});





DetailsStep.displayName = 'DetailsStep';

// Wrap with Sentry error boundary for production error tracking
export default Sentry.withErrorBoundary(React.memo(DetailsStep), {
  fallback: ({ resetError }) => (
    <div className="p-6 text-center">
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-red-800 dark:text-red-200 mb-2">
          Property Details Form Error
        </h3>
        <p className="text-sm text-red-600 dark:text-red-300 mb-4">
          There was an issue loading the property details form.
        </p>
        <button
          onClick={resetError}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
        >
          Try Again
        </button>
      </div>
    </div>
  ),
  onError: (error: unknown, componentStack: string) => {
    Sentry.logger.error('DetailsStep component error', {
      error: error instanceof Error ? error.message : String(error),
      componentStack,
    });
  },
  beforeCapture: (scope) => {
    scope.setTag('component', 'DetailsStep');
    scope.setTag('feature', 'property_modal');
    scope.setTag('step', 'details');
  },
});