// Ownership Entity Management API Functions
import { apiRequest } from './core';

/**
 * Entity type enum
 */
export type EntityType =
  | 'company'
  | 'individual'
  | 'trust'
  | 'partnership'
  | 'llc'
  | 'corporation'
  | 'other';

/**
 * Ownership entity interface
 */
export interface OwnershipEntity {
  id: string;
  user_id: string;
  entity_type: EntityType;
  name: string;
  legal_name?: string;
  tax_id?: string;
  contact_email?: string;
  contact_phone?: string;
  contact_name?: string;
  address?: string;
  city?: string;
  province?: string;
  postal_code?: string;
  country?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

/**
 * Ownership entity with statistics
 */
export interface OwnershipEntityWithStats extends OwnershipEntity {
  stats?: {
    units_owned: number;
    total_rent: number;
  };
}

/**
 * Create/Update ownership entity data
 */
export interface OwnershipEntityData {
  entity_type: EntityType;
  name: string;
  legal_name?: string;
  tax_id?: string;
  contact_email?: string;
  contact_phone?: string;
  contact_name?: string;
  address?: string;
  city?: string;
  province?: string;
  postal_code?: string;
  country?: string;
  notes?: string;
}

/**
 * Partial update data
 */
export type OwnershipEntityUpdateData = Partial<OwnershipEntityData>;

/**
 * Query parameters for fetching entities
 */
export interface FetchOwnershipEntitiesParams {
  page?: number;
  pageSize?: number;
  search?: string;
  entityType?: EntityType;
}

/**
 * Paginated response for ownership entities
 */
export interface OwnershipEntitiesResponse {
  entities: OwnershipEntity[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/**
 * Entity type option for dropdowns
 */
export interface EntityTypeOption {
  value: EntityType;
  label: string;
}

/**
 * Fetches all ownership entities for the current user
 */
export const fetchOwnershipEntities = async (
  params: FetchOwnershipEntitiesParams = {}
): Promise<OwnershipEntitiesResponse> => {
  const { page = 1, pageSize = 50, search, entityType } = params;

  const queryParams = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });

  if (search) {
    queryParams.append('search', search);
  }

  if (entityType) {
    queryParams.append('entity_type', entityType);
  }

  return apiRequest(`/ownership-entities?${queryParams.toString()}`);
};

/**
 * Fetches a single ownership entity by ID
 */
export const fetchOwnershipEntityById = async (
  entityId: string
): Promise<OwnershipEntity> => {
  if (!entityId) {
    throw new Error('Entity ID is required to fetch ownership entity details.');
  }
  return apiRequest(`/ownership-entities/${entityId}`);
};

/**
 * Fetches an ownership entity with statistics (units owned, total rent)
 */
export const fetchOwnershipEntityWithStats = async (
  entityId: string
): Promise<OwnershipEntityWithStats> => {
  if (!entityId) {
    throw new Error('Entity ID is required to fetch ownership entity stats.');
  }
  return apiRequest(`/ownership-entities/${entityId}/stats`);
};

/**
 * Creates a new ownership entity
 */
export const createOwnershipEntity = async (
  entityData: OwnershipEntityData
): Promise<OwnershipEntity> => {
  // Validate required fields
  if (!entityData.entity_type) {
    throw new Error('Entity type is required');
  }
  if (!entityData.name) {
    throw new Error('Entity name is required');
  }

  return apiRequest('/ownership-entities', {
    method: 'POST',
    body: JSON.stringify(entityData),
  });
};

/**
 * Updates an existing ownership entity
 */
export const updateOwnershipEntity = async (
  entityId: string,
  entityData: OwnershipEntityUpdateData
): Promise<OwnershipEntity> => {
  if (!entityId) {
    throw new Error('Entity ID is required to update ownership entity.');
  }

  return apiRequest(`/ownership-entities/${entityId}`, {
    method: 'PUT',
    body: JSON.stringify(entityData),
  });
};

/**
 * Deletes an ownership entity
 */
export const deleteOwnershipEntity = async (entityId: string): Promise<void> => {
  if (!entityId) {
    throw new Error('Entity ID is required to delete ownership entity.');
  }

  return apiRequest(`/ownership-entities/${entityId}`, {
    method: 'DELETE',
  });
};

/**
 * Entity type options for dropdowns
 */
export const ENTITY_TYPES: readonly EntityTypeOption[] = [
  { value: 'company', label: 'Company' },
  { value: 'individual', label: 'Individual' },
  { value: 'trust', label: 'Trust' },
  { value: 'partnership', label: 'Partnership' },
  { value: 'llc', label: 'LLC' },
  { value: 'corporation', label: 'Corporation' },
  { value: 'other', label: 'Other' },
] as const;
