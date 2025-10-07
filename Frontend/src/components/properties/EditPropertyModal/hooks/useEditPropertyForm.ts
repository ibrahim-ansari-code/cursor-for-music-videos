import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'react-toastify';
import { useEffect } from 'react';
import * as Sentry from '@sentry/react';
import { usePropertyMutation } from '../../NewPropertyModal/hooks/usePropertyMutation';
import { editPropertySchema, EditPropertyFormData } from '../validation/editPropertySchema';
import { Property, PropertyType } from '../../../../types/property';

interface UseEditPropertyFormProps {
  propertyData: Property;
  onSuccess: () => void;
  onClose: () => void;
}

/**
 * Transform property data from backend format to React Hook Form compatible format
 * Ensures all nested fields are properly structured for RHF registration
 */
const transformPropertyDataForForm = (propertyData: Property): EditPropertyFormData => {
  const baseData: EditPropertyFormData = {
    name: propertyData.name || '',
    status: propertyData.status,
    year_built: propertyData.year_built ?? null,
    description: propertyData.description || null,
    address: propertyData.address || '',
    city: propertyData.city || '',
    province: propertyData.province as any,
    postal_code: propertyData.postal_code || '',
    latitude: propertyData.latitude ?? null,
    longitude: propertyData.longitude ?? null,
    place_id: propertyData.place_id || null,
    formatted_address: propertyData.formatted_address || null,
    google_maps_data: (propertyData.google_maps_data as Record<string, unknown>) || null,
  };

  // Deep clone and properly structure type_specific_details
  if (propertyData.type_specific_details && typeof propertyData.type_specific_details === 'object') {
    const details = { ...propertyData.type_specific_details } as Record<string, any>;

    // Discriminator map for validation
    const discriminatorMap = {
      [PropertyType.RESIDENTIAL]: 'Residential',
      [PropertyType.APARTMENT_COMPLEX]: 'Apartment Complex',
      [PropertyType.COMMERCIAL]: 'Commercial',
      [PropertyType.INDUSTRIAL]: 'Industrial',
      [PropertyType.MIXED_USE]: 'Mixed-Use',
      [PropertyType.LAND]: 'Land',
      [PropertyType.SPECIAL_PURPOSE]: 'Special Purpose',
      [PropertyType.OTHER]: 'Other'
    } as const;

    // Ensure nested objects are properly structured for React Hook Form
    // This is critical for fields registered as paths like 'type_specific_details.unit_mix.studio'
    baseData.type_specific_details = {
      ...details,
      // Add discriminator field for validation
      property_type: discriminatorMap[propertyData.property_type],
      // Ensure unit_mix is an object (for apartment complex)
      // Convert null/undefined to empty object to avoid registration issues
      ...(details.unit_mix && typeof details.unit_mix === 'object'
        ? {
            unit_mix: {
              studio: Number(details.unit_mix.studio) || 0,
              '1br': Number(details.unit_mix['1br']) || 0,
              '2br': Number(details.unit_mix['2br']) || 0,
              '3br': Number(details.unit_mix['3br']) || 0,
              '4br': Number(details.unit_mix['4br']) || 0,
              penthouse: Number(details.unit_mix.penthouse) || 0,
            }
          }
        : {}),
      // Ensure shared_amenities is an array (for apartment complex)
      ...(details.shared_amenities && Array.isArray(details.shared_amenities)
        ? { shared_amenities: [...details.shared_amenities] }
        : {}),
      // Ensure residential_unit_types is an object (for mixed-use)
      ...(details.residential_unit_types && typeof details.residential_unit_types === 'object'
        ? { residential_unit_types: { ...details.residential_unit_types } }
        : {}),
      // Ensure arrays are properly copied
      ...(details.commercial_space_types && Array.isArray(details.commercial_space_types)
        ? { commercial_space_types: [...details.commercial_space_types] }
        : {}),
      ...(details.amenities && Array.isArray(details.amenities)
        ? { amenities: [...details.amenities] }
        : {}),
      // Ensure numeric fields are properly typed
      ...(details.number_of_buildings !== undefined && details.number_of_buildings !== null
        ? { number_of_buildings: Number(details.number_of_buildings) }
        : {}),
      ...(details.total_units !== undefined && details.total_units !== null
        ? { total_units: Number(details.total_units) }
        : {}),
      ...(details.parking_spaces_total !== undefined && details.parking_spaces_total !== null
        ? { parking_spaces_total: Number(details.parking_spaces_total) }
        : {}),
      ...(details.floor_count !== undefined && details.floor_count !== null
        ? { floor_count: Number(details.floor_count) }
        : {}),
      ...(details.elevator_count !== undefined && details.elevator_count !== null
        ? { elevator_count: Number(details.elevator_count) }
        : {}),
    };
  } else {
    // Add discriminator even when no type_specific_details exist
    const discriminatorMap = {
      [PropertyType.RESIDENTIAL]: 'Residential',
      [PropertyType.APARTMENT_COMPLEX]: 'Apartment Complex',
      [PropertyType.COMMERCIAL]: 'Commercial',
      [PropertyType.INDUSTRIAL]: 'Industrial',
      [PropertyType.MIXED_USE]: 'Mixed-Use',
      [PropertyType.LAND]: 'Land',
      [PropertyType.SPECIAL_PURPOSE]: 'Special Purpose',
      [PropertyType.OTHER]: 'Other'
    } as const;
    
    baseData.type_specific_details = {
      property_type: discriminatorMap[propertyData.property_type],
    };
  }

  return baseData;
};

