-- Add emergency_contacts column to tenants table
-- This column stores emergency contact information as JSONB array
-- Security: Database-level validation ensures data integrity and prevents malformed data
-- Idempotent: Safe to run multiple times

-- Add column only if it doesn't exist
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'public' 
    AND table_name = 'tenants' 
    AND column_name = 'emergency_contacts'
  ) THEN
    ALTER TABLE "public"."tenants"
    ADD COLUMN "emergency_contacts" jsonb DEFAULT '[]'::jsonb;
  END IF;
END $$;

-- Add comment to document the column purpose and security considerations
COMMENT ON COLUMN "public"."tenants"."emergency_contacts" IS 'Emergency contact information stored as JSON array. Each contact has: name (required), relationship (required), phone (required), email (optional), is_primary (boolean), notes (optional). Validated at both database and application layers for security.';

-- Create GIN index for efficient JSONB queries (only if doesn't exist)
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes 
    WHERE schemaname = 'public' 
    AND tablename = 'tenants' 
    AND indexname = 'idx_tenants_emergency_contacts_gin'
  ) THEN
    CREATE INDEX "idx_tenants_emergency_contacts_gin" ON "public"."tenants" USING gin ("emergency_contacts");
  END IF;
END $$;

-- ============================================================================
-- SECURITY CONSTRAINTS: Database-level validation for emergency contacts
-- These constraints work in conjunction with Pydantic validation in the backend
-- ============================================================================

-- Constraint 1: Maximum 5 emergency contacts allowed
-- Prevents abuse and ensures reasonable data size
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_schema = 'public' 
    AND table_name = 'tenants' 
    AND constraint_name = 'chk_tenants_max_emergency_contacts'
  ) THEN
    ALTER TABLE "public"."tenants"
    ADD CONSTRAINT "chk_tenants_max_emergency_contacts"
    CHECK (
      jsonb_array_length(emergency_contacts) <= 5
    );
  END IF;
END $$;

-- Constraint 2: Ensure only one primary emergency contact
-- Prevents race conditions when multiple contacts are marked primary simultaneously
-- Note: PostgreSQL doesn't allow subqueries in CHECK constraints, so we use a trigger function
CREATE OR REPLACE FUNCTION validate_emergency_contacts_primary()
RETURNS TRIGGER AS $$
DECLARE
  primary_count INTEGER;
BEGIN
  -- Count primary contacts
  SELECT COUNT(*)
  INTO primary_count
  FROM jsonb_array_elements(NEW.emergency_contacts) AS elem
  WHERE (elem->>'is_primary')::boolean = true;
  
  -- Ensure only one primary contact
  IF primary_count > 1 THEN
    RAISE EXCEPTION 'Only one emergency contact can be marked as primary';
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger only if it doesn't exist
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger 
    WHERE tgname = 'trg_validate_emergency_contacts_primary'
  ) THEN
    CREATE TRIGGER trg_validate_emergency_contacts_primary
    BEFORE INSERT OR UPDATE ON "public"."tenants"
    FOR EACH ROW
    EXECUTE FUNCTION validate_emergency_contacts_primary();
  END IF;
END $$;

-- Note: Additional validation (required fields, email format) is handled by:
-- 1. Pydantic validators in Backend/models/tenant.py (primary defense)
-- 2. Pydantic schemas in Backend/api/tenants/schemas.py (API layer)
-- We rely on application-layer validation for these checks rather than complex DB triggers

-- Add comment documenting the constraint
COMMENT ON CONSTRAINT "chk_tenants_max_emergency_contacts" ON "public"."tenants" IS 'Limits emergency contacts to maximum of 5 per tenant for security and performance';
