-- Billing Schema Migration
-- Creates billing schema with subscription management tables
-- Following industry-standard patterns for Stripe integration

-- Create billing schema for namespace isolation
CREATE SCHEMA IF NOT EXISTS billing;

-- ============================================================================
-- ALTER TABLE: users (add billing columns FIRST)
-- Purpose: Denormalize subscription status for fast access control checks
-- Note: Must happen before creating tables with FK references to users
-- ============================================================================

-- Add billing columns to users table
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255) UNIQUE;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(50) DEFAULT 'none';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(50) DEFAULT 'free';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS current_period_end TIMESTAMPTZ;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMPTZ;

-- Add column comments
COMMENT ON COLUMN public.users.stripe_customer_id IS 'Stripe Customer ID (cus_xxx) - cached for quick lookups';
COMMENT ON COLUMN public.users.subscription_status IS 'Cached subscription status from billing.user_subscriptions - updated by webhooks';
COMMENT ON COLUMN public.users.subscription_tier IS 'User tier (free, premium) for feature gating';
COMMENT ON COLUMN public.users.current_period_end IS 'Cached from billing.user_subscriptions for quick access checks';
COMMENT ON COLUMN public.users.trial_ends_at IS 'Trial expiration - users retain access until this date';

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_stripe_customer_id ON public.users(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON public.users(subscription_status);
CREATE INDEX IF NOT EXISTS idx_users_trial_ends_at ON public.users(trial_ends_at) WHERE trial_ends_at IS NOT NULL;

-- ============================================================================
-- TABLE: billing.subscription_plans
-- Purpose: Store available subscription plans (enables flexible pricing without code changes)
-- ============================================================================
CREATE TABLE billing.subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL, -- e.g., "Brikli Premium"
    description TEXT,
    stripe_product_id VARCHAR(255) NOT NULL UNIQUE,
    stripe_price_id VARCHAR(255) NOT NULL UNIQUE,
    amount DECIMAL(10, 2) NOT NULL, -- $99.99
    currency VARCHAR(3) NOT NULL DEFAULT 'CAD',
    interval VARCHAR(20) NOT NULL, -- month, year
    interval_count INTEGER NOT NULL DEFAULT 1,
    trial_period_days INTEGER DEFAULT 14,
    is_active BOOLEAN DEFAULT TRUE,
    features JSONB DEFAULT '[]'::jsonb, -- Array of feature descriptions
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_amount CHECK (amount >= 0),
    CONSTRAINT valid_interval CHECK (interval IN ('day', 'week', 'month', 'year')),
    CONSTRAINT valid_interval_count CHECK (interval_count > 0)
);

COMMENT ON TABLE billing.subscription_plans IS 'Available subscription plans with Stripe product/price mappings';
COMMENT ON COLUMN billing.subscription_plans.stripe_product_id IS 'Stripe Product ID (prod_xxx)';
COMMENT ON COLUMN billing.subscription_plans.stripe_price_id IS 'Stripe Price ID (price_xxx)';
COMMENT ON COLUMN billing.subscription_plans.features IS 'JSON array of feature strings for display';

-- ============================================================================
-- TABLE: billing.user_subscriptions
-- Purpose: Track user subscription state with full Stripe metadata
-- ============================================================================
CREATE TABLE billing.user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES billing.subscription_plans(id),
    
    -- Stripe references
    stripe_customer_id VARCHAR(255) NOT NULL,
    stripe_subscription_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Subscription state
    status VARCHAR(50) NOT NULL, -- active, canceled, past_due, trialing, incomplete, incomplete_expired, unpaid
    
    -- Billing periods
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    
    -- Cancellation tracking
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_status CHECK (
        status IN ('active', 'canceled', 'past_due', 'trialing', 'incomplete', 'incomplete_expired', 'unpaid')
    )
);

COMMENT ON TABLE billing.user_subscriptions IS 'User subscription records synced from Stripe';
COMMENT ON COLUMN billing.user_subscriptions.status IS 'Stripe subscription status - source of truth';
COMMENT ON COLUMN billing.user_subscriptions.cancel_at_period_end IS 'If true, subscription cancels at period end (user retains access until then)';

-- Indexes for performance
CREATE INDEX idx_user_subscriptions_user_id ON billing.user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_stripe_customer_id ON billing.user_subscriptions(stripe_customer_id);
CREATE INDEX idx_user_subscriptions_stripe_subscription_id ON billing.user_subscriptions(stripe_subscription_id);
CREATE INDEX idx_user_subscriptions_status ON billing.user_subscriptions(status);
CREATE INDEX idx_user_subscriptions_current_period_end ON billing.user_subscriptions(current_period_end);

-- ============================================================================
-- TABLE: billing.stripe_event_logs
-- Purpose: Store all Stripe webhook events for idempotent processing
-- ============================================================================
CREATE TABLE billing.stripe_event_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stripe_event_id VARCHAR(255) UNIQUE NOT NULL, -- evt_xxx (used for deduplication)
    event_type VARCHAR(100) NOT NULL, -- customer.subscription.created, etc.
    api_version VARCHAR(50),
    
    -- Event payload
    event_data JSONB NOT NULL, -- Full Stripe event object
    
    -- Processing state
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    processing_error TEXT,
    
    -- Request tracking
    stripe_request_id VARCHAR(255), -- For Stripe support tickets
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT stripe_event_id_format CHECK (stripe_event_id ~ '^evt_')
);

