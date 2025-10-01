-- Make QuickBooks refresh token optional for accounting-only scope
-- Purpose: Support accounting-only OAuth scope that doesn't provide refresh tokens
-- This allows Canadian users to connect without QuickBooks Payments onboarding

BEGIN;

-- Make refresh_token_encrypted nullable
ALTER TABLE public.quickbooks_integrations 
  ALTER COLUMN refresh_token_encrypted DROP NOT NULL;

-- Drop the constraint that required non-empty refresh token
ALTER TABLE public.quickbooks_integrations 
  DROP CONSTRAINT IF EXISTS quickbooks_integrations_check;

-- Add updated constraint that allows null or non-empty refresh token
ALTER TABLE public.quickbooks_integrations 
  ADD CONSTRAINT quickbooks_integrations_check 
  CHECK (
    char_length(realm_id) > 0 
    AND char_length(access_token_encrypted) > 0 
    AND (refresh_token_encrypted IS NULL OR char_length(refresh_token_encrypted) > 0)
  );

COMMIT;

