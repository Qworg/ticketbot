"""Add additional indexes and constraints

Revision ID: 002
Revises: 001
Create Date: 2025-07-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add full-text search index for transcript content
    op.execute(
        """
        CREATE INDEX idx_transcripts_content_search ON transcripts 
        USING gin(to_tsvector('english', content));
        """
    )
    
    # Add constraint to ensure ticket status is valid
    op.execute(
        """
        ALTER TABLE tickets 
        ADD CONSTRAINT chk_ticket_status 
        CHECK (status IN ('open', 'in_progress', 'waiting', 'closed', 'archived'));
        """
    )
    
    # Add constraint to ensure ticket priority is valid
    op.execute(
        """
        ALTER TABLE tickets 
        ADD CONSTRAINT chk_ticket_priority 
        CHECK (priority IN ('low', 'medium', 'high', 'urgent'));
        """
    )
    
    # Add constraint to ensure message type is valid
    op.execute(
        """
        ALTER TABLE messages 
        ADD CONSTRAINT chk_message_type 
        CHECK (message_type IN ('user_message', 'staff_message', 'system_message', 'bot_message'));
        """
    )
    
    # Add constraint to ensure staff role is valid
    op.execute(
        """
        ALTER TABLE staff 
        ADD CONSTRAINT chk_staff_role 
        CHECK (role IN ('admin', 'moderator', 'support'));
        """
    )
    
    # Add cascade delete for messages and transcripts when ticket is deleted
    op.drop_constraint('messages_ticket_id_fkey', 'messages', type_='foreignkey')
    op.create_foreign_key('messages_ticket_id_fkey', 'messages', 'tickets', ['ticket_id'], ['id'], ondelete='CASCADE')
    
    op.drop_constraint('transcripts_ticket_id_fkey', 'transcripts', type_='foreignkey')
    op.create_foreign_key('transcripts_ticket_id_fkey', 'transcripts', 'tickets', ['ticket_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    # Remove full-text search index
    op.execute("DROP INDEX IF EXISTS idx_transcripts_content_search;")
    
    # Remove constraints
    op.execute("ALTER TABLE tickets DROP CONSTRAINT IF EXISTS chk_ticket_status;")
    op.execute("ALTER TABLE tickets DROP CONSTRAINT IF EXISTS chk_ticket_priority;")
    op.execute("ALTER TABLE messages DROP CONSTRAINT IF EXISTS chk_message_type;")
    op.execute("ALTER TABLE staff DROP CONSTRAINT IF EXISTS chk_staff_role;")
    
    # Remove cascade delete
    op.drop_constraint('messages_ticket_id_fkey', 'messages', type_='foreignkey')
    op.create_foreign_key('messages_ticket_id_fkey', 'messages', 'tickets', ['ticket_id'], ['id'])
    
    op.drop_constraint('transcripts_ticket_id_fkey', 'transcripts', type_='foreignkey')
    op.create_foreign_key('transcripts_ticket_id_fkey', 'transcripts', 'tickets', ['ticket_id'], ['id'])