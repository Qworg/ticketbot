"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tickets table
    op.create_table('tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('discord_channel_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=True),
        sa.Column('creator_discord_id', sa.BigInteger(), nullable=False),
        sa.Column('assigned_staff_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_tickets_assigned_status', 'tickets', ['assigned_staff_id', 'status'], unique=False)
    op.create_index('idx_tickets_creator_status', 'tickets', ['creator_discord_id', 'status'], unique=False)
    op.create_index('idx_tickets_status_created', 'tickets', ['status', 'created_at'], unique=False)
    op.create_index(op.f('ix_tickets_assigned_staff_id'), 'tickets', ['assigned_staff_id'], unique=False)
    op.create_index(op.f('ix_tickets_creator_discord_id'), 'tickets', ['creator_discord_id'], unique=False)
    op.create_index(op.f('ix_tickets_discord_channel_id'), 'tickets', ['discord_channel_id'], unique=True)
    op.create_index(op.f('ix_tickets_priority'), 'tickets', ['priority'], unique=False)
    op.create_index(op.f('ix_tickets_status'), 'tickets', ['status'], unique=False)
    
    # Create messages table
    op.create_table('messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('discord_message_id', sa.BigInteger(), nullable=True),
        sa.Column('author_discord_id', sa.BigInteger(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_messages_author_created', 'messages', ['author_discord_id', 'created_at'], unique=False)
    op.create_index('idx_messages_ticket_created', 'messages', ['ticket_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_messages_author_discord_id'), 'messages', ['author_discord_id'], unique=False)
    op.create_index(op.f('ix_messages_discord_message_id'), 'messages', ['discord_message_id'], unique=True)
    op.create_index(op.f('ix_messages_message_type'), 'messages', ['message_type'], unique=False)
    op.create_index(op.f('ix_messages_ticket_id'), 'messages', ['ticket_id'], unique=False)
    
    # Create transcripts table
    op.create_table('transcripts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('formatted_content', sa.JSON(), nullable=True),
        sa.Column('share_token', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transcripts_share_token'), 'transcripts', ['share_token'], unique=True)
    op.create_index(op.f('ix_transcripts_ticket_id'), 'transcripts', ['ticket_id'], unique=False)
    
    # Create staff table
    op.create_table('staff',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('discord_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_staff_role_active', 'staff', ['role', 'active'], unique=False)
    op.create_index(op.f('ix_staff_active'), 'staff', ['active'], unique=False)
    op.create_index(op.f('ix_staff_discord_id'), 'staff', ['discord_id'], unique=True)
    op.create_index(op.f('ix_staff_role'), 'staff', ['role'], unique=False)


def downgrade() -> None:
    op.drop_table('staff')
    op.drop_table('transcripts')
    op.drop_table('messages')
    op.drop_table('tickets')