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
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_schema = 'public' 
    AND table_name = 'tenants' 
    AND constraint_name = 'chk_tenants_single_primary_emergency_contact'
  ) THEN
    ALTER TABLE "public"."tenants"
    ADD CONSTRAINT "chk_tenants_single_primary_emergency_contact"
    CHECK (
      (SELECT COUNT(*)
       FROM jsonb_array_elements(emergency_contacts) AS elem
       WHERE (elem->>'is_primary')::boolean = true) <= 1
    );
  END IF;
END $$;

-- Constraint 3: Validate required fields in each contact
-- Ensures name, phone, and relationship are present and non-empty
-- Note: This is a defensive check; primary validation happens in Pydantic
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_schema = 'public' 
    AND table_name = 'tenants' 
    AND constraint_name = 'chk_tenants_emergency_contact_required_fields'
  ) THEN
    ALTER TABLE "public"."tenants"
    ADD CONSTRAINT "chk_tenants_emergency_contact_required_fields"
    CHECK (
      -- All elements must have required fields
      NOT EXISTS (
        SELECT 1
        FROM jsonb_array_elements(emergency_contacts) AS elem
        WHERE
          -- name is required and must not be empty after trimming
          (elem->>'name' IS NULL OR TRIM(elem->>'name') = '')
          OR
          -- phone is required and must not be empty after trimming
          (elem->>'phone' IS NULL OR TRIM(elem->>'phone') = '')
          OR
          -- relationship is required and must not be empty after trimming
          (elem->>'relationship' IS NULL OR TRIM(elem->>'relationship') = '')
      )
    );
  END IF;
END $$;

-- Constraint 4: Validate email format if provided
-- Uses PostgreSQL regex pattern for basic email validation
-- Prevents obviously malformed email addresses at the database level
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_schema = 'public' 
    AND table_name = 'tenants' 
    AND constraint_name = 'chk_tenants_emergency_contact_email_format'
  ) THEN
    ALTER TABLE "public"."tenants"
    ADD CONSTRAINT "chk_tenants_emergency_contact_email_format"
    CHECK (
      NOT EXISTS (
        SELECT 1
        FROM jsonb_array_elements(emergency_contacts) AS elem
        WHERE
          -- If email is provided, it must match a basic email pattern
          elem->>'email' IS NOT NULL
          AND TRIM(elem->>'email') != ''
          AND elem->>'email' !~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
      )
    );
  END IF;
END $$;

-- Add comments documenting all constraints for reference
DO $$ 
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_schema = 'public' 
    AND table_name = 'tenants' 
    AND constraint_name = 'chk_tenants_max_emergency_contacts'
  ) THEN
    COMMENT ON CONSTRAINT "chk_tenants_max_emergency_contacts" ON "public"."tenants" IS 'Limits emergency contacts to maximum of 5 per tenant for security and performance';
  END IF;
  
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_schema = 'public' 
    AND table_name = 'tenants' 
    AND constraint_name = 'chk_tenants_single_primary_emergency_contact'
  ) THEN
    COMMENT ON CONSTRAINT "chk_tenants_single_primary_emergency_contact" ON "public"."tenants" IS 'Ensures only one contact can be marked as primary to prevent ambiguity';
  END IF;
  
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_schema = 'public' 
    AND table_name = 'tenants' 
    AND constraint_name = 'chk_tenants_emergency_contact_required_fields'
  ) THEN
    COMMENT ON CONSTRAINT "chk_tenants_emergency_contact_required_fields" ON "public"."tenants" IS 'Validates that all contacts have required fields: name, phone, and relationship';
  END IF;
  
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_schema = 'public' 
    AND table_name = 'tenants' 
    AND constraint_name = 'chk_tenants_emergency_contact_email_format'
  ) THEN
    COMMENT ON CONSTRAINT "chk_tenants_emergency_contact_email_format" ON "public"."tenants" IS 'Validates email format when provided to prevent malformed data';
  END IF;
END $$;
