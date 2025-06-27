"""create_role_assignments_table

Revision ID: d6e482473d34
Revises: 7a189a964723
Create Date: 2025-06-27 05:14:15.566680+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = "d6e482473d34"
down_revision = "7a189a964723"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create role_assignments table
    op.create_table(
        'role_assignments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('guild_id', sa.BigInteger, nullable=False),
        sa.Column('role', sa.String(50), nullable=False, default='USER'),
        sa.Column('assigned_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes
    op.create_index('idx_role_assignments_user_id', 'role_assignments', ['user_id'])
    op.create_index('idx_role_assignments_guild_role', 'role_assignments', ['guild_id', 'role'])
    op.create_index('idx_role_assignments_user_guild', 'role_assignments', ['user_id', 'guild_id'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_role_assignments_user_guild', 'role_assignments')
    op.drop_index('idx_role_assignments_guild_role', 'role_assignments')
    op.drop_index('idx_role_assignments_user_id', 'role_assignments')
    
    # Drop table
    op.drop_table('role_assignments')