export const useEditPropertyForm = ({ propertyData, onSuccess, onClose }: UseEditPropertyFormProps) => {
  const { updateProperty, isUpdating } = usePropertyMutation();

  // Initialize form with basic structure (will be reset with full data in useEffect)
  const methods = useForm<EditPropertyFormData>({
    resolver: zodResolver(editPropertySchema),
    mode: 'onChange',
    defaultValues: transformPropertyDataForForm(propertyData),
  });

  const {
    handleSubmit,
    formState: { errors, isDirty },
    reset,
    watch,
  } = methods;

  // Watch property type to show appropriate type-specific fields
  const propertyType = propertyData.property_type;

  // Reset form with properly transformed data when propertyData changes
  // This ensures all nested fields are recognized by React Hook Form
  useEffect(() => {
    const formData = transformPropertyDataForForm(propertyData);
    reset(formData, { keepDirty: false });

    // Log for debugging if needed
    if (import.meta.env.DEV) {
      console.log('[EditPropertyModal] Form reset with data:', {
        propertyId: propertyData.id,
        propertyType: propertyData.property_type,
        hasTypeSpecificDetails: !!formData.type_specific_details,
        typeSpecificDetailsKeys: formData.type_specific_details
          ? Object.keys(formData.type_specific_details)
          : [],
      });
    }
  }, [propertyData, reset]);

  const onSubmit = async (data: EditPropertyFormData) => {
    // Debug: Log when onSubmit is called
    if (import.meta.env.DEV) {
      console.log('[EditPropertyModal] onSubmit called with data:', data);
    }

    if (!propertyData.id) {
      toast.error('Property ID is missing');
      return;
    }

    try {
      // Build payload with only changed fields
      const payload: Record<string, unknown> = {};

      // Include fields that have values (even if they match original)
      if (data.name !== undefined) payload.name = data.name.trim();
      if (data.status !== undefined) payload.status = data.status;
      if (data.year_built !== undefined) payload.year_built = data.year_built;
      if (data.description !== undefined) payload.description = data.description?.trim() || null;
      if (data.address !== undefined) payload.address = data.address.trim();
      if (data.city !== undefined) payload.city = data.city.trim();
      if (data.province !== undefined) payload.province = data.province;
      if (data.postal_code !== undefined) payload.postal_code = data.postal_code.trim();
      if (data.latitude !== undefined) payload.latitude = data.latitude;
      if (data.longitude !== undefined) payload.longitude = data.longitude;
      if (data.place_id !== undefined) payload.place_id = data.place_id;
      if (data.formatted_address !== undefined) payload.formatted_address = data.formatted_address;
      if (data.google_maps_data !== undefined) payload.google_maps_data = data.google_maps_data;

      // Handle type-specific details
      if (data.type_specific_details && Object.keys(data.type_specific_details).length > 0) {
        // Add discriminator field for backend validation
        const discriminatorMap = {
          [PropertyType.RESIDENTIAL]: 'Residential',
          [PropertyType.APARTMENT_COMPLEX]: 'Apartment Complex',
          [PropertyType.COMMERCIAL]: 'Commercial',
          [PropertyType.INDUSTRIAL]: 'Industrial',
          [PropertyType.MIXED_USE]: 'Mixed-Use',
          [PropertyType.LAND]: 'Land',
          [PropertyType.SPECIAL_PURPOSE]: 'Special Purpose',
          [PropertyType.OTHER]: 'Other'
        } as const;

        payload.type_specific_details = {
          ...data.type_specific_details,
          property_type: discriminatorMap[propertyType],
        };
      }

      await updateProperty(propertyData.id, payload);

      toast.success('Property updated successfully!', {
        position: 'top-right',
        autoClose: 3000,
      });

      onSuccess();
      onClose();
    } catch (error) {
      // Structured logging with Sentry
      Sentry.logger.error('Error updating property', {
        error: error instanceof Error ? error.message : String(error),
        propertyId: propertyData.id,
        propertyType,
      });

      // Report to Sentry
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)), {
        tags: {
          action: 'update_property',
          component: 'EditPropertyModal',
          propertyType,
        },
        contexts: {
          property: {
            propertyId: propertyData.id,
            propertyType,
            isDirty,
          },
        },
      });

      const errorMessage = error instanceof Error ? error.message : 'Failed to update property';
      toast.error(`Unable to update property: ${errorMessage}`, {
        position: 'top-right',
        autoClose: 5000,
      });
    }
  };

  return {
    methods,
    onSubmit: handleSubmit(onSubmit),
    isSubmitting: isUpdating,
    isDirty,
    errors,
    propertyType,
    reset,
    watch,
  };
};
