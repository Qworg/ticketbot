---
title: Python Package Management with uv
inclusion: always
---

# Python Package Management with uv

This project uses `uv` as the Python package manager for faster dependency resolution and virtual environment management.

## Key Commands

- `uv venv` - Create a virtual environment
- `uv pip install -e .` - Install package in development mode
- `uv run python <script.py>` - Run Python scripts using the virtual environment
- `uv pip install <package>` - Install a package
- `uv pip freeze` - List installed packages

## Running Tests

Use `uv` to run tests:

```bash
cd backend
uv run python run_tests.py
```
OR
```bash
uv run pytest backend/tests/test_transcript_api.py -v
```

## Benefits of uv

- Faster dependency resolution
- Better caching
- Improved virtual environment management
- Compatible with pip and standard Python workflows

## Documentation

For more information about `uv`, visit the official documentation at [https://github.com/astral-sh/uv](https://github.com/astral-sh/uv).