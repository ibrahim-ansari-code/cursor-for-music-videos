"""Add payment_method to expenses table

Revision ID: 23f2543b8686
Revises: 62c631995e42
Create Date: 2025-07-05 04:18:09.392031

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '23f2543b8686'
down_revision: Union[str, None] = '62c631995e42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add payment_method column to expenses table."""
    # Add payment_method column to expenses table with default value 'Other'
    op.add_column('expenses', sa.Column('payment_method', 
        sa.Enum('Credit Card', 'Debit Card', 'Bank Transfer', 'Wire Transfer', 
               'Direct Deposit', 'Interac e-Transfer', 'Cash', 'Check', 
               'Bank Draft', 'PayPal', 'Internal Transfer', 'Other', 
               name='paymentmethod', create_constraint=True), 
        nullable=False, server_default='Other'))


def downgrade() -> None:
    """Remove payment_method column from expenses table."""
    # Drop the payment_method column
    op.drop_column('expenses', 'payment_method')
