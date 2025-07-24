#!/usr/bin/env python
"""
Run tests with the correct Python path.
This script ensures that both installed package imports and development imports work.
"""

import os
import sys
import pytest

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    # Run pytest with the correct path and configuration
    sys.exit(pytest.main(["-v", "--import-mode=importlib"]))