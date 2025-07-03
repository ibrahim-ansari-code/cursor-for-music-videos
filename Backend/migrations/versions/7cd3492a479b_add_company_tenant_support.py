"""add_company_tenant_support

Revision ID: 7cd3492a479b
Revises: be84796fc7de
Create Date: 2025-07-03 01:42:43.145814

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7cd3492a479b'
down_revision: Union[str, None] = 'be84796fc7de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add support for commercial/company tenants."""
    # Create the enum type first
    tenant_type_enum = sa.Enum('INDIVIDUAL', 'COMPANY', name='tenanttype')
    tenant_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Add tenant type enum and related fields for company support
    op.add_column('tenants', sa.Column('tenant_type', tenant_type_enum, nullable=False, server_default='INDIVIDUAL'))
    op.add_column('tenants', sa.Column('company_name', sa.String(length=200), nullable=True))
    op.add_column('tenants', sa.Column('contact_person', sa.String(length=200), nullable=True))
    
    # Make first_name and last_name nullable to support company tenants
    op.alter_column('tenants', 'first_name',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
    op.alter_column('tenants', 'last_name',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
    
    # Add index for tenant type filtering
    op.create_index('ix_tenants_tenant_type', 'tenants', ['tenant_type'], unique=False)
    
    # Remove the server default after applying it to existing rows
    op.alter_column('tenants', 'tenant_type', server_default=None)


def downgrade() -> None:
    """Remove company tenant support."""
    # Remove tenant type index
    op.drop_index('ix_tenants_tenant_type', table_name='tenants')
    
    # Make first_name and last_name required again
    op.alter_column('tenants', 'last_name',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)
    op.alter_column('tenants', 'first_name',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)
    
    # Remove new columns
    op.drop_column('tenants', 'contact_person')
    op.drop_column('tenants', 'company_name')
    op.drop_column('tenants', 'tenant_type')
    
    # Drop the enum type
    sa.Enum(name='tenanttype').drop(op.get_bind(), checkfirst=True)
