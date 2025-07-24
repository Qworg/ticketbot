"""Configuration for pytest."""

import os
import sys
import pytest
import logging
from unittest.mock import MagicMock

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Create a mock config for testing
class MockConfig:
    """Mock configuration for testing."""
    def __init__(self):
        self.staff_role_id = 123456789
        self.admin_role_id = 987654321
        self.support_team_ids = [111111, 222222]
        self.auto_invite_staff = True
        self.max_auto_invite_staff = 3
        self.command_prefix = "!"
        self.api_url = "http://localhost:8000"
        self.api_key = "test-api-key"

# Create a mock logger
mock_logger = MagicMock()

# Mock the config module
sys.modules['discord_bot.config.settings'] = MagicMock()
sys.modules['discord_bot.config.settings'].config = MockConfig()
sys.modules['discord_bot.config.settings'].logger = mock_logger