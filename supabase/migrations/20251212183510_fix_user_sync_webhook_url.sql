-- Enable pg_net extension for HTTP requests
CREATE EXTENSION IF NOT EXISTS pg_net;

-- Drop the old trigger and function if they exist
DROP TRIGGER IF EXISTS "sync-new-users" ON auth.users;
DROP FUNCTION IF EXISTS handle_user_sync_webhook CASCADE;

-- Create function to handle user sync webhook
CREATE OR REPLACE FUNCTION handle_user_sync_webhook()
RETURNS TRIGGER AS $$
BEGIN
  -- Make async HTTP request to backend
  PERFORM net.http_post(
    url := 'https://backend.brikli.com/api/auth/webhook/user-sync',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Webhook-Secret', 'bxJsBl4ure9yQ2tW5ifUYNm1umpVV4GotqWlGUjD7dE'
    ),
    body := jsonb_build_object(
      'type', TG_OP,
      'record', row_to_json(NEW),
      'old_record', CASE WHEN TG_OP = 'UPDATE' THEN row_to_json(OLD) ELSE NULL END
    ),
    timeout_milliseconds := 5000
  );
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger using the function
CREATE TRIGGER "sync-new-users"
  AFTER INSERT OR UPDATE ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION handle_user_sync_webhook();

-- Log the fix
DO $$
BEGIN
  RAISE NOTICE 'User sync webhook URL updated to: https://backend.brikli.com/api/auth/webhook/user-sync';
END $$;

