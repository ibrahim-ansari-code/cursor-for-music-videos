import { useState } from 'react';
import { toast } from 'react-toastify';
import { reportError } from '../../../../utils/error-reporting';
import { fetchPropertyById } from '../../../../utils/api';
import { useDeleteProperty } from '../../../../hooks/usePropertiesMutations';
import { Property } from '../../../../types/property';

// Runtime validation for property data
const validateProperty = (data: unknown): data is Property => {
  if (!data || typeof data !== 'object') return false;
  
  const property = data as Record<string, unknown>;
  
  // Check required fields exist and have correct types
  return (
    typeof property.id === 'number' &&
    typeof property.name === 'string' &&
    typeof property.address === 'string' &&
    typeof property.city === 'string' &&
    typeof property.province === 'string' &&
    typeof property.postal_code === 'string' &&
    typeof property.property_type === 'string' &&
    typeof property.status === 'string' &&
    typeof property.created_at === 'string'
  );
};

export const usePropertiesActions = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentProperty, setCurrentProperty] = useState<Property | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const deletePropertyMutation = useDeleteProperty();

  const handleEditProperty = async (propertyId: number) => {
    try {
      const property = await fetchPropertyById(propertyId);
      
      // Runtime validation instead of type assertion
      if (!validateProperty(property)) {
        const error = new Error('Invalid property data received from API');
        console.error('Invalid property data received from API. Property ID: ', propertyId);
        
        // Report property data validation errors with data sanitization
        reportError(error, {
          component: 'usePropertiesActions',
          action: 'edit_property',
          tags: {
            dataValidation: true,
          },
          extra: {
            property: {
              propertyId,
              receivedData: property, // Will be sanitized automatically
            }
          },
        }, 'error');
        
        toast.error('Invalid property data received. Please try again.');
        return;
      }
      
      setCurrentProperty(property);
      setIsEditing(true);
      setIsModalOpen(true);
    } catch (error) {
      console.error('Error fetching property details:', error);
      
      // Report property fetch errors with proper error handling
      reportError(error instanceof Error ? error : new Error(String(error)), {
        component: 'usePropertiesActions',
        action: 'fetch_property_details',
        extra: {
          property: {
            propertyId,
          }
        },
      }, 'error');
      
      toast.error('Failed to load property details');
    }
  };

  const handleDeleteProperty = async (propertyId: number) => {
    try {
      await deletePropertyMutation.mutateAsync(propertyId);
      toast.success('Property was successfully deleted');
    } catch (error) {
      console.error('Error deleting property:', error);
      
      // Report property deletion errors with proper error handling  
      reportError(error instanceof Error ? error : new Error(String(error)), {
        component: 'usePropertiesActions',
        action: 'delete_property',
        extra: {
          property: {
            propertyId,
          }
        },
      }, 'error');
      
      toast.error(error instanceof Error ? error.message : 'Failed to delete property. Please try again.');
    }
  };

  const handleAddProperty = () => {
    setCurrentProperty(null);
    setIsEditing(false);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setCurrentProperty(null);
    setIsEditing(false);
  };

  return {
    isModalOpen,
    currentProperty,
    isEditing,
    deletePropertyMutation,
    handleEditProperty,
    handleDeleteProperty,
    handleAddProperty,
    handleCloseModal,
  };
};