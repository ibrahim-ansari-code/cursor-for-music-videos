# Rent Payment System Implementation Plan

## Overview

Enable tenants on the Tenant Portal to pay rent directly to landlords on the Landlord Portal via **Stripe Connect Direct Charges**. Brikli never touches the money—funds flow directly from tenant to landlord, with Brikli collecting a 2% application fee.

### Key Decisions

| Decision | Choice |
|----------|--------|
| Geography | Canada only |
| Stripe Model | Direct Charges (landlord is merchant of record) |
| Platform Fee | 2% (paid by landlord, deducted from payout) |
| Primary Payment Method | Pre-authorized Debit (PAD/ACSS) |
| Secondary Payment Method | Card payments |
| Landlord Dashboard | Embedded in Brikli (not Stripe Express Dashboard) |

### Money Flow

```text
Tenant pays $1,500 rent
    │
    ▼
Stripe processes on Landlord's Connected Account
    │
    ├── Landlord receives: ~$1,455 (after Stripe fees + 2% Brikli fee)
    ├── Brikli receives: $30 (2% application fee)
    └── Stripe receives: ~$15 (processing fees)
```

---

## Phase 1: Database Schema

### New Tables

```sql
-- 1. Stripe Connected Accounts (Landlords)
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_connected_accounts_user ON stripe_connected_accounts(user_id);
CREATE INDEX idx_connected_accounts_stripe ON stripe_connected_accounts(stripe_account_id);

-- 2. Rent Payment Transactions
CREATE TABLE rent_payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Links to existing system
    payment_id INTEGER REFERENCES payments(id),  -- Creates record in existing payments table
    lease_id INTEGER NOT NULL REFERENCES leases(id),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    landlord_user_id UUID NOT NULL REFERENCES users(id),
    connected_account_id UUID REFERENCES stripe_connected_accounts(id),
    
    -- Stripe References
    stripe_payment_intent_id VARCHAR(255) UNIQUE,
    stripe_charge_id VARCHAR(255),
    
    -- Amounts (stored in cents for precision)
    amount_cents INTEGER NOT NULL,
    application_fee_cents INTEGER NOT NULL,  -- 2% fee
    currency VARCHAR(3) DEFAULT 'cad',
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- pending, requires_action, processing, succeeded, failed, canceled, refunded
    failure_code VARCHAR(100),
    failure_message TEXT,
    
    -- Payment Method Details
    payment_method_type VARCHAR(50),  -- acss_debit, card
    payment_method_last_four VARCHAR(4),
    bank_name VARCHAR(255),
    
    -- Timestamps
    initiated_at TIMESTAMPTZ DEFAULT NOW(),
    authorized_at TIMESTAMPTZ,
    succeeded_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rent_transactions_lease ON rent_payment_transactions(lease_id);
CREATE INDEX idx_rent_transactions_tenant ON rent_payment_transactions(tenant_id);
CREATE INDEX idx_rent_transactions_landlord ON rent_payment_transactions(landlord_user_id);
CREATE INDEX idx_rent_transactions_status ON rent_payment_transactions(status);
CREATE INDEX idx_rent_transactions_stripe_pi ON rent_payment_transactions(stripe_payment_intent_id);

-- 3. Tenant Payment Methods (for saved PAD/cards)
CREATE TABLE tenant_payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    stripe_payment_method_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- Type Info
    payment_method_type VARCHAR(50) NOT NULL,  -- acss_debit, card
    
    -- Display Info
    last_four VARCHAR(4),
    bank_name VARCHAR(255),       -- For bank accounts
    brand VARCHAR(50),            -- For cards (visa, mastercard)
    
    -- Status
    is_default BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,  -- For PAD microdeposit verification
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tenant_payment_methods_tenant ON tenant_payment_methods(tenant_id);
CREATE UNIQUE INDEX idx_tenant_default_payment ON tenant_payment_methods(tenant_id) 
    WHERE is_default = TRUE;

-- 4. Autopay Enrollments
CREATE TABLE rent_autopay_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lease_id INTEGER NOT NULL REFERENCES leases(id) ON DELETE CASCADE UNIQUE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    payment_method_id UUID REFERENCES tenant_payment_methods(id),
    
    -- Schedule (uses rent_due_day from lease)
    is_active BOOLEAN DEFAULT FALSE,
    amount_cents INTEGER NOT NULL,
    
    -- Retry Logic
    max_retries INTEGER DEFAULT 3,
    retry_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    next_scheduled_at TIMESTAMPTZ,
    
    -- Timestamps
    enrolled_at TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_autopay_lease ON rent_autopay_enrollments(lease_id);
CREATE INDEX idx_autopay_active ON rent_autopay_enrollments(is_active, next_scheduled_at);
```

---

## Phase 2: Backend Implementation

### File Structure

```text
Backend/api/rent_payments/
├── __init__.py
├── router.py              # FastAPI endpoints
├── schemas.py             # Pydantic request/response models
├── service.py             # Core payment logic
├── connect_service.py     # Stripe Connect onboarding
├── webhooks.py            # Stripe webhook handlers
└── constants.py           # Fee rates, status enums
```

