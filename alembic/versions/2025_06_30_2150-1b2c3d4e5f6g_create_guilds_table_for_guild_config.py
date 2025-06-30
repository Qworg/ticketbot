"""create guilds table for guild configuration

Revision ID: 1b2c3d4e5f6g
Revises: 9472ef34647b
Create Date: 2025-06-30 21:50:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1b2c3d4e5f6g"
down_revision = "9472ef34647b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create guilds table
    op.create_table(
        'guilds',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('staff_role_ids', sa.JSON(), nullable=True),
        sa.Column('admin_role_ids', sa.JSON(), nullable=True),
        sa.Column('ticket_category_id', sa.BigInteger(), nullable=True),
        sa.Column('ticket_category_name', sa.String(length=100), nullable=False),
        sa.Column('auto_archive_hours', sa.BigInteger(), nullable=False),
        sa.Column('auto_transcript', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_guilds_id'), 'guilds', ['id'], unique=False)


def downgrade() -> None:
    # Drop guilds table
    op.drop_index(op.f('ix_guilds_id'), table_name='guilds')
    op.drop_table('guilds')
