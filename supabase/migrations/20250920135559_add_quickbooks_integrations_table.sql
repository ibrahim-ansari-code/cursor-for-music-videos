-- QuickBooks integration subtable
-- Purpose: Store provider-specific OAuth and metadata for Intuit (QBO)

BEGIN;

CREATE TABLE IF NOT EXISTS public.quickbooks_integrations (
  -- 1:1 extension of public.integrations
  integration_id INTEGER PRIMARY KEY REFERENCES public.integrations(id) ON DELETE CASCADE,

  -- Intuit/QBO identifiers and tokens
  realm_id TEXT NOT NULL,
  access_token_encrypted TEXT NOT NULL,
  refresh_token_encrypted TEXT NOT NULL,
  access_token_expires_at TIMESTAMPTZ NOT NULL,
  refresh_token_expires_at TIMESTAMPTZ,
  scope TEXT,

  -- Optional cached metadata
  company_name TEXT,
  last_token_refresh_at TIMESTAMPTZ,

  -- Audit fields
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Basic sanity checks
  CHECK (char_length(realm_id) > 0),
  CHECK (char_length(access_token_encrypted) > 0),
  CHECK (char_length(refresh_token_encrypted) > 0)
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_quickbooks_integrations_realm_id
  ON public.quickbooks_integrations (realm_id);

CREATE INDEX IF NOT EXISTS idx_quickbooks_integrations_access_expiry
  ON public.quickbooks_integrations (access_token_expires_at);

-- Remove Apideck columns from integrations table (migration to Intuit-only)
ALTER TABLE public.integrations DROP COLUMN IF EXISTS apideck_consumer_id;
ALTER TABLE public.integrations DROP COLUMN IF EXISTS apideck_service_id;

COMMIT;


