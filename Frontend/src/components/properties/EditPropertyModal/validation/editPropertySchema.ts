import { z } from 'zod';
import { PropertyStatus } from '../../../../types/property';

// Province validation
export const validProvinces = [
  'AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT'
] as const;

// Permissive type-specific details schema to match NewPropertyModal forms
// This allows any fields to be set without strict validation during editing
// The backend will validate and store only the fields it recognizes
const typeSpecificDetailsSchema = z.record(z.string(), z.any()).optional();

// Main edit property schema - all fields optional for partial updates
export const editPropertySchema = z.object({
  // Basic information
  name: z.string().min(1, 'Property name cannot be empty').max(255).optional(),
  status: z.enum([
    PropertyStatus.ACTIVE,
    PropertyStatus.INACTIVE,
    PropertyStatus.DRAFT,
    PropertyStatus.ARCHIVED,
    PropertyStatus.RENTED,
    PropertyStatus.VACANT,
    PropertyStatus.PARTIALLY_RENTED,
  ]).optional(),
  year_built: z.number().int().min(1800).max(2100).nullable().optional(),
  description: z.string().max(2000).nullable().optional(),
  ownership_entity_id: z.string().nullable().optional(),

  // Location information
  address: z.string().min(1).max(500).optional(),
  city: z.string().min(1).max(100).optional(),
  province: z.enum(validProvinces).optional(),
  postal_code: z.string().min(3).max(20).optional(),

  // Google Maps data
  latitude: z.number().min(-90).max(90).nullable().optional(),
  longitude: z.number().min(-180).max(180).nullable().optional(),
  place_id: z.string().nullable().optional(),
  formatted_address: z.string().nullable().optional(),
  google_maps_data: z.record(z.string(), z.unknown()).nullable().optional(),

  // Type-specific details
  type_specific_details: typeSpecificDetailsSchema,
});

export type EditPropertyFormData = z.infer<typeof editPropertySchema>;
