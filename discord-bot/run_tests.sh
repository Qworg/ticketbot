#!/bin/bash
# Script to run tests with uv

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install uv first."
    echo "Visit https://github.com/astral-sh/uv for installation instructions."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Install the package in development mode
echo "Installing discord-bot package in development mode..."
uv pip install -e .

# Run the tests
echo "Running tests..."
uv run pytest -v --import-mode=importlib