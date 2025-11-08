-- Add webhook audit logs table for tracking all webhook requests
-- This migration adds comprehensive webhook monitoring and audit trail capabilities

CREATE TABLE IF NOT EXISTS public.webhook_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Webhook identification
    webhook_type TEXT NOT NULL,  -- e.g., "user_sync"
    event_type TEXT NOT NULL,  -- e.g., "INSERT", "UPDATE"
    
    -- Request details
    source_ip TEXT,
    user_agent TEXT,
    
    -- Payload information
    table_name TEXT NOT NULL,  -- e.g., "auth.users"
    record_id TEXT,  -- User ID or record ID
    record_email TEXT,  -- Email for user webhooks
    
    -- Processing results
    success BOOLEAN NOT NULL DEFAULT TRUE,
    action_taken TEXT,  -- e.g., "created", "updated", "linked", "idempotent", "error"
    error_message TEXT,
    error_type TEXT,
    
    -- Performance tracking
    processing_time_ms DOUBLE PRECISION,  -- Processing duration in milliseconds
    
    -- Audit trail
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_webhook_audit_logs_webhook_type ON public.webhook_audit_logs(webhook_type);
CREATE INDEX IF NOT EXISTS idx_webhook_audit_logs_event_type ON public.webhook_audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_audit_logs_record_id ON public.webhook_audit_logs(record_id) WHERE record_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_webhook_audit_logs_record_email ON public.webhook_audit_logs(record_email) WHERE record_email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_webhook_audit_logs_success ON public.webhook_audit_logs(success);
CREATE INDEX IF NOT EXISTS idx_webhook_audit_logs_created_at ON public.webhook_audit_logs(created_at DESC);

-- Add composite index for monitoring queries
CREATE INDEX IF NOT EXISTS idx_webhook_audit_logs_monitoring 
    ON public.webhook_audit_logs(webhook_type, success, created_at DESC);

-- Add RLS policies (webhook logs are internal, only admins can view)
ALTER TABLE public.webhook_audit_logs ENABLE ROW LEVEL SECURITY;

-- Policy: Only service role can insert webhook logs
CREATE POLICY "Service role can insert webhook audit logs"
    ON public.webhook_audit_logs
    FOR INSERT
    TO service_role
    WITH CHECK (true);

-- Policy: Admins can view all webhook logs
CREATE POLICY "Admins can view all webhook audit logs"
    ON public.webhook_audit_logs
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.users
            WHERE users.id = auth.uid()
            AND users.is_admin = true
            AND users.is_active = true
        )
    );

-- Grant necessary permissions
GRANT SELECT ON public.webhook_audit_logs TO authenticated;
GRANT INSERT ON public.webhook_audit_logs TO service_role;

-- Add helpful comments
COMMENT ON TABLE public.webhook_audit_logs IS 'Audit log for all webhook requests - tracks user sync events for monitoring and debugging';
COMMENT ON COLUMN public.webhook_audit_logs.webhook_type IS 'Type of webhook (e.g., user_sync)';
COMMENT ON COLUMN public.webhook_audit_logs.event_type IS 'Database event type (INSERT, UPDATE, DELETE)';
COMMENT ON COLUMN public.webhook_audit_logs.action_taken IS 'Action performed: created, updated, oauth_account_linked, idempotent, error, etc.';
COMMENT ON COLUMN public.webhook_audit_logs.processing_time_ms IS 'Time taken to process webhook in milliseconds';
COMMENT ON COLUMN public.webhook_audit_logs.success IS 'Whether the webhook processing succeeded';

