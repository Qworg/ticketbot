"""
Local database setup script for the Discord Ticket Bot system.
This script initializes the database, runs migrations, and creates sample data.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from db import sync_engine
from models import Base


def run_migrations():
    """Run Alembic migrations to create or update the database schema."""
    print("Running database migrations...")
    
    # Get the backend directory path
    backend_dir = Path(__file__).parent.parent
    
    # Run Alembic migrations
    try:
        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            check=True
        )
        print("Migrations completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running migrations: {e}")
        return False


def create_sample_data():
    """Create sample data for development and testing."""
    print("Creating sample data...")
    
    # Get the script path
    script_path = Path(__file__).parent / "init_db.py"
    
    # Run the sample data script
    try:
        subprocess.run(
            [sys.executable, str(script_path)],
            check=True
        )
        print("Sample data created successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating sample data: {e}")
        return False


def setup_database():
    """Set up the local database for development and testing."""
    print("Setting up local database...")
    
    # Run migrations
    if not run_migrations():
        print("Failed to run migrations. Aborting setup.")
        return False
    
    # Create sample data
    if not create_sample_data():
        print("Failed to create sample data. Aborting setup.")
        return False
    
    print("\nLocal database setup complete!")
    print("You can now start the Discord Ticket Bot system.")
    
    return True


if __name__ == "__main__":
    # Create directory if it doesn't exist
    os.makedirs(Path(__file__).parent, exist_ok=True)
    
    # Set up the database
    setup_database()