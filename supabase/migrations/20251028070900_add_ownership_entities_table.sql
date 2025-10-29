-- Create ownership_entities table
-- This table stores companies, individuals, and other entities that own or have stakes in property units

CREATE TABLE IF NOT EXISTS public.ownership_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,

    -- Entity identification
    entity_type VARCHAR(50) NOT NULL CHECK (entity_type IN ('company', 'individual', 'trust', 'partnership', 'llc', 'corporation', 'other')),
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(500),
    tax_id VARCHAR(100),  -- Consider encryption for production

    -- Contact information
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    contact_name VARCHAR(255),

    -- Address (optional)
    address VARCHAR(500),
    city VARCHAR(100),
    province VARCHAR(50),
    postal_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'Canada',

    -- Notes
    notes VARCHAR(2000),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS ix_ownership_entities_user_id ON public.ownership_entities(user_id);
CREATE INDEX IF NOT EXISTS ix_ownership_entities_name ON public.ownership_entities(name);
CREATE INDEX IF NOT EXISTS ix_ownership_entities_entity_type ON public.ownership_entities(entity_type);

-- Create trigger to automatically update updated_at timestamp
CREATE TRIGGER update_ownership_entities_updated_at
    BEFORE UPDATE ON public.ownership_entities
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- Add RLS (Row Level Security) policies
ALTER TABLE public.ownership_entities ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own ownership entities
CREATE POLICY "Users can view own ownership entities"
    ON public.ownership_entities
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can insert their own ownership entities
CREATE POLICY "Users can insert own ownership entities"
    ON public.ownership_entities
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own ownership entities
CREATE POLICY "Users can update own ownership entities"
    ON public.ownership_entities
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can delete their own ownership entities
CREATE POLICY "Users can delete own ownership entities"
    ON public.ownership_entities
    FOR DELETE
    USING (auth.uid() = user_id);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON public.ownership_entities TO authenticated;
GRANT ALL ON public.ownership_entities TO service_role;

-- Add comment
COMMENT ON TABLE public.ownership_entities IS 'Stores ownership entities (companies, individuals, etc.) that own properties';

-- ============================================================
-- Add ownership_entity_id to properties table
-- ============================================================
-- Properties are owned by legal entities (companies, individuals, etc.)
-- This allows tracking which entity owns which property

ALTER TABLE public.properties
ADD COLUMN IF NOT EXISTS ownership_entity_id UUID REFERENCES public.ownership_entities(id) ON DELETE SET NULL;

-- Create index for ownership entity lookups
CREATE INDEX IF NOT EXISTS ix_properties_ownership_entity_id ON public.properties(ownership_entity_id);

-- Add comment
COMMENT ON COLUMN public.properties.ownership_entity_id IS 'UUID of the ownership entity that owns this property';
