-- ============================================================================
-- Rent Payment System Tables (Stripe Connect Direct Charges)
-- ============================================================================
-- Enables tenants to pay landlords directly via Stripe Connect.
-- Money flows: Tenant → Landlord (directly), Brikli gets 2% application fee.
-- ============================================================================

-- 1. Stripe Connected Accounts (Landlords)
-- Stores Stripe Express account info for landlords receiving rent payments
CREATE TABLE IF NOT EXISTS stripe_connected_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    stripe_account_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- Onboarding status flags
    charges_enabled BOOLEAN DEFAULT FALSE,
    payouts_enabled BOOLEAN DEFAULT FALSE,
    details_submitted BOOLEAN DEFAULT FALSE,
    
    -- Account details (cached from Stripe)
    business_type VARCHAR(50),
    country VARCHAR(2) DEFAULT 'CA',
    default_currency VARCHAR(3) DEFAULT 'cad',
    
    -- Timestamps
    onboarding_completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_connected_accounts_user ON stripe_connected_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_connected_accounts_stripe ON stripe_connected_accounts(stripe_account_id);

COMMENT ON TABLE stripe_connected_accounts IS 'Stripe Express accounts for landlords to receive rent payments via Connect Direct Charges';
COMMENT ON COLUMN stripe_connected_accounts.charges_enabled IS 'Whether the account can accept charges';
COMMENT ON COLUMN stripe_connected_accounts.payouts_enabled IS 'Whether the account can receive payouts to bank';

-- 2. Tenant Payment Methods
-- Stores saved payment methods (PAD bank accounts, cards) for tenants
CREATE TABLE IF NOT EXISTS tenant_payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    stripe_payment_method_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- Type info
    payment_method_type VARCHAR(50) NOT NULL,
    
    -- Display info
    last_four VARCHAR(4),
    bank_name VARCHAR(255),
    institution_number VARCHAR(10),
    brand VARCHAR(50),
    exp_month INTEGER,
    exp_year INTEGER,
    
    -- Status
    is_default BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tenant_payment_methods_tenant ON tenant_payment_methods(tenant_id);

COMMENT ON TABLE tenant_payment_methods IS 'Saved payment methods (PAD/cards) for tenant rent payments';
COMMENT ON COLUMN tenant_payment_methods.payment_method_type IS 'acss_debit for Canadian PAD, card for credit/debit cards';
COMMENT ON COLUMN tenant_payment_methods.is_verified IS 'For PAD: whether microdeposit verification is complete';

-- 3. Rent Payment Transactions
-- Tracks all rent payment attempts via Stripe Connect
CREATE TABLE IF NOT EXISTS rent_payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Links to existing system
    payment_id INTEGER REFERENCES payments(id),
    lease_id INTEGER NOT NULL REFERENCES leases(id),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    landlord_user_id UUID NOT NULL REFERENCES users(id),
    connected_account_id UUID REFERENCES stripe_connected_accounts(id),
    payment_method_id UUID REFERENCES tenant_payment_methods(id),
    
    -- Stripe references
    stripe_payment_intent_id VARCHAR(255) UNIQUE,
    stripe_charge_id VARCHAR(255),
    
    -- Amounts (stored in cents)
    amount_cents INTEGER NOT NULL,
    application_fee_cents INTEGER NOT NULL DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'cad',
    
    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    failure_code VARCHAR(100),
    failure_message TEXT,
    
    -- Payment method details (denormalized for history)
    payment_method_type VARCHAR(50),
    payment_method_last_four VARCHAR(4),
    payment_method_bank_name VARCHAR(255),
    
    -- Timestamps
    initiated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    authorized_at TIMESTAMPTZ,
    succeeded_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    refunded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('pending', 'requires_action', 'requires_payment_method', 'processing', 'succeeded', 'failed', 'canceled', 'refunded')),
    CONSTRAINT positive_amount CHECK (amount_cents > 0),
    CONSTRAINT non_negative_fee CHECK (application_fee_cents >= 0)
);

CREATE INDEX IF NOT EXISTS idx_rent_transactions_lease ON rent_payment_transactions(lease_id);
CREATE INDEX IF NOT EXISTS idx_rent_transactions_tenant ON rent_payment_transactions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_rent_transactions_landlord ON rent_payment_transactions(landlord_user_id);
CREATE INDEX IF NOT EXISTS idx_rent_transactions_status ON rent_payment_transactions(status);
CREATE INDEX IF NOT EXISTS idx_rent_transactions_stripe_pi ON rent_payment_transactions(stripe_payment_intent_id);

