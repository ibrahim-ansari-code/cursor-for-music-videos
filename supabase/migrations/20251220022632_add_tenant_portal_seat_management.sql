-- Add Tenant Portal Seat Management
-- Implements GitHub-style seat licensing: single limit field with real-time counting

-- Add seat limit to users table (2 free seats by default)
ALTER TABLE users
  ADD COLUMN tenant_portal_seat_limit INTEGER NOT NULL DEFAULT 2;

COMMENT ON COLUMN users.tenant_portal_seat_limit IS 'Maximum tenant portal seats (2 free + purchased subscriptions). Seats used = COUNT(tenants WHERE user_id IS NOT NULL).';

-- Create index for seat availability checks (used in JOIN queries)
CREATE INDEX idx_users_seat_limit ON users(id, tenant_portal_seat_limit);

-- Create tenant_portal_seat_subscriptions table
-- Tracks Stripe subscriptions for additional seats beyond the 2 free seats
CREATE TABLE tenant_portal_seat_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  landlord_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  stripe_subscription_id TEXT UNIQUE NOT NULL,
  stripe_price_id TEXT NOT NULL,
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  status TEXT NOT NULL CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'unpaid', 'incomplete', 'incomplete_expired')),
  current_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
  current_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE tenant_portal_seat_subscriptions IS 'Tracks Stripe recurring subscriptions for tenant portal seats ($3/seat/month). Updates users.tenant_portal_seat_limit via webhook handlers.';

-- Indexes for performance
CREATE INDEX idx_seat_subscriptions_landlord ON tenant_portal_seat_subscriptions(landlord_user_id);
CREATE INDEX idx_seat_subscriptions_stripe_id ON tenant_portal_seat_subscriptions(stripe_subscription_id);
CREATE INDEX idx_seat_subscriptions_status ON tenant_portal_seat_subscriptions(status) WHERE status = 'active';

-- Helper function: Get seat usage for a landlord (real-time count, not cached)
-- Usage: SELECT get_tenant_portal_seat_usage('user-uuid-here');
CREATE OR REPLACE FUNCTION get_tenant_portal_seat_usage(landlord_uuid UUID)
RETURNS TABLE (
  limit_seats INTEGER,
  used_seats BIGINT,
  available_seats INTEGER
) AS $$
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
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_tenant_portal_seat_usage(UUID) IS 'Real-time seat usage calculation. Returns limit, used (COUNT of tenants with user_id), and available seats.';
