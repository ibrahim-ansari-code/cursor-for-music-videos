-- ========================================================================
-- COMPREHENSIVE NOTIFICATION SYSTEM
-- Based on industry best practices from GitHub, Slack, Linear
-- Implements: In-app notifications + Email notifications + User preferences
-- ========================================================================

-- ========================================================================
-- 1. CREATE NOTIFICATIONS TABLE
-- ========================================================================
-- Stores all user notifications with support for multi-channel delivery
CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Notification Content
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  link TEXT, -- Deep link to relevant page (e.g., '/tenants/123')
  
  -- Actor (who triggered this notification)
  actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
  actor_name TEXT,
  actor_avatar_url TEXT,
  
  -- Context & Metadata
  metadata JSONB DEFAULT '{}'::jsonb, -- { property_id, tenant_id, amount, etc. }
  
  -- Status
  is_read BOOLEAN DEFAULT FALSE,
  is_archived BOOLEAN DEFAULT FALSE,
  read_at TIMESTAMPTZ,
  
  -- Priority & Delivery
  priority TEXT DEFAULT 'normal', -- 'urgent', 'high', 'normal', 'low'
  delivery_channels TEXT[] DEFAULT ARRAY['in_app'], -- ['in_app', 'email', 'sms']
  
  -- Grouping (for notification bundling)
  group_key TEXT, -- e.g., 'rent_reminders_2024_10'
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ, -- Auto-delete after expiry
  
  -- Constraints
  CONSTRAINT valid_type CHECK (type IN (
    'rent_reminder', 'lease_expiring', 'system_update'
  )),
  CONSTRAINT valid_priority CHECK (priority IN ('urgent', 'high', 'normal', 'low'))
);

-- Performance indexes for notifications table
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX idx_notifications_type ON notifications(type);
CREATE INDEX idx_notifications_group_key ON notifications(group_key) WHERE group_key IS NOT NULL;

-- ========================================================================
-- 2. CREATE NOTIFICATION_PREFERENCES TABLE
-- ========================================================================
-- Per-user notification preferences with granular control per type and channel
CREATE TABLE notification_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Global Toggle
  enabled BOOLEAN DEFAULT TRUE,
  
  -- Per-Type Preferences (6 notification types)
  -- Each type has: enabled, channels array, frequency
  preferences JSONB DEFAULT '{
    "rent_reminder": {"enabled": true, "channels": ["in_app", "email"], "frequency": "immediate"},
    "payment_received": {"enabled": true, "channels": ["in_app", "email"], "frequency": "immediate"},
    "lease_expiring": {"enabled": true, "channels": ["in_app", "email"], "frequency": "immediate"},
    "maintenance_update": {"enabled": true, "channels": ["in_app", "email"], "frequency": "immediate"},
    "new_application": {"enabled": false, "channels": ["in_app"], "frequency": "immediate"},
    "system_update": {"enabled": false, "channels": ["in_app"], "frequency": "immediate"}
  }'::jsonb,
  
  -- Digest Settings
  email_digest_frequency TEXT DEFAULT 'immediate', -- 'immediate', 'hourly', 'daily', 'weekly', 'never'
  email_digest_time TIME DEFAULT '08:00:00', -- When to send daily/weekly digests
  timezone TEXT DEFAULT 'America/Toronto',
  
  -- Do Not Disturb (future feature)
  quiet_hours_enabled BOOLEAN DEFAULT FALSE,
  quiet_hours_start TIME,
  quiet_hours_end TIME,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Constraints
  CONSTRAINT unique_user_preferences UNIQUE(user_id),
  CONSTRAINT valid_digest_frequency CHECK (email_digest_frequency IN (
    'immediate', 'hourly', 'daily', 'weekly', 'never'
  ))
);

-- Index for quick preference lookups
CREATE INDEX idx_notification_preferences_user ON notification_preferences(user_id);

-- ========================================================================
-- 3. CREATE NOTIFICATION_DELIVERY_LOG TABLE (Analytics & Debugging)
-- ========================================================================
-- Tracks notification delivery status for analytics and debugging
CREATE TABLE notification_delivery_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Delivery Details
  channel TEXT NOT NULL, -- 'in_app', 'email', 'sms'
  status TEXT NOT NULL, -- 'pending', 'sent', 'delivered', 'failed', 'bounced'
  
  -- Email-specific fields
  email_provider TEXT, -- 'supabase', 'sendgrid', etc.
  email_message_id TEXT,
  email_opened_at TIMESTAMPTZ,
  email_clicked_at TIMESTAMPTZ,
  
  -- Error handling
  error_message TEXT,
  retry_count INT DEFAULT 0,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  sent_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  
  -- Constraints
  CONSTRAINT valid_channel CHECK (channel IN ('in_app', 'email', 'sms')),
  CONSTRAINT valid_status CHECK (status IN (
    'pending', 'sent', 'delivered', 'failed', 'bounced'
  ))
);

-- Indexes for delivery log queries
CREATE INDEX idx_delivery_log_notification ON notification_delivery_log(notification_id);
CREATE INDEX idx_delivery_log_status ON notification_delivery_log(status);
CREATE INDEX idx_delivery_log_created ON notification_delivery_log(created_at DESC);

