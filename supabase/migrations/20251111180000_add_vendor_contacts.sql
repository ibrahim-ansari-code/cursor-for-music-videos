-- ========================================================================
-- VENDOR MANAGEMENT SYSTEM - NORMALIZED DESIGN
-- ========================================================================
-- Creates a central vendors table with a join table for user-vendor relationships.
-- This design prevents data duplication when multiple users add the same vendor
-- and enables future features like vendor marketplace, ratings, and shared vendors.
-- ========================================================================

-- ========================================================================
-- 1. CREATE CENTRAL VENDORS TABLE
-- ========================================================================

CREATE TABLE vendors (
  id SERIAL PRIMARY KEY,
  
  -- Core Vendor Information
  company_name VARCHAR(255) NOT NULL,
  contact_person VARCHAR(255),
  trade_category VARCHAR(100) NOT NULL,
  
  -- Contact Information
  phone VARCHAR(20) NOT NULL,
  email VARCHAR(255),
  
  -- Platform Features (Future)
  is_verified BOOLEAN DEFAULT FALSE NOT NULL,
  verification_date TIMESTAMPTZ,
  average_rating DECIMAL(3,2),
  total_reviews INTEGER DEFAULT 0,
  
  -- Audit Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  
  -- Data Quality Constraints
  CONSTRAINT vendors_company_name_check CHECK (TRIM(company_name) <> ''),
  CONSTRAINT vendors_trade_category_check CHECK (TRIM(trade_category) <> ''),
  CONSTRAINT vendors_phone_check CHECK (TRIM(phone) <> '' AND phone ~ '^[0-9+() -]+$'),
  CONSTRAINT vendors_email_format_check CHECK (email IS NULL OR email ~ '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
  CONSTRAINT vendors_average_rating_check CHECK (average_rating IS NULL OR (average_rating >= 0 AND average_rating <= 5))
);

-- Performance indexes for vendors
CREATE INDEX idx_vendors_company_name ON vendors(company_name);
CREATE INDEX idx_vendors_trade_category ON vendors(trade_category);
CREATE INDEX idx_vendors_phone ON vendors(phone);
CREATE INDEX idx_vendors_email ON vendors(email) WHERE email IS NOT NULL;
CREATE INDEX idx_vendors_is_verified ON vendors(is_verified) WHERE is_verified = TRUE;

-- Full-text search index for vendor search
CREATE INDEX idx_vendors_search ON vendors USING gin(
  to_tsvector('english', company_name || ' ' || COALESCE(contact_person, ''))
);

-- Updated_at trigger for vendors
CREATE TRIGGER update_vendors_updated_at
  BEFORE UPDATE ON vendors
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ========================================================================
-- 2. CREATE USER-VENDOR JOIN TABLE
-- ========================================================================

CREATE TABLE user_vendors (
  id SERIAL PRIMARY KEY,
  
  -- Foreign Keys
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  vendor_id INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
  
  -- User-Specific Data
  notes TEXT,
  is_active BOOLEAN DEFAULT TRUE NOT NULL,
  is_favorite BOOLEAN DEFAULT FALSE NOT NULL,
  
  -- User's Personal Rating (separate from platform rating)
  personal_rating INTEGER,
  
  -- Audit Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  
  -- Constraints
  CONSTRAINT user_vendors_unique_association UNIQUE(user_id, vendor_id),
  CONSTRAINT user_vendors_personal_rating_check CHECK (personal_rating IS NULL OR (personal_rating >= 1 AND personal_rating <= 5))
);

-- Performance indexes for user_vendors
CREATE INDEX idx_user_vendors_user_id ON user_vendors(user_id);
CREATE INDEX idx_user_vendors_vendor_id ON user_vendors(vendor_id);
CREATE INDEX idx_user_vendors_is_active ON user_vendors(user_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_user_vendors_is_favorite ON user_vendors(user_id, is_favorite) WHERE is_favorite = TRUE;

-- Updated_at trigger for user_vendors
CREATE TRIGGER update_user_vendors_updated_at
  BEFORE UPDATE ON user_vendors
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ========================================================================
-- 3. UPDATE MAINTENANCE_REQUESTS TABLE
-- ========================================================================

-- Add vendor assignment and tenant notification fields
ALTER TABLE maintenance_requests 
  ADD COLUMN vendor_id INTEGER REFERENCES vendors(id) ON DELETE SET NULL,
  ADD COLUMN notify_tenant BOOLEAN DEFAULT FALSE NOT NULL;

-- Index for vendor lookups on maintenance requests
CREATE INDEX idx_maintenance_requests_vendor_id ON maintenance_requests(vendor_id);

-- Add comment explaining the relationship
COMMENT ON COLUMN maintenance_requests.vendor_id IS 'Reference to the assigned vendor from the central vendors table';

-- ========================================================================
-- 4. ROW LEVEL SECURITY (RLS) POLICIES
-- ========================================================================

-- Enable RLS on vendors table
ALTER TABLE vendors ENABLE ROW LEVEL SECURITY;

-- Enable RLS on user_vendors join table
ALTER TABLE user_vendors ENABLE ROW LEVEL SECURITY;

-- ========================================================================
-- VENDORS TABLE POLICIES
-- ========================================================================

-- Policy: All authenticated users can view vendors (for marketplace/search)
CREATE POLICY "Authenticated users can view vendors"
  ON vendors
  FOR SELECT
  USING (auth.role() = 'authenticated');

-- Policy: System can insert vendors (via API that checks for duplicates)
-- Users don't directly insert into vendors table
CREATE POLICY "Service role can insert vendors"
  ON vendors
  FOR INSERT
  WITH CHECK (auth.role() = 'service_role' OR auth.role() = 'authenticated');

-- Policy: Service role can update vendors (for platform features)
CREATE POLICY "Service role can update vendors"
  ON vendors
  FOR UPDATE
  USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');

-- Policy: Service role can delete vendors
CREATE POLICY "Service role can delete vendors"
  ON vendors
  FOR DELETE
  USING (auth.role() = 'service_role');

-- ========================================================================
-- USER_VENDORS JOIN TABLE POLICIES
-- ========================================================================

-- Policy: Users can view their own vendor associations
CREATE POLICY "Users can view their own vendor associations"
  ON user_vendors
  FOR SELECT
  USING (auth.uid() = user_id);

-- Policy: Users can create their own vendor associations
CREATE POLICY "Users can create their own vendor associations"
  ON user_vendors
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own vendor associations
CREATE POLICY "Users can update their own vendor associations"
  ON user_vendors
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Policy: Users can delete their own vendor associations
CREATE POLICY "Users can delete their own vendor associations"
  ON user_vendors
  FOR DELETE
  USING (auth.uid() = user_id);

-- ========================================================================
-- 5. DOCUMENTATION COMMENTS
-- ========================================================================

-- Vendors table comments
COMMENT ON TABLE vendors IS 'Central repository of all vendors/contractors in the platform. Shared across users to prevent duplication and enable marketplace features.';
COMMENT ON COLUMN vendors.company_name IS 'Vendor company or business name (required)';
COMMENT ON COLUMN vendors.contact_person IS 'Name of the primary contact person at the vendor';
COMMENT ON COLUMN vendors.trade_category IS 'Type of service provided (e.g., Plumber, Electrician, HVAC, Carpenter)';
COMMENT ON COLUMN vendors.phone IS 'Vendor phone number (required for notifications)';
COMMENT ON COLUMN vendors.email IS 'Vendor email address (optional, for email notifications)';
COMMENT ON COLUMN vendors.is_verified IS 'Whether this vendor has been verified by the platform (future feature)';
COMMENT ON COLUMN vendors.average_rating IS 'Platform-wide average rating (0-5 scale) aggregated from all user reviews';
COMMENT ON COLUMN vendors.total_reviews IS 'Total number of reviews across all users';

-- User-Vendors join table comments
COMMENT ON TABLE user_vendors IS 'Join table linking users to vendors. Stores user-specific preferences and notes about each vendor relationship.';
COMMENT ON COLUMN user_vendors.user_id IS 'The landlord/user who added this vendor to their contacts';
COMMENT ON COLUMN user_vendors.vendor_id IS 'Reference to the vendor in the central vendors table';
COMMENT ON COLUMN user_vendors.notes IS 'User-specific notes about this vendor (rates, availability, preferences, etc.)';
COMMENT ON COLUMN user_vendors.is_active IS 'Whether this user still wants to work with this vendor';
COMMENT ON COLUMN user_vendors.is_favorite IS 'Whether this user has marked this vendor as a favorite';
COMMENT ON COLUMN user_vendors.personal_rating IS 'User''s personal rating of this vendor (1-5 scale), separate from platform average';

-- Maintenance requests comments
COMMENT ON COLUMN maintenance_requests.notify_tenant IS 'Whether to send status update notifications to the tenant for this maintenance request';

