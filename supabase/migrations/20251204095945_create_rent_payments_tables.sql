-- ============================================================================
-- Rent Payments System Tables
-- Enables tenant-to-landlord payments via Stripe Connect Direct Charges
-- ============================================================================

-- 1. Stripe Connected Accounts (Landlords)
-- Stores Stripe Express account info for landlords receiving payouts
CREATE TABLE stripe_connected_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    stripe_account_id VARCHAR(255) NOT NULL UNIQUE,  -- acct_xxx
    
    -- Onboarding Status
    charges_enabled BOOLEAN DEFAULT FALSE,
    payouts_enabled BOOLEAN DEFAULT FALSE,
    details_submitted BOOLEAN DEFAULT FALSE,
    
    -- Account Details (cached from Stripe)
    business_type VARCHAR(50),  -- individual, company
    country VARCHAR(2) DEFAULT 'CA',
    default_currency VARCHAR(3) DEFAULT 'cad',
    
    -- Timestamps
    onboarding_completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_connected_accounts_user ON stripe_connected_accounts(user_id);
CREATE INDEX idx_connected_accounts_stripe ON stripe_connected_accounts(stripe_account_id);

COMMENT ON TABLE stripe_connected_accounts IS 'Stripe Express accounts for landlords to receive rent payments';
COMMENT ON COLUMN stripe_connected_accounts.charges_enabled IS 'Whether the account can accept charges';
COMMENT ON COLUMN stripe_connected_accounts.payouts_enabled IS 'Whether the account can receive payouts';

-- 2. Tenant Payment Methods
-- Stores saved PAD bank accounts and cards for tenants
CREATE TABLE tenant_payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    stripe_payment_method_id VARCHAR(255) NOT NULL UNIQUE,  -- pm_xxx
    
    -- Type Info
    payment_method_type VARCHAR(50) NOT NULL,  -- acss_debit, card
    
    -- Display Info
    last_four VARCHAR(4),
    bank_name VARCHAR(255),       -- For bank accounts
    institution_number VARCHAR(10), -- Canadian institution number
    brand VARCHAR(50),            -- For cards (visa, mastercard)
    exp_month INTEGER,            -- Card expiry month
    exp_year INTEGER,             -- Card expiry year
    
    -- Status
    is_default BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,  -- For PAD microdeposit verification
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_tenant_payment_methods_tenant ON tenant_payment_methods(tenant_id);
CREATE UNIQUE INDEX idx_tenant_default_payment ON tenant_payment_methods(tenant_id) 
    WHERE is_default = TRUE;

COMMENT ON TABLE tenant_payment_methods IS 'Saved payment methods (PAD bank accounts, cards) for tenants';
COMMENT ON COLUMN tenant_payment_methods.is_verified IS 'For PAD: whether microdeposit verification is complete';

-- 3. Rent Payment Transactions
-- Tracks all rent payment attempts and their status
CREATE TABLE rent_payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Links to existing system
    payment_id INTEGER REFERENCES payments(id) ON DELETE SET NULL,  -- Created on success
    lease_id INTEGER NOT NULL REFERENCES leases(id),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    landlord_user_id UUID NOT NULL REFERENCES users(id),
    connected_account_id UUID REFERENCES stripe_connected_accounts(id),
    payment_method_id UUID REFERENCES tenant_payment_methods(id),
    
    -- Stripe References
    stripe_payment_intent_id VARCHAR(255) UNIQUE,  -- pi_xxx
    stripe_charge_id VARCHAR(255),                  -- ch_xxx
    
    -- Amounts (stored in cents for precision)
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    application_fee_cents INTEGER NOT NULL DEFAULT 0 CHECK (application_fee_cents >= 0),
    currency VARCHAR(3) DEFAULT 'cad' NOT NULL,
    
    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'requires_action', 'requires_payment_method', 
                          'processing', 'succeeded', 'failed', 'canceled', 'refunded')),
    failure_code VARCHAR(100),
    failure_message TEXT,
    
    -- Payment Method Details (denormalized for history)
    payment_method_type VARCHAR(50),  -- acss_debit, card
    payment_method_last_four VARCHAR(4),
    payment_method_bank_name VARCHAR(255),
    
    -- Timestamps
    initiated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    authorized_at TIMESTAMPTZ,
    succeeded_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    refunded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_rent_transactions_lease ON rent_payment_transactions(lease_id);