COMMENT ON TABLE billing.stripe_event_logs IS 'Stripe webhook event log for idempotent processing and audit trail';
COMMENT ON COLUMN billing.stripe_event_logs.stripe_event_id IS 'Unique Stripe event ID - prevents duplicate processing';
COMMENT ON COLUMN billing.stripe_event_logs.stripe_request_id IS 'Stripe-Request-Id header for support correlation';

-- Indexes for webhook processing
CREATE INDEX idx_stripe_event_logs_stripe_event_id ON billing.stripe_event_logs(stripe_event_id);
CREATE INDEX idx_stripe_event_logs_event_type ON billing.stripe_event_logs(event_type);
CREATE INDEX idx_stripe_event_logs_processed ON billing.stripe_event_logs(processed);
CREATE INDEX idx_stripe_event_logs_created_at ON billing.stripe_event_logs(created_at DESC);

-- ============================================================================
-- TABLE: billing.billing_audit_logs
-- Purpose: Business-level audit trail for billing operations
-- ============================================================================
CREATE TABLE billing.billing_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    subscription_id UUID REFERENCES billing.user_subscriptions(id) ON DELETE SET NULL,
    
    -- Action tracking
    action VARCHAR(100) NOT NULL, -- subscription_created, payment_succeeded, subscription_canceled, etc.
    actor VARCHAR(50), -- system, user, admin, stripe_webhook
    
    -- Context
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Financial tracking (for reconciliation)
    amount DECIMAL(10, 2),
    currency VARCHAR(3),
    
    -- Source tracking
    stripe_event_id VARCHAR(255), -- Links to stripe_event_logs if applicable
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE billing.billing_audit_logs IS 'Business-level audit trail for all billing operations';
COMMENT ON COLUMN billing.billing_audit_logs.actor IS 'Who/what initiated the action (system, user, admin, webhook)';
COMMENT ON COLUMN billing.billing_audit_logs.stripe_event_id IS 'Optional link to stripe_event_logs for webhook-triggered actions';

-- Indexes for audit queries
CREATE INDEX idx_billing_audit_logs_user_id ON billing.billing_audit_logs(user_id);
CREATE INDEX idx_billing_audit_logs_subscription_id ON billing.billing_audit_logs(subscription_id);
CREATE INDEX idx_billing_audit_logs_action ON billing.billing_audit_logs(action);
CREATE INDEX idx_billing_audit_logs_created_at ON billing.billing_audit_logs(created_at DESC);

-- ============================================================================
-- FUNCTION: update_user_subscription_cache
-- Purpose: Sync denormalized user fields from user_subscriptions table
-- Note: user columns were already added at the beginning of this migration
-- ============================================================================
CREATE OR REPLACE FUNCTION billing.update_user_subscription_cache()
RETURNS TRIGGER AS $$
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
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION billing.update_user_subscription_cache IS 'Trigger function to keep user subscription cache in sync';

-- Create trigger for INSERT or UPDATE
DROP TRIGGER IF EXISTS trigger_update_user_subscription_cache_upsert ON billing.user_subscriptions;
CREATE TRIGGER trigger_update_user_subscription_cache_upsert
    AFTER INSERT OR UPDATE ON billing.user_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION billing.update_user_subscription_cache();

-- ============================================================================
-- FUNCTION: clear_user_subscription_cache
-- Purpose: Reset user subscription cache when subscription is deleted
-- ============================================================================
CREATE OR REPLACE FUNCTION billing.clear_user_subscription_cache()
RETURNS TRIGGER AS $$
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
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION billing.clear_user_subscription_cache IS 'Trigger function to reset user subscription cache on DELETE';

-- Create trigger for DELETE
DROP TRIGGER IF EXISTS trigger_update_user_subscription_cache_delete ON billing.user_subscriptions;
CREATE TRIGGER trigger_update_user_subscription_cache_delete
    AFTER DELETE ON billing.user_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION billing.clear_user_subscription_cache();

-- ============================================================================
-- FUNCTION: update_updated_at_column
-- Purpose: Auto-update updated_at timestamps
-- ============================================================================
CREATE OR REPLACE FUNCTION billing.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to tables with updated_at
CREATE TRIGGER trigger_subscription_plans_updated_at
    BEFORE UPDATE ON billing.subscription_plans
    FOR EACH ROW
    EXECUTE FUNCTION billing.update_updated_at_column();

CREATE TRIGGER trigger_user_subscriptions_updated_at
    BEFORE UPDATE ON billing.user_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION billing.update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- Purpose: Tenant isolation - users can only see their own subscriptions
-- ============================================================================

-- Enable RLS on user-facing tables
ALTER TABLE billing.user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing.billing_audit_logs ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own subscriptions
CREATE POLICY user_subscriptions_select_own
    ON billing.user_subscriptions
    FOR SELECT
    USING (user_id = auth.uid());

-- Policy: Users can view their own audit logs
CREATE POLICY billing_audit_logs_select_own
    ON billing.billing_audit_logs
    FOR SELECT
    USING (user_id = auth.uid());

-- Service role has full access (for backend operations)
-- This is handled by Supabase automatically for service_role

-- ============================================================================
-- Note: Subscription plans will be created via backend after Stripe product setup
-- ============================================================================

