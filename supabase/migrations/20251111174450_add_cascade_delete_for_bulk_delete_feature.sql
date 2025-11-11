-- Migration: Add CASCADE delete for bulk delete feature
-- Description: Updates leases.tenant_id foreign key to CASCADE on delete
-- This allows automatic deletion of non-active leases when a tenant is deleted
-- Active lease validation is enforced at the service layer

-- Drop the existing foreign key constraint
ALTER TABLE leases
DROP CONSTRAINT IF EXISTS leases_tenant_id_fkey;

-- Recreate the foreign key constraint with CASCADE delete
ALTER TABLE leases
ADD CONSTRAINT leases_tenant_id_fkey
FOREIGN KEY (tenant_id)
REFERENCES tenants(id)
ON DELETE CASCADE;

-- Add comment for documentation
COMMENT ON CONSTRAINT leases_tenant_id_fkey ON leases IS
'Cascades lease deletion when tenant is deleted. Active lease validation is enforced at service layer to prevent deletion of tenants with active leases.';
