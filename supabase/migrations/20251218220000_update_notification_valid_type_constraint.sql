-- Update valid_type check constraint to include all notification types
-- Current constraint only has: rent_reminder, lease_expiring, system_update
-- Add missing types: payment_received, maintenance_update, maintenance_request_new, new_application
--
-- This migration ensures the notifications table accepts all notification types
-- used by both the landlord and tenant portals.

BEGIN;

-- Drop the old constraint
ALTER TABLE public.notifications
DROP CONSTRAINT IF EXISTS valid_type;

-- Add the updated constraint with all valid notification types
ALTER TABLE public.notifications
ADD CONSTRAINT valid_type CHECK (
  type = ANY (ARRAY[
    'rent_reminder',
    'payment_received',
    'lease_expiring',
    'maintenance_update',
    'maintenance_request_new',
    'new_application',
    'system_update'
  ]::text[])
);

COMMIT;

