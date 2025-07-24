#!/usr/bin/env python
"""Script to run tests using uv."""

import os
import sys
import subprocess

def main():
    """Run tests using uv."""
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check if uv is installed
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: uv is not installed. Please install uv first.")
        print("Visit https://github.com/astral-sh/uv for installation instructions.")
        return 1
    
    # Run the tests using uv
    print("Running tests with uv...")
    result = subprocess.run(["uv", "run", "pytest", "-v", "--import-mode=importlib"], cwd=current_dir)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())