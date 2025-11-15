import { UseMutationResult } from '@tanstack/react-query';
import { Property } from '../types/property';

export function useCreateProperty(): UseMutationResult<Property, Error, any>;

export function useUpdateProperty(): UseMutationResult<
  Property,
  Error,
  { propertyId: number; propertyData: any }
>;

export function useDeleteProperty(): UseMutationResult<void, Error, number>;

export function useBulkDeleteProperties(): UseMutationResult<void, Error, number[]>;