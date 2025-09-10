import { z } from 'zod';
import { PropertyType, PropertyStatus } from '../../../../types/property';

// Canadian postal code regex (e.g., M5V 3A8 or M5V3A8)
const CANADIAN_POSTAL_CODE = /^[A-Z]\d[A-Z][\s]?\d[A-Z]\d$/i;

// Province codes for Canada
const CANADIAN_PROVINCES = [
  'AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT'
] as const;

// Step 1: Location validation
export const locationSchema = z.object({
  address: z.string()
    .min(5, 'Address must be at least 5 characters')
    .max(255, 'Address must be less than 255 characters'),
  
  city: z.string()
    .min(2, 'City must be at least 2 characters')
    .max(100, 'City must be less than 100 characters'),
  
  province: z.union([
    z.enum(CANADIAN_PROVINCES),
    z.literal(''),
    z.undefined()
  ]),
  
  postal_code: z.string()
    .regex(CANADIAN_POSTAL_CODE, 'Please enter a valid Canadian postal code (e.g., M5V 3A8)')
    .transform(val => val.toUpperCase().replace(/\s/g, '')), // Normalize format
  
  latitude: z.number()
    .min(-90, 'Latitude must be between -90 and 90')
    .max(90, 'Latitude must be between -90 and 90')
    .nullable()
    .optional(),
  
  longitude: z.number()
    .min(-180, 'Longitude must be between -180 and 180')
    .max(180, 'Longitude must be between -180 and 180')
    .nullable()
    .optional(),
  
  place_id: z.string().nullable().optional(),
  formatted_address: z.string().nullable().optional(),
  google_maps_data: z.any().nullable().optional(),
});

