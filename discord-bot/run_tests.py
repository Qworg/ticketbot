#!/usr/bin/env python
"""Script to run tests for the Discord bot."""

import os
import sys
import pytest

if __name__ == "__main__":
    # Add the current directory to sys.path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    # Run pytest with the specified arguments
    sys.exit(pytest.main(["-v", "tests"]))