### API Endpoints

#### Connect (Landlord Onboarding)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rent-payments/connect/onboard` | Create Express account & return onboarding link |
| GET | `/api/rent-payments/connect/status` | Check onboarding completion status |
| POST | `/api/rent-payments/connect/dashboard-link` | Generate login link for Express dashboard |
| POST | `/api/rent-payments/connect/refresh-link` | Refresh expired onboarding link |

#### Payment Methods (Tenant)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rent-payments/setup-intent` | Create SetupIntent for adding payment method |
| POST | `/api/rent-payments/payment-methods` | Save payment method after Stripe confirmation |
| GET | `/api/rent-payments/payment-methods` | List tenant's saved payment methods |
| DELETE | `/api/rent-payments/payment-methods/{id}` | Remove a payment method |
| PUT | `/api/rent-payments/payment-methods/{id}/default` | Set as default |

#### Payments (Tenant)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/rent-payments/balance` | Get current balance for tenant's lease |
| POST | `/api/rent-payments/pay` | Initiate rent payment |
| GET | `/api/rent-payments/transactions` | List payment history |
| GET | `/api/rent-payments/transactions/{id}` | Get transaction details |

#### Autopay (Tenant)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rent-payments/autopay/enroll` | Enable autopay for lease |
| GET | `/api/rent-payments/autopay/status` | Check autopay enrollment |
| PUT | `/api/rent-payments/autopay/settings` | Update payment method/settings |
| DELETE | `/api/rent-payments/autopay` | Cancel autopay |

#### Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rent-payments/webhooks/stripe` | Handle Stripe Connect webhooks |

### Key Service Functions

```python
# connect_service.py
async def create_connected_account(user: User) -> ConnectOnboardingResponse
async def create_account_link(user: User) -> str
async def get_connect_status(user: User) -> ConnectStatusResponse
async def handle_account_updated(event: stripe.Event) -> None

# service.py
async def get_tenant_balance(tenant_id: int) -> TenantBalanceResponse
async def create_payment_intent(tenant: Tenant, lease: Lease, amount: Decimal) -> PaymentIntentResponse
async def confirm_payment(transaction_id: UUID) -> RentPaymentResponse
async def process_autopay_payments() -> list[RentPaymentResponse]  # Called by scheduler

# webhooks.py
async def handle_payment_intent_succeeded(event: stripe.Event) -> None
async def handle_payment_intent_failed(event: stripe.Event) -> None
async def handle_charge_refunded(event: stripe.Event) -> None
```

### Fee Calculation

```python
# constants.py
PLATFORM_FEE_RATE = Decimal("0.02")  # 2%

def calculate_application_fee(amount_cents: int) -> int:
    """Calculate 2% platform fee in cents."""
    fee = int(amount_cents * PLATFORM_FEE_RATE)
    return max(fee, 50)  # Minimum 50 cents
```

---

## Phase 3: Tenant Portal Frontend

### New Components

```text
Tenant-Frontend/src/
├── components/payments/
│   ├── PayRentModal.tsx           # Payment flow modal
│   ├── AddPaymentMethodModal.tsx  # Stripe Elements for PAD/card
│   ├── SetupAutopayModal.tsx      # Autopay enrollment
│   ├── PaymentConfirmation.tsx    # Success/failure states
│   └── PADMandateTerms.tsx        # Canadian PAD authorization text
├── hooks/
│   ├── useRentPayments.ts         # React Query hooks
│   └── useStripeElements.ts       # Stripe.js integration
└── utils/api/
    └── rentPayments.ts            # API client functions
```

### Payment Flow (Tenant)

```text
1. Tenant clicks "Make a Payment"
   │
2. PayRentModal opens
   │  - Shows current balance
   │  - Shows saved payment methods (or add new)
   │  - Shows PAD mandate terms for bank payments
   │
3. Tenant selects/adds payment method
   │  - Card: Stripe CardElement
   │  - Bank: Stripe PaymentElement with acss_debit
   │
4. Tenant confirms payment
   │  - API creates PaymentIntent on landlord's Connected Account
   │  - Frontend confirms with Stripe.js
   │
5. Payment processing
   │  - PAD: 3-5 business days to settle
   │  - Card: Instant confirmation
   │
6. Webhook updates transaction status
   │
7. Record created in payments table (landlord sees in PaymentsTab)
```

### Key UI States

| State | Display |
|-------|---------|
| No balance | "You're all caught up!" |
| Balance due | Amount + due date + "Make a Payment" button |
| Processing | "Payment processing..." with spinner |
| PAD pending | "Payment initiated - funds will be withdrawn in 3-5 days" |
| Success | Confetti + receipt download |
| Failed | Error message + retry option |

---

## Phase 4: Landlord Portal Frontend

### New Components

```text
Frontend/src/
├── components/settings/
│   └── PayoutSettings.jsx         # Connect onboarding UI
├── components/accounting/
│   └── PaymentsTab.jsx            # Add "Online Payment" badge
└── utils/api/
    └── connect.js                 # Connect API client
```

