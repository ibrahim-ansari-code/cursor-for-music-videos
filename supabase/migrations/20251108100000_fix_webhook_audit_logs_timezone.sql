-- Fix webhook_audit_logs.created_at to use timezone-aware timestamp
-- This aligns with the codebase standard of using timezone-aware datetimes

ALTER TABLE public.webhook_audit_logs 
  ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

COMMENT ON COLUMN public.webhook_audit_logs.created_at IS 'Timestamp when the webhook audit log was created (timezone-aware UTC)';

