-- Add unit_type_details JSONB column to property_units table
-- This column stores property-type-specific unit details

ALTER TABLE public.property_units
ADD COLUMN IF NOT EXISTS unit_type_details JSONB DEFAULT '{}'::jsonb;

-- Create GIN index for efficient JSONB queries
CREATE INDEX IF NOT EXISTS idx_property_units_unit_type_details
    ON public.property_units USING GIN (unit_type_details);

-- Add comment
COMMENT ON COLUMN public.property_units.unit_type_details IS 'Type-specific unit details based on parent property type (e.g., bedrooms/bathrooms for residential, ownership/additional_rent for industrial)';
