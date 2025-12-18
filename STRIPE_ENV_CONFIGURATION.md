# Stripe Billing - Environment Configuration

## 🎯 Overview

This guide provides the complete environment variable configuration required for Stripe billing integration in both development and production environments.

## 📋 Required Environment Variables

### Backend (.env)

```bash
# ============================================================
# STRIPE CONFIGURATION (Required for Billing)
# ============================================================

# Stripe API Keys
# Get from: https://dashboard.stripe.com/apikeys
STRIPE_API_KEY=sk_live_xxxxxxxxxxxxxxxxxxxxx              # Production: sk_live_*
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxxxxxxxxxxx      # Production: pk_live_*

# Stripe Price ID for Platform Subscription
# Get from: https://dashboard.stripe.com/products (after creating product)
STRIPE_PRICE_ID_PLATFORM=price_xxxxxxxxxxxxxxxxxxxxx      # Your $99.99 CAD/month price ID

# Stripe Webhook Secret
# Get from: https://dashboard.stripe.com/webhooks (after creating webhook)
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxx         # Webhook signing secret

# Billing Portal Configuration
STRIPE_BILLING_PORTAL_RETURN_URL=https://app.brikli.com/settings?tab=billing

# Trial Period (days)
STRIPE_TRIAL_PERIOD_DAYS=14
```

### Development Environment

For local development, use Stripe **test mode** keys:

```bash
# Development/Local (.env)
STRIPE_API_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxx              # Test mode key
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxx      # Test mode key
STRIPE_PRICE_ID_PLATFORM=price_xxxxxxxxxxxxxxxxxxxxx      # Test mode price ID
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxx         # Test webhook secret
STRIPE_BILLING_PORTAL_RETURN_URL=http://localhost:5173/settings?tab=billing
STRIPE_TRIAL_PERIOD_DAYS=14
```

### Frontend (.env)

```bash
# ============================================================
# STRIPE CONFIGURATION (Frontend)
# ============================================================

# Stripe Publishable Key (safe to expose in frontend)
VITE_STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxxxxxxxxxxx  # Production
# VITE_STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxx  # Development
```

---

## 🚀 Setup Steps

### Step 1: Create Stripe Product & Price