CREATE INDEX idx_rent_transactions_tenant ON rent_payment_transactions(tenant_id);
CREATE INDEX idx_rent_transactions_landlord ON rent_payment_transactions(landlord_user_id);
CREATE INDEX idx_rent_transactions_status ON rent_payment_transactions(status);
CREATE INDEX idx_rent_transactions_stripe_pi ON rent_payment_transactions(stripe_payment_intent_id);
CREATE INDEX idx_rent_transactions_created ON rent_payment_transactions(created_at DESC);

COMMENT ON TABLE rent_payment_transactions IS 'All rent payment attempts via Stripe Connect Direct Charges';
COMMENT ON COLUMN rent_payment_transactions.payment_id IS 'Links to payments table once transaction succeeds';
COMMENT ON COLUMN rent_payment_transactions.amount_cents IS 'Payment amount in cents (e.g., 150000 = $1,500.00)';
COMMENT ON COLUMN rent_payment_transactions.application_fee_cents IS '2% platform fee in cents';

-- 4. Rent Autopay Enrollments
-- Tracks autopay settings per lease
CREATE TABLE rent_autopay_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lease_id INTEGER NOT NULL REFERENCES leases(id) ON DELETE CASCADE UNIQUE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    payment_method_id UUID REFERENCES tenant_payment_methods(id) ON DELETE SET NULL,
    
    -- Schedule (day of month comes from lease.rent_due_day)
    is_active BOOLEAN DEFAULT FALSE NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    
    -- Retry Logic
    max_retries INTEGER DEFAULT 3 NOT NULL,
    current_retry_count INTEGER DEFAULT 0 NOT NULL,
    last_attempt_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    last_failure_reason TEXT,
    next_scheduled_at TIMESTAMPTZ,
    
    -- Timestamps
    enrolled_at TIMESTAMPTZ,
    paused_at TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_autopay_lease ON rent_autopay_enrollments(lease_id);
CREATE INDEX idx_autopay_tenant ON rent_autopay_enrollments(tenant_id);
CREATE INDEX idx_autopay_active_scheduled ON rent_autopay_enrollments(is_active, next_scheduled_at) 
    WHERE is_active = TRUE;

COMMENT ON TABLE rent_autopay_enrollments IS 'Autopay enrollment settings for recurring rent payments';
COMMENT ON COLUMN rent_autopay_enrollments.next_scheduled_at IS 'Next date autopay will attempt to charge';

-- ============================================================================
-- Row Level Security Policies
-- ============================================================================

-- Enable RLS on all new tables
ALTER TABLE stripe_connected_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_payment_methods ENABLE ROW LEVEL SECURITY;
ALTER TABLE rent_payment_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE rent_autopay_enrollments ENABLE ROW LEVEL SECURITY;

-- stripe_connected_accounts: Landlords can only see their own
CREATE POLICY "Users can view own connected account"
    ON stripe_connected_accounts FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can insert own connected account"
    ON stripe_connected_accounts FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own connected account"
    ON stripe_connected_accounts FOR UPDATE
    USING (user_id = auth.uid());

-- tenant_payment_methods: Access via tenant's user_id
CREATE POLICY "Tenants can view own payment methods"
    ON tenant_payment_methods FOR SELECT
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Tenants can insert own payment methods"
    ON tenant_payment_methods FOR INSERT
    WITH CHECK (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Tenants can update own payment methods"
    ON tenant_payment_methods FOR UPDATE
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Tenants can delete own payment methods"
    ON tenant_payment_methods FOR DELETE
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

-- rent_payment_transactions: Tenants see own, Landlords see payments to them
CREATE POLICY "Tenants can view own transactions"
    ON rent_payment_transactions FOR SELECT
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Landlords can view transactions to them"
    ON rent_payment_transactions FOR SELECT
    USING (landlord_user_id = auth.uid());

CREATE POLICY "Tenants can insert own transactions"
    ON rent_payment_transactions FOR INSERT
    WITH CHECK (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

-- rent_autopay_enrollments: Tenants manage own autopay
CREATE POLICY "Tenants can view own autopay"
    ON rent_autopay_enrollments FOR SELECT
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Tenants can insert own autopay"
    ON rent_autopay_enrollments FOR INSERT
    WITH CHECK (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Tenants can update own autopay"
    ON rent_autopay_enrollments FOR UPDATE
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Tenants can delete own autopay"
    ON rent_autopay_enrollments FOR DELETE
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

-- Landlords can view autopay for their tenants
CREATE POLICY "Landlords can view tenant autopay"
    ON rent_autopay_enrollments FOR SELECT
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE landlord_id = auth.uid()
        )
    );

