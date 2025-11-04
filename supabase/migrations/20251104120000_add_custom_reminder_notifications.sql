-- ========================================================================
-- Custom Reminder Notifications Enhancement
-- 
-- Adds notification tracking to custom_reminders table to support
-- scheduled notification delivery with deduplication.
-- ========================================================================

-- ========================================================================
-- STEP 1: Add Notification Tracking Columns
-- ========================================================================

ALTER TABLE custom_reminders 
ADD COLUMN IF NOT EXISTS notified_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS notification_id UUID REFERENCES notifications(id) ON DELETE SET NULL;

COMMENT ON COLUMN custom_reminders.notified_at IS 'Timestamp when notification was sent (prevents duplicates)';
COMMENT ON COLUMN custom_reminders.notification_id IS 'Reference to created notification record';

-- ========================================================================
-- STEP 2: Create Indexes for Efficient Queries
-- ========================================================================

-- Index optimized for the notification check query
-- Covers: WHERE is_completed = FALSE AND notified_at IS NULL
CREATE INDEX IF NOT EXISTS idx_custom_reminders_notification_check 
ON custom_reminders(reminder_date, notify_before_hours, is_completed, notified_at)
WHERE is_completed = FALSE AND notified_at IS NULL;

COMMENT ON INDEX idx_custom_reminders_notification_check IS 'Optimizes queries for finding reminders that need notifications';

-- Index optimized for calendar event queries by user
-- Covers: WHERE user_id = ? AND reminder_date BETWEEN ? AND ? AND is_completed = FALSE
CREATE INDEX IF NOT EXISTS idx_custom_reminders_user_date
ON custom_reminders(user_id, reminder_date)
WHERE is_completed = FALSE;

COMMENT ON INDEX idx_custom_reminders_user_date IS 'Optimizes calendar queries for fetching user reminders by date range';

-- ========================================================================
-- STEP 3: Create PostgreSQL Function for Cron Job
-- ========================================================================

CREATE OR REPLACE FUNCTION check_custom_reminder_notifications()
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
  -- Get API URL from configuration table (or use production default)
  SELECT value INTO api_url 
  FROM notification_scheduler_config 
  WHERE key = 'api_url';
  
  -- Default to production URL if not configured
  IF api_url IS NULL OR api_url = '' THEN
    api_url := 'https://brikli-api-8919-7953fd68-fofj7ysk.onporter.run';
  END IF;
  
  -- Append the endpoint path
  api_url := api_url || '/api/notifications/scheduled/reminders';
  
  -- Get API key from configuration table
  SELECT value INTO api_key 
  FROM notification_scheduler_config 
  WHERE key = 'internal_api_key';

  -- Validate API key is configured
  IF api_key IS NULL OR api_key = '' THEN
    RAISE WARNING 'API key not configured in notification_scheduler_config table';
    RETURN;
  END IF;

  -- Make HTTP POST request to FastAPI endpoint
  response := http((
    'POST',
    api_url,
    ARRAY[http_header('Content-Type', 'application/json'), 
          http_header('X-Internal-API-Key', api_key)],
    'application/json',
    '{}'
  )::http_request);

  -- Log the response
  RAISE NOTICE 'Custom reminder notifications response: % %', response.status, response.content;

  -- Raise exception if request failed
  IF response.status NOT BETWEEN 200 AND 299 THEN
    RAISE EXCEPTION 'Failed to trigger reminder notifications: % %', 
      response.status, response.content;
  END IF;

EXCEPTION
  WHEN OTHERS THEN
    -- Log error but don't fail the cron job
    RAISE WARNING 'Error in check_custom_reminder_notifications: %', SQLERRM;
END;
$$;

COMMENT ON FUNCTION check_custom_reminder_notifications() IS 'Called by pg_cron to trigger custom reminder notifications via FastAPI. Reads configuration from notification_scheduler_config table.';

-- ========================================================================
-- STEP 4: Schedule Cron Job (Idempotent)
-- ========================================================================

-- Schedule the job to run every 15 minutes
-- Cron schedule: "0,15,30,45 * * * *" = Every 15 minutes
-- This provides good balance between timely notifications and system load

-- Unschedule if exists, then schedule (idempotent)
DO $$
BEGIN
  -- Check if job exists and unschedule it
  IF EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'custom-reminder-notifications') THEN
    PERFORM cron.unschedule('custom-reminder-notifications');
  END IF;
END
$$;

SELECT cron.schedule(
  'custom-reminder-notifications',     -- Job name
  '0,15,30,45 * * * *',                -- Every 15 minutes
  'SELECT check_custom_reminder_notifications()'
);

-- ========================================================================
-- STEP 5: Configure API Settings
-- ========================================================================

-- The cron job reads configuration from the notification_scheduler_config table.
-- This table is created by migration 20251031235900_add_cron_config_table.sql
--
-- Required settings:
-- 1. internal_api_key - Already configured by the earlier migration
-- 2. api_url (optional) - Defaults to production URL if not set
--
-- To update the API URL for production:
--   INSERT INTO notification_scheduler_config (key, value, description)
--   VALUES ('api_url', 'https://brikli-api-8919-7953fd68-fofj7ysk.onporter.run', 'Base API URL for notification endpoints')
--   ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();
--
-- IMPORTANT: The internal API key must also be set in your backend .env file:
--   INTERNAL_CRON_API_KEY=<same-value-as-in-notification_scheduler_config>

-- ========================================================================
-- STEP 6: Verify Installation
-- ========================================================================

-- Query to check if cron job was created successfully
-- Run: SELECT * FROM cron.job WHERE jobname = 'custom-reminder-notifications';

-- Verify configuration settings are set:
-- SELECT current_setting('app.settings.api_url', true) as api_url,
--        CASE
--          WHEN current_setting('app.settings.internal_api_key', true) IS NOT NULL
--          THEN '***configured***'
--          ELSE 'NOT SET'
--        END as api_key_status;

-- To manually trigger the job for testing:
-- SELECT check_custom_reminder_notifications();

-- To check job execution history:
-- SELECT * FROM cron.job_run_details 
-- WHERE jobid = (SELECT jobid FROM cron.job WHERE jobname = 'custom-reminder-notifications')
-- ORDER BY start_time DESC LIMIT 10;

-- ========================================================================
-- ROLLBACK INSTRUCTIONS
-- ========================================================================

-- To remove the cron job:
-- SELECT cron.unschedule('custom-reminder-notifications');

-- To drop the function:
-- DROP FUNCTION IF EXISTS check_custom_reminder_notifications();

-- To remove the indexes:
-- DROP INDEX IF EXISTS idx_custom_reminders_notification_check;
-- DROP INDEX IF EXISTS idx_custom_reminders_user_date;

-- To remove the columns (CAUTION: data loss):
-- ALTER TABLE custom_reminders 
-- DROP COLUMN IF EXISTS notified_at,
-- DROP COLUMN IF EXISTS notification_id;

