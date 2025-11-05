-- Add comprehensive fields to properties_land table for ground leases and land parcels
-- Supports McDonald's-style ground leases, vacant land, and development land

-- ===== LAND MEASUREMENTS =====
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS total_area_sqft NUMERIC(12, 2);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS leased_portion_sqft NUMERIC(12, 2);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS leased_portion_percentage NUMERIC(5, 2);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS frontage_meters NUMERIC(10, 2);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS depth_meters NUMERIC(10, 2);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS survey_date DATE;
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS survey_reference VARCHAR(200);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS survey_document_url VARCHAR(500);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS lot_numbers VARCHAR(200);

-- ===== LAND USE & ZONING =====
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS municipality VARCHAR(200);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS zoning_code VARCHAR(100);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS official_plan_designation VARCHAR(100);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS overlays_restrictions TEXT;
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS site_plan_status VARCHAR(50);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS permitted_uses JSONB DEFAULT '[]'::jsonb;

-- ===== GROUND LEASE SPECIFICS =====
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS lease_structure VARCHAR(100);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS allows_structures BOOLEAN DEFAULT false;
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS development_rights TEXT;
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS signage_rights BOOLEAN DEFAULT false;
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS subletting_allowed BOOLEAN DEFAULT false;
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS revenue_share_percentage NUMERIC(5, 2);

-- ===== ENCUMBRANCES & LEGAL =====
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS registered_covenants TEXT;
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS title_registration_province VARCHAR(100);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS title_registration_number VARCHAR(200);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS easements TEXT;
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS environmental_restrictions TEXT;

-- ===== FINANCIAL STRUCTURE =====
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS assessment_roll_number VARCHAR(100);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS insurance_responsibility VARCHAR(50);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS operating_expenses_responsibility VARCHAR(50);

-- ===== PHYSICAL FEATURES =====
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS topography VARCHAR(50);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS soil_type VARCHAR(100);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS drainage VARCHAR(100);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS floodplain_indicator BOOLEAN DEFAULT false;
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS brownfield_indicator BOOLEAN DEFAULT false;
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS conservation_area BOOLEAN DEFAULT false;

-- ===== UTILITIES & INFRASTRUCTURE =====
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS utilities_status JSONB DEFAULT '{}'::jsonb;
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS road_access VARCHAR(200);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS parking_spaces INTEGER;

-- ===== ENVIRONMENTAL ASSESSMENTS =====
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS environmental_assessment_phase1 BOOLEAN DEFAULT false;
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS environmental_assessment_phase2 BOOLEAN DEFAULT false;
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS esa_document_urls JSONB DEFAULT '[]'::jsonb;

-- ===== DOCUMENTATION & MEDIA =====
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS zoning_certificate_url VARCHAR(500);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS site_plan_url VARCHAR(500);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS parcel_map_url VARCHAR(500);
ALTER TABLE properties_land ADD COLUMN IF NOT EXISTS aerial_photo_urls JSONB DEFAULT '[]'::jsonb;

-- Add comments for documentation
COMMENT ON COLUMN properties_land.total_area_sqft IS 'Total land area in square feet';
COMMENT ON COLUMN properties_land.leased_portion_sqft IS 'Leased portion in square feet (for partial land leases)';
COMMENT ON COLUMN properties_land.permitted_uses IS 'List of permitted land uses (JSON array)';
COMMENT ON COLUMN properties_land.lease_structure IS 'Type: ground_lease, air_rights, mineral_rights, agricultural, mixed';
COMMENT ON COLUMN properties_land.utilities_status IS 'Utility connection status: {water: connected|available|not_available, ...}';
COMMENT ON COLUMN properties_land.environmental_assessment_phase1 IS 'Whether Phase I Environmental Site Assessment completed';
COMMENT ON COLUMN properties_land.environmental_assessment_phase2 IS 'Whether Phase II Environmental Site Assessment completed';

-- Add check constraints for data integrity
ALTER TABLE properties_land ADD CONSTRAINT check_leased_portion_percentage 
  CHECK (leased_portion_percentage IS NULL OR (leased_portion_percentage >= 0 AND leased_portion_percentage <= 100));

ALTER TABLE properties_land ADD CONSTRAINT check_revenue_share_percentage 
  CHECK (revenue_share_percentage IS NULL OR (revenue_share_percentage >= 0 AND revenue_share_percentage <= 100));

ALTER TABLE properties_land ADD CONSTRAINT check_site_plan_status 
  CHECK (site_plan_status IS NULL OR site_plan_status IN ('approved', 'pending', 'not_submitted'));

ALTER TABLE properties_land ADD CONSTRAINT check_insurance_responsibility 
  CHECK (insurance_responsibility IS NULL OR insurance_responsibility IN ('landlord', 'tenant', 'shared'));

ALTER TABLE properties_land ADD CONSTRAINT check_operating_expenses_responsibility 
  CHECK (operating_expenses_responsibility IS NULL OR operating_expenses_responsibility IN ('landlord', 'tenant', 'shared'));

