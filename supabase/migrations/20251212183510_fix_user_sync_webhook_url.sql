-- Drop the old trigger with incorrect URL
DROP TRIGGER IF EXISTS "sync-new-users" ON auth.users;

-- Recreate trigger with correct production URL
CREATE TRIGGER "sync-new-users"
  AFTER INSERT OR UPDATE ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION supabase_functions.http_request(
    'https://backend.brikli.com/api/auth/webhook/user-sync',
    'POST',
    '{"Content-type":"application/json","X-Webhook-Secret":"bxJsBl4ure9yQ2tW5ifUYNm1umpVV4GotqWlGUjD7dE"}',
    '{}',
    '5000'
  );

-- Log the fix
DO $$
BEGIN
  RAISE NOTICE 'User sync webhook URL updated to: https://backend.brikli.com/api/auth/webhook/user-sync';
END $$;

