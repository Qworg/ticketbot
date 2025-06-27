"""make channel_id nullable in tickets table

Revision ID: 92db72f4e8eb
Revises: 43c3df509024
Create Date: 2025-06-27 17:40:21.222177+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "92db72f4e8eb"
down_revision = "43c3df509024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make channel_id nullable in tickets table
    op.alter_column('tickets', 'channel_id',
                    existing_type=sa.BIGINT(),
                    nullable=True)


def downgrade() -> None:
    # Make channel_id not nullable again
    op.alter_column('tickets', 'channel_id',
                    existing_type=sa.BIGINT(),
                    nullable=False)
