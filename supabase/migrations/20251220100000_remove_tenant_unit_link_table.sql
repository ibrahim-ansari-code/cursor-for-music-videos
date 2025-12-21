-- =============================================================================
-- Migration: Remove tenant_unit_link Table
-- Description: Consolidates tenant-unit relationships to use only the direct
--              foreign key (property_units.tenant_id), removing the redundant
--              many-to-many link table that provided no historical value.
-- 
-- Background: Analysis showed that:
--   - The link table had 189 entries, ALL with end_date = NULL (no history)
--   - It was a 100% duplicate of property_units.tenant_id
--   - Only used as a fallback in ONE place (maintenance service)
--   - Never used for displaying tenant info or any core features
--
-- This migration:
--   1. Drops the tenant_unit_link table
--   2. Adds documentation to property_units.tenant_id column
-- 
-- Data Safety:
--   - All code that writes to tenant_unit_link has been removed
--   - All code that reads from it has been updated to use property_units.tenant_id
--   - Active lease data was synced to property_units.tenant_id before this migration
-- =============================================================================

-- Drop the tenant_unit_link table
DROP TABLE IF EXISTS tenant_unit_link CASCADE;

-- Add comment to document the single source of truth
COMMENT ON COLUMN property_units.tenant_id IS 
  'Direct FK to current tenant occupying this unit. Single source of truth for tenant-unit assignments. Set by lease activation, cleared by lease termination.';

