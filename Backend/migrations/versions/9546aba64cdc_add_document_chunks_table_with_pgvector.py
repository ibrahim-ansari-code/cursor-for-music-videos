"""add_document_chunks_table_with_pgvector

Revision ID: 9546aba64cdc
Revises: cb5736c74395
Create Date: 2025-07-08 01:12:05.645470

"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9546aba64cdc'
down_revision: Union[str, None] = 'cb5736c74395'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create document_chunks table with pgvector support for Phase 2"""
    
    # Check if pgvector extension exists in Supabase
    # Note: pgvector is pre-installed in Supabase but may need to be enabled in the schema
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
                CREATE EXTENSION vector;
            END IF;
        END $$;
    """)
    
    # Create document_chunks table directly with vector type
    op.execute("""
        CREATE TABLE document_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            source_id UUID NOT NULL,
            source_type VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            embedding vector(1536),
            chunk_metadata JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    
    # Create indexes for efficient querying
    op.create_index(op.f('ix_document_chunks_user_id'), 'document_chunks', ['user_id'], unique=False)
    op.create_index(op.f('ix_document_chunks_source_id'), 'document_chunks', ['source_id'], unique=False)
    op.create_index(op.f('ix_document_chunks_source_type'), 'document_chunks', ['source_type'], unique=False)
    
    # Create composite index for user + source type queries
    op.create_index('ix_document_chunks_user_source_type', 'document_chunks', ['user_id', 'source_type'], unique=False)
    
    # Create IVFFlat index for vector similarity search
    # Using vector_cosine_ops for cosine similarity (most common for text embeddings)
    op.execute("""
        CREATE INDEX ix_document_chunks_embedding 
        ON document_chunks 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)
    
    # Add comment to table for documentation
    op.execute("""
        COMMENT ON TABLE document_chunks IS 
        'Stores document embeddings for semantic search. Used by Brikli Agent to search through leases, invoices, and other documents.'
    """)
    
    # Add column comments
    op.execute("COMMENT ON COLUMN document_chunks.source_type IS 'Type of source document: lease, invoice, expense, etc.'")
    op.execute("COMMENT ON COLUMN document_chunks.embedding IS 'Vector embedding from OpenAI text-embedding-ada-002 model'")
    op.execute("COMMENT ON COLUMN document_chunks.chunk_metadata IS 'Additional metadata like page number, section, chunk index, etc.'")
    
    # Remove the auto-generated command that tries to drop a system table
    # op.drop_table('wrappers_fdw_stats') - This is a Supabase system table, should not be dropped


def downgrade() -> None:
    """Drop document_chunks table and related indexes"""
    
    # Drop the table (indexes will be dropped automatically)
    op.drop_table('document_chunks')
    
    # Note: We don't drop the pgvector extension as other tables might be using it
    # Note: We don't recreate wrappers_fdw_stats as it's a Supabase system table
