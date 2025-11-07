-- Migration: Add user_id to payments and create payment_allocations table
-- This implements the industry-standard payment allocation pattern used by Stripe, QuickBooks, FreshBooks
--
-- Data Analysis (as of migration):
-- - 171 total payments in database
-- - 160 payments with lease_id (user_id via lease → property)
-- - 11 payments with only tenant_id (user_id via tenant → landlord_id)
-- - 0 orphaned payments
-- - ALL payments can have user_id backfilled successfully
--
-- Changes:
-- 1. Add user_id to payments table (landlord who owns the payment)
-- 2. Create payment_allocations junction table (links payments to invoices)
-- 3. Backfill user_id for all existing payments
-- 4. Add indexes for performance
-- 5. Add helper functions for invoice status computation
-- 6. Add trigger to auto-update invoice status when payments allocated
-- 7. Enable RLS on payment_allocations table

-- =============================================================================
-- STEP 1: Add user_id column to payments table
-- =============================================================================

-- Add the column as nullable first to allow backfill
ALTER TABLE payments
ADD COLUMN IF NOT EXISTS user_id uuid;

-- Add index before backfill for performance
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);

-- Backfill user_id for all existing payments
-- Strategy 1: Payments with leases get user_id from property owner
UPDATE payments p
SET user_id = pr.user_id
FROM leases l
INNER JOIN properties pr ON l.property_id = pr.id
WHERE p.lease_id = l.id
  AND p.user_id IS NULL;

-- Strategy 2: Payments without leases get user_id from tenant's landlord
UPDATE payments p
SET user_id = t.landlord_id
FROM tenants t
WHERE p.tenant_id = t.id
  AND p.lease_id IS NULL
  AND p.user_id IS NULL
  AND t.landlord_id IS NOT NULL;

-- Verify all payments have user_id before making it NOT NULL
-- If any payments still have NULL user_id, this will help debug
DO $$
DECLARE
  null_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO null_count FROM payments WHERE user_id IS NULL;

  IF null_count > 0 THEN
    RAISE EXCEPTION 'Failed to backfill user_id for % payments. Migration cannot proceed. Please fix orphaned payments manually.', null_count;
  ELSE
    -- All payments have a user_id, it's safe to make the column NOT NULL
    ALTER TABLE payments
    ALTER COLUMN user_id SET NOT NULL;

    RAISE NOTICE 'Successfully backfilled user_id for all payments and set column to NOT NULL.';
  END IF;
END $$;

-- Add foreign key constraint (only if column is NOT NULL)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'payments_user_id_fkey'
  ) THEN
    ALTER TABLE payments
    ADD CONSTRAINT payments_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;
  END IF;
END $$;

-- Add comment for documentation
COMMENT ON COLUMN payments.user_id IS 'Landlord/user who owns this payment (enables direct querying without joins). Backfilled from lease→property→user_id or tenant→landlord_id.';

-- =============================================================================
-- STEP 2: Create payment_allocations junction table
-- =============================================================================