// Step 2: Property Details validation
export const detailsSchema = z.object({
  name: z.string()
    .min(3, 'Property name must be at least 3 characters')
    .max(100, 'Property name must be less than 100 characters'),
  
  property_type: z.nativeEnum(PropertyType),
  
  status: z.nativeEnum(PropertyStatus),
  
  year_built: z.union([z.string(), z.number(), z.undefined(), z.null()])
    .optional()
    .nullable()
    .transform(val => {
      // Handle empty values
      if (val === null || val === undefined || val === '') return null;
      
      // Convert to number if it's a string
      const numVal = typeof val === 'string' ? Number(val) : (val as number);
      
      // Return null if not a valid number
      if (isNaN(numVal)) return null;
      
      return numVal;
    })
    .refine((val) => val === null || (val >= 1800 && val <= new Date().getFullYear()), { 
      message: `Year must be between 1800 and ${new Date().getFullYear()}` 
    })
    .refine((val) => val === null || (val >= 1000 && val <= 9999), { 
      message: 'Must be a 4-digit year' 
    }),
  
  description: z.string()
    .max(1000, 'Description must be less than 1000 characters')
    .nullable()
    .optional(),
  
  // Apartment complex specific fields
  num_floors: z.string().optional(),
  units_per_floor: z.string().optional(),
  auto_generate_units: z.boolean().optional(),
  manual_units: z.string().optional(),
  
  // Type specific details
  type_specific_details: z.record(z.string(), z.any()).optional(),
}).superRefine((data, ctx) => {
    // Validation for apartment complex fields
    if (data.property_type === PropertyType.APARTMENT_COMPLEX) {
      const details = data.type_specific_details || {};
      
      // Check required fields for apartment complex
      const numBuildings = Number(details.number_of_buildings);
      const numUnits = Number(details.total_units);
      
      // Complex style is required
      if (!details.complex_style) {
        ctx.addIssue({
          code: "custom",
          message: 'Complex style is required',
          path: ['type_specific_details', 'complex_style']
        });
      } else {
        const validStyles = ['garden', 'highrise', 'midrise', 'townhome', 'luxury', 'student'];
        if (!validStyles.includes(details.complex_style)) {
          ctx.addIssue({
            code: "custom",
            message: `Complex style must be one of: ${validStyles.join(', ')}`,
            path: ['type_specific_details', 'complex_style']
          });
        }
      }
      
      if (!details.number_of_buildings || isNaN(numBuildings) || numBuildings <= 0) {
        ctx.addIssue({
          code: "custom",
          message: 'Number of buildings is required',
          path: ['type_specific_details', 'number_of_buildings']
        });
      } else if (numBuildings > 100) {
        ctx.addIssue({
          code: "custom",
          message: 'Maximum 100 buildings allowed',
          path: ['type_specific_details', 'number_of_buildings']
        });
      }
      
      if (!details.total_units || isNaN(numUnits) || numUnits <= 0) {
        ctx.addIssue({
          code: "custom",
          message: 'Total units is required',
          path: ['type_specific_details', 'total_units']
        });
      } else if (numUnits > 10000) {
        ctx.addIssue({
          code: "custom",
          message: 'Maximum 10,000 units allowed',
          path: ['type_specific_details', 'total_units']
        });
      }
      
      // Check unit mix validation is now required - only validate if we have total units
      if (numUnits > 0) {
        const unitMix: Record<string, number | string> = details.unit_mix || {};
        const unitMixSum: number = Object.values(unitMix).reduce((sum: number, count: number | string): number => {
          const num = Number(count);
          return sum + (isNaN(num) ? 0 : num);
        }, 0);
        
        if (unitMixSum === 0) {
          ctx.addIssue({
            code: "custom",
            message: 'Please distribute units across bedroom types',
            path: ['type_specific_details', 'unit_mix']
          });
        } else if (unitMixSum > 0 && unitMixSum !== numUnits) {
          ctx.addIssue({
            code: "custom",
            message: `Unit distribution (${unitMixSum}) must equal total units (${numUnits})`,
            path: ['type_specific_details', 'unit_mix']
          });
        }
      }
      
      // Skip old unit generation validation if using new unit mix system
      const hasUnitMix = details.unit_mix && Object.values(details.unit_mix).some(count => Number(count) > 0);
      
      // Only validate old unit generation system if NOT using new unit mix system
      if (!hasUnitMix) {
        // Old validation for auto-generate units (if still needed for backwards compatibility)
        if (data.auto_generate_units) {
          // If auto-generating, need floors and units per floor
          const floors = parseInt(data.num_floors || '');
          const unitsPerFloor = parseInt(data.units_per_floor || '');
          
          if (!floors || floors < 1 || floors > 100) {
            ctx.addIssue({
              code: "custom",
              message: 'Please provide valid number of floors (1-100)',
              path: ['num_floors']
            });
          }
          if (!unitsPerFloor || unitsPerFloor < 1 || unitsPerFloor > 50) {
            ctx.addIssue({
              code: "custom",
              message: 'Please provide valid units per floor (1-50)',
              path: ['units_per_floor']
            });
          }
        } else if (data.auto_generate_units === false) {
          // If manual entry, need at least one unit with better validation
          if (!data.manual_units || !data.manual_units.trim()) {
            ctx.addIssue({
              code: "custom",
              message: 'Please provide at least one unit',
              path: ['manual_units']
            });
          } else {
            const unitNames = data.manual_units.split(',').map(u => u.trim()).filter(Boolean);
            if (unitNames.length < 1) {
              ctx.addIssue({
                code: "custom",
                message: 'Please provide at least one valid unit name',
                path: ['manual_units']
              });
            }
            
            // Check for duplicate unit names
            const duplicates = unitNames.filter((name, index) => unitNames.indexOf(name) !== index);
            if (duplicates.length > 0) {
              ctx.addIssue({
                code: "custom",
                message: `Duplicate unit names found: ${duplicates.join(', ')}`,
                path: ['manual_units']
              });
            }
            
            // Validate unit name length and characters
            const invalidUnits = unitNames.filter(name => name.length > 50 || !/^[a-zA-Z0-9\s\-#\.]+$/.test(name));
            if (invalidUnits.length > 0) {
              ctx.addIssue({
                code: "custom",
                message: 'Unit names must be under 50 characters and contain only letters, numbers, spaces, hyphens, #, and dots',
                path: ['manual_units']
              });
            }
          }
        }
      }
    }
    
    // Validation for residential properties
    if (data.property_type === PropertyType.RESIDENTIAL) {
      const details = data.type_specific_details || {};
      const bedrooms = Number(details.bedrooms);
      const bathrooms = Number(details.bathrooms);
      
      // Check required fields for residential
      if (!details.bedrooms || isNaN(bedrooms) || bedrooms <= 0) {
        ctx.addIssue({
          code: "custom",
          message: 'Bedrooms is required',
          path: ['type_specific_details', 'bedrooms']
        });
      }
      if (!details.bathrooms || isNaN(bathrooms) || bathrooms <= 0) {
        ctx.addIssue({
          code: "custom",
          message: 'Bathrooms is required',
          path: ['type_specific_details', 'bathrooms']
        });
      }
    }
    
    // Validation for commercial properties
    if (data.property_type === PropertyType.COMMERCIAL) {
      const details = data.type_specific_details || {};
      const usableSqft = Number(details.usable_square_feet);
      const rentableSqft = Number(details.rentable_square_feet);
      
      // Check required fields for commercial
      if (!details.space_type) {
        ctx.addIssue({
          code: "custom",
          message: 'Space type is required',
          path: ['type_specific_details', 'space_type']
        });
      }
      if (!details.usable_square_feet || isNaN(usableSqft) || usableSqft <= 0) {
        ctx.addIssue({
          code: "custom",
          message: 'Usable square feet is required',
          path: ['type_specific_details', 'usable_square_feet']
        });
      }
      if (!details.rentable_square_feet || isNaN(rentableSqft) || rentableSqft <= 0) {
        ctx.addIssue({
          code: "custom",
          message: 'Rentable square feet is required',
          path: ['type_specific_details', 'rentable_square_feet']
        });
      }
      if (!details.lease_type) {
        ctx.addIssue({
          code: "custom",
          message: 'Lease type is required',
          path: ['type_specific_details', 'lease_type']
        });
      }
      // Soft client-side guard: RSF should be >= USF
      if (!isNaN(usableSqft) && !isNaN(rentableSqft) && usableSqft > 0 && rentableSqft > 0 && rentableSqft < usableSqft) {
        ctx.addIssue({
          code: "custom",
          message: 'Rentable SF should be greater than or equal to Usable SF',
          path: ['type_specific_details', 'rentable_square_feet']
        });
      }
    }
    
    // Validation for industrial properties
    if (data.property_type === PropertyType.INDUSTRIAL) {
      const details = data.type_specific_details || {};
      const totalSqft = Number(details.total_square_feet);
      const warehouseSqft = Number(details.warehouse_square_feet) || 0;
      const officeSqft = Number(details.office_square_feet) || 0;
      const manufacturingSqft = Number(details.manufacturing_square_feet) || 0;
      
      // Check required fields for industrial
      if (!details.industrial_type) {
        ctx.addIssue({
          code: "custom",
          message: 'Please select a facility type',
          path: ['type_specific_details', 'industrial_type']
        });
      }
      if (!details.total_square_feet || isNaN(totalSqft) || totalSqft <= 0) {
        ctx.addIssue({
          code: "custom",
          message: 'Total square feet is required',
          path: ['type_specific_details', 'total_square_feet']
        });
      }
      // Validate space distribution equals total
      const distributedSqft = warehouseSqft + officeSqft + manufacturingSqft;
      if (totalSqft > 0 && distributedSqft !== totalSqft) {
        ctx.addIssue({
          code: "custom",
          message: `Space distribution (${distributedSqft.toLocaleString()} SF) must equal total square feet (${totalSqft.toLocaleString()} SF)`,
          path: ['type_specific_details', 'space_distribution']
        });
      }
    }
    
    // Validation for mixed-use properties
    if (data.property_type === PropertyType.MIXED_USE) {
      const details = data.type_specific_details || {};
      const residentialSF = Number(details.residential_square_feet) || 0;
      const commercialSF = Number(details.commercial_square_feet) || 0;
      
      // Check required fields for mixed-use (match actual form fields)
      if (!details.residential_square_feet || residentialSF <= 0) {
        ctx.addIssue({
          code: "custom",
          message: 'Residential square feet is required for mixed-use properties',
          path: ['type_specific_details', 'residential_square_feet']
        });
      }
      if (!details.commercial_square_feet || commercialSF <= 0) {
        ctx.addIssue({
          code: "custom",
          message: 'Commercial square feet is required for mixed-use properties',
          path: ['type_specific_details', 'commercial_square_feet']
        });
      }
    }
  });

// Step 3: Media validation
export const mediaSchema = z.object({
  images_to_upload: z.array(z.instanceof(File))
    .optional()
    .refine(
      (files) => {
        if (!files) return true;
        // Check file sizes (max 10MB each)
        return files.every(file => file.size <= 10 * 1024 * 1024);
      },
      { message: 'Each image must be less than 10MB' }
    )
    .refine(
      (files) => {
        if (!files) return true;
        // Check file types
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
        return files.every(file => validTypes.includes(file.type));
      },
      { message: 'Only JPG, PNG, GIF, and WebP images are allowed' }
    ),
});

// Units schema - for unit step data
export const unitsSchema = z.object({
  // Generated units from the new UnitsStep
  generated_units: z.array(z.object({
    name: z.string(),
    description: z.string().optional(),
    size: z.number().optional(),
    monthly_rent: z.number().optional(),
    bedrooms: z.number().optional(),
    bathrooms: z.number().optional(),
    floor: z.number().optional(),
    unit_type: z.string().optional(),
  })).optional(),
  
  // Legacy fields for apartment complex generation
  auto_generate_units: z.boolean().optional(),
  num_floors: z.string().optional(),
  units_per_floor: z.string().optional(),
  manual_units: z.string().optional(),
});

// Type-specific details schema - flexible to accommodate different property types
const typeSpecificSchema = z.object({
  type_specific_details: z.record(z.string(), z.any()).optional(),
});

// Combined schema for the entire form
export const propertyFormSchema = locationSchema
  .merge(detailsSchema)
  .merge(mediaSchema)
  .merge(unitsSchema)
  .merge(typeSpecificSchema);

// Type inference from schema
export type PropertyFormSchemaType = z.infer<typeof propertyFormSchema>;

// Basic details schema (for Basic Info tab)
export const basicDetailsSchema = z.object({
  name: z.string()
    .min(3, 'Property name must be at least 3 characters')
    .max(100, 'Property name must be less than 100 characters'),
  
  property_type: z.nativeEnum(PropertyType),
  
  status: z.nativeEnum(PropertyStatus),
  
  year_built: z.union([z.string(), z.number(), z.undefined(), z.null()])
    .optional()
    .nullable()
    .transform(val => {
      // Handle empty values
      if (val === null || val === undefined || val === '') return null;
      
      // Convert to number if it's a string
      const numVal = typeof val === 'string' ? Number(val) : (val as number);
      
      // Return null if not a valid number
      if (isNaN(numVal)) return null;
      
      return numVal;
    })
    .refine((val) => val === null || (val >= 1800 && val <= new Date().getFullYear()), { 
      message: `Year must be between 1800 and ${new Date().getFullYear()}` 
    })
    .refine((val) => val === null || (val >= 1000 && val <= 9999), { 
      message: 'Must be a 4-digit year' 
    }),
  
  description: z.string()
    .max(1000, 'Description must be less than 1000 characters')
    .nullable()
    .optional(),
});

// Validation functions for individual steps
export const validateLocationStep = (data: unknown) => {
  return locationSchema.safeParse(data);
};

export const validateDetailsStep = (data: unknown, tabName?: 'basic' | 'specific') => {
  // If validating basic tab only
  if (tabName === 'basic') {
    return basicDetailsSchema.safeParse(data);
  }
  
  // If validating specific tab, just check type-specific required fields
  if (tabName === 'specific') {
    const propertyType = (data as any).property_type;
    const details = (data as any).type_specific_details || {};
    
    // Create a custom validation for property-specific required fields
    const errors: Array<{ path: string[]; message: string }> = [];
    
    if (propertyType === PropertyType.APARTMENT_COMPLEX) {
      const numBuildings = Number(details.number_of_buildings);
      const numUnits = Number(details.total_units);
      
      if (!details.complex_style) {
        errors.push({ path: ['type_specific_details', 'complex_style'], message: 'Complex style is required' });
      }
      
      if (!details.number_of_buildings || isNaN(numBuildings) || numBuildings <= 0) {
        errors.push({ path: ['type_specific_details', 'number_of_buildings'], message: 'Number of buildings is required' });
      } else if (numBuildings > 100) {
        errors.push({ path: ['type_specific_details', 'number_of_buildings'], message: 'Maximum 100 buildings allowed' });
      }
      
      if (!details.total_units || isNaN(numUnits) || numUnits <= 0) {
        errors.push({ path: ['type_specific_details', 'total_units'], message: 'Total units is required' });
      } else if (numUnits > 10000) {
        errors.push({ path: ['type_specific_details', 'total_units'], message: 'Maximum 10,000 units allowed' });
      }
      
      // Check unit mix validation - only validate if we have total units
      if (numUnits > 0) {
        const unitMix: Record<string, number | string> = details.unit_mix || {};
        const unitMixSum: number = Object.values(unitMix).reduce((sum: number, count: number | string): number => {
          const num = Number(count);
          return sum + (isNaN(num) ? 0 : num);
        }, 0);
        
        // Unit mix is required and must match total units
        if (unitMixSum === 0) {
          errors.push({ 
            path: ['type_specific_details', 'unit_mix'], 
            message: 'Please distribute units across bedroom types' 
          });
        } else if (unitMixSum > 0 && unitMixSum !== numUnits) {
          errors.push({ 
            path: ['type_specific_details', 'unit_mix'], 
            message: `Unit distribution (${unitMixSum}) must equal total units (${numUnits})` 
          });
        }
      }
    }
    
    if (propertyType === PropertyType.RESIDENTIAL) {
      const bedrooms = Number(details.bedrooms);
      const bathrooms = Number(details.bathrooms);
      
      if (!details.bedrooms || isNaN(bedrooms) || bedrooms <= 0) {
        errors.push({ path: ['type_specific_details', 'bedrooms'], message: 'Bedrooms is required' });
      }
      if (!details.bathrooms || isNaN(bathrooms) || bathrooms <= 0) {
        errors.push({ path: ['type_specific_details', 'bathrooms'], message: 'Bathrooms is required' });
      }
    }
    
    if (propertyType === PropertyType.COMMERCIAL) {
      const usableSqft = Number(details.usable_square_feet);
      const rentableSqft = Number(details.rentable_square_feet);
      
      if (!details.space_type) {
        errors.push({ path: ['type_specific_details', 'space_type'], message: 'Space type is required' });
      }
      if (!details.usable_square_feet || isNaN(usableSqft) || usableSqft <= 0) {
        errors.push({ path: ['type_specific_details', 'usable_square_feet'], message: 'Usable square feet is required' });
      }
      if (!details.rentable_square_feet || isNaN(rentableSqft) || rentableSqft <= 0) {
        errors.push({ path: ['type_specific_details', 'rentable_square_feet'], message: 'Rentable square feet is required' });
      }
      if (!details.lease_type) {
        errors.push({ path: ['type_specific_details', 'lease_type'], message: 'Lease type is required' });
      }
      if (!isNaN(usableSqft) && !isNaN(rentableSqft) && usableSqft > 0 && rentableSqft > 0 && rentableSqft < usableSqft) {
        errors.push({ path: ['type_specific_details', 'rentable_square_feet'], message: 'Rentable SF should be ≥ Usable SF' });
      }
    }
    
    if (propertyType === PropertyType.INDUSTRIAL) {
      const totalSqft = Number(details.total_square_feet);
      const warehouseSqft = Number(details.warehouse_square_feet) || 0;
      const officeSqft = Number(details.office_square_feet) || 0;
      const manufacturingSqft = Number(details.manufacturing_square_feet) || 0;
      
      if (!details.industrial_type) {
        errors.push({ path: ['type_specific_details', 'industrial_type'], message: 'Please select a facility type' });
      }
      if (!details.total_square_feet || isNaN(totalSqft) || totalSqft <= 0) {
        errors.push({ path: ['type_specific_details', 'total_square_feet'], message: 'Total square feet is required' });
      }
      // Validate space distribution equals total
      const distributedSqft = warehouseSqft + officeSqft + manufacturingSqft;
      if (totalSqft > 0 && distributedSqft !== totalSqft) {
        errors.push({ 
          path: ['type_specific_details', 'space_distribution'], 
          message: `Space distribution (${distributedSqft.toLocaleString()} SF) must equal total square feet (${totalSqft.toLocaleString()} SF)` 
        });
      }
    }
    
    // Return validation result
    if (errors.length > 0) {
      return {
        success: false,
        error: {
          issues: errors.map(err => ({
            ...err,
            code: 'custom',
            message: err.message
          }))
        }
      };
    }
    
    return { success: true, data };
  }
  
  // Full validation for both tabs
  return detailsSchema.safeParse(data);
};

export const validateMediaStep = (data: unknown) => {
  return mediaSchema.safeParse(data);
};

// Full form validation
export const validatePropertyForm = (data: unknown) => {
  return propertyFormSchema.safeParse(data);
};

// Helper to get field-specific error messages
export const getFieldError = (
  errors: z.ZodError | undefined,
  field: string
): string | undefined => {
  if (!errors) return undefined;
  
  const fieldError = errors.issues.find((err) => 
    err.path.map(String).join('.') === field || String(err.path[0]) === field
  );
  
  return fieldError?.message;
};

// Helper to get all errors for a step
export const getStepErrors = (result: ReturnType<typeof propertyFormSchema.safeParse>) => {
  if (result.success) return {};
  
  const errors: Record<string, string> = {};
  result.error.issues.forEach((err) => {
    const field = err.path.map(String).join('.');
    if (!errors[field]) {
      errors[field] = err.message;
    }
  });
  
  return errors;
};