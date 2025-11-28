-- Migration: Fix Function Search Path Security
-- Description: Set search_path = '' on all functions to prevent security vulnerabilities
-- Related: Supabase Security Advisor - Function Search Path Mutable warnings
-- Reference: https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable

-- =====================================================================
-- BILLING SCHEMA FUNCTIONS
-- =====================================================================

-- Fix: billing.clear_user_subscription_cache
CREATE OR REPLACE FUNCTION billing.clear_user_subscription_cache()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $function$
BEGIN
    UPDATE public.users
    SET
        subscription_status = 'none',
        subscription_tier = 'free',
        current_period_end = NULL,
        trial_ends_at = NULL,
        updated_at = NOW()
    WHERE id = OLD.user_id;
    
    RETURN OLD;
END;
$function$;

-- Fix: billing.update_user_subscription_cache
CREATE OR REPLACE FUNCTION billing.update_user_subscription_cache()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $function$
BEGIN
    -- Update user table with latest subscription data
    UPDATE public.users
    SET 
        subscription_status = NEW.status,
        subscription_tier = CASE 
            WHEN NEW.status IN ('active', 'trialing') THEN 'premium'
            ELSE 'free'
        END,
        current_period_end = NEW.current_period_end,
        trial_ends_at = NEW.trial_end,
        updated_at = NOW()
    WHERE id = NEW.user_id;
    
    RETURN NEW;
END;
$function$;

-- Fix: billing.update_updated_at_column
CREATE OR REPLACE FUNCTION billing.update_updated_at_column()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$;

-- =====================================================================
-- PUBLIC SCHEMA FUNCTIONS
-- =====================================================================

-- Fix: public.get_invoice_amount_paid
CREATE OR REPLACE FUNCTION public.get_invoice_amount_paid(invoice_id_param integer)
RETURNS numeric
LANGUAGE sql
STABLE
SET search_path = ''
AS $function$
  SELECT COALESCE(SUM(amount_applied), 0)
  FROM public.payment_allocations
  WHERE invoice_id = invoice_id_param;
$function$;

-- Fix: public.get_invoice_amount_due
CREATE OR REPLACE FUNCTION public.get_invoice_amount_due(invoice_id_param integer)
RETURNS numeric
LANGUAGE sql
STABLE
SET search_path = ''
AS $function$
  SELECT i.amount - COALESCE(
    (SELECT SUM(amount_applied) FROM public.payment_allocations WHERE invoice_id = invoice_id_param),
    0
  )
  FROM public.invoices i
  WHERE i.id = invoice_id_param;
$function$;

-- Fix: public.is_invoice_fully_paid
CREATE OR REPLACE FUNCTION public.is_invoice_fully_paid(invoice_id_param integer)
RETURNS boolean
LANGUAGE sql
STABLE
SET search_path = ''
AS $function$
  SELECT COALESCE(public.get_invoice_amount_due(invoice_id_param) <= 0, false);
$function$;

-- Fix: public.update_invoice_status_from_allocations
CREATE OR REPLACE FUNCTION public.update_invoice_status_from_allocations()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $function$
DECLARE
  v_invoice_id INTEGER;
  v_invoice_amount NUMERIC;
  v_total_paid NUMERIC;
  v_amount_due NUMERIC;
BEGIN
  -- Get the invoice_id from the trigger (works for INSERT, UPDATE, DELETE)
  IF TG_OP = 'DELETE' THEN
    v_invoice_id := OLD.invoice_id;
  ELSE
    v_invoice_id := NEW.invoice_id;
  END IF;

  -- Get invoice amount and total paid
  SELECT i.amount, COALESCE(SUM(pa.amount_applied), 0)
  INTO v_invoice_amount, v_total_paid
  FROM public.invoices i
  LEFT JOIN public.payment_allocations pa ON pa.invoice_id = i.id
  WHERE i.id = v_invoice_id
  GROUP BY i.amount;

  -- Calculate amount due
  v_amount_due := v_invoice_amount - v_total_paid;

  -- Update invoice status based on payment
  IF v_amount_due <= 0 THEN
    -- Fully paid
    UPDATE public.invoices SET status = 'Paid', updated_at = now() WHERE id = v_invoice_id;
  ELSIF v_total_paid > 0 AND v_amount_due > 0 THEN
    -- Partially paid
    UPDATE public.invoices SET status = 'Partial', updated_at = now() WHERE id = v_invoice_id;
  -- If no payments and status is currently Paid or Partial, revert to Pending
  ELSIF v_total_paid = 0 THEN
    UPDATE public.invoices
    SET status = 'Pending', updated_at = now()
    WHERE id = v_invoice_id
      AND status IN ('Paid', 'Partial');
  END IF;

  RETURN COALESCE(NEW, OLD);
END;
$function$;

-- =====================================================================
-- RLS POLICY PERFORMANCE OPTIMIZATION
-- =====================================================================
-- Fix: Wrap auth.uid() and auth.role() in subqueries to prevent per-row re-evaluation
-- Related: Supabase Performance Advisor - Auth RLS Initialization Plan warnings
-- Performance impact: Up to 1000x fewer function calls on large result sets

-- Fix: billing.user_subscriptions - SELECT policy
DROP POLICY IF EXISTS "user_subscriptions_select_own" ON billing.user_subscriptions;
CREATE POLICY "user_subscriptions_select_own" ON billing.user_subscriptions
    FOR SELECT
    TO public
    USING (user_id = (select auth.uid()));

