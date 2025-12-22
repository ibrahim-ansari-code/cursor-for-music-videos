-- Add accepted_payment_methods column to stripe_connected_accounts
-- Allows landlords to configure which payment methods they accept from tenants
-- Options: "card" (Credit/Debit - $8 fee), "acss_debit" (PAD Bank Transfer - $3 fee)

ALTER TABLE stripe_connected_accounts
ADD COLUMN IF NOT EXISTS accepted_payment_methods JSONB NOT NULL DEFAULT '["card", "acss_debit"]'::jsonb;

-- Add a comment explaining the column
COMMENT ON COLUMN stripe_connected_accounts.accepted_payment_methods IS 'List of accepted payment methods: card, acss_debit. Defaults to both enabled.';
