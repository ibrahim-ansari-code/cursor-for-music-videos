-- Add rent_payment_webhook_logs table for idempotent webhook processing
-- This prevents duplicate processing and provides audit trail

CREATE TABLE IF NOT EXISTS public.rent_payment_webhook_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Stripe event identification
    stripe_event_id VARCHAR(255) NOT NULL UNIQUE,
    event_type VARCHAR(100) NOT NULL,
    api_version VARCHAR(50),
    
    -- Event payload for replay/debugging
    event_data JSONB NOT NULL,
    
    -- Processing state
    processed BOOLEAN NOT NULL DEFAULT false,
    processed_at TIMESTAMPTZ,
    processing_error TEXT,
    
    -- Request tracking for Stripe support
    stripe_request_id VARCHAR(255),
    
    -- Connected account tracking
    stripe_account_id VARCHAR(255),
    
    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_rent_payment_webhook_logs_stripe_event_id 
    ON public.rent_payment_webhook_logs(stripe_event_id);

CREATE INDEX IF NOT EXISTS idx_rent_payment_webhook_logs_event_type 
    ON public.rent_payment_webhook_logs(event_type);

CREATE INDEX IF NOT EXISTS idx_rent_payment_webhook_logs_stripe_account_id 
    ON public.rent_payment_webhook_logs(stripe_account_id);

CREATE INDEX IF NOT EXISTS idx_rent_payment_webhook_logs_created_at 
    ON public.rent_payment_webhook_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_rent_payment_webhook_logs_processed 
    ON public.rent_payment_webhook_logs(processed) 
    WHERE processed = false;

-- Add comment for documentation
COMMENT ON TABLE public.rent_payment_webhook_logs IS 
    'Webhook event log for rent payment webhooks. Ensures idempotent processing and provides audit trail.';

COMMENT ON COLUMN public.rent_payment_webhook_logs.stripe_event_id IS 
    'Unique Stripe event ID (evt_xxx). Used to prevent duplicate processing.';

COMMENT ON COLUMN public.rent_payment_webhook_logs.event_data IS 
    'Full Stripe event object stored as JSONB for replay and debugging.';

COMMENT ON COLUMN public.rent_payment_webhook_logs.processed IS 
    'Whether the event was successfully processed. False indicates pending or failed.';

COMMENT ON COLUMN public.rent_payment_webhook_logs.stripe_account_id IS 
    'Connected account ID for Stripe Connect events.';