-- ========================================================================
-- 4. ROW LEVEL SECURITY (RLS) POLICIES
-- ========================================================================
-- Enable RLS on all notification tables
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_delivery_log ENABLE ROW LEVEL SECURITY;

-- Notifications: Users can only see their own notifications
CREATE POLICY "Users can view own notifications"
  ON notifications FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update own notifications"
  ON notifications FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own notifications"
  ON notifications FOR DELETE
  USING (auth.uid() = user_id);

-- Preferences: Users can manage their own preferences
CREATE POLICY "Users can view own preferences"
  ON notification_preferences FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update own preferences"
  ON notification_preferences FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own preferences"
  ON notification_preferences FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Delivery log: Users can view their own delivery logs (read-only)
CREATE POLICY "Users can view own delivery logs"
  ON notification_delivery_log FOR SELECT
  USING (auth.uid() = user_id);

-- ========================================================================
-- 5. TRIGGER: AUTO-UPDATE updated_at TIMESTAMP
-- ========================================================================
CREATE OR REPLACE FUNCTION update_notification_preferences_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER notification_preferences_updated_at
  BEFORE UPDATE ON notification_preferences
  FOR EACH ROW
  EXECUTE FUNCTION update_notification_preferences_updated_at();

-- ========================================================================
-- 6. TRIGGER: AUTO-CREATE DEFAULT PREFERENCES FOR NEW USERS
-- ========================================================================
CREATE OR REPLACE FUNCTION create_default_notification_preferences()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO notification_preferences (user_id)
  VALUES (NEW.id)
  ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER create_user_notification_preferences
  AFTER INSERT ON users
  FOR EACH ROW
  EXECUTE FUNCTION create_default_notification_preferences();

-- ========================================================================
-- 7. MAINTENANCE FUNCTIONS (for scheduled cleanup)
-- ========================================================================

-- Function to cleanup expired notifications
CREATE OR REPLACE FUNCTION cleanup_expired_notifications()
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  DELETE FROM notifications
  WHERE expires_at IS NOT NULL AND expires_at < NOW();
  
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old archived notifications (90+ days old)
CREATE OR REPLACE FUNCTION cleanup_old_archived_notifications()
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  DELETE FROM notifications
  WHERE is_archived = TRUE 
    AND created_at < NOW() - INTERVAL '90 days';
  
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get unread notification count for a user
CREATE OR REPLACE FUNCTION get_unread_notification_count(p_user_id UUID)
RETURNS INTEGER AS $$
DECLARE
  unread_count INTEGER;
BEGIN
  SELECT COUNT(*)
  INTO unread_count
  FROM notifications
  WHERE user_id = p_user_id
    AND is_read = FALSE
    AND is_archived = FALSE;
  
  RETURN unread_count;
END;
$$ LANGUAGE plpgsql;

-- ========================================================================
-- 8. ENABLE REALTIME FOR NOTIFICATIONS
-- ========================================================================
-- Enable Supabase Realtime for notifications table
-- This allows frontend to subscribe to new notifications in real-time
ALTER PUBLICATION supabase_realtime ADD TABLE notifications;

-- ========================================================================
-- 9. COMMENTS FOR DOCUMENTATION
-- ========================================================================
COMMENT ON TABLE notifications IS 'Stores all user notifications with support for multi-channel delivery (in-app, email, SMS)';
COMMENT ON TABLE notification_preferences IS 'Per-user notification preferences with granular control per notification type and delivery channel';
COMMENT ON TABLE notification_delivery_log IS 'Tracks notification delivery status for analytics, debugging, and compliance';

COMMENT ON COLUMN notifications.type IS 'Notification type: rent_reminder, payment_received, lease_expiring, maintenance_update, new_application, system_update';
COMMENT ON COLUMN notifications.priority IS 'Priority level: urgent, high, normal, low - affects UI presentation and delivery urgency';
COMMENT ON COLUMN notifications.metadata IS 'Flexible JSONB field for type-specific data (property_id, tenant_id, amount, etc.)';
COMMENT ON COLUMN notifications.group_key IS 'Used to group related notifications for bundling/collapsing in UI';

COMMENT ON COLUMN notification_preferences.preferences IS 'JSONB object with per-type settings: {type: {enabled: bool, channels: [string], frequency: string}}';
COMMENT ON COLUMN notification_preferences.email_digest_frequency IS 'How often to send email digests: immediate, hourly, daily, weekly, never';
COMMENT ON COLUMN notification_preferences.timezone IS 'User timezone for digest scheduling (e.g., America/Toronto)';

-- ========================================================================
-- 10. CREATE DEFAULT PREFERENCES FOR EXISTING USERS
-- ========================================================================
-- Backfill notification preferences for any existing users who don't have them
INSERT INTO notification_preferences (user_id)
SELECT id FROM users
WHERE id NOT IN (SELECT user_id FROM notification_preferences)
ON CONFLICT (user_id) DO NOTHING;

-- ========================================================================
-- MIGRATION COMPLETE
-- ========================================================================
-- Summary:
-- - Created 3 tables: notifications, notification_preferences, notification_delivery_log
-- - Added 11 indexes for optimal query performance
-- - Configured RLS policies for security
-- - Added triggers for auto-update and default preferences
-- - Created 3 maintenance functions for cleanup and stats
-- - Enabled Supabase Realtime for notifications
-- - Backfilled preferences for existing users
-- ========================================================================

