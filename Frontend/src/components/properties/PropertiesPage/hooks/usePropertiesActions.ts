import { useState } from 'react';
import { toast } from 'react-toastify';
import { fetchPropertyById } from '../../../../utils/api';
import { useDeleteProperty } from '../../../../hooks/usePropertiesMutations';
import { Property } from '../../../../types/property';

export const usePropertiesActions = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentProperty, setCurrentProperty] = useState<Property | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const deletePropertyMutation = useDeleteProperty();

  const handleEditProperty = async (propertyId: number) => {
    try {
      const property = await fetchPropertyById(propertyId);
      setCurrentProperty(property);
      setIsEditing(true);
      setIsModalOpen(true);
    } catch (error) {
      console.error('Error fetching property details:', error);
      toast.error('Failed to load property details');
    }
  };

  const handleDeleteProperty = async (propertyId: number) => {
    try {
      await deletePropertyMutation.mutateAsync(propertyId);
      toast.success('Property was successfully deleted');
    } catch (error) {
      console.error('Error deleting property:', error);
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