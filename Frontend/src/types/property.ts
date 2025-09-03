// Property type definitions
export enum PropertyType {
  RESIDENTIAL = 'Residential',
  COMMERCIAL = 'Commercial',
  INDUSTRIAL = 'Industrial',
  LAND = 'Land',
  SPECIAL_PURPOSE = 'Special Purpose',
  MIXED_USE = 'Mixed-Use',
  APARTMENT_COMPLEX = 'Apartment Complex',
  OTHER = 'Other'
}

export enum PropertyStatus {
  ACTIVE = 'ACTIVE',
  INACTIVE = 'INACTIVE',
  DRAFT = 'DRAFT',
  ARCHIVED = 'ARCHIVED',
  RENTED = 'RENTED',
  VACANT = 'VACANT',
  PARTIALLY_RENTED = 'PARTIALLY_RENTED'
}

export interface PropertyImage {
  id?: number;
  property_id?: number;
  image_url: string;
  image_type?: 'photo' | 'floorplan' | 'document';
  is_primary?: boolean;
  caption?: string;
  display_order?: number;
  created_at?: string;
  updated_at?: string;
}

export interface PropertyUnit {
  id?: number;
  name: string;
  floor?: number;
  description?: string;
  size?: number;
  monthly_rent?: number;
  is_rented?: boolean;
  bedrooms?: number;
  bathrooms?: number;
}

export interface Property {
  id?: number;
  name: string;
  address: string;
  city: string;
  province: string;
  postal_code: string;
  property_type: PropertyType;
  year_built?: number | null;
  description?: string | null;
  status: PropertyStatus;
  
  // Google Maps fields
  latitude?: number | null;
  longitude?: number | null;
  place_id?: string | null;
  formatted_address?: string | null;
  google_maps_data?: GoogleMapsData | null;
  
  // Relations
  units?: PropertyUnit[];
  images?: PropertyImage[];
  user_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface GoogleMapsData {
  address_components?: google.maps.GeocoderAddressComponent[];
  viewport?: {
    northeast: { lat: number; lng: number };
    southwest: { lat: number; lng: number };
  };
  place_types?: string[];
  plus_code?: string;
  timezone?: string;
  nearby_amenities?: {
    schools?: PlaceResult[];
    transit?: PlaceResult[];
    shopping?: PlaceResult[];
    parks?: PlaceResult[];
  };
}

export interface PlaceResult {
  name: string;
  place_id: string;
  distance?: number;
  rating?: number;
  types?: string[];
}

export interface GeneratedUnit {
  name: string;
  description?: string;
  size?: number;
  monthly_rent?: number;
  bedrooms?: number;
  bathrooms?: number;
  floor?: number;
  unit_type?: string;
  building_id?: string;
}

export interface UploadedImageInfo {
  id: number;
  propertyId: number;
  imageUrl: string;
  isPrimary: boolean;
  displayOrder: number;
  status: 'completed';
}

export interface PropertyFormData extends Omit<Property, 'id' | 'created_at' | 'updated_at' | 'user_id'> {
  // Form-specific fields
  num_floors?: string;
  units_per_floor?: string;
  auto_generate_units?: boolean;
  manual_units?: string;
  
  // Image handling fields
  images_to_upload?: File[]; // For new properties - files to upload after creation
  uploaded_images?: UploadedImageInfo[]; // For existing properties - already uploaded images
  post_creation_image_upload?: (propertyId: number) => Promise<void>; // Upload function for post-creation
  
  // Unit generation fields
  generated_units?: GeneratedUnit[];
  num_bays?: string;
  spaces_per_floor?: string;
  default_space_type?: string;
  industrial_unit_type?: string;
  include_loading_docks?: boolean;
  unit_generation_pattern?: string;
  
  // Type-specific details (will be sent to backend)
  type_specific_details?: any; // Will be typed based on property_type in form
}

export interface PropertyCreatePayload {
  name: string;
  address: string;
  city: string;
  province: string;
  postal_code: string;
  property_type: PropertyType;
  status?: PropertyStatus;
  year_built?: number;
  description?: string;
  
  // Google Maps fields
  latitude?: number;
  longitude?: number;
  place_id?: string;
  formatted_address?: string;
  google_maps_data?: GoogleMapsData;
  
  // For apartment complexes
  units?: string[];
  
  // Type-specific details
  type_specific_details?: any;
}

export interface PropertyUpdatePayload {
  name?: string;
  address?: string;
  city?: string;
  province?: string;
  postal_code?: string;
  status?: PropertyStatus;
  year_built?: number;
  description?: string;
  
  // Google Maps fields
  latitude?: number;
  longitude?: number;
  place_id?: string;
  formatted_address?: string;
  google_maps_data?: GoogleMapsData;
}