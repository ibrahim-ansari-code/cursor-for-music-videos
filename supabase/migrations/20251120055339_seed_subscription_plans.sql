-- Seed subscription plans
-- This migration was applied via MCP during development

INSERT INTO billing.subscription_plans (
    name,
    description,
    stripe_product_id,
    stripe_price_id,
    amount,
    currency,
    interval,
    interval_count,
    trial_period_days,
    is_active,
    features
)
SELECT
    'Brikli Premium',
    'Full access to Brikli property management platform - Unlimited properties, tenants, advanced reporting, QuickBooks integration, and priority support',
    'prod_TS44IXJeF5Bsn8',
    'price_1SV9ziKoVREUyxXN2WL5Wbzb',
    99.99,
    'CAD',
    'month',
    1,
    14,
    true,
    to_jsonb(ARRAY['Unlimited properties', 'Unlimited tenants', 'Advanced reporting', 'QuickBooks integration', 'Priority support', 'AI-powered receipt parsing', 'Maintenance tracking', 'Lease management', 'Payment tracking', 'Financial analytics'])
WHERE NOT EXISTS (
    SELECT 1 FROM billing.subscription_plans WHERE stripe_price_id = 'price_1SV9ziKoVREUyxXN2WL5Wbzb'
);


