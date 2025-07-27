#!/usr/bin/env python3
"""
Integration test runner for the Discord Ticket Bot backend.
Runs comprehensive integration tests with proper setup and teardown.
"""
import asyncio
import subprocess
import sys
import os
from pathlib import Path


def setup_test_environment():
    """Set up test environment variables and dependencies."""
    # Set test environment variables
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_integration.db"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["JWT_SECRET_KEY"] = "test_secret_key_for_integration_tests"
    
    print("✓ Test environment configured")


def cleanup_test_files():
    """Clean up test database files."""
    test_files = [
        "test_integration.db",
        "test_integration.db-shm",
        "test_integration.db-wal"
    ]
    
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"✓ Cleaned up {file}")


def run_integration_tests():
    """Run integration tests with proper configuration."""
    print("🚀 Starting integration tests...")
    
    # Setup
    setup_test_environment()
    cleanup_test_files()
    
    try:
        # Run integration tests
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/integration/",
            "-v",
            "--tb=short",
            "--asyncio-mode=auto",
            "--disable-warnings"
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print("✅ All integration tests passed!")
        else:
            print("❌ Some integration tests failed!")
            
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1
    finally:
        # Cleanup
        cleanup_test_files()
        print("🧹 Cleanup completed")


def run_specific_test(test_path):
    """Run a specific integration test."""
    print(f"🎯 Running specific test: {test_path}")
    
    setup_test_environment()
    cleanup_test_files()
    
    try:
        cmd = [
            sys.executable, "-m", "pytest",
            f"tests/integration/{test_path}",
            "-v",
            "--tb=short",
            "--asyncio-mode=auto"
        ]
        
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        return result.returncode
    finally:
        cleanup_test_files()


def main():
    """Main entry point for integration test runner."""
    if len(sys.argv) > 1:
        # Run specific test
        test_path = sys.argv[1]
        return run_specific_test(test_path)
    else:
        # Run all integration tests
        return run_integration_tests()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)