// Type-specific property detail interfaces matching backend schemas

// ===== Base Types =====
export interface ContactInfo {
  name?: string;
  phone?: string;
  email?: string;
  role?: string;
}

export interface ParkingConfiguration {
  surface_spots?: number;
  covered_spots?: number;
  garage_spots?: number;
  handicap_spots?: number;
  visitor_spots?: number;
  electric_charging_stations?: number;
}

// ===== Apartment Complex =====
export interface ApartmentComplexDetails {
  // Required fields
  number_of_buildings: number;
  total_units: number;
  unit_mix?: Record<string, number>; // e.g., { "studio": 10, "1br": 20, "2br": 15 }
  
  // Management
  assigned_property_manager?: string;
  property_management_company?: string;
  on_site_management?: boolean;
  management_office_location?: string;
  management_office_hours?: Record<string, string>;
  management_contact_phone?: string;
  management_contact_email?: string;
  
  // Building Information
  building_codes_names?: Record<string, string>;
  year_renovated?: number;
  construction_type?: 'wood_frame' | 'steel_frame' | 'concrete' | 'masonry';
  
  // Amenities
  shared_amenities?: string[];
  amenity_fees?: Record<string, number>;
  
  // Security
  has_security_system?: boolean;
  security_system_type?: 'cameras' | 'key_fob' | 'doorman' | 'gate' | 'combination';
  security_system_details?: string;
  controlled_access_entries?: string[];
  
  // Infrastructure
  floor_count?: number;
  floor_count_custom?: number;
  elevator_count?: number;
  laundry_type?: 'in_unit' | 'shared_floor' | 'shared_building' | 'none';
  heating_type?: 'central' | 'baseboard' | 'radiator' | 'forced_air';
  cooling_type?: 'central_air' | 'window_units' | 'split_system' | 'none';
  
  // Waste Management
  trash_system_type?: 'chute' | 'compactor' | 'dumpster' | 'curbside' | 'valet';
  trash_collection_schedule?: string;
  trash_system_details?: string;
  recycling_program?: boolean;
  
  // Parking
  parking_spaces_total?: number;
  guest_parking_spaces?: number;
  parking_configuration?: ParkingConfiguration;
  
  // Financial Metrics
  average_rent_by_type?: Record<string, number>;
  vacancy_rate?: number;
  
  // Lease Management
  lease_expiry_distribution?: Record<string, number>;
  renewal_rate?: number;
  
  // Policies
  pet_policy?: string;
  pet_deposit?: number;
  pet_rent_monthly?: number;
  smoking_policy?: 'no_smoking' | 'designated_areas' | 'allowed';
  utilities_included?: string[];
  
  // Emergency & Compliance
  emergency_contacts?: ContactInfo[];
  last_inspection_date?: string;
  inspection_status?: 'passed' | 'failed' | 'pending' | 'scheduled';
  compliance_certificates?: string[];
}

// ===== Residential =====
export interface ResidentialDetails {
  // Required fields
  bedrooms: number;
  bathrooms: number;
  
  // Property Dimensions
  square_feet?: number;
  lot_size?: number;
  lot_dimensions?: string;
  stories?: number;
  
  // Property Type Details
  property_subtype?: 'single_family' | 'townhouse' | 'condo' | 'duplex' | 'manufactured';
  architectural_style?: string;
  construction_material?: string;
  foundation_type?: 'slab' | 'crawl_space' | 'basement' | 'pier';
  roof_type?: 'shingle' | 'tile' | 'metal' | 'flat';
  roof_age_years?: number;
  
  // Rooms & Layout
  master_bedroom_location?: 'main_floor' | 'upper_floor' | 'basement';
  kitchen_features?: string[];
  living_rooms?: number;
  dining_rooms?: number;
  family_rooms?: number;
  office_rooms?: number;
  
  // Garage & Parking
  garage_spaces?: number;
  garage_type?: 'attached' | 'detached' | 'carport' | 'none';
  driveway_type?: 'concrete' | 'asphalt' | 'gravel' | 'paved';
  additional_parking_spaces?: number;
  
  // Basement & Attic
  has_basement?: boolean;
  basement_finished?: boolean;
  basement_square_feet?: number;
  has_attic?: boolean;
  attic_finished?: boolean;
  
  // Outdoor Features
  has_pool?: boolean;
  pool_type?: 'in_ground' | 'above_ground';
  pool_heated?: boolean;
  has_hot_tub?: boolean;
  deck_patio_sqft?: number;
  has_fence?: boolean;
  fence_type?: 'wood' | 'chain_link' | 'vinyl' | 'iron';
  
  // Systems & Utilities
  heating_system?: 'forced_air' | 'radiant' | 'heat_pump' | 'baseboard';
  cooling_system?: 'central_air' | 'window_units' | 'evaporative' | 'none';
  water_heater_type?: 'gas' | 'electric' | 'tankless' | 'solar';
  electrical_panel_amps?: number;
  solar_panels?: boolean;
  septic_or_sewer?: 'septic' | 'sewer';
  well_or_city_water?: 'well' | 'city';
  
  // HOA Information
  has_hoa?: boolean;
  hoa_fee_monthly?: number;
  hoa_amenities?: string[];
  hoa_restrictions?: string;
  
  // Financial
  property_tax_annual?: number;
  insurance_annual?: number;
  last_sale_price?: number;
  last_sale_date?: string;
}

