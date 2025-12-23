-- Add portal_status enum type
CREATE TYPE portal_status AS ENUM ('none', 'invited', 'active', 'revoked');

-- Add portal tracking fields to tenants table
ALTER TABLE tenants
ADD COLUMN portal_status portal_status NOT NULL DEFAULT 'none',
ADD COLUMN last_portal_login_at TIMESTAMPTZ NULL;

-- Create index for efficient seat counting queries
CREATE INDEX idx_tenants_portal_status ON tenants(portal_status);

-- Create index for portal status per landlord (for seat counting)
CREATE INDEX idx_tenants_landlord_portal_status ON tenants(landlord_id, portal_status);

-- Migrate existing data: tenants with user_id set should be marked as 'active'
-- This preserves the current state where user_id != NULL means they have portal access
UPDATE tenants
SET portal_status = 'active'
WHERE user_id IS NOT NULL;

-- Add comment explaining the field
COMMENT ON COLUMN tenants.portal_status IS 'Tenant portal access status. ACTIVE = using a landlord seat. Used for seat-based billing.';
COMMENT ON COLUMN tenants.last_portal_login_at IS 'Timestamp of tenant''s last portal login. Used for analytics.';

-- Add metadata column to notification_delivery_log for rate limiting and tracking
ALTER TABLE notification_delivery_log
ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT NULL;

-- Add index for efficient rate limit queries
CREATE INDEX IF NOT EXISTS idx_notification_delivery_log_rate_limit
ON notification_delivery_log (user_id, channel, created_at)
WHERE channel = 'tenant_reminder';

COMMENT ON COLUMN notification_delivery_log.metadata IS 'Flexible metadata for rate limiting and tracking: {tenant_id, event_type, etc.}';
