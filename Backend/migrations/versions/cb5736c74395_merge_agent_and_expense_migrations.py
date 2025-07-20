"""merge agent and expense migrations

Revision ID: cb5736c74395
Revises: 23f2543b8686, c4d6a02c4765
Create Date: 2025-07-08 01:10:57.373622

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb5736c74395'
down_revision: Union[str, None] = ('23f2543b8686', 'c4d6a02c4765')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
