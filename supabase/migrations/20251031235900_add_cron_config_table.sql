-- ========================================================================
-- Notification Scheduler Configuration Table
-- 
-- This migration creates a configuration table to store the internal API key
-- for pg_cron scheduled jobs. This approach works with Supabase permissions.
-- ========================================================================

-- Create configuration table
CREATE TABLE IF NOT EXISTS notification_scheduler_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS for security
ALTER TABLE notification_scheduler_config ENABLE ROW LEVEL SECURITY;

-- Create RLS policies: Only service role (used by functions) can access
CREATE POLICY IF NOT EXISTS "Service role can read config"
ON notification_scheduler_config
FOR SELECT
TO service_role
USING (true);

CREATE POLICY IF NOT EXISTS "Service role can write config"
ON notification_scheduler_config
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Block all other access (authenticated users, anon)
CREATE POLICY IF NOT EXISTS "Block public access to config"
ON notification_scheduler_config
FOR ALL
TO authenticated, anon
USING (false)
WITH CHECK (false);

-- Grant necessary permissions
GRANT SELECT ON notification_scheduler_config TO service_role;
GRANT ALL ON notification_scheduler_config TO postgres;

-- Insert the API key configuration (you'll update this value)
INSERT INTO notification_scheduler_config (key, value, description)
VALUES (
    'internal_api_key',
    'Bv7HnVbscOnkk2iiC0WsaAESjd11igJZ3JtYaTb3kqw',
    'Internal API key for authenticating pg_cron scheduled notification jobs'
)
ON CONFLICT (key) DO NOTHING;

-- Add comment for documentation
COMMENT ON TABLE notification_scheduler_config IS 
'Configuration settings for the notification scheduler. Stores the internal API key used by pg_cron jobs. RLS enabled to restrict access to service_role only.';

-- ========================================================================
-- Update existing notification scheduler functions to use config table
-- ========================================================================

-- Update rent reminder function
CREATE OR REPLACE FUNCTION send_rent_reminder_notifications()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  api_url TEXT;
  api_key TEXT;
  response http_response;
BEGIN
  -- Construct API URL (production)
  api_url := 'https://brikli-api-8919-7953fd68-fofj7ysk.onporter.run/api/notifications/scheduled/rent-reminders';
  
  -- Get API key from configuration table
  SELECT value INTO api_key 
  FROM notification_scheduler_config 
  WHERE key = 'internal_api_key';
  
  -- If not found, use default (should be configured after migration)
  IF api_key IS NULL OR api_key = '' THEN
    RAISE WARNING 'API key not configured in notification_scheduler_config table';
    api_key := 'change_me_in_production';
  END IF;
  
  -- Call FastAPI backend to process rent reminders
  SELECT * INTO response
  FROM http((
    'POST',
    api_url,
    ARRAY[
      http_header('Content-Type', 'application/json'),
      http_header('X-Internal-API-Key', api_key)
    ],
    'application/json',
    '{}'
  )::http_request);
  
  -- Log the result
  IF response.status >= 200 AND response.status < 300 THEN
    RAISE NOTICE 'Rent reminder notifications sent successfully: %', response.content;
  ELSE
    RAISE WARNING 'Failed to send rent reminders. Status: %, Response: %', response.status, response.content;
  END IF;
  
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'Failed to send rent reminders: %', SQLERRM;
END;
$$;

-- Update lease expiring function
CREATE OR REPLACE FUNCTION send_lease_expiring_notifications()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  api_url TEXT;
  api_key TEXT;
  response http_response;
BEGIN
  -- Construct API URL (production)
  api_url := 'https://brikli-api-8919-7953fd68-fofj7ysk.onporter.run/api/notifications/scheduled/lease-expiring';
  
  -- Get API key from configuration table
  SELECT value INTO api_key 
  FROM notification_scheduler_config 
  WHERE key = 'internal_api_key';
  
  -- If not found, use default (should be configured after migration)
  IF api_key IS NULL OR api_key = '' THEN
    RAISE WARNING 'API key not configured in notification_scheduler_config table';
    api_key := 'change_me_in_production';
  END IF;
  
  -- Call FastAPI backend to process lease expiring notifications
  SELECT * INTO response
  FROM http((
    'POST',
    api_url,
    ARRAY[
      http_header('Content-Type', 'application/json'),
      http_header('X-Internal-API-Key', api_key)
    ],
    'application/json',
    '{}'
  )::http_request);
  
  -- Log the result
  IF response.status >= 200 AND response.status < 300 THEN
    RAISE NOTICE 'Lease expiring notifications sent successfully: %', response.content;
  ELSE
    RAISE WARNING 'Failed to send lease expiring notifications. Status: %, Response: %', response.status, response.content;
  END IF;
  
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'Failed to send lease expiring notifications: %', SQLERRM;
END;
$$;

-- ========================================================================
-- INSTRUCTIONS:
-- After running this migration, update the API key with this SQL:
-- 
-- UPDATE notification_scheduler_config 
-- SET value = 'Bv7HnVbscOnkk2iiC0WsaAESjd11igJZ3JtYaTb3kqw',
--     updated_at = NOW()
-- WHERE key = 'internal_api_key';
-- ========================================================================

