-- ============================================================================
-- TENANT DOCUMENTS SYSTEM
-- ============================================================================
-- This migration creates a comprehensive document management system for tenants
-- with strong typing, RLS policies, and compliance tracking capabilities.
--
-- Features:
-- - 14 document categories with PostgreSQL ENUMs for type safety
-- - Document status workflow (pending → verified/rejected/expired)
-- - Expiry date tracking for compliance documents
-- - Tag-based organization
-- - Full-text search support
-- - Row-level security policies
-- - Automatic timestamp management
--
-- Created: 2025-10-19
-- ============================================================================

-- ============================================================================
-- STEP 1: CREATE ENUM TYPES
-- ============================================================================

-- Document category enum (14 main categories)
CREATE TYPE document_category_enum AS ENUM (
  'lease_agreements',
  'lease_addendums',
  'condition_inspections',
  'province_forms',
  'commercial_files',
  'applications_kyc',
  'insurance_risk',
  'financial_payments',
  'maintenance_work',
  'legal_notices',
  'communications',
  'move_in_out',
  'privacy_security',
  'health_safety'
);

-- Document status enum (workflow states)
CREATE TYPE document_status_enum AS ENUM (
  'pending',
  'verified',
  'rejected',
  'expired'
);

-- ============================================================================
-- STEP 2: CREATE TENANT_DOCUMENTS TABLE
-- ============================================================================

CREATE TABLE tenant_documents (
  -- ===== PRIMARY KEY =====
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- ===== FOREIGN KEYS =====
  tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  uploaded_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  
  -- ===== FILE METADATA =====
  file_name VARCHAR(255) NOT NULL,
  file_path TEXT NOT NULL,
  file_size BIGINT NOT NULL,
  file_type VARCHAR(100) NOT NULL,
  
  -- ===== DOCUMENT CLASSIFICATION (STRONGLY TYPED) =====
  document_category document_category_enum NOT NULL,
  document_type VARCHAR(100) NOT NULL,
  
  -- ===== ORGANIZATION =====
  tags TEXT[] DEFAULT '{}',
  notes TEXT,
  
  -- ===== COMPLIANCE TRACKING =====
  expiry_date DATE,
  status document_status_enum NOT NULL DEFAULT 'pending',
  
  -- ===== TIMESTAMPS =====
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- STEP 3: ADD TABLE CONSTRAINTS
-- ============================================================================

-- Ensure notes don't exceed 280 characters
ALTER TABLE tenant_documents
  ADD CONSTRAINT notes_length_check 
  CHECK (char_length(notes) <= 280);

-- Ensure file_size is positive
ALTER TABLE tenant_documents
  ADD CONSTRAINT file_size_positive_check 
  CHECK (file_size > 0);

-- Ensure file_name is not empty
ALTER TABLE tenant_documents
  ADD CONSTRAINT file_name_not_empty_check
  CHECK (char_length(trim(file_name)) > 0);

-- Ensure file_path is not empty
ALTER TABLE tenant_documents
  ADD CONSTRAINT file_path_not_empty_check
  CHECK (char_length(trim(file_path)) > 0);

-- Ensure document_type is not empty
ALTER TABLE tenant_documents
  ADD CONSTRAINT document_type_not_empty_check
  CHECK (char_length(trim(document_type)) > 0);

-- ============================================================================
-- STEP 4: CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

-- Primary lookup: Get all documents for a tenant
CREATE INDEX idx_tenant_documents_tenant_id ON tenant_documents(tenant_id);

-- Filtering by category
CREATE INDEX idx_tenant_documents_category ON tenant_documents(document_category);

-- Filtering by status
CREATE INDEX idx_tenant_documents_status ON tenant_documents(status);

-- Expiry tracking (partial index for non-null expiry dates)
CREATE INDEX idx_tenant_documents_expiry 
  ON tenant_documents(expiry_date) 
  WHERE expiry_date IS NOT NULL;

-- Sort by upload date (DESC for most recent first)
CREATE INDEX idx_tenant_documents_uploaded_at ON tenant_documents(uploaded_at DESC);

-- Composite index for common query pattern (tenant + filters)
-- Optimizes: SELECT * FROM tenant_documents WHERE tenant_id = ? AND document_category = ? AND status = ?
CREATE INDEX idx_tenant_documents_tenant_category_status 
  ON tenant_documents(tenant_id, document_category, status);

-- Full-text search support for file_name and notes
CREATE INDEX idx_tenant_documents_search 
  ON tenant_documents USING gin(to_tsvector('english', coalesce(file_name, '') || ' ' || coalesce(notes, '')));

-- ============================================================================
-- STEP 5: ENABLE ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE tenant_documents ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- STEP 6: CREATE RLS POLICIES
-- ============================================================================

-- Policy: Users can view documents for tenants they manage
CREATE POLICY "Users can view tenant documents they manage"
  ON tenant_documents FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM tenants
      WHERE tenants.id = tenant_documents.tenant_id
      AND tenants.landlord_id = auth.uid()
    )
  );

-- Policy: Users can insert documents for tenants they manage
CREATE POLICY "Users can upload documents for tenants they manage"
  ON tenant_documents FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM tenants
      WHERE tenants.id = tenant_documents.tenant_id
      AND tenants.landlord_id = auth.uid()
    )
  );

-- Policy: Users can update documents for tenants they manage
CREATE POLICY "Users can update documents for tenants they manage"
  ON tenant_documents FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM tenants
      WHERE tenants.id = tenant_documents.tenant_id
      AND tenants.landlord_id = auth.uid()
    )
  );

-- Policy: Users can delete documents for tenants they manage
CREATE POLICY "Users can delete documents for tenants they manage"
  ON tenant_documents FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM tenants
      WHERE tenants.id = tenant_documents.tenant_id
      AND tenants.landlord_id = auth.uid()
    )
  );

-- ============================================================================
-- STEP 7: CREATE TRIGGER FOR AUTO-UPDATE TIMESTAMP
-- ============================================================================

-- Create trigger to automatically update updated_at timestamp
CREATE TRIGGER update_tenant_documents_updated_at
  BEFORE UPDATE ON tenant_documents
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- STEP 8: ADD HELPFUL COMMENTS
-- ============================================================================

COMMENT ON TABLE tenant_documents IS 'Stores tenant-specific documents across 14 categories with compliance tracking';
COMMENT ON COLUMN tenant_documents.document_category IS 'Document category from 14 predefined types (strongly typed enum)';
COMMENT ON COLUMN tenant_documents.document_type IS 'Specific document type within category (200+ types available)';
COMMENT ON COLUMN tenant_documents.status IS 'Document workflow status: pending → verified/rejected/expired';
COMMENT ON COLUMN tenant_documents.expiry_date IS 'Expiration date for compliance tracking (insurance, licenses, etc.)';
COMMENT ON COLUMN tenant_documents.tags IS 'Flexible array of tags for organization and filtering';
COMMENT ON COLUMN tenant_documents.notes IS 'Additional notes about document (max 280 characters)';
COMMENT ON COLUMN tenant_documents.uploaded_by IS 'User who uploaded the document (for audit trail)';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- This migration creates a production-ready document management system with:
-- ✅ Strong typing via PostgreSQL ENUMs
-- ✅ Row-level security for multi-tenant isolation
-- ✅ Performance indexes for fast queries
-- ✅ Full-text search capability
-- ✅ Compliance tracking with expiry dates
-- ✅ Audit trail with uploaded_by and timestamps
-- ✅ Data integrity via constraints
-- ============================================================================
