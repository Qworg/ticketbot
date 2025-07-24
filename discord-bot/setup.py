"""Setup script for discord-bot package."""

from setuptools import setup, find_packages

setup(
    name="discord_bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "py-cord>=2.0.0",
        "httpx>=0.20.0",
        "pytest>=7.0.0",
        "pytest-asyncio>=0.18.0",
    ],
)