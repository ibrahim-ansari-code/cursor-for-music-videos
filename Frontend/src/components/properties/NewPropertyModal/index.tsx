import React, { useState, useCallback, useRef } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { AnimatePresence, motion } from 'framer-motion';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'react-toastify';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';

import { PropertyType, PropertyStatus, PropertyFormData, GeneratedUnit } from '@/types/property';

import { usePropertyMutation } from './hooks/usePropertyMutation';
import { useImageUpload } from './hooks/useImageUpload';
import { propertyFormSchema, validateLocationStep, validateDetailsStep, validateMediaStep, PropertyFormSchemaType } from './validation/schemas';
import PropertyModalErrorBoundary from './components/ErrorBoundary';
import { LoadingOverlay } from './components/LoadingStates';

// Import steps
import LocationStep from './steps/LocationStep';
import DetailsStep, { DetailsStepRef } from './steps/DetailsStep/DetailsStep';
import UnitsStep from './steps/UnitsStep';
import MediaStep from './steps/MediaStep';
import ReviewStep from './steps/ReviewStep/index';

import { MapPin, Building, Layers, Camera, CheckCircle } from 'lucide-react';

// Define step configuration
const STEPS = [
  { id: 'location', title: 'Location', Icon: MapPin },
  { id: 'details', title: 'Property Details', Icon: Building },
  { id: 'units', title: 'Units Setup', Icon: Layers },
  { id: 'media', title: 'Photos & Media', Icon: Camera },
  { id: 'review', title: 'Review & Submit', Icon: CheckCircle },
];

interface PropertyData {
  id?: number;
  name?: string;
  address?: string;
  city?: string;
  province?: string;
  postal_code?: string;
  property_type?: PropertyType;
  status?: PropertyStatus;
  year_built?: number;
  description?: string;
  latitude?: number;
  longitude?: number;
  place_id?: string;
  formatted_address?: string;
  google_maps_data?: Record<string, unknown>;
  type_specific_details?: Record<string, unknown>;
  [key: string]: unknown;
}

interface NewPropertyModalProps {
  isOpen: boolean;
  onClose: () => void;
  propertyData?: PropertyData | null;
  isEditing?: boolean;
}

