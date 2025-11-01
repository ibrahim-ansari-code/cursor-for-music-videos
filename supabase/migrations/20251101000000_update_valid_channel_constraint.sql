-- Add 'test_endpoint' to valid_channel constraint for rate limiting
-- This allows the notification_delivery_log table to track test endpoint rate limits

ALTER TABLE public.notification_delivery_log 
DROP CONSTRAINT IF EXISTS valid_channel;

ALTER TABLE public.notification_delivery_log 
ADD CONSTRAINT valid_channel CHECK (channel IN ('in_app', 'email', 'sms', 'test_endpoint'));

-- Add comment for clarity
COMMENT ON CONSTRAINT valid_channel ON public.notification_delivery_log IS 
'Validates notification delivery channel. test_endpoint is used for tracking test email/notification rate limits.';