COMMENT ON TABLE rent_payment_transactions IS 'Tracks rent payment lifecycle via Stripe Connect Direct Charges';
COMMENT ON COLUMN rent_payment_transactions.payment_id IS 'Links to payments table once transaction succeeds';
COMMENT ON COLUMN rent_payment_transactions.amount_cents IS 'Payment amount in cents (150000 = $1,500.00)';
COMMENT ON COLUMN rent_payment_transactions.application_fee_cents IS 'Platform fee (2%) collected by Brikli';

-- 4. Rent Autopay Enrollments
-- Tracks autopay settings for recurring rent payments
CREATE TABLE IF NOT EXISTS rent_autopay_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Links
    lease_id INTEGER NOT NULL REFERENCES leases(id) ON DELETE CASCADE UNIQUE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    payment_method_id UUID REFERENCES tenant_payment_methods(id) ON DELETE SET NULL,
    
    -- Settings
    is_active BOOLEAN DEFAULT FALSE NOT NULL,
    amount_cents INTEGER NOT NULL,
    
    -- Retry logic
    max_retries INTEGER DEFAULT 3,
    current_retry_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    last_failure_reason TEXT,
    next_scheduled_at TIMESTAMPTZ,
    
    -- Lifecycle
    enrolled_at TIMESTAMPTZ,
    paused_at TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- Constraints
    CONSTRAINT positive_autopay_amount CHECK (amount_cents > 0),
    CONSTRAINT valid_retry_count CHECK (current_retry_count >= 0 AND current_retry_count <= max_retries)
);

CREATE INDEX IF NOT EXISTS idx_autopay_lease ON rent_autopay_enrollments(lease_id);
CREATE INDEX IF NOT EXISTS idx_autopay_active ON rent_autopay_enrollments(is_active, next_scheduled_at);
CREATE INDEX IF NOT EXISTS idx_autopay_tenant ON rent_autopay_enrollments(tenant_id);

COMMENT ON TABLE rent_autopay_enrollments IS 'Autopay settings for recurring rent collection';
COMMENT ON COLUMN rent_autopay_enrollments.next_scheduled_at IS 'When the next autopay attempt is scheduled';

-- 5. Enable RLS on all new tables
ALTER TABLE stripe_connected_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_payment_methods ENABLE ROW LEVEL SECURITY;
ALTER TABLE rent_payment_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE rent_autopay_enrollments ENABLE ROW LEVEL SECURITY;

-- 6. RLS Policies for stripe_connected_accounts
CREATE POLICY "Landlords can view their own connected account"
    ON stripe_connected_accounts FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Landlords can insert their own connected account"
    ON stripe_connected_accounts FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Landlords can update their own connected account"
    ON stripe_connected_accounts FOR UPDATE
    USING (user_id = auth.uid());

-- 7. RLS Policies for tenant_payment_methods
CREATE POLICY "Tenants can view their own payment methods"
    ON tenant_payment_methods FOR SELECT
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Tenants can manage their own payment methods"
    ON tenant_payment_methods FOR ALL
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

-- 8. RLS Policies for rent_payment_transactions
CREATE POLICY "Tenants can view their own transactions"
    ON rent_payment_transactions FOR SELECT
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Landlords can view transactions for their properties"
    ON rent_payment_transactions FOR SELECT
    USING (landlord_user_id = auth.uid());

-- 9. RLS Policies for rent_autopay_enrollments
CREATE POLICY "Tenants can view their own autopay enrollments"
    ON rent_autopay_enrollments FOR SELECT
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Tenants can manage their own autopay"
    ON rent_autopay_enrollments FOR ALL
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

-- 10. Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_rent_payment_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_connected_accounts_updated_at
    BEFORE UPDATE ON stripe_connected_accounts
    FOR EACH ROW EXECUTE FUNCTION update_rent_payment_updated_at();

CREATE TRIGGER tr_tenant_payment_methods_updated_at
    BEFORE UPDATE ON tenant_payment_methods
    FOR EACH ROW EXECUTE FUNCTION update_rent_payment_updated_at();

CREATE TRIGGER tr_rent_transactions_updated_at
    BEFORE UPDATE ON rent_payment_transactions
    FOR EACH ROW EXECUTE FUNCTION update_rent_payment_updated_at();

CREATE TRIGGER tr_autopay_enrollments_updated_at
    BEFORE UPDATE ON rent_autopay_enrollments
    FOR EACH ROW EXECUTE FUNCTION update_rent_payment_updated_at();