const NewPropertyModal: React.FC<NewPropertyModalProps> = ({
  isOpen,
  onClose,
  propertyData,
  isEditing = false,
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [stepErrors, setStepErrors] = useState<Record<number, boolean>>({});
  const detailsStepRef = useRef<DetailsStepRef>(null);
  const { createProperty, updateProperty } = usePropertyMutation();
  const { uploadMultipleImages, isUploading, uploadProgress } = useImageUpload();

  // Initialize form with react-hook-form and zod validation
  const methods = useForm<PropertyFormSchemaType>({
    resolver: zodResolver(propertyFormSchema) as any,
    mode: 'onChange', // Real-time validation on change
    defaultValues: {
      name: (propertyData?.name as string) || '',
      address: (propertyData?.address as string) || '',
      city: (propertyData?.city as string) || '',
      province: !propertyData?.province || propertyData.province === '' ? undefined : propertyData.province as any, // Cast to province enum type
      postal_code: (propertyData?.postal_code as string) || '',
      property_type: (propertyData?.property_type as PropertyType) || PropertyType.RESIDENTIAL,
      status: (propertyData?.status as PropertyStatus) || PropertyStatus.ACTIVE,
      year_built: (propertyData?.year_built as number) || null,
      description: (propertyData?.description as string) || null,
      latitude: (propertyData?.latitude as number) || null,
      longitude: (propertyData?.longitude as number) || null,
      place_id: (propertyData?.place_id as string) || null,
      formatted_address: (propertyData?.formatted_address as string) || null,
      google_maps_data: (propertyData?.google_maps_data as Record<string, unknown>) || null,
      images_to_upload: [],
      // Unit generation fields
      num_floors: (propertyData?.num_floors as string) || '',
      units_per_floor: (propertyData?.units_per_floor as string) || '',
      auto_generate_units: true,
      manual_units: '',
      // Type-specific details
      type_specific_details: propertyData?.type_specific_details || {},
    },
  });

  // Validate current step before proceeding
  const validateCurrentStep = useCallback(async () => {
    const formData = methods.getValues();
    let result;

    switch (currentStep) {
      case 0: // Location step
        result = validateLocationStep(formData);
        break;
      case 1: // Details step
        result = validateDetailsStep(formData);
        break;
      case 2: // Units step
        // Units are optional, so always return success
        return true;
      case 3: // Media step
        result = validateMediaStep(formData);
        break;
      default:
        return true;
    }

    if (!result.success && result.error) {
      // Show validation errors
      result.error.issues.forEach((error) => {
        const fieldName = error.path.join('.');
        methods.setError(fieldName as any, {
          type: 'manual',
          message: error.message,
        });
      });
      
      // Mark step as having errors
      setStepErrors(prev => ({ ...prev, [currentStep]: true }));
      
      // Show toast with error summary
      toast.error('Please review and fix the highlighted errors in the form', {
        position: 'bottom-right',
        autoClose: 4000,
      });
      
      return false;
    }

    // Clear step errors
    setStepErrors(prev => ({ ...prev, [currentStep]: false }));
    return true;
  }, [currentStep, methods]);

  const handleNext = useCallback(async () => {
    // Special handling for DetailsStep
    if (currentStep === 1 && detailsStepRef.current) {
      const currentTab = detailsStepRef.current.getCurrentTab();
      
      // If on basic tab and property type is selected, switch to specific tab
      if (currentTab === 'basic') {
        const formData = methods.getValues();
        
        // Validate basic info fields before switching tabs
        const basicValidation = validateDetailsStep(formData, 'basic');
        if (!basicValidation.success && basicValidation.error) {
          // Show validation errors for basic fields
          basicValidation.error.issues.forEach((error) => {
            const fieldName = error.path.join('.');
            methods.setError(fieldName as any, {
              type: 'manual',
              message: error.message,
            });
          });
          toast.error('Please complete all required basic information', {
            position: 'bottom-right',
            autoClose: 3000,
          });
          return;
        }
        
        // If property type is selected, switch to specific tab
        if (detailsStepRef.current.canSwitchToSpecific()) {
          detailsStepRef.current.switchToSpecificTab();
          return;
        } else {
          toast.error('Please select a property type first', {
            position: 'bottom-right',
            autoClose: 3000,
          });
          return;
        }
      }
      
      // If on specific tab, validate and move to next step
      if (currentTab === 'specific') {
        const formData = methods.getValues();
        const specificValidation = validateDetailsStep(formData, 'specific');
        
        if (!specificValidation.success && specificValidation.error) {
          // Show validation errors for specific fields
          specificValidation.error.issues.forEach((error) => {
            const fieldName = error.path.join('.');
            methods.setError(fieldName as any, {
              type: 'manual',
              message: error.message,
            });
          });
          toast.error('Please complete required property information', {
            position: 'bottom-right',
            autoClose: 3000,
          });
          return;
        }
      }
    }
    
    // Validate current step
    const isValid = await validateCurrentStep();
    
    if (isValid && currentStep < STEPS.length - 1) {
      setCurrentStep((prev) => prev + 1);
    }
  }, [currentStep, validateCurrentStep, methods]);

  const handlePrevious = useCallback(() => {
    // Special handling for DetailsStep
    if (currentStep === 1 && detailsStepRef.current) {
      const currentTab = detailsStepRef.current.getCurrentTab();
      
      // If on specific tab, go back to basic tab
      if (currentTab === 'specific') {
        detailsStepRef.current.switchToBasicTab();
        return;
      }
    }
    
    // Normal step navigation
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  }, [currentStep]);

  // Watch only specific fields needed for step validation to optimize performance
  const watchedPropertyType = methods.watch('property_type');
  const watchedName = methods.watch('name');
  const watchedStatus = methods.watch('status');
  const watchedAddress = methods.watch('address');
  const watchedCity = methods.watch('city');
  const watchedProvince = methods.watch('province');
  const watchedPostalCode = methods.watch('postal_code');
  const watchedLatitude = methods.watch('latitude');
  const watchedLongitude = methods.watch('longitude');
  const watchedTypeSpecificDetails = methods.watch('type_specific_details');
  
  // Check if current step is complete
  const isStepComplete = useCallback(() => {
    // Use specific watched values instead of watching everything
    const values = {
      property_type: watchedPropertyType,
      name: watchedName,
      status: watchedStatus,
      address: watchedAddress,
      city: watchedCity,
      province: watchedProvince,
      postal_code: watchedPostalCode,
      latitude: watchedLatitude,
      longitude: watchedLongitude,
      type_specific_details: watchedTypeSpecificDetails
    };
    

    
    switch (currentStep) {
      case 0: // Location
        return !!(values.address && values.city && values.province && 
                 values.postal_code && values.latitude && values.longitude);
      case 1: // Details
        // Basic info always required
        if (!values.name || !values.property_type || !values.status) {
          return false;
        }
        
        // If on specific tab, check property-specific required fields
        if (detailsStepRef.current?.getCurrentTab() === 'specific') {
          const details = values.type_specific_details || {};
          
          if (values.property_type === PropertyType.APARTMENT_COMPLEX) {
            const numBuildings = Number(details.number_of_buildings);
            const numUnits = Number(details.total_units);
            
            // Check all required fields for apartment complex
            if (!details.complex_style || 
                !details.number_of_buildings || isNaN(numBuildings) || numBuildings <= 0 ||
                !details.total_units || isNaN(numUnits) || numUnits <= 0) {
              return false;
            }
            
            // Check unit mix validation - required for apartment complexes
            if (numUnits > 0) {
              const unitMix: Record<string, number | string> = details.unit_mix || {};
              const unitMixSum = Object.values(unitMix).reduce((sum: number, count: number | string) => {
                const num = Number(count);
                return sum + (isNaN(num) ? 0 : num);
              }, 0);
              
              // Unit mix must be provided and must match total units exactly
              if (unitMixSum === 0 || unitMixSum !== numUnits) {
                return false;
              }
            }
            
            return true;
          }
          
          if (values.property_type === PropertyType.INDUSTRIAL) {
            const totalSqft = Number(details.total_square_feet);
            const warehouseSqft = Number(details.warehouse_square_feet) || 0;
            const officeSqft = Number(details.office_square_feet) || 0;
            const manufacturingSqft = Number(details.manufacturing_square_feet) || 0;
            
            // Check required fields
            if (!details.industrial_type) {
              return false;
            }
            if (!details.total_square_feet || isNaN(totalSqft) || totalSqft <= 0) {
              return false;
            }
            
            // Check space distribution equals total
            const distributedSqft = warehouseSqft + officeSqft + manufacturingSqft;
            if (totalSqft > 0 && distributedSqft !== totalSqft) {
              return false;
            }
            
            return true;
          }
          
          if (values.property_type === PropertyType.COMMERCIAL) {
            const usableSqft = Number(details.usable_square_feet);
            const rentableSqft = Number(details.rentable_square_feet);
            
            if (!details.space_type || !details.lease_type) {
              return false;
            }
            if (!details.usable_square_feet || isNaN(usableSqft) || usableSqft <= 0) {
              return false;
            }
            if (!details.rentable_square_feet || isNaN(rentableSqft) || rentableSqft <= 0) {
              return false;
            }
            
            return true;
          }
          
          if (values.property_type === PropertyType.RESIDENTIAL) {
            const bedrooms = Number(details.bedrooms);
            const bathrooms = Number(details.bathrooms);
            
            if (!details.bedrooms || isNaN(bedrooms) || bedrooms <= 0) {
              return false;
            }
            if (!details.bathrooms || isNaN(bathrooms) || bathrooms <= 0) {
              return false;
            }
            
            return true;
          }
          
          if (values.property_type === PropertyType.MIXED_USE) {
            // Mixed-use validation - need both residential and commercial components
            const residentialSF = Number(details.residential_square_feet) || 0;
            const commercialSF = Number(details.commercial_square_feet) || 0;
            const residentialUnits = Number(details.residential_units_count) || 0;
            
            // Check required mixed-use type
            if (!details.mixed_use_type) {
              return false;
            }
            
            // Must have both residential and commercial space
            if (residentialSF <= 0 || commercialSF <= 0) {
              return false;
            }
            
            // If residential units are specified, check unit mix validation
            if (residentialUnits > 0) {
              const unitTypes = details.residential_unit_types || {};
              const unitMixTotal = Object.values(unitTypes).reduce((sum: number, count: any) => {
                const num = Number(count);
                return sum + (isNaN(num) ? 0 : num);
              }, 0);
              
              // Unit mix must match total residential units
              if (unitMixTotal !== residentialUnits) {
                return false;
              }
            }
            
            return true;
          }
        }
        
        return true;
      case 2: // Units
        return true; // Units configuration is optional
      case 3: // Media
        return true; // Media is optional
      case 4: // Review
        return true;
      default:
        return false;
    }
  }, [currentStep, watchedPropertyType, watchedName, watchedStatus, watchedAddress, watchedCity, watchedProvince, watchedPostalCode, watchedLatitude, watchedLongitude, watchedTypeSpecificDetails, detailsStepRef]);

  const handleSubmit = async (data: PropertyFormSchemaType) => {
    setIsSubmitting(true);
    
    // Basic validation before submission
    if (!data.name?.trim()) {
      toast.error('Property name is required');
      setIsSubmitting(false);
      return;
    }
    
    if (!data.address?.trim() || !data.city?.trim() || !data.postal_code?.trim()) {
      toast.error('Complete address information is required');
      setIsSubmitting(false);
      return;
    }
    
    // Apartment complex specific validation
    if (data.property_type === PropertyType.APARTMENT_COMPLEX) {
      const details = data.type_specific_details || {};
      
      if (!details.complex_style) {
        toast.error('Complex style is required for apartment complex');
        setIsSubmitting(false);
        return;
      }
      if (!details.total_units || Number(details.total_units) <= 0) {
        toast.error('Total units is required for apartment complex');
        setIsSubmitting(false);
        return;
      }
      if (!details.number_of_buildings || Number(details.number_of_buildings) <= 0) {
        toast.error('Number of buildings is required for apartment complex');
        setIsSubmitting(false);
        return;
      }
    }
    
    // Industrial specific validation
    if (data.property_type === PropertyType.INDUSTRIAL) {
      const details = data.type_specific_details || {};
      
      if (!details.industrial_type) {
        toast.error('Industrial facility type is required');
        setIsSubmitting(false);
        return;
      }
      if (!details.total_square_feet || Number(details.total_square_feet) <= 0) {
        toast.error('Total square feet is required for industrial properties');
        setIsSubmitting(false);
        return;
      }
    }
    
    // Commercial specific validation
    if (data.property_type === PropertyType.COMMERCIAL) {
      const details = data.type_specific_details || {};
      
      if (!details.space_type) {
        toast.error('Commercial space type is required');
        setIsSubmitting(false);
        return;
      }
      if (!details.lease_type) {
        toast.error('Lease type is required for commercial properties');
        setIsSubmitting(false);
        return;
      }
      if (!details.usable_square_feet || Number(details.usable_square_feet) <= 0) {
        toast.error('Usable square feet is required for commercial properties');
        setIsSubmitting(false);
        return;
      }
      if (!details.rentable_square_feet || Number(details.rentable_square_feet) <= 0) {
        toast.error('Rentable square feet is required for commercial properties');
        setIsSubmitting(false);
        return;
      }
    }
    
    // Residential specific validation
    if (data.property_type === PropertyType.RESIDENTIAL) {
      const details = data.type_specific_details || {};
      
      if (!details.bedrooms || Number(details.bedrooms) < 0) {
        toast.error('Number of bedrooms is required for residential properties');
        setIsSubmitting(false);
        return;
      }
      if (!details.bathrooms || Number(details.bathrooms) <= 0) {
        toast.error('Number of bathrooms is required for residential properties');
        setIsSubmitting(false);
        return;
      }
    }
    
    try {
      // Handle units for creation (from generated_units or legacy method)
      let units: string[] | undefined;
      let detailedUnits: GeneratedUnit[] | undefined;
      
      if (!isEditing) {
        try {
          // Use generated_units if available (from new UnitsStep)
          const formData = data as PropertyFormData;
          if (formData.generated_units && Array.isArray(formData.generated_units) && formData.generated_units.length > 0) {
            // Send detailed unit data to backend with validation
            detailedUnits = formData.generated_units
              .filter(unit => unit?.name?.trim()) // Only include units with valid names
              .map(unit => ({
                name: unit.name.trim(),
                description: unit.description?.trim() || undefined,
                size: typeof unit.size === 'number' && unit.size > 0 ? unit.size : undefined,
                monthly_rent: typeof unit.monthly_rent === 'number' && unit.monthly_rent >= 0 ? unit.monthly_rent : undefined,
                bedrooms: typeof unit.bedrooms === 'number' && unit.bedrooms >= 0 ? unit.bedrooms : undefined,
                bathrooms: typeof unit.bathrooms === 'number' && unit.bathrooms >= 0 ? unit.bathrooms : undefined,
                floor: typeof unit.floor === 'number' && unit.floor > 0 ? unit.floor : undefined,
                is_rented: false
              }));
          } 
          // Legacy: Handle apartment complex units the old way
          else if (data.property_type === PropertyType.APARTMENT_COMPLEX) {
            if (data.auto_generate_units && data.num_floors && data.units_per_floor) {
              const floors = parseInt(data.num_floors);
              const unitsPerFloor = parseInt(data.units_per_floor);
              
              if (!isNaN(floors) && !isNaN(unitsPerFloor) && floors > 0 && unitsPerFloor > 0) {
                units = generateUnits(floors, unitsPerFloor);
              }
            } else if (!data.auto_generate_units && data.manual_units?.trim()) {
              units = data.manual_units
                .split(',')
                .map((unit) => unit.trim())
                .filter(Boolean)
                .filter(unit => unit.length > 0 && unit.length <= 50); // Validate unit names
            }
          }
        } catch (error) {
          console.warn('Error processing units data:', error);
          // Continue without units - they can be added later
        }
      }

      // Clean up the payload with validation - convert nulls to undefined for optional fields
      const cleanPayload = {
        name: data.name?.trim() || '',
        address: data.address?.trim() || '',
        city: data.city?.trim() || '',
        province: data.province || undefined,
        postal_code: data.postal_code?.trim() || '',
        property_type: data.property_type || PropertyType.RESIDENTIAL,
        status: data.status || PropertyStatus.ACTIVE,
        year_built: data.year_built ? (
          typeof data.year_built === 'number' 
            ? data.year_built 
            : parseInt(String(data.year_built))
        ) : undefined,
        description: data.description?.trim() || undefined,
        latitude: typeof data.latitude === 'number' ? data.latitude : undefined,
        longitude: typeof data.longitude === 'number' ? data.longitude : undefined,
        place_id: data.place_id?.trim() || undefined,
        formatted_address: data.formatted_address?.trim() || undefined,
        google_maps_data: data.google_maps_data && typeof data.google_maps_data === 'object' 
          ? data.google_maps_data 
          : undefined,
        type_specific_details: data.type_specific_details && typeof data.type_specific_details === 'object'
          ? {
              ...data.type_specific_details,
              // Add discriminator field for robust union validation (must match backend PropertyType enum values)
              property_type: (() => {
                // Map frontend enum to backend discriminator literals
                const discriminatorMap: Record<PropertyType, string> = {
                  [PropertyType.RESIDENTIAL]: 'Residential',
                  [PropertyType.APARTMENT_COMPLEX]: 'Apartment Complex',
                  [PropertyType.COMMERCIAL]: 'Commercial',
                  [PropertyType.INDUSTRIAL]: 'Industrial',
                  [PropertyType.MIXED_USE]: 'Mixed-Use',
                  [PropertyType.LAND]: 'Land',
                  [PropertyType.SPECIAL_PURPOSE]: 'Special Purpose',
                  [PropertyType.OTHER]: 'Other'
                };
                return discriminatorMap[data.property_type as PropertyType];
              })(),
              // Ensure required fields are properly typed for apartment complex
              ...(data.property_type === PropertyType.APARTMENT_COMPLEX && {
                complex_style: data.type_specific_details?.complex_style,
                number_of_buildings: Number(data.type_specific_details?.number_of_buildings),
                total_units: Number(data.type_specific_details?.total_units),
                unit_mix: (() => {
                  const rawUnitMix = data.type_specific_details?.unit_mix || {};
                  const cleanUnitMix: Record<string, number> = {};
                  // Only include unit types with positive values, convert null/undefined to 0 and filter out
                  Object.entries(rawUnitMix).forEach(([key, value]) => {
                    const numValue = Number(value);
                    if (!isNaN(numValue) && numValue > 0) {
                      cleanUnitMix[key] = numValue;
                    }
                  });
                  return cleanUnitMix;
                })()
              }),
              // Ensure required fields are properly typed for commercial
              ...(data.property_type === PropertyType.COMMERCIAL && {
                space_type: data.type_specific_details?.space_type,
                usable_square_feet: Number(data.type_specific_details?.usable_square_feet),
                rentable_square_feet: Number(data.type_specific_details?.rentable_square_feet),
                lease_type: data.type_specific_details?.lease_type,
                // Clean up optional numeric fields
                ceiling_height: data.type_specific_details?.ceiling_height ? Number(data.type_specific_details.ceiling_height) : undefined,
                loading_docks_count: data.type_specific_details?.loading_docks_count ? Number(data.type_specific_details.loading_docks_count) : undefined,
                floor_count: data.type_specific_details?.floor_count ? Number(data.type_specific_details.floor_count) : 1,
                common_area_maintenance_fee: data.type_specific_details?.common_area_maintenance_fee ? Number(data.type_specific_details.common_area_maintenance_fee) : undefined
              }),
              // Ensure required fields are properly typed for residential
              ...(data.property_type === PropertyType.RESIDENTIAL && {
                bedrooms: Number(data.type_specific_details?.bedrooms),
                bathrooms: Number(data.type_specific_details?.bathrooms),
                // Clean up optional numeric fields
                square_feet: data.type_specific_details?.square_feet ? Number(data.type_specific_details.square_feet) : undefined,
                lot_size: data.type_specific_details?.lot_size ? Number(data.type_specific_details.lot_size) : undefined,
                stories: data.type_specific_details?.stories ? Number(data.type_specific_details.stories) : 1,
                garage_spaces: data.type_specific_details?.garage_spaces ? Number(data.type_specific_details.garage_spaces) : 0
              }),
              // Ensure required fields are properly typed for industrial
              ...(data.property_type === PropertyType.INDUSTRIAL && {
                industrial_type: data.type_specific_details?.industrial_type,
                total_square_feet: Number(data.type_specific_details?.total_square_feet),
                // Clean up optional numeric fields - convert null/undefined to 0 or exclude
                warehouse_square_feet: data.type_specific_details?.warehouse_square_feet ? Number(data.type_specific_details.warehouse_square_feet) : undefined,
                office_square_feet: data.type_specific_details?.office_square_feet ? Number(data.type_specific_details.office_square_feet) : undefined,
                manufacturing_square_feet: data.type_specific_details?.manufacturing_square_feet ? Number(data.type_specific_details.manufacturing_square_feet) : undefined,
                clear_height: data.type_specific_details?.clear_height ? Number(data.type_specific_details.clear_height) : undefined,
                loading_docks_count: data.type_specific_details?.loading_docks_count ? Number(data.type_specific_details.loading_docks_count) : undefined,
                drive_in_doors_count: data.type_specific_details?.drive_in_doors_count ? Number(data.type_specific_details.drive_in_doors_count) : undefined,
                truck_court_size: data.type_specific_details?.truck_court_size ? Number(data.type_specific_details.truck_court_size) : undefined
              }),
              // Ensure required fields are properly typed for mixed-use
              ...(data.property_type === PropertyType.MIXED_USE && {
                // Clean up required numeric fields
                residential_square_feet: Number(data.type_specific_details?.residential_square_feet),
                commercial_square_feet: Number(data.type_specific_details?.commercial_square_feet),
                // Clean up optional numeric fields
                residential_units_count: data.type_specific_details?.residential_units_count ? Number(data.type_specific_details.residential_units_count) : undefined,
                commercial_units_count: data.type_specific_details?.commercial_units_count ? Number(data.type_specific_details.commercial_units_count) : undefined,
                parking_spaces_total: data.type_specific_details?.parking_spaces_total ? Number(data.type_specific_details.parking_spaces_total) : undefined,
                // Clean up residential unit types - filter out null values like apartment complex unit_mix
                residential_unit_types: (() => {
                  const rawUnitTypes = data.type_specific_details?.residential_unit_types || {};
                  const cleanUnitTypes: Record<string, number> = {};
                  // Only include unit types with positive values, filter out null/undefined
                  Object.entries(rawUnitTypes).forEach(([key, value]) => {
                    const numValue = Number(value);
                    if (!isNaN(numValue) && numValue > 0) {
                      cleanUnitTypes[key] = numValue;
                    }
                  });
                  return cleanUnitTypes;
                })(),
                // Clean up commercial space types array - filter out empty values
                commercial_space_types: (data.type_specific_details?.commercial_space_types || []).filter(Boolean),
                // Clean up shared amenities array - filter out empty values  
                shared_amenities: (data.type_specific_details?.shared_amenities || []).filter(Boolean)
              })
            }
          : undefined,
        detailed_units: detailedUnits,
        units: units,
      };



      // Submit property
      let propertyId: number;
      
      if (isEditing && propertyData?.id && typeof propertyData.id === 'number') {
        await updateProperty(propertyData.id, cleanPayload);
        propertyId = propertyData.id;
      } else {
        const newProperty = await createProperty({ 
          ...cleanPayload, 
          units: (units && units.length > 0) ? units : cleanPayload.units 
        } as any);
        
        if (!newProperty?.id || typeof newProperty.id !== 'number') {
          throw new Error('Invalid property ID returned from server');
        }
        
        propertyId = newProperty.id;
      }

      // Handle image uploads if any
      if (data.images_to_upload && Array.isArray(data.images_to_upload) && data.images_to_upload.length > 0) {
        try {
          toast.info('Uploading images...', {
            position: 'bottom-right',
            autoClose: 2000,
          });
          
          // Upload images to Azure with validation
          const validImages = data.images_to_upload.filter(img => img instanceof File && img.size > 0);
          
          if (validImages.length === 0) {
            throw new Error('No valid images to upload');
          }
          
          const uploadResults = await uploadMultipleImages(propertyId, validImages);
          
          if (uploadResults && uploadResults.length > 0) {
            toast.success(
              `Property ${isEditing ? 'updated' : 'created'} with ${uploadResults.length} images!`,
              {
                position: 'bottom-right',
                autoClose: 3000,
              }
            );
          } else {
            toast.warning(
              `Property ${isEditing ? 'updated' : 'created'} but image upload failed. You can add images later.`,
              {
                position: 'bottom-right',
                autoClose: 4000,
              }
            );
          }
        } catch (uploadError) {
          console.error('Image upload error:', uploadError);
          toast.warning(
            `Property ${isEditing ? 'updated' : 'created'} but image upload failed. You can add images later.`,
            {
              position: 'bottom-right',
              autoClose: 4000,
            }
          );
        }
      } else {
        toast.success(
          `Property ${isEditing ? 'updated' : 'created'} successfully!`,
          {
            position: 'bottom-right',
            autoClose: 3000,
          }
        );
      }

      onClose();
      setCurrentStep(0);
      methods.reset();
    } catch (error: Error | unknown) {
      console.error('Error submitting property:', error);
      
      let errorMessage = 'An unexpected error occurred';
      
      if (error instanceof Error) {
        errorMessage = error.message;
        
        // Provide more specific error messages based on error content
        if (error.message.includes('validation')) {
          errorMessage = 'Please check all required fields and try again';
        } else if (error.message.includes('network') || error.message.includes('fetch')) {
          errorMessage = 'Network error. Please check your connection and try again';
        } else if (error.message.includes('permission') || error.message.includes('auth')) {
          errorMessage = 'You do not have permission to perform this action';
        }
      } else if (typeof error === 'string') {
        errorMessage = error;
      }
      
      toast.error(
        `Unable to ${isEditing ? 'update' : 'create'} property: ${errorMessage}`,
        {
          position: 'bottom-right',
          autoClose: 5000,
        }
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const generateUnits = useCallback((floors: number, unitsPerFloor: number): string[] => {
    // Strict input validation to prevent invalid data
    if (!Number.isFinite(floors) || !Number.isFinite(unitsPerFloor)) {
      console.warn('Invalid input for unit generation - not finite numbers');
      return [];
    }
    
    if (floors <= 0 || unitsPerFloor <= 0) {
      console.warn('Invalid input for unit generation - values must be positive');
      return [];
    }
    
    const validFloors = Math.max(1, Math.min(100, Math.floor(floors)));
    const validUnitsPerFloor = Math.max(1, Math.min(50, Math.floor(unitsPerFloor)));
    
    const maxUnits = validFloors * validUnitsPerFloor;
    if (maxUnits > 5000) {
      console.warn('Unit generation would create too many units, limiting to reasonable size');
      return [];
    }
    
    const units: string[] = [];
    try {
      for (let floor = 1; floor <= validFloors; floor++) {
        for (let unit = 1; unit <= validUnitsPerFloor; unit++) {
          const unitName = `${floor}${String(unit).padStart(2, '0')}`;
          units.push(unitName);
        }
      }
    } catch (error) {
      console.error('Error generating units:', error);
      return [];
    }
    
    return units;
  }, []);

  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return <LocationStep onNext={handleNext} />;
      case 1:
        return <DetailsStep ref={detailsStepRef} onNext={handleNext} />;
      case 2:
        return <UnitsStep onNext={handleNext} />;
      case 3:
        return <MediaStep onNext={handleNext} />;
      case 4:
        return (
          <ReviewStep
            isEditing={isEditing}
          />
        );
      default:
        return null;
    }
  };

  return (
    <Dialog.Root open={isOpen} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0"
          />
        </Dialog.Overlay>

        <Dialog.Content className="fixed left-[50%] top-[50%] translate-x-[-50%] translate-y-[-50%] z-50">
          <PropertyModalErrorBoundary onReset={() => {
            setCurrentStep(0);
            methods.reset();
          }}>
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
              layout
              layoutId="property-modal"
              className="w-[90vw] max-w-4xl bg-white rounded-2xl shadow-2xl overflow-hidden relative"
              style={{ minHeight: '500px' }}
            >
              {/* Loading overlay */}
              <LoadingOverlay 
                isVisible={isSubmitting || isUploading} 
                message={
                  isUploading 
                    ? `Uploading images... ${uploadProgress.overall || 0}%`
                    : isEditing 
                    ? 'Updating property...' 
                    : 'Creating property...'
                } 
              />
            {/* Header */}
            <div className="relative bg-white border-b border-gray-200">
              <div className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Dialog.Title className="text-lg font-semibold text-gray-900">
                      {isEditing ? 'Edit Property' : 'New Property'}
                    </Dialog.Title>
                    <Dialog.Description className="sr-only">
                      {isEditing 
                        ? 'Edit property information including location, details, units, and media' 
                        : 'Create a new property by entering location, details, units, and media information'}
                    </Dialog.Description>
                  </div>
                  <Dialog.Close asChild>
                    <button
                      className="rounded-lg p-1.5 hover:bg-gray-100 transition-colors"
                      aria-label="Close"
                    >
                      <X className="h-5 w-5 text-gray-500" />
                    </button>
                  </Dialog.Close>
                </div>
              </div>

              {/* Step indicators */}
              <div className="px-6 pb-4">
                <div className="flex items-center justify-between">
                {STEPS.map((step, index) => (
                  <div
                    key={step.id}
                    className={`flex items-center ${
                      index < STEPS.length - 1 ? 'flex-1' : ''
                    }`}
                  >
                    <div className="flex flex-col items-center">
                      <div
                        className={`relative flex items-center justify-center w-8 h-8 rounded-full transition-all ${
                          index === currentStep
                            ? 'bg-blue-600 text-white'
                            : index < currentStep
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-200 text-gray-400'
                        }`}
                      >
                        {index < currentStep ? (
                          <CheckCircle className="w-4 h-4" />
                        ) : (
                          <step.Icon className="w-4 h-4" />
                        )}
                        {/* Error indicator */}
                        {stepErrors[index] && (
                          <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white" />
                        )}
                      </div>
                      <span className={`text-xs mt-2 font-medium ${
                        index === currentStep
                          ? 'text-gray-900'
                          : index < currentStep
                          ? 'text-gray-600'
                          : 'text-gray-400'
                      }`}>
                        {step.title}
                      </span>
                    </div>
                    {index < STEPS.length - 1 && (
                      <div
                        className={`flex-1 h-0.5 mx-3 rounded-full transition-all mt-4 ${
                          index < currentStep ? 'bg-blue-600' : 'bg-gray-200'
                        }`}
                      />
                    )}
                  </div>
                ))}
                </div>
              </div>
            </div>

            {/* Content - Dynamic height with scrolling */}
            <motion.div 
              className="max-h-[70vh] min-h-[400px] overflow-y-auto p-6"
              layout
              transition={{ 
                layout: { duration: 0.3, ease: [0.4, 0.0, 0.2, 1] }
              }}
            >
              <FormProvider {...methods}>
                <AnimatePresence mode="wait">
                  <motion.div
                    key={currentStep}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.2 }}
                  >
                    {renderStep()}
                  </motion.div>
                </AnimatePresence>
              </FormProvider>
            </motion.div>

            {/* Footer navigation */}
            <div className="border-t px-6 py-3 flex justify-between items-center bg-white">
              <button
                onClick={handlePrevious}
                disabled={currentStep === 0}
                className={`flex items-center px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  currentStep === 0
                    ? 'invisible'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Back
              </button>

              <div className="flex space-x-1.5">
                {[...Array(STEPS.length)].map((_, index) => (
                  <div
                    key={index}
                    className={`h-1.5 rounded-full transition-all ${
                      index === currentStep
                        ? 'w-6 bg-blue-600'
                        : index < currentStep
                        ? 'w-1.5 bg-blue-400'
                        : 'w-1.5 bg-gray-300'
                    }`}
                  />
                ))}
              </div>

              {currentStep < 4 ? (
                <button
                  onClick={handleNext}
                  disabled={!isStepComplete()}
                  className={`flex items-center px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    isStepComplete()
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  {/* Show "Continue" when moving from basic to specific tab */}
                  {currentStep === 1 && detailsStepRef.current?.getCurrentTab() === 'basic' && detailsStepRef.current?.canSwitchToSpecific()
                    ? 'Continue'
                    : 'Next'}
                  <ChevronRight className="h-4 w-4 ml-1" />
                </button>
              ) : (
                <button
                  onClick={methods.handleSubmit(handleSubmit as any)}
                  disabled={isSubmitting}
                  className={`flex items-center px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    !isSubmitting
                      ? 'bg-green-600 text-white hover:bg-green-700'
                      : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  {isSubmitting ? 'Submitting...' : isEditing ? 'Update' : 'Create'}
                </button>
              )}
            </div>
          </motion.div>
          </PropertyModalErrorBoundary>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};

export default NewPropertyModal;