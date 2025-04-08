"""Fix NULL property status values

Revision ID: fix_null_property_status
Revises: 91ef9481277d
Create Date: 2023-04-07

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_null_property_status'
down_revision = '91ef9481277d'  # Points to add_status_column_to_property_model
branch_labels = None
depends_on = None

def upgrade():
    # Update NULL status values to 'active'
    op.execute("UPDATE properties SET status = 'active' WHERE status IS NULL")

def downgrade():
    # Not reversible
    pass 