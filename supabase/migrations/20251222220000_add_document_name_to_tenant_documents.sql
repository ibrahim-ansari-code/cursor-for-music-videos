-- Add document_name column to tenant_documents table
-- This allows landlords to set a user-friendly name separate from the file name

ALTER TABLE tenant_documents
ADD COLUMN IF NOT EXISTS document_name VARCHAR(255) DEFAULT NULL;

-- Add comment for documentation
COMMENT ON COLUMN tenant_documents.document_name IS 'User-friendly document name (defaults to file_name if not provided)';