// ===== Commercial =====
export interface CommercialDetails {
  // Required fields (matching form validation)
  space_type: 'retail' | 'office' | 'medical' | 'restaurant' | 'hotel_motel' | 'multi_tenant';
  usable_square_feet: number;
  rentable_square_feet: number;
  lease_type: 'gross' | 'triple_net' | 'modified_gross';
  
  // Space Configuration
  // CAF is computed server-side from (RSF - USF) / USF * 100
  // It's a generated column in the database, not sent by client
  common_area_factor?: number; // read-only, computed value from API
  ceiling_height?: number;
  floor_count?: number;
  floor_count_custom?: number;
  
  // Building Details
  number_of_units?: number;
  floor_plate_size?: number;
  building_class?: 'A' | 'A+' | 'B' | 'B+' | 'C' | 'C+';
  year_renovated?: number;
  
  // Loading & Logistics
  has_loading_area?: boolean;
  loading_docks_count?: number;
  loading_area_details?: string;
  drive_in_doors?: number;
  
  // Signage
  signage_rights?: boolean;
  signage_restrictions?: string;
  monument_signage?: boolean;
  pylon_signage?: boolean;
  building_signage?: boolean;
  
  // Zoning & Compliance
  zoning_code?: string;
  zoning_type?: string;
  permitted_uses?: string[];
  max_floor_area_ratio?: number;
  
  // Infrastructure & Features
  on_site_maintenance?: boolean;
  fiber_ready?: boolean;
  fiber_optic_ready?: boolean;
  backup_power?: boolean;
  backup_generator?: boolean;
  security_system?: boolean;
  sprinkler_system?: boolean;
  hvac_type?: string;
  electrical_capacity?: string;
  
  // Parking & Access
  parking_ratio?: number;
  parking_spaces?: number;
  
  // Amenities
  has_conference_rooms?: boolean;
  has_kitchen_facilities?: boolean;
  has_fitness_center?: boolean;
  has_cafeteria?: boolean;
  
  // Financial
  average_rent_per_sqft?: number;
  operating_expenses_per_sqft?: number;
  real_estate_taxes?: number;
  cam_charges?: number;
}

// ===== Industrial =====
export interface IndustrialDetails {
  // Required fields
  total_sqft: number;
  
  // Space Breakdown
  warehouse_sqft?: number;
  office_sqft?: number;
  manufacturing_sqft?: number;
  yard_size_sqft?: number;
  
  // Building Specifications
  ceiling_height?: number;
  clear_height?: number;
  column_spacing?: string;
  floor_thickness?: number;
  floor_load_capacity?: number;
  
  // Loading & Access
  loading_docks?: number;
  drive_in_doors?: number;
  dock_high_doors?: number;
  grade_level_doors?: number;
  rail_access?: boolean;
  rail_spur_length?: number;
  
  // Power & Utilities
  power_capacity?: number;
  power_voltage?: string;
  has_compressed_air?: boolean;
  has_steam?: boolean;
  water_capacity?: number;
  sewer_capacity?: number;
  
  // Special Features
  crane_capacity?: number;
  has_freezer?: boolean;
  freezer_size_sqft?: number;
  has_cooler?: boolean;
  cooler_size_sqft?: number;
  
  // Environmental
  environmental_phase?: 'Phase I' | 'Phase II' | 'Phase III';
  has_storm_water_permit?: boolean;
  has_air_permit?: boolean;
  
  // Yard & Exterior
  truck_court_depth?: number;
  trailer_parking_spots?: number;
  fenced_yard?: boolean;
  security_features?: string[];
  
  // Zoning
  zoning_type?: string;
  permitted_uses?: string[];
  fire_suppression_type?: string;
}

// ===== Mixed Use =====
export interface MixedUseDetails {
  // Space Allocation
  residential_units?: number;
  commercial_units?: number;
  residential_sqft?: number;
  commercial_sqft?: number;
  retail_sqft?: number;
  office_sqft?: number;
  total_sqft?: number;
  
  // Residential Component
  residential_unit_mix?: Record<string, number>;
  average_residential_rent?: number;
  residential_occupancy?: number;
  residential_amenities?: string[];
  
  // Commercial Component
  retail_tenants?: string[];
  anchor_tenant?: string;
  commercial_occupancy?: number;
  average_commercial_rent_per_sqft?: number;
  
  // Shared Features
  parking_spaces?: number;
  residential_parking?: number;
  commercial_parking?: number;
  visitor_parking?: number;
  
  // Building Details
  total_floors?: number;
  residential_floors?: string;
  commercial_floors?: string;
  has_doorman?: boolean;
  has_concierge?: boolean;
  separate_entrances?: boolean;
  
  // Amenities
  shared_amenities?: string[];
  residential_only_amenities?: string[];
  commercial_only_amenities?: string[];
  
  // Operations
  property_management_company?: string;
  separate_utilities?: boolean;
  common_area_maintenance?: number;
  
  // Zoning & Compliance
  zoning_classification?: string;
  mixed_use_ratio?: string;
  ground_floor_retail?: boolean;
}

// Union type for all property type details
export type PropertyTypeDetails = 
  | ApartmentComplexDetails
  | ResidentialDetails
  | CommercialDetails
  | IndustrialDetails
  | MixedUseDetails;