-- Migration: Remove Alembic Infrastructure
-- Purpose: Drop alembic_version table as we transition to Supabase-only migrations
-- Context: Alembic was causing schema confusion with JIT user creation, preventing
--          authentication from working properly. The notification system tables exist
--          via Supabase migrations, but Alembic's metadata didn't know about them.

-- Drop the alembic_version table if it exists
DROP TABLE IF EXISTS alembic_version CASCADE;

-- Add comment for audit trail
COMMENT ON SCHEMA public IS 'Public schema - managed exclusively by Supabase migrations. Alembic removed as of 2025-11-04.';

