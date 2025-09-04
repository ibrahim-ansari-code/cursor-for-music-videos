-- Add tax preference fields to users table
ALTER TABLE users 
ADD COLUMN default_tax_name VARCHAR(100),
ADD COLUMN default_tax_rate NUMERIC(6,3);

-- Add comments for documentation
COMMENT ON COLUMN users.default_tax_name IS 'User''s default tax name (e.g., ''HST'', ''GST'')';
COMMENT ON COLUMN users.default_tax_rate IS 'User''s default tax rate as percentage (0-100)';

-- Add tax preference fields to properties table
ALTER TABLE properties
ADD COLUMN default_tax_name VARCHAR(100),
ADD COLUMN default_tax_rate NUMERIC(6,3);

-- Add comments for documentation
COMMENT ON COLUMN properties.default_tax_name IS 'Property''s default tax name (e.g., ''HST'', ''GST+PST'')';
COMMENT ON COLUMN properties.default_tax_rate IS 'Property''s default tax rate as percentage (0-100)';

-- Create invoice_tax_details table
CREATE TABLE invoice_tax_details (
    id SERIAL PRIMARY KEY,
    tax_name VARCHAR(100) NOT NULL,
    tax_rate NUMERIC(6,3) NOT NULL CHECK (tax_rate >= 0 AND tax_rate <= 100),
    tax_amount NUMERIC(12,2) NOT NULL CHECK (tax_amount >= 0),
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Add index for performance
CREATE INDEX ix_invoice_tax_details_invoice_id ON invoice_tax_details(invoice_id);

-- Add unique constraint to prevent duplicate tax types on the same invoice
CREATE UNIQUE INDEX unique_invoice_tax_name ON invoice_tax_details(invoice_id, tax_name);
COMMENT ON INDEX unique_invoice_tax_name IS 'Prevents duplicate tax types (e.g., multiple HST entries) on the same invoice';

-- Add comments
COMMENT ON TABLE invoice_tax_details IS 'Tax line items associated with invoices';
COMMENT ON COLUMN invoice_tax_details.tax_name IS 'Name of the tax (e.g., HST, GST)';
COMMENT ON COLUMN invoice_tax_details.tax_rate IS 'Tax rate as percentage (0-100)';
COMMENT ON COLUMN invoice_tax_details.tax_amount IS 'Calculated tax amount in dollars';
COMMENT ON COLUMN invoice_tax_details.invoice_id IS 'Reference to parent invoice';

-- Enable RLS on invoice_tax_details
ALTER TABLE invoice_tax_details ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only access tax details for their own invoices
CREATE POLICY "Users can view own invoice tax details" ON invoice_tax_details
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM invoices i
            JOIN properties p ON i.property_id = p.id
            WHERE i.id = invoice_tax_details.invoice_id
            AND p.user_id = auth.uid()
        )
        OR
        EXISTS (
            SELECT 1 FROM invoices i
            JOIN tenants t ON i.tenant_id = t.id
            WHERE i.id = invoice_tax_details.invoice_id
            AND t.landlord_id = auth.uid()
        )
    );

-- RLS Policy: Users can insert tax details for their own invoices
CREATE POLICY "Users can insert own invoice tax details" ON invoice_tax_details
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM invoices i
            JOIN properties p ON i.property_id = p.id
            WHERE i.id = invoice_tax_details.invoice_id
            AND p.user_id = auth.uid()
        )
        OR
        EXISTS (
            SELECT 1 FROM invoices i
            JOIN tenants t ON i.tenant_id = t.id
            WHERE i.id = invoice_tax_details.invoice_id
            AND t.landlord_id = auth.uid()
        )
    );

-- RLS Policy: Users can update tax details for their own invoices
CREATE POLICY "Users can update own invoice tax details" ON invoice_tax_details
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM invoices i
            JOIN properties p ON i.property_id = p.id
            WHERE i.id = invoice_tax_details.invoice_id
            AND p.user_id = auth.uid()
        )
        OR
        EXISTS (
            SELECT 1 FROM invoices i
            JOIN tenants t ON i.tenant_id = t.id
            WHERE i.id = invoice_tax_details.invoice_id
            AND t.landlord_id = auth.uid()
        )
    );

-- RLS Policy: Users can delete tax details for their own invoices
CREATE POLICY "Users can delete own invoice tax details" ON invoice_tax_details
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM invoices i
            JOIN properties p ON i.property_id = p.id
            WHERE i.id = invoice_tax_details.invoice_id
            AND p.user_id = auth.uid()
        )
        OR
        EXISTS (
            SELECT 1 FROM invoices i
            JOIN tenants t ON i.tenant_id = t.id
            WHERE i.id = invoice_tax_details.invoice_id
            AND t.landlord_id = auth.uid()
        )
    );

-- Create trigger for updated_at timestamp on invoice_tax_details
CREATE OR REPLACE FUNCTION update_invoice_tax_details_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_invoice_tax_details_updated_at
    BEFORE UPDATE ON invoice_tax_details
    FOR EACH ROW
    EXECUTE FUNCTION update_invoice_tax_details_updated_at();