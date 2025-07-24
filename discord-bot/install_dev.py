#!/usr/bin/env python
"""Script to install the Discord bot package in development mode."""

import os
import sys
import subprocess

def main():
    """Install the Discord bot package in development mode."""
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check if uv is installed
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: uv is not installed. Please install uv first.")
        print("Visit https://github.com/astral-sh/uv for installation instructions.")
        return 1
    
    # Create a virtual environment if it doesn't exist
    venv_dir = os.path.join(current_dir, ".venv")
    if not os.path.exists(venv_dir):
        print("Creating virtual environment...")
        subprocess.run(["uv", "venv"], check=True)
    
    # Install the package in development mode
    print("Installing discord-bot package in development mode...")
    subprocess.run(["uv", "pip", "install", "-e", "."], check=True)
    
    print("Installation complete!")
    print("\nTo run tests, use:")
    print("  uv run pytest")
    print("  or")
    print("  uv run python run_tests_fixed.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())