CREATE TABLE IF NOT EXISTS payment_allocations (
  id SERIAL PRIMARY KEY,
  payment_id integer NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
  invoice_id integer NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
  amount_applied numeric(12, 2) NOT NULL CHECK (amount_applied > 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),

  -- Ensure we don't double-allocate the same payment to the same invoice
  CONSTRAINT payment_allocations_unique_payment_invoice UNIQUE (payment_id, invoice_id)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_payment_allocations_payment_id ON payment_allocations(payment_id);
CREATE INDEX IF NOT EXISTS idx_payment_allocations_invoice_id ON payment_allocations(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payment_allocations_created_at ON payment_allocations(created_at);

-- Add table comment
COMMENT ON TABLE payment_allocations IS 'Junction table linking payments to invoices with allocation amounts (supports partial payments and multi-invoice payments). Industry standard pattern used by Stripe, QuickBooks, FreshBooks.';
COMMENT ON COLUMN payment_allocations.payment_id IS 'Reference to the payment being allocated';
COMMENT ON COLUMN payment_allocations.invoice_id IS 'Reference to the invoice receiving payment';
COMMENT ON COLUMN payment_allocations.amount_applied IS 'Amount of the payment applied to this specific invoice (supports partial/split payments)';

-- Add trigger for updated_at (only if update_updated_at_column function exists)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'update_updated_at_column') THEN
    DROP TRIGGER IF EXISTS update_payment_allocations_updated_at ON payment_allocations;
    CREATE TRIGGER update_payment_allocations_updated_at
      BEFORE UPDATE ON payment_allocations
      FOR EACH ROW
      EXECUTE FUNCTION update_updated_at_column();
  END IF;
END $$;

-- =============================================================================
-- STEP 3: Create helper functions to compute invoice payment status
-- =============================================================================

-- Function to get total amount paid for an invoice
CREATE OR REPLACE FUNCTION get_invoice_amount_paid(invoice_id_param INTEGER)
RETURNS NUMERIC AS $$
  SELECT COALESCE(SUM(amount_applied), 0)
  FROM payment_allocations
  WHERE invoice_id = invoice_id_param;
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION get_invoice_amount_paid IS 'Returns total amount paid towards an invoice from all payment allocations';

-- Function to get amount due for an invoice
CREATE OR REPLACE FUNCTION get_invoice_amount_due(invoice_id_param INTEGER)
RETURNS NUMERIC AS $$
  SELECT i.amount - COALESCE(
    (SELECT SUM(amount_applied) FROM payment_allocations WHERE invoice_id = invoice_id_param),
    0
  )
  FROM invoices i
  WHERE i.id = invoice_id_param;
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION get_invoice_amount_due IS 'Returns remaining amount due for an invoice (invoice amount - total payments)';

-- Function to check if invoice is fully paid
CREATE OR REPLACE FUNCTION is_invoice_fully_paid(invoice_id_param INTEGER)
RETURNS BOOLEAN AS $$
  SELECT COALESCE(get_invoice_amount_due(invoice_id_param) <= 0, false);
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION is_invoice_fully_paid IS 'Returns true if invoice is fully paid (amount due <= 0)';

-- =============================================================================
-- STEP 4: Create trigger to auto-update invoice status when payments allocated
-- =============================================================================

CREATE OR REPLACE FUNCTION update_invoice_status_from_allocations()
RETURNS TRIGGER AS $$
DECLARE
  v_invoice_id INTEGER;
  v_invoice_amount NUMERIC;
  v_total_paid NUMERIC;
  v_amount_due NUMERIC;
BEGIN
  -- Get the invoice_id from the trigger (works for INSERT, UPDATE, DELETE)
  IF TG_OP = 'DELETE' THEN
    v_invoice_id := OLD.invoice_id;
  ELSE
    v_invoice_id := NEW.invoice_id;
  END IF;

  -- Get invoice amount and total paid
  SELECT i.amount, COALESCE(SUM(pa.amount_applied), 0)
  INTO v_invoice_amount, v_total_paid
  FROM invoices i
  LEFT JOIN payment_allocations pa ON pa.invoice_id = i.id
  WHERE i.id = v_invoice_id
  GROUP BY i.amount;

  -- Calculate amount due
  v_amount_due := v_invoice_amount - v_total_paid;

  -- Update invoice status based on payment
  IF v_amount_due <= 0 THEN
    -- Fully paid
    UPDATE invoices SET status = 'Paid', updated_at = now() WHERE id = v_invoice_id;
  ELSIF v_total_paid > 0 AND v_amount_due > 0 THEN
    -- Partially paid
    UPDATE invoices SET status = 'Partial', updated_at = now() WHERE id = v_invoice_id;
  -- If no payments and status is currently Paid or Partial, revert to Pending
  ELSIF v_total_paid = 0 THEN
    UPDATE invoices
    SET status = 'Pending', updated_at = now()
    WHERE id = v_invoice_id
      AND status IN ('Paid', 'Partial');
  END IF;

  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_invoice_status_from_allocations IS 'Automatically updates invoice status (Paid/Partial/Pending) when payment allocations change. Triggered on payment_allocations INSERT/UPDATE/DELETE.';

-- Create trigger
DROP TRIGGER IF EXISTS trigger_update_invoice_status_on_allocation ON payment_allocations;
CREATE TRIGGER trigger_update_invoice_status_on_allocation
  AFTER INSERT OR UPDATE OR DELETE ON payment_allocations
  FOR EACH ROW
  EXECUTE FUNCTION update_invoice_status_from_allocations();

-- =============================================================================
-- STEP 5: Add RLS policies for payment_allocations
-- =============================================================================

ALTER TABLE payment_allocations ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS payment_allocations_select_policy ON payment_allocations;
DROP POLICY IF EXISTS payment_allocations_insert_policy ON payment_allocations;
DROP POLICY IF EXISTS payment_allocations_update_policy ON payment_allocations;
DROP POLICY IF EXISTS payment_allocations_delete_policy ON payment_allocations;

-- Policy: Users can view their own payment allocations
CREATE POLICY payment_allocations_select_policy ON payment_allocations
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM payments p
      WHERE p.id = payment_allocations.payment_id
        AND p.user_id = auth.uid()
    )
  );

