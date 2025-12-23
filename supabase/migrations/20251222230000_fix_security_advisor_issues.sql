-- Migration: Fix Security Advisor Issues
-- 1. Enable RLS on tables missing it
-- 2. Fix function search_path vulnerabilities

-- =============================================================================
-- 1. ENABLE RLS ON MISSING TABLES
-- =============================================================================

-- Enable RLS on rent_payment_refunds
ALTER TABLE public.rent_payment_refunds ENABLE ROW LEVEL SECURITY;

-- Enable RLS on rent_payment_disputes
ALTER TABLE public.rent_payment_disputes ENABLE ROW LEVEL SECURITY;

-- Enable RLS on rent_payment_webhook_logs
ALTER TABLE public.rent_payment_webhook_logs ENABLE ROW LEVEL SECURITY;

-- Enable RLS on tenant_portal_seat_subscriptions
ALTER TABLE public.tenant_portal_seat_subscriptions ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- 2. RLS POLICIES FOR rent_payment_refunds
-- =============================================================================

-- Landlords can view refunds for their transactions
CREATE POLICY "Landlords can view their refunds"
ON public.rent_payment_refunds
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.rent_payment_transactions t
    WHERE t.id = rent_payment_refunds.transaction_id
    AND t.landlord_user_id = auth.uid()
  )
);

-- Tenants can view refunds for their transactions
CREATE POLICY "Tenants can view their refunds"
ON public.rent_payment_refunds
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.rent_payment_transactions t
    WHERE t.id = rent_payment_refunds.transaction_id
    AND t.tenant_id IN (
      SELECT id FROM public.tenants WHERE user_id = auth.uid()
    )
  )
);

-- Service role can do everything (for backend operations)
CREATE POLICY "Service role full access to refunds"
ON public.rent_payment_refunds
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- =============================================================================
-- 3. RLS POLICIES FOR rent_payment_disputes
-- =============================================================================

-- Landlords can view disputes for their transactions
CREATE POLICY "Landlords can view their disputes"
ON public.rent_payment_disputes
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.rent_payment_transactions t
    WHERE t.id = rent_payment_disputes.transaction_id
    AND t.landlord_user_id = auth.uid()
  )
);

-- Tenants can view disputes for their transactions
CREATE POLICY "Tenants can view their disputes"
ON public.rent_payment_disputes
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.rent_payment_transactions t
    WHERE t.id = rent_payment_disputes.transaction_id
    AND t.tenant_id IN (
      SELECT id FROM public.tenants WHERE user_id = auth.uid()
    )
  )
);

-- Service role can do everything (for backend operations)
CREATE POLICY "Service role full access to disputes"
ON public.rent_payment_disputes
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- =============================================================================
-- 4. RLS POLICIES FOR rent_payment_webhook_logs
-- =============================================================================

-- Webhook logs are internal - only service role should access
CREATE POLICY "Service role full access to webhook logs"
ON public.rent_payment_webhook_logs
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- No access for regular authenticated users (webhook logs are internal)

-- =============================================================================
-- 5. RLS POLICIES FOR tenant_portal_seat_subscriptions
-- =============================================================================

-- Landlords can view their own seat subscriptions
CREATE POLICY "Landlords can view their seat subscriptions"
ON public.tenant_portal_seat_subscriptions
FOR SELECT
TO authenticated
USING (landlord_user_id = auth.uid());

-- Service role can do everything
CREATE POLICY "Service role full access to seat subscriptions"
ON public.tenant_portal_seat_subscriptions
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- =============================================================================
-- 6. FIX FUNCTION SEARCH_PATH VULNERABILITIES
-- =============================================================================

-- Fix get_tenant_portal_seat_usage
CREATE OR REPLACE FUNCTION public.get_tenant_portal_seat_usage(landlord_uuid uuid)
RETURNS TABLE(limit_seats integer, used_seats bigint, available_seats integer)
LANGUAGE plpgsql
STABLE
SET search_path = public
AS $function$
BEGIN
  RETURN QUERY
  SELECT
    u.tenant_portal_seat_limit as limit_seats,
    COUNT(t.id) FILTER (WHERE t.user_id IS NOT NULL) as used_seats,
    GREATEST(0, u.tenant_portal_seat_limit - COUNT(t.id) FILTER (WHERE t.user_id IS NOT NULL)::INTEGER) as available_seats
  FROM users u
  LEFT JOIN tenants t ON t.landlord_id = u.id
  WHERE u.id = landlord_uuid
  GROUP BY u.id, u.tenant_portal_seat_limit;
END;
$function$;

-- Fix update_rent_payment_updated_at
CREATE OR REPLACE FUNCTION public.update_rent_payment_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$;

-- Fix process_daily_autopay
CREATE OR REPLACE FUNCTION public.process_daily_autopay()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $function$
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
$function$;