1. **Go to Stripe Dashboard** → [Products](https://dashboard.stripe.com/products)
2. **Click "Add product"**
   - **Name**: Brikli Platform Subscription
   - **Description**: Monthly subscription to Brikli property management platform
   - **Pricing Model**: Standard pricing
   - **Price**: $99.99 CAD
   - **Billing Period**: Monthly
   - **Currency**: CAD
3. **Click "Save product"**
4. **Copy the Price ID** (starts with `price_`) → Use for `STRIPE_PRICE_ID_PLATFORM`

### Step 2: Get API Keys

1. **Go to** [API Keys](https://dashboard.stripe.com/apikeys)
2. **Copy** the following:
   - **Publishable key** (starts with `pk_live_` or `pk_test_`)
   - **Secret key** (starts with `sk_live_` or `sk_test_`)
   - ⚠️ **Never commit secret keys to git**

### Step 3: Create Webhook Endpoint

1. **Go to** [Webhooks](https://dashboard.stripe.com/webhooks)
2. **Click "Add endpoint"**
3. **Endpoint URL**: `https://api.brikli.com/api/billing/webhook`
   - For local testing: Use [ngrok](https://ngrok.com) or Stripe CLI
4. **Description**: Brikli subscription webhooks
5. **Events to send**: Select these events:
   - ✅ `customer.subscription.created`
   - ✅ `customer.subscription.updated`
   - ✅ `customer.subscription.deleted`
   - ✅ `invoice.payment_succeeded`
   - ✅ `invoice.payment_failed`
   - ✅ `customer.subscription.trial_will_end` (optional, for reminders)
6. **Click "Add endpoint"**
7. **Copy the Signing secret** (starts with `whsec_`) → Use for `STRIPE_WEBHOOK_SECRET`

### Step 4: Configure Customer Portal

1. **Go to** [Customer Portal Settings](https://dashboard.stripe.com/settings/billing/portal)
2. **Enable** the following features:
   - ✅ Invoice history
   - ✅ Update payment methods
   - ✅ Cancel subscriptions (enable "Prevent cancellation" for retention)
3. **Cancellation behavior**:
   - ✅ "At the end of the billing period" (recommended)
   - ✅ Show cancellation survey (optional)
4. **Save settings**

---

## 🧪 Testing with Stripe CLI (Development)

### Install Stripe CLI

```bash
# macOS
brew install stripe/stripe-cli/stripe

# Verify installation
stripe --version
```

### Login to Stripe

```bash
stripe login
```

### Forward Webhooks to Local Backend

```bash
# Start local webhook forwarding
stripe listen --forward-to http://localhost:8000/api/billing/webhook

# Copy the webhook signing secret (whsec_xxx) to your .env
```

### Test Webhook Events

```bash
# Trigger subscription created event
stripe trigger customer.subscription.created

# Trigger payment succeeded event
stripe trigger invoice.payment_succeeded

# Trigger payment failed event
stripe trigger invoice.payment_failed
```

### Test Cards

Use these test card numbers in Stripe Checkout:

| Card Number         | Scenario                    |
|--------------------|-----------------------------|
| 4242 4242 4242 4242 | Success                     |
| 4000 0000 0000 0002 | Card declined               |
| 4000 0000 0000 9995 | Insufficient funds          |
| 4000 0025 0000 3155 | Requires authentication     |

**Expiry**: Any future date  
**CVC**: Any 3 digits  
**Postal**: Any valid postal code

---

## 🔐 Security Checklist

- [ ] ✅ Never commit `STRIPE_API_KEY` or `STRIPE_WEBHOOK_SECRET` to git
- [ ] ✅ Use test mode keys (`sk_test_*`) in development
- [ ] ✅ Use live mode keys (`sk_live_*`) only in production
- [ ] ✅ Rotate webhook secrets if compromised
- [ ] ✅ Enable webhook signature verification (already implemented)
- [ ] ✅ Use environment variables for all sensitive data
- [ ] ✅ Restrict API key permissions if possible

---

## 📊 Monitoring & Alerts

### Stripe Dashboard

Monitor the following in production:

1. **[Subscriptions](https://dashboard.stripe.com/subscriptions)** - Active user base
2. **[Revenue](https://dashboard.stripe.com/revenue)** - MRR tracking
3. **[Failed Payments](https://dashboard.stripe.com/payments?status%5B%5D=failed)** - Payment issues
4. **[Webhook Logs](https://dashboard.stripe.com/webhooks)** - Integration health

### Set Up Alerts

In Stripe Dashboard → [Notifications](https://dashboard.stripe.com/settings/notifications):

- [ ] ✅ Payment failures
- [ ] ✅ Subscription cancellations
- [ ] ✅ Trial ending soon
- [ ] ✅ Dispute notifications

---

## 🚨 Common Issues & Solutions

### Issue: Webhook Signature Verification Failed

**Cause**: Incorrect `STRIPE_WEBHOOK_SECRET` or webhook endpoint mismatch.

**Solution**:

1. Verify webhook secret from Stripe Dashboard
2. Ensure endpoint URL matches exactly: `/api/billing/webhook`
3. Check webhook is not disabled in Stripe Dashboard

### Issue: "Subscription Required" on all routes

**Cause**: User doesn't have trial or subscription.

**Solution**:

1. Check user's `subscription_status` and `trial_ends_at` in database
2. Manually grant trial: `UPDATE users SET trial_ends_at = NOW() + INTERVAL '14 days' WHERE email = 'user@example.com';`
3. Or bypass by setting `is_admin = true` temporarily

### Issue: Price ID not found

**Cause**: `STRIPE_PRICE_ID_PLATFORM` doesn't match Stripe Dashboard.

**Solution**:

1. Go to Stripe Dashboard → Products
2. Copy the correct Price ID (starts with `price_`)
3. Update environment variable and restart backend

---

## 📈 Production Deployment Checklist

### Before Merging to Main

- [ ] ✅ All environment variables configured in production
- [ ] ✅ Webhook endpoint created with production URL
- [ ] ✅ Webhook secret added to production env
- [ ] ✅ Product and price created in Stripe (live mode)
- [ ] ✅ Customer portal configured
- [ ] ✅ Stripe email notifications enabled
- [ ] ✅ Test subscription flow in staging

### After Migration Runs

- [ ] ✅ Verify `billing` schema created in database
- [ ] ✅ Verify `users` table has new billing columns
- [ ] ✅ Test webhook endpoint: `curl -X POST https://api.brikli.com/api/billing/webhook`
- [ ] ✅ Create test subscription and verify webhook processing
- [ ] ✅ Verify Sentry error tracking for billing events

### Monitoring Setup

- [ ] ✅ Monitor Sentry for billing errors
- [ ] ✅ Set up Stripe alerts in Dashboard
- [ ] ✅ Track subscription metrics (MRR, churn rate)
- [ ] ✅ Monitor failed payment recovery

---

## 🎓 Additional Resources

- [Stripe API Documentation](https://stripe.com/docs/api)
- [Stripe Billing Best Practices](https://stripe.com/docs/billing/best-practices)
- [Webhook Integration Guide](https://stripe.com/docs/webhooks/best-practices)
- [Testing Guide](https://stripe.com/docs/testing)
- [Customer Portal Guide](https://stripe.com/docs/customer-management/portal)

---

## 💬 Support

For billing-related issues:

- **Stripe Support**: <https://support.stripe.com>
- **Brikli Internal**: Check `Backend/api/billing/` for implementation details
- **Logs**: Check Sentry and Stripe webhook logs for debugging
