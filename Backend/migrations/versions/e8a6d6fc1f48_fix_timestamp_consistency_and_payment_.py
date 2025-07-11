"""Fix timestamp consistency and payment history protection

Revision ID: e8a6d6fc1f48
Revises: 23f2543b8686
Create Date: 2025-07-11 03:32:17.156243

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e8a6d6fc1f48'
down_revision: Union[str, None] = '23f2543b8686'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Fix timestamp consistency and payment history protection."""
    # Fix payment history protection: Change foreign key constraint from SET NULL to RESTRICT
    op.drop_constraint('payments_lease_id_fkey', 'payments', type_='foreignkey')
    op.create_foreign_key('payments_lease_id_fkey', 'payments', 'leases', ['lease_id'], ['id'], ondelete='RESTRICT')
    
    # Fix timestamp consistency: Change tenant_unit_link timestamps to timezone-aware
    op.alter_column('tenant_unit_link', 'start_date',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)
    op.alter_column('tenant_unit_link', 'end_date',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema - Revert timestamp and foreign key changes."""
    # Revert timestamp changes
    op.alter_column('tenant_unit_link', 'end_date',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('tenant_unit_link', 'start_date',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    
    # Revert foreign key constraint change
    op.drop_constraint('payments_lease_id_fkey', 'payments', type_='foreignkey')
    op.create_foreign_key('payments_lease_id_fkey', 'payments', 'leases', ['lease_id'], ['id'], ondelete='SET NULL')
