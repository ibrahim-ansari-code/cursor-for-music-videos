-- Migration: Add Stripe Connect Requirements and Restrictions Tracking
-- Description: Add fields to track verification requirements and account restrictions
--              for Stripe Express accounts. Enables proactive notification when
--              landlords need to submit additional documents or information.
-- Created: 2025-12-17

-- ============================================================================
-- Add Requirements and Restrictions Columns
-- ============================================================================

-- Add columns to stripe_connected_accounts table
ALTER TABLE public.stripe_connected_accounts
ADD COLUMN IF NOT EXISTS disabled_reason VARCHAR(100),
ADD COLUMN IF NOT EXISTS requirements_currently_due JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS requirements_past_due JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS requirements_eventually_due JSONB DEFAULT '[]'::jsonb;

-- Add comments for documentation
COMMENT ON COLUMN public.stripe_connected_accounts.disabled_reason IS 
'Reason the account is disabled (e.g., requirements.past_due, rejected.fraud)';

COMMENT ON COLUMN public.stripe_connected_accounts.requirements_currently_due IS 
'Array of fields/documents currently needed from account holder';

COMMENT ON COLUMN public.stripe_connected_accounts.requirements_past_due IS 
'Array of overdue requirements that must be submitted immediately';

COMMENT ON COLUMN public.stripe_connected_accounts.requirements_eventually_due IS 
'Array of requirements that will be needed in the future';

-- ============================================================================
-- Add Index for Performance
-- ============================================================================

-- Index for quickly finding accounts that need action
CREATE INDEX IF NOT EXISTS idx_stripe_connected_accounts_needs_action
ON public.stripe_connected_accounts ((jsonb_array_length(requirements_currently_due) + jsonb_array_length(requirements_past_due)))
WHERE jsonb_array_length(requirements_currently_due) > 0 
   OR jsonb_array_length(requirements_past_due) > 0;

-- ============================================================================
-- Update RLS Policies (if needed)
-- ============================================================================

-- No RLS policy changes needed - existing policies cover the new columns
-- Landlords can only see their own stripe_connected_accounts records

-- ============================================================================
-- Migration Verification
-- ============================================================================

-- Verify columns were added
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'stripe_connected_accounts' 
        AND column_name = 'disabled_reason'
    ) THEN
        RAISE EXCEPTION 'Migration failed: disabled_reason column not created';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'stripe_connected_accounts' 
        AND column_name = 'requirements_currently_due'
    ) THEN
        RAISE EXCEPTION 'Migration failed: requirements_currently_due column not created';
    END IF;
    
    RAISE NOTICE 'Migration completed successfully: Stripe Connect requirements tracking added';
END $$;

