"""Payment methods and reductions added

Revision ID: 9abb53522bb5
Revises: 7cd3492a479b
Create Date: 2025-07-04 04:53:58.530976

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9abb53522bb5'
down_revision: Union[str, None] = '7cd3492a479b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add reduction columns to payments table
    op.add_column('payments', sa.Column('reduction_amount', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('payments', sa.Column('reduction_reason', sa.String(), nullable=True))
    
    # Update the paymentmethod enum to include new payment methods
    # First, create a new enum type with all payment methods
    op.execute("""
        CREATE TYPE paymentmethod_new AS ENUM (
            'Credit Card',
            'Debit Card',
            'Bank Transfer',
            'Wire Transfer',
            'Direct Deposit',
            'Interac e-Transfer',
            'Cash',
            'Check',
            'Bank Draft',
            'PayPal',
            'Internal Transfer',
            'Other'
        );
    """)
    
    # Update the column to use the new enum
    op.execute("""
        ALTER TABLE payments
        ALTER COLUMN payment_method TYPE paymentmethod_new
        USING payment_method::text::paymentmethod_new;
    """)
    
    # Drop the old enum type
    op.execute("DROP TYPE paymentmethod;")
    
    # Rename the new enum type to the original name
    op.execute("ALTER TYPE paymentmethod_new RENAME TO paymentmethod;")


def downgrade() -> None:
    """Downgrade schema."""
    # Remove reduction columns
    op.drop_column('payments', 'reduction_reason')
    op.drop_column('payments', 'reduction_amount')
    
    # Revert the paymentmethod enum to original values
    # Create the old enum type
    op.execute("""
        CREATE TYPE paymentmethod_old AS ENUM (
            'Credit Card',
            'Bank Transfer',
            'Cash',
            'Check',
            'Other'
        );
    """)
    
    # Update any new payment method values to 'Other' before conversion
    op.execute("""
        UPDATE payments
        SET payment_method = 'Other'
        WHERE payment_method NOT IN ('Credit Card', 'Bank Transfer', 'Cash', 'Check', 'Other');
    """)
    
    # Update the column to use the old enum
    op.execute("""
        ALTER TABLE payments
        ALTER COLUMN payment_method TYPE paymentmethod_old
        USING payment_method::text::paymentmethod_old;
    """)
    
    # Drop the current enum type
    op.execute("DROP TYPE paymentmethod;")
    
    # Rename the old enum type to the original name
    op.execute("ALTER TYPE paymentmethod_old RENAME TO paymentmethod;")
