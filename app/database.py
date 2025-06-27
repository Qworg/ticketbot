"""
Database configuration and connection setup for the ticketbot application.
"""
import os
from sqlalchemy import create_engine, pool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ticketbot.db")

# Create SQLAlchemy engine with connection pooling
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=os.getenv("DEBUG", "False").lower() == "true"
    )
else:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=os.getenv("DEBUG", "False").lower() == "true"
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for all models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    Used with FastAPI dependency injection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """
    Get database session for direct use (not dependency injection).
    Used for OAuth2 callback and other non-FastAPI contexts.
    
    Returns:
        SQLAlchemy session
    """
    return SessionLocal()


def init_db():
    """
    Initialize database tables.
    Creates all tables defined in models.
    """
    Base.metadata.create_all(bind=engine)
