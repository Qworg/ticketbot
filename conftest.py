"""
Pytest configuration for the ticketbot project.
Sets up test environment variables and fixtures.
"""

import os
import pytest


def pytest_configure():
    """Configure pytest with necessary environment variables."""
    # Set JWT secret key for testing
    os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only-do-not-use-in-production'
    
    # Set other test environment variables
    os.environ['REDIS_URL'] = 'redis://localhost:6379/1'  # Use test database
    os.environ['SESSION_SECRET_KEY'] = 'test-session-secret-key'


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment before running tests."""
    # Ensure JWT secret is set
    if 'JWT_SECRET_KEY' not in os.environ:
        os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only'
    
    yield
    
    # Cleanup after tests (if needed)
    pass


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    from unittest.mock import Mock
    mock_client = Mock()
    mock_client.get.return_value = None
    mock_client.setex.return_value = True
    mock_client.incr.return_value = 1
    mock_client.delete.return_value = 1
    return mock_client
