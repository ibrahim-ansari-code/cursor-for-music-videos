-- Fix search_path security issues for trigger functions
-- This prevents search path hijacking attacks by explicitly setting search_path

-- Fix update_invoice_tax_details_updated_at function
CREATE OR REPLACE FUNCTION public.update_invoice_tax_details_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path = ''
AS $function$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$function$;

-- Fix validate_emergency_contacts_primary function
CREATE OR REPLACE FUNCTION public.validate_emergency_contacts_primary()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path = ''
AS $function$
DECLARE
  primary_count INTEGER;
BEGIN
  -- Count primary contacts
  SELECT COUNT(*)
  INTO primary_count
  FROM jsonb_array_elements(NEW.emergency_contacts) AS elem
  WHERE (elem->>'is_primary')::boolean = true;
  
  -- Ensure only one primary contact
  IF primary_count > 1 THEN
    RAISE EXCEPTION 'Only one emergency contact can be marked as primary';
  END IF;
  
  RETURN NEW;
END;
$function$;
