BEGIN;

ALTER TABLE public.maintenance_requests
ADD COLUMN IF NOT EXISTS preferred_time VARCHAR(255) NULL;

COMMIT;