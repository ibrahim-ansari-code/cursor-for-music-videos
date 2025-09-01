/**
 * Type definitions for Apartment Complex properties
 * Matches backend PropertyApartmentComplex model exactly
 */

export type ComplexStyle = 
  | 'garden' 
  | 'highrise' 
  | 'midrise' 
  | 'townhome' 
  | 'luxury' 
  | 'student';

export type SecuritySystemType = 
  | 'cameras' 
  | 'key_fob' 
  | 'doorman' 
  | 'gated' 
  | 'combination';

export type TrashSystemType = 
  | 'chute' 
  | 'compactor' 
  | 'curbside' 
  | 'valet' 
  | 'dumpster';

export type SharedAmenity = 
  | 'gym' 
  | 'pool' 
  | 'parking_garage' 
  | 'clubhouse' 
  | 'laundry' 
  | 'playground' 
  | 'business_center' 
  | 'pet_area' 
  | 'bbq_area' 
  | 'tennis_court' 
  | 'basketball_court' 
  | 'storage';

export interface UnitMixDistribution {
  studio?: number;
  '1br'?: number;
  '2br'?: number;
  '3br'?: number;
  '4br'?: number;
  penthouse?: number;
}

export interface EmergencyContact {
  name: string;
  role: string;
  phone: string;
  available?: string;
}

/**
 * Complete apartment complex details interface
 * Matches backend model for full type safety
 */
export interface ApartmentComplexDetails {
  // ===== REQUIRED FIELDS =====
  complex_style: ComplexStyle;
  number_of_buildings: number;
  total_units: number;
  unit_mix: UnitMixDistribution;

  // ===== OPTIONAL BUT IMPORTANT FIELDS =====
  // Building Information
  floor_count?: number;
  floor_count_custom?: number | string; // Form input can be string initially
  elevator_count?: number;
  elevator_count_custom?: number | string; // Form input can be string initially
  parking_spaces_total?: number;

  // Management
  assigned_property_manager?: string;
  property_management_company?: string;
  on_site_management?: boolean;
  management_office_location?: string;
  management_contact_phone?: string;
  management_contact_email?: string;

  // Security & Systems
  has_security_system?: boolean;
  security_system_type?: SecuritySystemType;
  security_system_details?: string;
  trash_system_type?: TrashSystemType;
  trash_collection_schedule?: string;
  trash_system_details?: string;

  // Amenities
  shared_amenities?: SharedAmenity[];

  // Emergency Contacts
  emergency_contacts?: EmergencyContact[];

  // Policies
  pet_policy?: string;
  utilities_included?: string[];

  // Financial (for future use)
  average_rent_by_type?: Record<string, string>;
  vacancy_rate?: number;
}

/**
 * Form validation state interface
 */
export interface ApartmentComplexFormState {
  details: Partial<ApartmentComplexDetails>;
  errors: Record<string, string>;
  isValid: boolean;
  isDirty: boolean;
}

/**
 * Props for the ApartmentComplexForm component
 */
export interface ApartmentComplexFormProps {
  initialData?: Partial<ApartmentComplexDetails>;
  onValidationChange?: (isValid: boolean) => void;
  onDataChange?: (data: Partial<ApartmentComplexDetails>) => void;
  disabled?: boolean;
  showOptionalFields?: boolean;
}

/**
 * Type guards for runtime type checking
 */
export function isComplexStyle(value: string): value is ComplexStyle {
  return ['garden', 'highrise', 'midrise', 'townhome', 'luxury', 'student'].includes(value);
}

export function isSecuritySystemType(value: string): value is SecuritySystemType {
  return ['cameras', 'key_fob', 'doorman', 'gated', 'combination'].includes(value);
}

export function isTrashSystemType(value: string): value is TrashSystemType {
  return ['chute', 'compactor', 'curbside', 'valet', 'dumpster'].includes(value);
}

export function isSharedAmenity(value: string): value is SharedAmenity {
  return [
    'gym', 'pool', 'parking_garage', 'clubhouse', 'laundry', 'playground',
    'business_center', 'pet_area', 'bbq_area', 'tennis_court', 'basketball_court', 'storage'
  ].includes(value);
}
