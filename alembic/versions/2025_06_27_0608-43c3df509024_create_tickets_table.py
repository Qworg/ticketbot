"""create_tickets_table

Revision ID: 43c3df509024
Revises: 3d0546d0b919
Create Date: 2025-06-27 06:08:44.183874+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "43c3df509024"
down_revision = "3d0546d0b919"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tickets table
    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("creator_id", sa.BigInteger(), nullable=False),
        sa.Column("assigned_to", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("close_reason", sa.Text(), nullable=True),
        sa.Column("is_shadow_closed", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create indexes for performance
    op.create_index("idx_tickets_channel_id", "tickets", ["channel_id"], unique=True)
    op.create_index("idx_tickets_guild_id", "tickets", ["guild_id"], unique=False)
    op.create_index("idx_tickets_creator_id", "tickets", ["creator_id"], unique=False)
    op.create_index("idx_tickets_assigned_to", "tickets", ["assigned_to"], unique=False)
    op.create_index("idx_tickets_status", "tickets", ["status"], unique=False)
    op.create_index("idx_tickets_created_at", "tickets", ["created_at"], unique=False)
    op.create_index("idx_tickets_guild_status", "tickets", ["guild_id", "status"], unique=False)
    op.create_index(op.f("ix_tickets_id"), "tickets", ["id"], unique=False)


def downgrade() -> None:
    # Drop all indexes
    op.drop_index("idx_tickets_guild_status", table_name="tickets")
    op.drop_index("idx_tickets_created_at", table_name="tickets")
    op.drop_index("idx_tickets_status", table_name="tickets")
    op.drop_index("idx_tickets_assigned_to", table_name="tickets")
    op.drop_index("idx_tickets_creator_id", table_name="tickets")
    op.drop_index("idx_tickets_guild_id", table_name="tickets")
    op.drop_index("idx_tickets_channel_id", table_name="tickets")
    op.drop_index(op.f("ix_tickets_id"), table_name="tickets")
    
    # Drop the table
    op.drop_table("tickets")
