"""
Unit tests for the User model.
Tests user creation, validation, and database operations.
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.database import Base
from app.models.user import User


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


class TestUserModel:
    """Test suite for User model functionality."""

    def test_user_creation_with_required_fields(self, db_session):
        """Test creating a user with only required fields."""
        discord_id = 123456789012345678
        user = User(discord_id=discord_id)
        
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert isinstance(user.id, uuid.UUID)
        assert user.discord_id == discord_id
        assert user.role == "USER"  # Default role
        assert user.email is None
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_creation_with_all_fields(self, db_session):
        """Test creating a user with all fields populated."""
        discord_id = 123456789012345678
        email = "test@example.com"
        role = "STAFF"
        
        user = User(discord_id=discord_id, email=email, role=role)
        
        db_session.add(user)
        db_session.commit()
        
        assert user.discord_id == discord_id
        assert user.email == email
        assert user.role == role
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_factory_method(self, db_session):
        """Test the create_user factory method."""
        discord_id = 987654321098765432
        email = "factory@example.com"
        role = "admin"
        
        user = User.create_user(discord_id=discord_id, email=email, role=role)
        
        db_session.add(user)
        db_session.commit()
        
        assert user.discord_id == discord_id
        assert user.email == email
        assert user.role == "ADMIN"  # Should be uppercase

    def test_discord_id_uniqueness(self, db_session):
        """Test that discord_id must be unique."""
        discord_id = 123456789012345678
        
        user1 = User(discord_id=discord_id)
        user2 = User(discord_id=discord_id)
        
        db_session.add(user1)
        db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_to_dict(self, db_session):
        """Test user serialization to dictionary."""
        discord_id = 123456789012345678
        email = "test@example.com"
        role = "STAFF"
        
        user = User(discord_id=discord_id, email=email, role=role)
        db_session.add(user)
        db_session.commit()
        
        user_dict = user.to_dict()
        
        assert user_dict["discord_id"] == str(discord_id)
        assert user_dict["email"] == email
        assert user_dict["role"] == role
        assert "id" in user_dict
        assert "created_at" in user_dict
        assert "updated_at" in user_dict

    def test_user_repr(self, db_session):
        """Test user string representation."""
        discord_id = 123456789012345678
        role = "USER"
        
        user = User(discord_id=discord_id, role=role)
        db_session.add(user)
        db_session.commit()
        
        repr_str = repr(user)
        assert f"discord_id={discord_id}" in repr_str
        assert f"role={role}" in repr_str

    def test_email_indexing(self, db_session):
        """Test that email queries can use the index (performance test)."""
        email = "indexed@example.com"
        user = User(discord_id=123456789012345678, email=email)
        
        db_session.add(user)
        db_session.commit()
        
        # Query by email should work efficiently
        found_user = db_session.query(User).filter(User.email == email).first()
        assert found_user is not None
        assert found_user.email == email

    def test_discord_id_indexing(self, db_session):
        """Test that discord_id queries can use the index (performance test)."""
        discord_id = 123456789012345678
        user = User(discord_id=discord_id)
        
        db_session.add(user)
        db_session.commit()
        
        # Query by discord_id should work efficiently
        found_user = db_session.query(User).filter(User.discord_id == discord_id).first()
        assert found_user is not None
        assert found_user.discord_id == discord_id

    def test_role_validation_defaults(self, db_session):
        """Test that role defaults to USER when not specified."""
        user = User(discord_id=123456789012345678)
        assert user.role == "USER"

    def test_timestamps_automatic(self, db_session):
        """Test that timestamps are set automatically."""
        user = User(discord_id=123456789012345678)
        
        # Before saving, timestamps might not be set
        db_session.add(user)
        db_session.commit()
        
        # After saving, timestamps should be set
        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
