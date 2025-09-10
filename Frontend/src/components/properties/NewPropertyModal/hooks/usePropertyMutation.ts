import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createProperty as createPropertyAPI, updateProperty as updatePropertyAPI } from '../../../../utils/api/properties';
import { PropertyCreatePayload, PropertyUpdatePayload } from '../../../../types/property';

export const usePropertyMutation = () => {
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data: PropertyCreatePayload) => createPropertyAPI(data),
    onSuccess: () => {
      // Invalidate and refetch properties
      queryClient.invalidateQueries({ queryKey: ['properties'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: PropertyUpdatePayload }) => 
      updatePropertyAPI(id, data),
    onSuccess: () => {
      // Invalidate and refetch properties
      queryClient.invalidateQueries({ queryKey: ['properties'] });
    },
  });

  return {
    createProperty: createMutation.mutateAsync,
    updateProperty: (id: number, data: PropertyUpdatePayload) => 
      updateMutation.mutateAsync({ id, data }),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
  };
};
