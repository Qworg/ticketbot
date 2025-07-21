"""
Simple test runner script for the backend tests.
"""
import pytest
import sys

if __name__ == "__main__":
    # Get command line arguments
    args = sys.argv[1:]
    
    # If no arguments provided, run all tests
    if not args:
        args = ["-v", "tests/"]
    
    # Run the tests
    sys.exit(pytest.main(args))