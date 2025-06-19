"""Optimize indexes remove duplicates add composite

Revision ID: be84796fc7de
Revises: afe06420ef77
Create Date: 2025-06-14 08:02:52.930429

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'be84796fc7de'
down_revision: Union[str, None] = 'afe06420ef77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Applies schema changes to optimize database indexes and constraints.
    
    Removes redundant indexes on the `invoices` and `payments` tables, replacing them with unique constraints on relevant columns. Drops individual indexes on `property_units` and creates a composite index on `property_id` and `tenant_id`.
    """
    # Remove duplicate indexes on invoices (unique constraints create their own indexes)
    op.drop_index(op.f('ix_invoices_invoice_number'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_quickbooks_id'), table_name='invoices')
    op.create_unique_constraint('uq_invoices_quickbooks_id', 'invoices', ['quickbooks_id'])
    op.create_unique_constraint('uq_invoices_invoice_number', 'invoices', ['invoice_number'])
    
    # Remove duplicate index on payments (unique constraint creates its own index)
    op.drop_index(op.f('ix_payments_quickbooks_id'), table_name='payments')
    op.create_unique_constraint('uq_payments_quickbooks_id', 'payments', ['quickbooks_id'])
    
    # Note: ix_payments_lease_id already exists, no need to create it
    
    # Replace individual indexes with composite index on property_units
    op.drop_index(op.f('ix_property_units_property_id'), table_name='property_units')
    op.drop_index(op.f('ix_property_units_tenant_id'), table_name='property_units')
    op.create_index('ix_property_units_property_tenant', 'property_units', ['property_id', 'tenant_id'], unique=False)


def downgrade() -> None:
    """
    Reverts the schema changes made in the upgrade by restoring dropped indexes and removing added constraints.
    
    This function drops the composite index and unique constraints introduced during upgrade, recreates the original individual indexes on the `property_units`, `payments`, and `invoices` tables, and restores the previous indexing structure.
    """
    # Restore individual indexes on property_units
    op.drop_index('ix_property_units_property_tenant', table_name='property_units')
    op.create_index(op.f('ix_property_units_tenant_id'), 'property_units', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_property_units_property_id'), 'property_units', ['property_id'], unique=False)
    
    # Note: ix_payments_lease_id was already in the database, so we don't remove it
    
    # Restore redundant indexes on payments
    op.drop_constraint('uq_payments_quickbooks_id', 'payments', type_='unique')
    op.create_index(op.f('ix_payments_quickbooks_id'), 'payments', ['quickbooks_id'], unique=True)
    
    # Restore redundant indexes on invoices
    op.drop_constraint('uq_invoices_invoice_number', 'invoices', type_='unique')
    op.drop_constraint('uq_invoices_quickbooks_id', 'invoices', type_='unique')
    op.create_index(op.f('ix_invoices_quickbooks_id'), 'invoices', ['quickbooks_id'], unique=True)
    op.create_index(op.f('ix_invoices_invoice_number'), 'invoices', ['invoice_number'], unique=True)
