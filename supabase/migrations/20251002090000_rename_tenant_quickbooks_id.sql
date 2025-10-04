-- Rename tenants.quickbooks_id to quickbooks_customer_id and add indexes/constraints

BEGIN;

-- 1) Rename column
ALTER TABLE public.tenants RENAME COLUMN quickbooks_id TO quickbooks_customer_id;

-- 2) Create index on the new column
CREATE INDEX IF NOT EXISTS idx_tenants_qb_customer_id ON public.tenants (quickbooks_customer_id);

-- 3) Create landlord-scoped unique index for non-null values
CREATE UNIQUE INDEX IF NOT EXISTS ux_tenants_landlord_qb_customer_id
ON public.tenants (landlord_id, quickbooks_customer_id)
WHERE quickbooks_customer_id IS NOT NULL;

COMMIT;
