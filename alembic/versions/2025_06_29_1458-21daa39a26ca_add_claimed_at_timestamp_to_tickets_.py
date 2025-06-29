"""add claimed_at timestamp to tickets table

Revision ID: 21daa39a26ca
Revises: 92db72f4e8eb
Create Date: 2025-06-29 14:58:27.089384+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "21daa39a26ca"
down_revision = "92db72f4e8eb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add claimed_at timestamp column to tickets table
    op.add_column('tickets', sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove claimed_at column from tickets table
    op.drop_column('tickets', 'claimed_at')