-- Fix: billing.billing_audit_logs - SELECT policy
DROP POLICY IF EXISTS "billing_audit_logs_select_own" ON billing.billing_audit_logs;
CREATE POLICY "billing_audit_logs_select_own" ON billing.billing_audit_logs
    FOR SELECT
    TO public
    USING (user_id = (select auth.uid()));

-- Fix: public.payment_allocations - All 4 policies
DROP POLICY IF EXISTS "payment_allocations_select_policy" ON public.payment_allocations;
CREATE POLICY "payment_allocations_select_policy" ON public.payment_allocations
    FOR SELECT
    TO public
    USING (
        EXISTS (
            SELECT 1
            FROM public.payments p
            WHERE p.id = payment_allocations.payment_id 
              AND p.user_id = (select auth.uid())
        )
    );

DROP POLICY IF EXISTS "payment_allocations_insert_policy" ON public.payment_allocations;
CREATE POLICY "payment_allocations_insert_policy" ON public.payment_allocations
    FOR INSERT
    TO public
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM public.payments p
            WHERE p.id = payment_allocations.payment_id 
              AND p.user_id = (select auth.uid())
        )
    );

DROP POLICY IF EXISTS "payment_allocations_update_policy" ON public.payment_allocations;
CREATE POLICY "payment_allocations_update_policy" ON public.payment_allocations
    FOR UPDATE
    TO public
    USING (
        EXISTS (
            SELECT 1
            FROM public.payments p
            WHERE p.id = payment_allocations.payment_id 
              AND p.user_id = (select auth.uid())
        )
    );

DROP POLICY IF EXISTS "payment_allocations_delete_policy" ON public.payment_allocations;
CREATE POLICY "payment_allocations_delete_policy" ON public.payment_allocations
    FOR DELETE
    TO public
    USING (
        EXISTS (
            SELECT 1
            FROM public.payments p
            WHERE p.id = payment_allocations.payment_id 
              AND p.user_id = (select auth.uid())
        )
    );

-- Fix: public.user_vendors - All 4 policies
DROP POLICY IF EXISTS "Users can view their own vendor associations" ON public.user_vendors;
CREATE POLICY "Users can view their own vendor associations" ON public.user_vendors
    FOR SELECT
    TO public
    USING ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can create their own vendor associations" ON public.user_vendors;
CREATE POLICY "Users can create their own vendor associations" ON public.user_vendors
    FOR INSERT
    TO public
    WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can update their own vendor associations" ON public.user_vendors;
CREATE POLICY "Users can update their own vendor associations" ON public.user_vendors
    FOR UPDATE
    TO public
    USING ((select auth.uid()) = user_id)
    WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can delete their own vendor associations" ON public.user_vendors;
CREATE POLICY "Users can delete their own vendor associations" ON public.user_vendors
    FOR DELETE
    TO public
    USING ((select auth.uid()) = user_id);

-- Fix: public.vendors - All 4 policies
DROP POLICY IF EXISTS "Authenticated users can view vendors" ON public.vendors;
CREATE POLICY "Authenticated users can view vendors" ON public.vendors
    FOR SELECT
    TO public
    USING ((select auth.role()) = 'authenticated');

DROP POLICY IF EXISTS "Service role can insert vendors" ON public.vendors;
CREATE POLICY "Service role can insert vendors" ON public.vendors
    FOR INSERT
    TO public
    WITH CHECK ((select auth.role()) = 'service_role' OR (select auth.role()) = 'authenticated');

DROP POLICY IF EXISTS "Service role can update vendors" ON public.vendors;
CREATE POLICY "Service role can update vendors" ON public.vendors
    FOR UPDATE
    TO public
    USING ((select auth.role()) = 'service_role' OR (select auth.role()) = 'authenticated');

DROP POLICY IF EXISTS "Service role can delete vendors" ON public.vendors;
CREATE POLICY "Service role can delete vendors" ON public.vendors
    FOR DELETE
    TO public
    USING ((select auth.role()) = 'service_role');

-- Fix: public.webhook_audit_logs - SELECT policy
DROP POLICY IF EXISTS "Admins can view all webhook audit logs" ON public.webhook_audit_logs;
CREATE POLICY "Admins can view all webhook audit logs" ON public.webhook_audit_logs
    FOR SELECT
    TO public
    USING (
        EXISTS (
            SELECT 1
            FROM public.users
            WHERE users.id = (select auth.uid())
              AND users.is_admin = true 
              AND users.is_active = true
        )
    );

-- =====================================================================
-- VERIFICATION
-- =====================================================================

-- Verify all functions now have search_path set
-- Run this query to confirm:
-- SELECT 
--   n.nspname as schema,
--   p.proname as function_name,
--   pg_get_function_identity_arguments(p.oid) as arguments,
--   CASE 
--     WHEN pg_catalog.array_to_string(p.proconfig, ', ') LIKE '%search_path%' 
--     THEN '✅ SET' 
--     ELSE '❌ NOT SET' 
--   END as search_path_status
-- FROM pg_proc p
-- JOIN pg_namespace n ON p.pronamespace = n.oid
-- WHERE p.proname IN (
--     'clear_user_subscription_cache',
--     'update_user_subscription_cache', 
--     'update_updated_at_column',
--     'get_invoice_amount_paid',
--     'get_invoice_amount_due',
--     'is_invoice_fully_paid',
--     'update_invoice_status_from_allocations'
-- )
-- AND n.nspname IN ('public', 'billing')
-- ORDER BY n.nspname, p.proname;

