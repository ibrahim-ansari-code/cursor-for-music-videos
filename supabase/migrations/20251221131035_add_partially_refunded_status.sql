-- Add 'Partially Refunded' status to support partial refunds
-- This migration adds the new status to both:
-- 1. The paymentstatus enum (used by payments table)
-- 2. The CHECK constraint on rent_payment_transactions.status

-- =============================================================================
-- STEP 1: Add 'Partially Refunded' to the paymentstatus enum
-- =============================================================================
-- PostgreSQL enums can have new values added, but they're appended at the end
-- unless we specify a position. We'll add it before 'Refunded' for logical ordering.

ALTER TYPE public.paymentstatus ADD VALUE IF NOT EXISTS 'Partially Refunded' BEFORE 'Refunded';

-- =============================================================================
-- STEP 2: Update the CHECK constraint on rent_payment_transactions.status
-- =============================================================================
-- The rent_payment_transactions table uses a VARCHAR with CHECK constraint.
-- We need to drop the old constraint and add a new one with 'partially_refunded'.

-- Drop the existing constraint
ALTER TABLE rent_payment_transactions
DROP CONSTRAINT IF EXISTS valid_status;

-- Add the updated constraint with 'partially_refunded'
ALTER TABLE rent_payment_transactions
ADD CONSTRAINT valid_status CHECK (
  status IN (
    'pending',
    'requires_action',
    'requires_payment_method',
    'processing',
    'succeeded',
    'failed',
    'canceled',
    'partially_refunded',
    'refunded'
  )
);

-- =============================================================================
-- STEP 3: Add comment for documentation
-- =============================================================================
COMMENT ON COLUMN rent_payment_transactions.status IS
'Transaction status: pending, requires_action, requires_payment_method, processing, succeeded, failed, canceled, partially_refunded, refunded';

-- =============================================================================
-- Log migration completion
-- =============================================================================
DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '==========================================================';
  RAISE NOTICE 'Migration: add_partially_refunded_status';
  RAISE NOTICE '==========================================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Added "Partially Refunded" status to support partial refunds:';
  RAISE NOTICE '  - Added to paymentstatus enum (payments table)';
  RAISE NOTICE '  - Added to rent_payment_transactions CHECK constraint';
  RAISE NOTICE '';
  RAISE NOTICE 'This enables proper tracking of partial vs full refunds.';
  RAISE NOTICE '';
END $$;
