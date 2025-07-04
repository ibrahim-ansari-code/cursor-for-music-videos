"""Added constraint for reduction <= amount

Revision ID: 62c631995e42
Revises: 9abb53522bb5
Create Date: 2025-07-04 08:13:41.468567

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '62c631995e42'
down_revision: Union[str, None] = '9abb53522bb5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add check constraint to ensure reduction_amount <= amount."""
    op.create_check_constraint(
        'check_reduction_amount_not_greater_than_amount',
        'payments',
        'reduction_amount <= amount'
    )


def downgrade() -> None:
    """Remove check constraint."""
    op.drop_constraint(
        'check_reduction_amount_not_greater_than_amount',
        'payments',
        type_='check'
    )
