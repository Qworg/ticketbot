"""
Simple test runner script for the database service tests.
"""
import pytest
import sys

if __name__ == "__main__":
    # Run the tests
    test_file = "tests/test_enhanced_database_service.py"
    sys.exit(pytest.main(["-v", test_file]))