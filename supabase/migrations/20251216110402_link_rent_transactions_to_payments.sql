-- Migration: Link Rent Payment Transactions to Main Payments Ledger
-- Description: Add foreign key from rent_payment_transactions to payments table
--              to integrate online rent payments into the main accounting system.
--              When tenants pay via Stripe Connect, entries are automatically
--              recorded in both the rent_payments system AND the accounting ledger.
-- Created: 2025-12-17

-- ============================================================================
-- Add Stripe Payment Intent ID to Payments Table
-- ============================================================================

-- Add stripe_payment_intent_id to payments table for online payment tracking
ALTER TABLE public.payments
ADD COLUMN IF NOT EXISTS stripe_payment_intent_id VARCHAR(255);

-- Add unique index (online payments should only create one ledger entry)
CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_stripe_payment_intent_id
ON public.payments(stripe_payment_intent_id)
WHERE stripe_payment_intent_id IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN public.payments.stripe_payment_intent_id IS 
'Stripe PaymentIntent ID for online rent payments. Links ledger entries to Stripe Connect transactions.';

-- ============================================================================
-- Add Payment ID Foreign Key to Rent Transactions
-- ============================================================================

-- Add payment_id column to link to main accounting payments table
ALTER TABLE public.rent_payment_transactions
ADD COLUMN IF NOT EXISTS payment_id INTEGER;

-- Add foreign key constraint to payments table
ALTER TABLE public.rent_payment_transactions
ADD CONSTRAINT fk_rent_payment_transactions_payment_id
FOREIGN KEY (payment_id)
REFERENCES public.payments(id)
ON DELETE SET NULL;  -- If payment is deleted, keep transaction record but clear link

-- Add index for performance (queries joining to payments table)
CREATE INDEX IF NOT EXISTS idx_rent_payment_transactions_payment_id
ON public.rent_payment_transactions(payment_id);

-- Add comment for documentation
COMMENT ON COLUMN public.rent_payment_transactions.payment_id IS 
'Foreign key to payments table. Links online rent payments to main accounting ledger for unified reporting.';

-- ============================================================================
-- Migration Verification
-- ============================================================================

DO $$
BEGIN
    -- Verify column was added
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'rent_payment_transactions' 
        AND column_name = 'payment_id'
    ) THEN
        RAISE EXCEPTION 'Migration failed: payment_id column not created';
    END IF;
    
    -- Verify foreign key constraint exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_schema = 'public'
        AND table_name = 'rent_payment_transactions'
        AND constraint_name = 'fk_rent_payment_transactions_payment_id'
        AND constraint_type = 'FOREIGN KEY'
    ) THEN
        RAISE EXCEPTION 'Migration failed: foreign key constraint not created';
    END IF;
    
    RAISE NOTICE 'Migration completed successfully: Rent transactions linked to payments ledger';
END $$;

