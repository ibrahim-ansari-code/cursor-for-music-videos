-- Add completed_date column to maintenance_requests table
-- This column will store when a maintenance request was completed

ALTER TABLE "public"."maintenance_requests" 
ADD COLUMN "completed_date" timestamp with time zone;

-- Add a comment to document the column purpose
COMMENT ON COLUMN "public"."maintenance_requests"."completed_date" IS 'Timestamp when the maintenance request was completed'; 
