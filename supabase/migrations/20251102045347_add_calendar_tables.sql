-- Add calendar feature tables and fields
-- Part of Calendar feature implementation

-- ============================================================================
-- 1. Add expiry date columns to properties table
-- ============================================================================

ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS insurance_expiry_date DATE,
ADD COLUMN IF NOT EXISTS mortgage_renewal_date DATE;

-- Add indexes for efficient calendar queries
CREATE INDEX IF NOT EXISTS idx_properties_insurance_expiry 
  ON properties(insurance_expiry_date) 
  WHERE insurance_expiry_date IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_properties_mortgage_renewal 
  ON properties(mortgage_renewal_date) 
  WHERE mortgage_renewal_date IS NOT NULL;

-- Add comments
COMMENT ON COLUMN properties.insurance_expiry_date IS 'Property insurance policy expiration date for calendar tracking';
COMMENT ON COLUMN properties.mortgage_renewal_date IS 'Property mortgage renewal date for calendar tracking';

-- ============================================================================
-- 2. Create custom_reminders table for user-created calendar events
-- ============================================================================

CREATE TABLE IF NOT EXISTS custom_reminders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Reminder content
  title TEXT NOT NULL,
  description TEXT,
  reminder_date TIMESTAMPTZ NOT NULL,
  all_day BOOLEAN DEFAULT FALSE,
  
  -- Optional associations
  property_id INT REFERENCES properties(id) ON DELETE CASCADE,
  unit_id INT REFERENCES property_units(id) ON DELETE CASCADE,
  tenant_id INT REFERENCES tenants(id) ON DELETE CASCADE,
  
  -- Status tracking
  is_completed BOOLEAN DEFAULT FALSE,
  completed_at TIMESTAMPTZ,
  
  -- Notification settings
  notify_before_hours INT DEFAULT 24,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_custom_reminders_user_id ON custom_reminders(user_id);
CREATE INDEX IF NOT EXISTS idx_custom_reminders_date ON custom_reminders(reminder_date);
CREATE INDEX IF NOT EXISTS idx_custom_reminders_property ON custom_reminders(property_id) WHERE property_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_custom_reminders_completed ON custom_reminders(is_completed, reminder_date);

-- ============================================================================
-- 3. RLS Policies for custom_reminders
-- ============================================================================

ALTER TABLE custom_reminders ENABLE ROW LEVEL SECURITY;

-- Users can view their own reminders
CREATE POLICY "Users can view their own reminders"
  ON custom_reminders FOR SELECT
  USING (user_id = auth.uid());

-- Users can create their own reminders
CREATE POLICY "Users can create their own reminders"
  ON custom_reminders FOR INSERT
  WITH CHECK (user_id = auth.uid());

-- Users can update their own reminders
CREATE POLICY "Users can update their own reminders"
  ON custom_reminders FOR UPDATE
  USING (user_id = auth.uid());

-- Users can delete their own reminders
CREATE POLICY "Users can delete their own reminders"
  ON custom_reminders FOR DELETE
  USING (user_id = auth.uid());

-- Add helpful comment
COMMENT ON TABLE custom_reminders IS 'User-created calendar reminders with optional property/tenant associations';

