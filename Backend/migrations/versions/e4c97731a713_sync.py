"""sync

Revision ID: e4c97731a713
Revises: cc44eac7c923
Create Date: 2025-05-29 17:46:47.581713

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4c97731a713'
down_revision: Union[str, None] = 'cc44eac7c923'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    No-op migration upgrade; does not apply any schema changes.
    """
    pass


def downgrade() -> None:
    """
    Placeholder for reverting schema changes in this migration.

    This function does not perform any operations.
    """
    pass