### Landlord Onboarding Flow

```text
1. Landlord goes to Settings → Payouts
   │
2. "Set up Online Payments" CTA
   │  - Explains 2% fee
   │  - Shows benefits (automatic tracking, etc.)
   │
3. Click "Connect with Stripe"
   │  - Creates Express account
   │  - Redirects to Stripe-hosted onboarding
   │
4. Stripe collects:
   │  - Business info
   │  - Bank account for payouts
   │  - Identity verification
   │
5. Redirect back to Brikli
   │  - Webhook confirms account ready
   │  - "Online Payments Active" badge shown
   │
6. Tenants can now pay this landlord online
```

### PaymentsTab Updates

Add "Source" column to show:

- **Brikli** - Manual entry
- **QuickBooks** - Synced from QB
- **Online** - Paid via Stripe (NEW)

Add filter for payment source.

---

## Phase 5: Webhooks & Background Jobs

### Stripe Webhooks to Handle

| Event | Action |
|-------|--------|
| `account.updated` | Update connected account status |
| `payment_intent.succeeded` | Mark transaction succeeded, create payment record |
| `payment_intent.payment_failed` | Mark transaction failed, notify tenant |
| `charge.refunded` | Update transaction status |
| `payment_method.attached` | Confirm payment method saved |

### Background Jobs (pg_cron or Celery)

| Job | Schedule | Description |
|-----|----------|-------------|
| `process_autopay` | Daily 6am | Process autopay for due payments |
| `retry_failed_payments` | Daily 9am | Retry failed autopay (up to 3x) |
| `send_payment_reminders` | Daily 8am | Remind tenants of upcoming due dates |
| `sync_connect_status` | Hourly | Refresh connected account status |

---

## Phase 6: Testing Strategy

### Unit Tests

- Fee calculation accuracy
- Payment status state machine
- Webhook signature verification
- Authorization checks (tenant can only pay their own lease)

### Integration Tests

- Full payment flow with Stripe test mode
- Connect onboarding flow
- Webhook processing
- Autopay scheduling

### Stripe Test Data

```text
# Test bank account (Canada PAD)
Institution: 000
Transit: 11000
Account: 000123456789

# Test card
Number: 4242 4242 4242 4242
Expiry: Any future date
CVC: Any 3 digits
```

---

## Implementation Order

### Week 1: Foundation

- [ ] Database migration
- [ ] Backend models (`stripe_connected_account.py`, `rent_payment_transaction.py`)
- [ ] Schemas and constants
- [ ] Extend Stripe client with Connect methods

### Week 2: Landlord Connect

- [ ] Connect onboarding endpoints
- [ ] Account link generation
- [ ] Webhook handler for `account.updated`
- [ ] Landlord frontend: PayoutSettings component

### Week 3: Tenant Payment Methods

- [ ] SetupIntent creation
- [ ] Payment method CRUD endpoints
- [ ] Tenant frontend: AddPaymentMethodModal
- [ ] PAD mandate terms component

### Week 4: Payment Flow

- [ ] PaymentIntent creation with Direct Charges
- [ ] Transaction tracking
- [ ] Payment webhooks
- [ ] Tenant frontend: PayRentModal, PaymentHistory integration

### Week 5: Autopay & Polish

- [ ] Autopay enrollment endpoints
- [ ] Background job for autopay processing
- [ ] Retry logic
- [ ] Tenant frontend: SetupAutopayModal

### Week 6: Integration & Testing

- [ ] Connect payments to existing `payments` table
- [ ] Update PaymentsTab to show online payments
- [ ] Full E2E testing
- [ ] Error handling and edge cases

---

## Environment Variables

```bash
# Backend/.env (new additions)
STRIPE_CONNECT_WEBHOOK_SECRET=whsec_xxx      # Separate webhook for Connect
STRIPE_PLATFORM_FEE_PERCENT=2                # Configurable fee rate

# Frontend/.env (new additions)  
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_xxx      # For Stripe.js

# Tenant-Frontend/.env (new additions)
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_xxx      # For Stripe.js
```

---

## Security Considerations

1. **Idempotency**: Use idempotency keys for all payment creation
2. **Webhook Verification**: Verify Stripe signatures on all webhooks
3. **Authorization**: Tenants can only pay their own leases
4. **PCI Compliance**: Never handle raw card data (use Stripe Elements)
5. **PAD Compliance**: Display proper mandate language for Canadian regulations
6. **Rate Limiting**: Protect payment endpoints from abuse

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Landlord Connect completion rate | > 80% |
| Payment success rate | > 95% |
| Autopay enrollment | > 50% of tenants |
| Time to first payment | < 5 minutes |
| Webhook processing time | < 2 seconds |

---

## Rollback Plan

If issues arise:

1. Disable Connect onboarding (feature flag)
2. Mark existing connected accounts inactive
3. Hide payment UI in tenant portal
4. Existing manual payment recording continues to work
5. No data loss - transactions table serves as audit log
