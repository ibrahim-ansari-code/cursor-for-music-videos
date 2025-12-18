-- ========================================================================
-- Autopay Scheduler Setup
-- 
-- This migration sets up the scheduled autopay job using pg_cron.
-- Runs daily at 08:00 UTC (3 AM EST) to process autopay enrollments.
-- 
-- The job:
-- - Finds all active autopay enrollments due for payment
-- - Creates and confirms Stripe PaymentIntents
-- - Handles retries for failed payments (1, 3, 7 days)
-- - Sends email notifications (success/failure)
-- - Pauses enrollments after max retries
-- ========================================================================

-- ========================================================================
-- Create PostgreSQL Function
-- ========================================================================
CREATE OR REPLACE FUNCTION process_daily_autopay()
RETURNS void AS $$
DECLARE
  api_url TEXT;
  api_key TEXT;
  response http_response;
BEGIN
  -- Construct API URL (production)
  api_url := 'https://backend.brikli.com/api/rent-payments/scheduled/process-autopay';
  
  -- Get API key from environment variable or database setting
  api_key := current_setting('app.settings.internal_api_key', true);
  
  -- If not set in settings, use a default (should be configured in production)
  IF api_key IS NULL OR api_key = '' THEN
    api_key := 'change_me_in_production';
  END IF;
  
  -- Call FastAPI backend to process autopay
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
    RAISE NOTICE 'Autopay processing completed successfully: %', response.content;
  ELSE
    RAISE WARNING 'Failed to process autopay. Status: %, Response: %', response.status, response.content;
  END IF;
  
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'Failed to process autopay: %', SQLERRM;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ========================================================================
-- Schedule Daily Autopay Job
-- ========================================================================

-- Remove existing job if it exists (for idempotency)
SELECT cron.unschedule('daily_autopay_processing') WHERE EXISTS (
  SELECT 1 FROM cron.job WHERE jobname = 'daily_autopay_processing'
);

-- Schedule autopay processing (08:00 UTC = 3:00 AM EST daily)
SELECT cron.schedule(
  'daily_autopay_processing',
  '0 8 * * *',
  $$SELECT process_daily_autopay();$$
);

-- Add documentation
COMMENT ON FUNCTION process_daily_autopay() IS 
'Scheduled function that calls the FastAPI backend to process daily autopay enrollments. 
Handles payment creation, retries (1, 3, 7 days), and email notifications. 
Runs daily at 08:00 UTC (3 AM EST).';

-- ========================================================================
-- DEPLOYMENT NOTES:
-- ========================================================================
-- 
-- After applying this migration:
-- 
-- 1. The internal API key should already be set from notification scheduler
--    If not, set it in the configuration:
--    ALTER DATABASE postgres SET app.settings.internal_api_key = 'your_secure_key_here';
-- 
-- 2. API URL is already configured for production
--    (https://backend.brikli.com)
-- 
-- 3. Verify job is scheduled:
--    SELECT jobname, schedule, active, nodename 
--    FROM cron.job 
--    WHERE jobname = 'daily_autopay_processing';
-- 
-- 4. Monitor job execution:
--    SELECT * FROM cron.job_run_details 
--    WHERE command LIKE '%process_daily_autopay%'
--    ORDER BY start_time DESC 
--    LIMIT 10;
-- 
-- 5. Manually test the job (optional):
--    SELECT process_daily_autopay();
-- 
-- 6. Check autopay enrollments that will be processed:
--    SELECT id, tenant_id, lease_id, is_active, next_scheduled_at, 
--           current_retry_count, last_attempt_at
--    FROM rent_autopay_enrollments
--    WHERE is_active = true 
--      AND next_scheduled_at <= CURRENT_DATE
--    ORDER BY next_scheduled_at;
-- 
-- 7. Processing Logic:
--    - Finds active enrollments with next_scheduled_at <= today
--    - Creates Stripe PaymentIntent with off_session=true
--    - On success: schedules next payment for next month
--    - On failure: retries after 1, 3, then 7 days
--    - After max retries: pauses enrollment and notifies tenant
-- 
-- ========================================================================
