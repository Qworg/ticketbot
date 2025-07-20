"""
Database initialization script for the Discord Ticket Bot system.
This script creates sample data for development and testing.
"""

import os
import sys
import uuid
import datetime
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from models import Base, TicketStatus, Priority, MessageType, StaffRole
from db import sync_engine, get_sync_session


def create_sample_data():
    """Create sample data for development and testing."""
    session = get_sync_session()
    
    try:
        # Create sample staff members
        print("Creating sample staff members...")
        admin_id = uuid.uuid4()
        mod_id = uuid.uuid4()
        support_id = uuid.uuid4()
        
        session.execute(text("""
            INSERT INTO staff (id, discord_id, username, role, permissions, active)
            VALUES 
            (:admin_id, 123456789012345678, 'admin_user', 'admin', '{"manage_tickets": true, "manage_staff": true, "view_all_tickets": true}', true),
            (:mod_id, 234567890123456789, 'mod_user', 'moderator', '{"manage_tickets": true, "view_all_tickets": true}', true),
            (:support_id, 345678901234567890, 'support_user', 'support', '{"manage_tickets": true}', true)
        """), {"admin_id": admin_id, "mod_id": mod_id, "support_id": support_id})
        
        # Create sample tickets
        print("Creating sample tickets...")
        ticket1_id = uuid.uuid4()
        ticket2_id = uuid.uuid4()
        ticket3_id = uuid.uuid4()
        
        # Open ticket
        session.execute(text("""
            INSERT INTO tickets (id, discord_channel_id, title, description, status, priority, creator_discord_id, assigned_staff_id, created_at)
            VALUES 
            (:ticket1_id, 111111111111111111, 'Help with login issues', 'I cannot log into my account', 'open', 'high', 
             987654321098765432, 234567890123456789, :created_at)
        """), {"ticket1_id": ticket1_id, "created_at": datetime.datetime.now() - datetime.timedelta(hours=2)})
        
        # In progress ticket
        session.execute(text("""
            INSERT INTO tickets (id, discord_channel_id, title, description, status, priority, creator_discord_id, assigned_staff_id, created_at)
            VALUES 
            (:ticket2_id, 222222222222222222, 'Feature request: dark mode', 'Please add dark mode to the application', 'in_progress', 'medium', 
             876543210987654321, 345678901234567890, :created_at)
        """), {"ticket2_id": ticket2_id, "created_at": datetime.datetime.now() - datetime.timedelta(days=1)})
        
        # Closed ticket
        session.execute(text("""
            INSERT INTO tickets (id, discord_channel_id, title, description, status, priority, creator_discord_id, assigned_staff_id, created_at, closed_at)
            VALUES 
            (:ticket3_id, 333333333333333333, 'Billing question', 'I have a question about my recent bill', 'closed', 'low', 
             765432109876543210, 123456789012345678, :created_at, :closed_at)
        """), {
            "ticket3_id": ticket3_id, 
            "created_at": datetime.datetime.now() - datetime.timedelta(days=3),
            "closed_at": datetime.datetime.now() - datetime.timedelta(days=2)
        })
        
        # Create sample messages for each ticket
        print("Creating sample messages...")
        
        # Messages for ticket 1
        session.execute(text("""
            INSERT INTO messages (id, ticket_id, discord_message_id, author_discord_id, content, message_type, created_at)
            VALUES 
            (:msg1_id, :ticket1_id, 444444444444444444, 987654321098765432, 'I cannot log into my account. It says invalid credentials.', 'user_message', :created_at1),
            (:msg2_id, :ticket1_id, 555555555555555555, 234567890123456789, 'Have you tried resetting your password?', 'staff_message', :created_at2),
            (:msg3_id, :ticket1_id, 666666666666666666, 987654321098765432, 'Yes, but I still cannot log in.', 'user_message', :created_at3)
        """), {
            "msg1_id": uuid.uuid4(), "msg2_id": uuid.uuid4(), "msg3_id": uuid.uuid4(),
            "ticket1_id": ticket1_id,
            "created_at1": datetime.datetime.now() - datetime.timedelta(hours=2),
            "created_at2": datetime.datetime.now() - datetime.timedelta(hours=1, minutes=45),
            "created_at3": datetime.datetime.now() - datetime.timedelta(hours=1, minutes=30)
        })
        
        # Messages for ticket 2
        session.execute(text("""
            INSERT INTO messages (id, ticket_id, discord_message_id, author_discord_id, content, message_type, created_at)
            VALUES 
            (:msg1_id, :ticket2_id, 777777777777777777, 876543210987654321, 'Please add dark mode to the application. It would be easier on the eyes.', 'user_message', :created_at1),
            (:msg2_id, :ticket2_id, 888888888888888888, 345678901234567890, 'Thanks for the suggestion! We are working on it.', 'staff_message', :created_at2),
            (:msg3_id, :ticket2_id, 999999999999999999, 876543210987654321, 'Great! When can I expect it to be released?', 'user_message', :created_at3),
            (:msg4_id, :ticket2_id, 101010101010101010, 345678901234567890, 'We are planning to release it next month.', 'staff_message', :created_at4)
        """), {
            "msg1_id": uuid.uuid4(), "msg2_id": uuid.uuid4(), "msg3_id": uuid.uuid4(), "msg4_id": uuid.uuid4(),
            "ticket2_id": ticket2_id,
            "created_at1": datetime.datetime.now() - datetime.timedelta(days=1),
            "created_at2": datetime.datetime.now() - datetime.timedelta(hours=23),
            "created_at3": datetime.datetime.now() - datetime.timedelta(hours=22),
            "created_at4": datetime.datetime.now() - datetime.timedelta(hours=21)
        })
        
        # Messages for ticket 3
        session.execute(text("""
            INSERT INTO messages (id, ticket_id, discord_message_id, author_discord_id, content, message_type, created_at)
            VALUES 
            (:msg1_id, :ticket3_id, 121212121212121212, 765432109876543210, 'I have a question about my recent bill. It seems higher than usual.', 'user_message', :created_at1),
            (:msg2_id, :ticket3_id, 131313131313131313, 123456789012345678, 'Let me check your account. Can you provide your account number?', 'staff_message', :created_at2),
            (:msg3_id, :ticket3_id, 141414141414141414, 765432109876543210, 'My account number is ABC123.', 'user_message', :created_at3),
            (:msg4_id, :ticket3_id, 151515151515151515, 123456789012345678, 'I see the issue. There was an extra charge that should not have been applied. I have removed it and issued a refund.', 'staff_message', :created_at4),
            (:msg5_id, :ticket3_id, 161616161616161616, 765432109876543210, 'Thank you! That resolves my issue.', 'user_message', :created_at5),
            (:msg6_id, :ticket3_id, 171717171717171717, 123456789012345678, 'You are welcome! Is there anything else I can help you with?', 'staff_message', :created_at6),
            (:msg7_id, :ticket3_id, 181818181818181818, 765432109876543210, 'No, that is all. Thank you!', 'user_message', :created_at7),
            (:msg8_id, :ticket3_id, 191919191919191919, 123456789012345678, 'This ticket is now closed. Thank you for contacting us!', 'system_message', :created_at8)
        """), {
            "msg1_id": uuid.uuid4(), "msg2_id": uuid.uuid4(), "msg3_id": uuid.uuid4(), "msg4_id": uuid.uuid4(),
            "msg5_id": uuid.uuid4(), "msg6_id": uuid.uuid4(), "msg7_id": uuid.uuid4(), "msg8_id": uuid.uuid4(),
            "ticket3_id": ticket3_id,
            "created_at1": datetime.datetime.now() - datetime.timedelta(days=3),
            "created_at2": datetime.datetime.now() - datetime.timedelta(days=3, hours=23),
            "created_at3": datetime.datetime.now() - datetime.timedelta(days=3, hours=22),
            "created_at4": datetime.datetime.now() - datetime.timedelta(days=3, hours=21),
            "created_at5": datetime.datetime.now() - datetime.timedelta(days=2, hours=23),
            "created_at6": datetime.datetime.now() - datetime.timedelta(days=2, hours=22),
            "created_at7": datetime.datetime.now() - datetime.timedelta(days=2, hours=21),
            "created_at8": datetime.datetime.now() - datetime.timedelta(days=2, hours=20)
        })
        
        # Create sample transcript for the closed ticket
        print("Creating sample transcript...")
        session.execute(text("""
            INSERT INTO transcripts (id, ticket_id, content, formatted_content, share_token, created_at, updated_at)
            VALUES 
            (:transcript_id, :ticket3_id, :content, :formatted_content, :share_token, :created_at, :updated_at)
        """), {
            "transcript_id": uuid.uuid4(),
            "ticket3_id": ticket3_id,
            "content": """
User (765432109876543210): I have a question about my recent bill. It seems higher than usual.
Staff (123456789012345678): Let me check your account. Can you provide your account number?
User (765432109876543210): My account number is ABC123.
Staff (123456789012345678): I see the issue. There was an extra charge that should not have been applied. I have removed it and issued a refund.
User (765432109876543210): Thank you! That resolves my issue.
Staff (123456789012345678): You are welcome! Is there anything else I can help you with?
User (765432109876543210): No, that is all. Thank you!
System: This ticket is now closed. Thank you for contacting us!
            """,
            "formatted_content": {
                "ticket_id": str(ticket3_id),
                "title": "Billing question",
                "status": "closed",
                "created_at": (datetime.datetime.now() - datetime.timedelta(days=3)).isoformat(),
                "closed_at": (datetime.datetime.now() - datetime.timedelta(days=2)).isoformat(),
                "messages": [
                    {
                        "author": "User",
                        "author_id": "765432109876543210",
                        "content": "I have a question about my recent bill. It seems higher than usual.",
                        "timestamp": (datetime.datetime.now() - datetime.timedelta(days=3)).isoformat(),
                        "type": "user_message"
                    },
                    {
                        "author": "Staff",
                        "author_id": "123456789012345678",
                        "content": "Let me check your account. Can you provide your account number?",
                        "timestamp": (datetime.datetime.now() - datetime.timedelta(days=3, hours=23)).isoformat(),
                        "type": "staff_message"
                    },
                    {
                        "author": "User",
                        "author_id": "765432109876543210",
                        "content": "My account number is ABC123.",
                        "timestamp": (datetime.datetime.now() - datetime.timedelta(days=3, hours=22)).isoformat(),
                        "type": "user_message"
                    },
                    {
                        "author": "Staff",
                        "author_id": "123456789012345678",
                        "content": "I see the issue. There was an extra charge that should not have been applied. I have removed it and issued a refund.",
                        "timestamp": (datetime.datetime.now() - datetime.timedelta(days=3, hours=21)).isoformat(),
                        "type": "staff_message"
                    },
                    {
                        "author": "User",
                        "author_id": "765432109876543210",
                        "content": "Thank you! That resolves my issue.",
                        "timestamp": (datetime.datetime.now() - datetime.timedelta(days=2, hours=23)).isoformat(),
                        "type": "user_message"
                    },
                    {
                        "author": "Staff",
                        "author_id": "123456789012345678",
                        "content": "You are welcome! Is there anything else I can help you with?",
                        "timestamp": (datetime.datetime.now() - datetime.timedelta(days=2, hours=22)).isoformat(),
                        "type": "staff_message"
                    },
                    {
                        "author": "User",
                        "author_id": "765432109876543210",
                        "content": "No, that is all. Thank you!",
                        "timestamp": (datetime.datetime.now() - datetime.timedelta(days=2, hours=21)).isoformat(),
                        "type": "user_message"
                    },
                    {
                        "author": "System",
                        "content": "This ticket is now closed. Thank you for contacting us!",
                        "timestamp": (datetime.datetime.now() - datetime.timedelta(days=2, hours=20)).isoformat(),
                        "type": "system_message"
                    }
                ]
            },
            "share_token": "sample-share-token-123456",
            "created_at": datetime.datetime.now() - datetime.timedelta(days=2, hours=20),
            "updated_at": datetime.datetime.now() - datetime.timedelta(days=2, hours=20)
        })
        
        session.commit()
        print("Sample data created successfully!")
        
    except Exception as e:
        session.rollback()
        print(f"Error creating sample data: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    # Create directory if it doesn't exist
    os.makedirs(Path(__file__).parent, exist_ok=True)
    
    # Create sample data
    create_sample_data()