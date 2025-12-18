# Tenant Rent Payments Setup

## Overview
The tenant rent payment system allows tenants to pay rent to landlords using Stripe Connect (Direct Charges). Brikli never touches the money - payments go directly from tenant to landlord, with Brikli collecting a small platform fee.

## Environment Variables Required

Add these to your `Tenant-Frontend/.env` file:

```bash
# API Configuration
VITE_API_URL=http://127.0.0.1:8000

# Supabase Configuration
VITE_SUPABASE_URL=http://127.0.0.1:54321
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key

# Stripe Configuration (REQUIRED for rent payments)
VITE_STRIPE_PUBLISHABLE_KEY=your-stripe-publishable-key

# Sentry (optional)
VITE_SENTRY_DSN=your-sentry-dsn
```

## Features Implemented

### 1. Payment Methods
- **Add Payment Methods**: Tenants can save bank accounts (PAD) or cards
- **Manage Methods**: View, set default, and remove saved payment methods
- **Security**: Uses Stripe SetupIntent for secure verification

### 2. Rent Payments
- **Pay Rent**: One-time rent payments with live balance display
- **Payment Breakdown**: Shows rent amount, platform fee, and total charge
- **Multiple Methods**: Pay with saved methods or enter new payment details
- **Real-time Status**: Instant payment confirmation with toast notifications

### 3. Autopay
- **Enroll**: Set up automatic monthly rent payments
- **Customize**: Choose payment method and day of month (1-28)
- **Manage**: View status and cancel anytime
- **Notifications**: Receive notifications after each autopay transaction

### 4. Payment History
- **Transaction Log**: View all past rent payments
- **Status Tracking**: See pending, succeeded, or failed payments
- **Details**: Amount, date, payment method for each transaction

## Platform Fees

- **Bank Transfer (PAD)**: $3.00 per transaction
- **Credit/Debit Card**: $8.00 per transaction

The fee is charged to the tenant on top of the rent amount.

## File Structure

```
Tenant-Frontend/src/
├── types/
│   └── payments.ts                    # Payment type definitions
├── utils/api/
│   └── payments.ts                    # Payment API functions
├── hooks/
│   └── usePayments.ts                 # TanStack Query hooks
├── components/payments/
│   ├── PayRentModal.tsx              # Main payment modal with Stripe Elements
│   ├── AddPaymentMethodModal.tsx     # Add/save payment methods
│   ├── SetupAutopayModal.tsx         # Autopay enrollment
│   ├── CurrentBalance.tsx            # Displays rent balance (updated)
│   ├── PaymentMethods.tsx            # Payment methods list (updated)
│   └── PaymentHistory.tsx            # Transaction history (updated)
└── pages/
    └── Payments.tsx                   # Main payments page (fully integrated)
```

## API Endpoints Used

### Balance & Fees
- `GET /api/rent-payments/balance` - Get tenant's current rent balance
- `GET /api/rent-payments/fees` - Get platform fees by payment method

### Payment Methods
- `POST /api/rent-payments/payment-methods/setup-intent` - Create SetupIntent
- `POST /api/rent-payments/payment-methods` - Save payment method
- `GET /api/rent-payments/payment-methods` - List saved methods
- `DELETE /api/rent-payments/payment-methods/{id}` - Remove method
- `POST /api/rent-payments/payment-methods/{id}/default` - Set default

### Payments
- `POST /api/rent-payments/pay` - Create PaymentIntent for rent
- `GET /api/rent-payments/transactions` - Get transaction history
- `GET /api/rent-payments/transactions/{id}` - Get specific transaction

### Autopay
- `POST /api/rent-payments/autopay/enroll` - Enroll in autopay
- `GET /api/rent-payments/autopay/status` - Get enrollment status
- `POST /api/rent-payments/autopay/cancel` - Cancel autopay

## Testing

1. **Start Backend**: `cd Backend && poetry run uvicorn Backend.api.app:app --reload`
2. **Start Supabase**: `supabase start`
3. **Start Frontend**: `cd Tenant-Frontend && npm run dev`
4. Navigate to `/payments` as a tenant user

### Test Flow
1. Add a payment method (use Stripe test cards)
2. View current balance
3. Make a rent payment
4. Check payment history
5. Set up autopay
6. Manage autopay settings

### Stripe Test Cards
- **Visa**: `4242 4242 4242 4242`
- **Mastercard**: `5555 5555 5555 4444`
- **Declined**: `4000 0000 0000 0002`

Use any future expiry date and any 3-digit CVC.

## Integration Checklist

- [x] Stripe React libraries installed
- [x] Payment types defined
- [x] API utility functions created
- [x] TanStack Query hooks implemented
- [x] PayRentModal with Stripe Elements
- [x] AddPaymentMethodModal with SetupIntent
- [x] SetupAutopayModal with enrollment logic
- [x] Payments.tsx fully integrated
- [x] Error handling with Sentry
- [x] Toast notifications
- [ ] Add `.env` file with `VITE_STRIPE_PUBLISHABLE_KEY`
- [ ] Test with real tenant account

## Next Steps

### For Landlords (Frontend Portal)
Already completed! Landlords can:
- Complete Stripe Connect onboarding
- View payout status in PaymentsTab
- Access Stripe Dashboard for payouts
- See online payment transactions in the ledger

### For Tenants (This Portal)
All features are now implemented and ready for testing!

## Notes

- All monetary values are stored in cents in the database
- Currency formatted as CAD (Canadian Dollars)
- Stripe Elements handles PCI compliance
- Direct Charges model: money goes directly from tenant to landlord
- Platform fees collected via `application_fee_amount` in Stripe


