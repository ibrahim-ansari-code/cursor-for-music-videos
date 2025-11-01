-- ========================================================================
-- Notification Scheduler Setup
-- 
-- This migration sets up scheduled notification jobs using pg_cron.
-- Two daily jobs run at 14:00 UTC (9 AM EST):
-- 1. Rent Reminders - Notify landlords 3 days before rent is due
-- 2. Lease Expiring - Notify landlords 30 and 60 days before lease expiration
-- ========================================================================

-- ========================================================================
-- STEP 1: Enable Required Extensions
-- ========================================================================

-- Enable pg_cron extension for scheduled jobs
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Enable http extension for making HTTP requests to FastAPI
CREATE EXTENSION IF NOT EXISTS http;

-- Grant permissions for pg_cron
GRANT USAGE ON SCHEMA cron TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cron TO postgres;

-- ========================================================================
-- STEP 2: Create PostgreSQL Functions
-- ========================================================================

-- ========================================================================
-- FUNCTION: Send Rent Reminder Notifications
-- Triggered daily at 14:00 UTC (9 AM EST) to notify landlords about upcoming rent payments
-- ========================================================================
CREATE OR REPLACE FUNCTION send_rent_reminder_notifications()
RETURNS void AS $$
DECLARE
  api_url TEXT;
  api_key TEXT;
  response http_response;
BEGIN
  -- Construct API URL (production)
  api_url := 'https://brikli-api-8919-7953fd68-fofj7ysk.onporter.run/api/notifications/scheduled/rent-reminders';
  
  -- Get API key from environment variable or database setting
  -- For production, store in Supabase Vault or as a database setting
  api_key := current_setting('app.settings.internal_api_key', true);
  
  -- If not set in settings, use a default (should be configured in production)
  IF api_key IS NULL OR api_key = '' THEN
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
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ========================================================================
-- FUNCTION: Send Lease Expiring Notifications
-- Triggered daily at 14:00 UTC (9 AM EST) to notify landlords about expiring leases
-- ========================================================================
CREATE OR REPLACE FUNCTION send_lease_expiring_notifications()
RETURNS void AS $$
DECLARE
  api_url TEXT;
  api_key TEXT;
  response http_response;
BEGIN
  -- Construct API URL (production)
  api_url := 'https://brikli-api-8919-7953fd68-fofj7ysk.onporter.run/api/notifications/scheduled/lease-expiring';
  
  -- Get API key from environment variable or database setting
  api_key := current_setting('app.settings.internal_api_key', true);
  
  -- If not set in settings, use a default (should be configured in production)
  IF api_key IS NULL OR api_key = '' THEN
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
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ========================================================================
-- STEP 3: Schedule Daily Notification Jobs
-- ========================================================================

-- Remove existing jobs if they exist (for idempotency)
SELECT cron.unschedule('daily_rent_reminders') WHERE EXISTS (
  SELECT 1 FROM cron.job WHERE jobname = 'daily_rent_reminders'
);

SELECT cron.unschedule('daily_lease_expiring') WHERE EXISTS (
  SELECT 1 FROM cron.job WHERE jobname = 'daily_lease_expiring'
);

-- Schedule rent reminders (14:00 UTC = 9:00 AM EST daily)
SELECT cron.schedule(
  'daily_rent_reminders',
  '0 14 * * *',  -- Every day at 14:00 UTC (9 AM EST / 10 AM EDT)
  $$SELECT send_rent_reminder_notifications();$$
);

-- Schedule lease expiring alerts (14:00 UTC = 9:00 AM EST daily)
SELECT cron.schedule(
  'daily_lease_expiring',
  '0 14 * * *',  -- Every day at 14:00 UTC (9 AM EST / 10 AM EDT)
  $$SELECT send_lease_expiring_notifications();$$
);

-- ========================================================================
-- STEP 4: Add Comments for Documentation
-- ========================================================================

COMMENT ON FUNCTION send_rent_reminder_notifications() IS 
'Scheduled function that calls the FastAPI backend to create rent reminder notifications for landlords. Runs daily at 14:00 UTC (9 AM EST).';

COMMENT ON FUNCTION send_lease_expiring_notifications() IS 
'Scheduled function that calls the FastAPI backend to create lease expiring notifications for landlords. Runs daily at 14:00 UTC (9 AM EST).';

-- ========================================================================
-- DEPLOYMENT NOTES:
-- ========================================================================
-- 
-- After applying this migration:
-- 
-- 1. Set the internal API key in the configuration table:
--    UPDATE notification_scheduler_config 
--    SET value = 'your_secure_key_here'
--    WHERE key = 'internal_api_key';
-- 
-- 2. API URLs are already configured for production
--    (https://brikli-api-8919-7953fd68-fofj7ysk.onporter.run)
-- 
-- 3. Verify jobs are scheduled:
--    SELECT * FROM cron.job;
-- 
-- 4. Monitor job execution:
--    SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 10;
-- 
-- 5. Manually test the jobs (optional):
--    SELECT send_rent_reminder_notifications();
--    SELECT send_lease_expiring_notifications();
-- 
-- ========================================================================

