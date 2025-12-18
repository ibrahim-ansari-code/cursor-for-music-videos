-- Add Rent Payment Refunds and Disputes Tables
-- 
-- This migration adds comprehensive refund and dispute tracking for rent payments:
-- 1. rent_payment_refunds - tracks all refunds (full and partial)
-- 2. rent_payment_disputes - tracks payment disputes/chargebacks

-- ============================================================================
-- Refunds Table
-- ============================================================================

CREATE TABLE rent_payment_refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES rent_payment_transactions(id) ON DELETE CASCADE,
    
    -- Stripe IDs
    stripe_refund_id VARCHAR(255) NOT NULL UNIQUE,
    stripe_charge_id VARCHAR(255) NOT NULL,
    
    -- Refund details
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'cad',
    
    -- Reason and notes
    reason VARCHAR(100) NOT NULL,
    notes TEXT,
    
    -- Status
    status VARCHAR(50) NOT NULL,
    failure_reason TEXT,
    
    -- Application fee handling
    application_fee_refunded_cents INTEGER,
    
    -- Who initiated
    initiated_by_user_id UUID NOT NULL REFERENCES users(id),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    succeeded_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_refund_amount CHECK (amount_cents > 0),
    CONSTRAINT valid_refund_status CHECK (status IN ('pending', 'processing', 'succeeded', 'failed', 'canceled'))
);

-- Indexes for refunds
CREATE INDEX idx_refunds_transaction_id ON rent_payment_refunds(transaction_id);
CREATE INDEX idx_refunds_stripe_refund_id ON rent_payment_refunds(stripe_refund_id);
CREATE INDEX idx_refunds_status ON rent_payment_refunds(status);
CREATE INDEX idx_refunds_created_at ON rent_payment_refunds(created_at);

-- ============================================================================
-- Disputes Table
-- ============================================================================

CREATE TABLE rent_payment_disputes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES rent_payment_transactions(id) ON DELETE CASCADE,
    
    -- Stripe IDs
    stripe_dispute_id VARCHAR(255) NOT NULL UNIQUE,
    stripe_charge_id VARCHAR(255) NOT NULL,
    
    -- Dispute details
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'cad',
    
    -- Reason and status
    reason VARCHAR(100) NOT NULL,
    status VARCHAR(100) NOT NULL,
    
    -- Evidence handling
    evidence_due_by TIMESTAMPTZ,
    evidence_submitted BOOLEAN NOT NULL DEFAULT FALSE,
    evidence_submitted_at TIMESTAMPTZ,
    
    -- Refundability
    is_charge_refundable BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Landlord notifications
    landlord_notified BOOLEAN NOT NULL DEFAULT FALSE,
    landlord_notified_at TIMESTAMPTZ,
    
    CONSTRAINT valid_dispute_amount CHECK (amount_cents > 0)
);

-- Indexes for disputes
CREATE INDEX idx_disputes_transaction_id ON rent_payment_disputes(transaction_id);
CREATE INDEX idx_disputes_stripe_dispute_id ON rent_payment_disputes(stripe_dispute_id);
CREATE INDEX idx_disputes_status ON rent_payment_disputes(status);
CREATE INDEX idx_disputes_needs_attention ON rent_payment_disputes(status, evidence_submitted) 
    WHERE status IN ('warning_needs_response', 'needs_response') AND evidence_submitted = FALSE;
CREATE INDEX idx_disputes_created_at ON rent_payment_disputes(created_at);

-- ============================================================================
-- Comments for documentation
-- ============================================================================

COMMENT ON TABLE rent_payment_refunds IS 'Tracks all refunds issued for rent payments, including partial and full refunds';
COMMENT ON TABLE rent_payment_disputes IS 'Tracks payment disputes (chargebacks) initiated by tenants through their bank/card issuer';

COMMENT ON COLUMN rent_payment_refunds.reason IS 'Refund reason: duplicate, fraudulent, requested_by_customer, rent_adjustment, lease_cancellation, overpayment, other';
COMMENT ON COLUMN rent_payment_refunds.application_fee_refunded_cents IS 'Amount of Brikli platform fee that was refunded to landlord';

COMMENT ON COLUMN rent_payment_disputes.reason IS 'Dispute reason from Stripe (bank_cannot_process, debit_not_authorized, fraudulent, etc.)';
COMMENT ON COLUMN rent_payment_disputes.status IS 'Dispute status: warning_needs_response, needs_response, under_review, won, lost, charge_refunded, etc.';
COMMENT ON COLUMN rent_payment_disputes.evidence_submitted IS 'Whether landlord has submitted evidence to contest the dispute';