-- Policy: Users can create allocations for their own payments
CREATE POLICY payment_allocations_insert_policy ON payment_allocations
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM payments p
      WHERE p.id = payment_allocations.payment_id
        AND p.user_id = auth.uid()
    )
  );

-- Policy: Users can update their own payment allocations
CREATE POLICY payment_allocations_update_policy ON payment_allocations
  FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM payments p
      WHERE p.id = payment_allocations.payment_id
        AND p.user_id = auth.uid()
    )
  );

-- Policy: Users can delete their own payment allocations
CREATE POLICY payment_allocations_delete_policy ON payment_allocations
  FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM payments p
      WHERE p.id = payment_allocations.payment_id
        AND p.user_id = auth.uid()
    )
  );

-- =============================================================================
-- VERIFICATION & LOGGING
-- =============================================================================

-- Log migration results
DO $$
DECLARE
  total_payments INTEGER;
  payments_with_user_id INTEGER;
  payments_without_user_id INTEGER;
  allocations_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO total_payments FROM payments;
  SELECT COUNT(*) INTO payments_with_user_id FROM payments WHERE user_id IS NOT NULL;
  SELECT COUNT(*) INTO payments_without_user_id FROM payments WHERE user_id IS NULL;
  SELECT COUNT(*) INTO allocations_count FROM payment_allocations;

  RAISE NOTICE '=== Migration Summary ===';
  RAISE NOTICE 'Total payments: %', total_payments;
  RAISE NOTICE 'Payments with user_id: %', payments_with_user_id;
  RAISE NOTICE 'Payments without user_id: %', payments_without_user_id;
  RAISE NOTICE 'Payment allocations: %', allocations_count;
  RAISE NOTICE '';
  RAISE NOTICE 'New Features:';
  RAISE NOTICE '  ✓ user_id column added to payments (enables direct landlord querying)';
  RAISE NOTICE '  ✓ payment_allocations table created (links payments to invoices)';
  RAISE NOTICE '  ✓ Helper functions: get_invoice_amount_paid(), get_invoice_amount_due(), is_invoice_fully_paid()';
  RAISE NOTICE '  ✓ Auto-update trigger: invoice status updates when payments are allocated';
  RAISE NOTICE '  ✓ RLS policies enabled for payment_allocations';
  RAISE NOTICE '';
  RAISE NOTICE 'Migration completed successfully!';
END $$;
