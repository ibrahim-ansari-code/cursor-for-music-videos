"""align_paymentstatus_enum_with_manual_changes

Revision ID: cc44eac7c923
Revises: 77576eb47c7e
Create Date: 2025-05-21 06:20:17.261360

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc44eac7c923'
down_revision: Union[str, None] = '77576eb47c7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
