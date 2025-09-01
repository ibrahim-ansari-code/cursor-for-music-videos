-- Property Type Split Migration
-- Implements table inheritance pattern for property types
-- Base properties table remains the single source of truth

-- First, add property_details JSONB column for flexible data storage
ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS property_details JSONB DEFAULT '{}';

-- Add index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_properties_details ON properties USING gin(property_details);

-- ============================================
-- APARTMENT COMPLEX TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS properties_apartment_complex (
  property_id INTEGER PRIMARY KEY REFERENCES properties(id) ON DELETE CASCADE,
  
  -- Complex Style (Required)
  complex_style VARCHAR(50) NOT NULL,
  
  -- Building Information
  number_of_buildings INTEGER NOT NULL DEFAULT 1,
  total_units INTEGER NOT NULL,
  assigned_property_manager VARCHAR(200),
  building_codes_names JSONB DEFAULT '{}', -- {"A": "North Tower", "B": "South Tower"}
  
  -- Unit Distribution
  unit_mix JSONB DEFAULT '{}', -- {"studio": 20, "1br": 40, "2br": 30, "3br": 10}
  studio_units INTEGER DEFAULT 0,
  one_bed_units INTEGER DEFAULT 0,
  two_bed_units INTEGER DEFAULT 0,
  three_bed_units INTEGER DEFAULT 0,
  penthouse_units INTEGER DEFAULT 0,
  
  -- Amenities & Infrastructure
  shared_amenities JSONB DEFAULT '[]', -- ["gym", "pool", "parking_garage", "clubhouse"]
  has_security_system BOOLEAN DEFAULT false,
  security_system_type VARCHAR(100),
  security_system_details TEXT,
  floor_count INTEGER DEFAULT 1,
  elevator_count INTEGER DEFAULT 0,
  parking_spaces_total INTEGER,
  
  -- Waste Management
  trash_system_type VARCHAR(50), -- 'chute', 'compactor', 'curbside', 'valet'
  trash_collection_schedule VARCHAR(200),
  trash_system_details TEXT,
  
  -- Management & Operations
  property_management_company VARCHAR(200),
  on_site_management BOOLEAN DEFAULT false,
  management_office_location VARCHAR(100),
  management_office_hours JSONB DEFAULT '{}',
  emergency_contacts JSONB DEFAULT '[]',
  lease_expiry_distribution JSONB DEFAULT '{}',
  
  -- Policies & Financials
  pet_policy VARCHAR(500),
  utilities_included JSONB DEFAULT '[]',
  average_rent_by_type JSONB DEFAULT '{}',
  vacancy_rate NUMERIC(5,2),
  
  -- Management Contacts
  management_contact_phone VARCHAR(20),
  management_contact_email VARCHAR(255),
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- COMMERCIAL PROPERTY TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS properties_commercial (
  property_id INTEGER PRIMARY KEY REFERENCES properties(id) ON DELETE CASCADE,
  
  -- Space Information
  space_type VARCHAR(50) NOT NULL, -- 'retail', 'office', 'medical', 'restaurant', 'hotel_motel', 'multi_tenant'
  usable_square_feet INTEGER NOT NULL,
  rentable_square_feet INTEGER NOT NULL,
  common_area_factor NUMERIC(5,2) GENERATED ALWAYS AS (((rentable_square_feet - usable_square_feet)::numeric * 100) / NULLIF(usable_square_feet, 0)) STORED,
  lease_type VARCHAR(50) NOT NULL, -- 'gross', 'triple_net', 'modified_gross'
  
  -- Compliance & Zoning
  zoning_code VARCHAR(50),
  business_licensing_compliance JSONB DEFAULT '{}',
  permitted_uses JSONB DEFAULT '[]',
  
  -- Physical Specifications
  ceiling_height NUMERIC(5,2),
  has_loading_area BOOLEAN DEFAULT false,
  loading_docks_count INTEGER DEFAULT 0,
  loading_area_details TEXT,
  signage_rights BOOLEAN DEFAULT false,
  signage_restrictions TEXT,
  floor_count INTEGER DEFAULT 1,
  
  -- Infrastructure
  power_supply_info JSONB DEFAULT '{}',
  hvac_details JSONB DEFAULT '{}',
  internet_infrastructure JSONB DEFAULT '{}',
  
  -- Management
  on_site_maintenance BOOLEAN DEFAULT false,
  common_area_maintenance_fee NUMERIC(12,2),
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Data Integrity Constraints
  CONSTRAINT chk_properties_commercial_sqft_positive CHECK (usable_square_feet > 0 AND rentable_square_feet > 0),
  CONSTRAINT chk_properties_commercial_rsf_gte_usf CHECK (rentable_square_feet >= usable_square_feet)
);

-- ============================================
-- RESIDENTIAL PROPERTY TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS properties_residential (
  property_id INTEGER PRIMARY KEY REFERENCES properties(id) ON DELETE CASCADE,
  
  -- Living Spaces
  bedrooms INTEGER NOT NULL,
  bathrooms NUMERIC(3,1) NOT NULL,
  square_feet INTEGER,
  lot_size INTEGER,
  stories INTEGER DEFAULT 1,
  
  -- Parking
  garage_spaces INTEGER DEFAULT 0,
  has_driveway BOOLEAN DEFAULT false,
  street_parking BOOLEAN DEFAULT false,
  
  -- Systems
  heating_type VARCHAR(50),
  cooling_type VARCHAR(50),
  water_heater_type VARCHAR(50),
  
  -- Property Details
  property_subtype VARCHAR(50), -- 'single_family', 'townhouse', 'condo', 'mobile_home'
  roof_type VARCHAR(50),
  exterior_material VARCHAR(50),
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDUSTRIAL PROPERTY TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS properties_industrial (
  property_id INTEGER PRIMARY KEY REFERENCES properties(id) ON DELETE CASCADE,
  
  -- Facility Type (Required)
  industrial_type VARCHAR(50) NOT NULL,
  
  -- Space Specifications
  total_square_feet INTEGER NOT NULL,
  warehouse_square_feet INTEGER,
  office_square_feet INTEGER,
  manufacturing_square_feet INTEGER,
  clear_height NUMERIC(5,2),
  
  -- Loading & Access
  loading_docks_count INTEGER DEFAULT 0,
  drive_in_doors_count INTEGER DEFAULT 0,
  rail_access BOOLEAN DEFAULT false,
  truck_court_size INTEGER,
  
  -- Infrastructure
  power_capacity VARCHAR(50),
  power_voltage VARCHAR(50),
  has_crane BOOLEAN DEFAULT false,
  crane_capacity VARCHAR(50),
  sprinkler_system_type VARCHAR(50),
  
  -- Environmental
  environmental_compliance JSONB DEFAULT '{}',
  hazmat_storage_permitted BOOLEAN DEFAULT false,
  
  -- Zoning & Use
  zoning_classification VARCHAR(50),
  permitted_uses JSONB DEFAULT '[]',
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- MIXED USE PROPERTY TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS properties_mixed_use (
  property_id INTEGER PRIMARY KEY REFERENCES properties(id) ON DELETE CASCADE,
  
  -- Space Distribution
  residential_square_feet INTEGER,
  commercial_square_feet INTEGER,
  residential_units_count INTEGER,
  commercial_units_count INTEGER,
  
  -- Unit Types
  residential_unit_types JSONB DEFAULT '{}', -- {"studio": 5, "1br": 10, "2br": 8}
  commercial_space_types JSONB DEFAULT '[]', -- ["retail", "office", "restaurant", "hotel_motel"]
  
  -- Shared Facilities
  shared_amenities JSONB DEFAULT '[]',
  separate_entrances BOOLEAN DEFAULT true,
  shared_parking BOOLEAN DEFAULT true,
  parking_spaces_total INTEGER,
  
  -- Management
  single_management_company BOOLEAN DEFAULT true,
  management_structure TEXT,
  
  -- Zoning
  zoning_designation VARCHAR(50),
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- LAND PROPERTY TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS properties_land (
  property_id INTEGER PRIMARY KEY REFERENCES properties(id) ON DELETE CASCADE,
  
  -- Land Specifications
  total_acres NUMERIC(10,2) NOT NULL,
  usable_acres NUMERIC(10,2),
  
  -- Zoning & Development
  zoning_classification VARCHAR(50),
  allowed_uses JSONB DEFAULT '[]',
  max_building_height INTEGER,
  max_density VARCHAR(50),
  
  -- Utilities
  has_water_access BOOLEAN DEFAULT false,
  has_sewer_access BOOLEAN DEFAULT false,
  has_electric_access BOOLEAN DEFAULT false,
  has_gas_access BOOLEAN DEFAULT false,
  
  -- Physical Characteristics
  topography VARCHAR(100),
  soil_type VARCHAR(100),
  flood_zone VARCHAR(20),
  wetlands_present BOOLEAN DEFAULT false,
  
  -- Access
  road_frontage_feet INTEGER,
  access_type VARCHAR(50), -- 'paved', 'gravel', 'dirt', 'none'
  
  -- Environmental
  environmental_assessments JSONB DEFAULT '{}',
  mineral_rights_included BOOLEAN DEFAULT true,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- SPECIAL PURPOSE PROPERTY TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS properties_special_purpose (
  property_id INTEGER PRIMARY KEY REFERENCES properties(id) ON DELETE CASCADE,
  
  -- Property Specifics
  special_purpose_type VARCHAR(100) NOT NULL, -- 'church', 'school', 'hospital', 'hotel', 'gas_station'
  total_square_feet INTEGER,
  capacity INTEGER, -- seats, beds, students, etc.
  
  -- Facilities
  special_features JSONB DEFAULT '[]',
  auxiliary_buildings_count INTEGER DEFAULT 0,
  auxiliary_buildings_details JSONB DEFAULT '[]',
  
  -- Compliance
  licensing_requirements JSONB DEFAULT '{}',
  special_permits JSONB DEFAULT '[]',
  ada_compliant BOOLEAN DEFAULT false,
  
  -- Operations
  operating_requirements TEXT,
  special_equipment JSONB DEFAULT '[]',
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- OTHER PROPERTY TYPE TABLE (Catch-all)
-- ============================================
CREATE TABLE IF NOT EXISTS properties_other (
  property_id INTEGER PRIMARY KEY REFERENCES properties(id) ON DELETE CASCADE,
  
  -- Flexible Fields
  property_subtype VARCHAR(100),
  custom_attributes JSONB DEFAULT '{}',
  notes TEXT,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================
CREATE INDEX IF NOT EXISTS idx_apartment_complex_total_units ON properties_apartment_complex(total_units);
CREATE INDEX IF NOT EXISTS idx_apartment_complex_style ON properties_apartment_complex(complex_style);
CREATE INDEX IF NOT EXISTS idx_industrial_type ON properties_industrial(industrial_type);
CREATE INDEX IF NOT EXISTS idx_commercial_space_type ON properties_commercial(space_type);
CREATE INDEX IF NOT EXISTS idx_commercial_lease_type ON properties_commercial(lease_type);
CREATE INDEX IF NOT EXISTS idx_residential_bedrooms ON properties_residential(bedrooms);
CREATE INDEX IF NOT EXISTS idx_industrial_square_feet ON properties_industrial(total_square_feet);
CREATE INDEX IF NOT EXISTS idx_land_acres ON properties_land(total_acres);

-- ============================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to all property type tables
CREATE TRIGGER update_properties_apartment_complex_updated_at 
  BEFORE UPDATE ON properties_apartment_complex
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_properties_commercial_updated_at 
  BEFORE UPDATE ON properties_commercial
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_properties_residential_updated_at 
  BEFORE UPDATE ON properties_residential
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_properties_industrial_updated_at 
  BEFORE UPDATE ON properties_industrial
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_properties_mixed_use_updated_at 
  BEFORE UPDATE ON properties_mixed_use
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_properties_land_updated_at 
  BEFORE UPDATE ON properties_land
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_properties_special_purpose_updated_at 
  BEFORE UPDATE ON properties_special_purpose
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_properties_other_updated_at 
  BEFORE UPDATE ON properties_other
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all property type tables
ALTER TABLE properties_apartment_complex ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties_commercial ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties_residential ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties_industrial ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties_mixed_use ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties_land ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties_special_purpose ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties_other ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for each table (users can only see their own property details)
CREATE POLICY "Users can view their own apartment complex details"
  ON properties_apartment_complex FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_apartment_complex.property_id
      AND (properties.user_id = auth.uid() OR EXISTS (
        SELECT 1 FROM users WHERE users.id = auth.uid() AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can modify their own apartment complex details"
  ON properties_apartment_complex FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_apartment_complex.property_id
      AND properties.user_id = auth.uid()
    )
  );

-- Repeat similar policies for all other property type tables
CREATE POLICY "Users can view their own commercial details"
  ON properties_commercial FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_commercial.property_id
      AND (properties.user_id = auth.uid() OR EXISTS (
        SELECT 1 FROM users WHERE users.id = auth.uid() AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can modify their own commercial details"
  ON properties_commercial FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_commercial.property_id
      AND properties.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can view their own residential details"
  ON properties_residential FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_residential.property_id
      AND (properties.user_id = auth.uid() OR EXISTS (
        SELECT 1 FROM users WHERE users.id = auth.uid() AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can modify their own residential details"
  ON properties_residential FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_residential.property_id
      AND properties.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can view their own industrial details"
  ON properties_industrial FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_industrial.property_id
      AND (properties.user_id = auth.uid() OR EXISTS (
        SELECT 1 FROM users WHERE users.id = auth.uid() AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can modify their own industrial details"
  ON properties_industrial FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_industrial.property_id
      AND properties.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can view their own mixed use details"
  ON properties_mixed_use FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_mixed_use.property_id
      AND (properties.user_id = auth.uid() OR EXISTS (
        SELECT 1 FROM users WHERE users.id = auth.uid() AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can modify their own mixed use details"
  ON properties_mixed_use FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_mixed_use.property_id
      AND properties.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can view their own land details"
  ON properties_land FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_land.property_id
      AND (properties.user_id = auth.uid() OR EXISTS (
        SELECT 1 FROM users WHERE users.id = auth.uid() AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can modify their own land details"
  ON properties_land FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_land.property_id
      AND properties.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can view their own special purpose details"
  ON properties_special_purpose FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_special_purpose.property_id
      AND (properties.user_id = auth.uid() OR EXISTS (
        SELECT 1 FROM users WHERE users.id = auth.uid() AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can modify their own special purpose details"
  ON properties_special_purpose FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_special_purpose.property_id
      AND properties.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can view their own other property details"
  ON properties_other FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_other.property_id
      AND (properties.user_id = auth.uid() OR EXISTS (
        SELECT 1 FROM users WHERE users.id = auth.uid() AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can modify their own other property details"
  ON properties_other FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_other.property_id
      AND properties.user_id = auth.uid()
    )
  );

-- ============================================
-- CREATE VIEW FOR UNIFIED PROPERTY QUERIES
-- ============================================
CREATE OR REPLACE VIEW v_properties_full AS
SELECT 
  p.*,
  -- Include type-specific data as JSON
  CASE 
    WHEN p.property_type = 'Apartment Complex' THEN row_to_json(pac)
    WHEN p.property_type = 'Commercial' THEN row_to_json(pc)
    WHEN p.property_type = 'Residential' THEN row_to_json(pr)
    WHEN p.property_type = 'Industrial' THEN row_to_json(pi)
    WHEN p.property_type = 'Mixed-Use' THEN row_to_json(pmu)
    WHEN p.property_type = 'Land' THEN row_to_json(pl)
    WHEN p.property_type = 'Special Purpose' THEN row_to_json(psp)
    WHEN p.property_type = 'Other' THEN row_to_json(po)
    ELSE NULL
  END AS type_specific_details
FROM properties p
LEFT JOIN properties_apartment_complex pac ON p.id = pac.property_id
LEFT JOIN properties_commercial pc ON p.id = pc.property_id
LEFT JOIN properties_residential pr ON p.id = pr.property_id
LEFT JOIN properties_industrial pi ON p.id = pi.property_id
LEFT JOIN properties_mixed_use pmu ON p.id = pmu.property_id
LEFT JOIN properties_land pl ON p.id = pl.property_id
LEFT JOIN properties_special_purpose psp ON p.id = psp.property_id
LEFT JOIN properties_other po ON p.id = po.property_id;

-- ============================================
-- CONSTRAINTS FOR DATA INTEGRITY
-- ============================================
-- Add constraints to apartment complex table
ALTER TABLE properties_apartment_complex 
ADD CONSTRAINT chk_apartment_complex_style 
CHECK (complex_style IN ('garden', 'highrise', 'midrise', 'townhome', 'luxury', 'student'));

-- Add constraints to industrial table
ALTER TABLE properties_industrial 
ADD CONSTRAINT chk_industrial_type 
CHECK (industrial_type IN ('warehouse', 'distribution', 'manufacturing', 'flex', 'cold_storage', 'data_center', 'light_industrial', 'rd_tech'));

-- ============================================
-- DATA MIGRATION FOR EXISTING PROPERTIES
-- ============================================
-- Create entries in type-specific tables for existing properties
-- We'll add default/empty records that can be updated later

-- Migrate Apartment Complex properties
INSERT INTO properties_apartment_complex (property_id, complex_style, total_units, number_of_buildings)
SELECT id, 
       'garden' as complex_style, -- Default value, can be updated later
       COALESCE((
         CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'property_units')
         THEN (SELECT COUNT(*) FROM property_units WHERE property_id = p.id)
         ELSE 1 END
       ), 1) as total_units,
       1 as number_of_buildings
FROM properties p
WHERE p.property_type = 'Apartment Complex'
AND NOT EXISTS (
  SELECT 1 FROM properties_apartment_complex 
  WHERE property_id = p.id
);

-- Migrate Commercial properties
INSERT INTO properties_commercial (property_id, space_type, usable_square_feet, rentable_square_feet, lease_type)
SELECT id, 
       'office' as space_type,
       1000 as usable_square_feet,
       1000 as rentable_square_feet,
       'gross' as lease_type
FROM properties p
WHERE p.property_type = 'Commercial'
AND NOT EXISTS (
  SELECT 1 FROM properties_commercial 
  WHERE property_id = p.id
);

-- Migrate Residential properties
INSERT INTO properties_residential (property_id, bedrooms, bathrooms, property_subtype)
SELECT id, 
       3 as bedrooms,
       2.0 as bathrooms,
       'single_family' as property_subtype
FROM properties p
WHERE p.property_type = 'Residential'
AND NOT EXISTS (
  SELECT 1 FROM properties_residential 
  WHERE property_id = p.id
);

-- Migrate Industrial properties
INSERT INTO properties_industrial (property_id, industrial_type, total_square_feet)
SELECT id, 
       'warehouse' as industrial_type, -- Default value, can be updated later
       5000 as total_square_feet
FROM properties p
WHERE p.property_type = 'Industrial'
AND NOT EXISTS (
  SELECT 1 FROM properties_industrial 
  WHERE property_id = p.id
);

-- Migrate Mixed-Use properties
INSERT INTO properties_mixed_use (property_id)
SELECT id
FROM properties p
WHERE p.property_type = 'Mixed-Use'
AND NOT EXISTS (
  SELECT 1 FROM properties_mixed_use 
  WHERE property_id = p.id
);

-- Add comment explaining the migration
COMMENT ON TABLE properties_apartment_complex IS 'Stores apartment complex-specific property details';
COMMENT ON TABLE properties_commercial IS 'Stores commercial property-specific details';
COMMENT ON TABLE properties_residential IS 'Stores residential property-specific details';
COMMENT ON TABLE properties_industrial IS 'Stores industrial property-specific details';
COMMENT ON TABLE properties_mixed_use IS 'Stores mixed-use property-specific details';
COMMENT ON TABLE properties_land IS 'Stores land property-specific details';
COMMENT ON TABLE properties_special_purpose IS 'Stores special purpose property-specific details';
COMMENT ON TABLE properties_other IS 'Stores other/custom property type details';
COMMENT ON VIEW v_properties_full IS 'Unified view of all properties with their type-specific details';