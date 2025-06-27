#!/usr/bin/env python3
"""
Quick test script to verify the authentication middleware fixes.
"""

import os
import sys
sys.path.insert(0, '.')

# Set environment variable for JWT
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing'

def test_jwt_generation():
    """Test that JWT generation works with env var set."""
    try:
        from app.auth import generate_token
        user_data = {
            'user_id': '12345',
            'discord_id': 123456789,
            'role': 'USER',
            'email': 'test@example.com'
        }
        token = generate_token(user_data)
        print(f"✅ JWT generation successful: {len(token)} characters")
        return True
    except Exception as e:
        print(f"❌ JWT generation failed: {e}")
        return False

def test_middleware_import():
    """Test that middleware can be imported."""
    try:
        from app.middleware import get_current_user, require_authentication
        print("✅ Middleware import successful")
        return True
    except Exception as e:
        print(f"❌ Middleware import failed: {e}")
        return False

def test_authentication_flow():
    """Test the basic authentication flow."""
    try:
        from fastapi import FastAPI, Depends
        from fastapi.testclient import TestClient
        from app.middleware import require_authentication
        
        # Create test app
        app = FastAPI()
        
        @app.get("/protected")
        def protected_endpoint(user_info=Depends(require_authentication())):
            return {"message": "protected", "user_id": user_info["user_id"]}
        
        client = TestClient(app)
        
        # Test without auth header
        response = client.get("/protected")
        
        if response.status_code == 401:
            detail = response.json()["detail"]
            if "Authorization header required" in detail:
                print("✅ Missing auth header handled correctly")
                return True
            else:
                print(f"❌ Unexpected error message: {detail}")
                return False
        else:
            print(f"❌ Expected 401, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Authentication flow test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing authentication middleware fixes...")
    print()
    
    tests = [
        test_jwt_generation,
        test_middleware_import,
        test_authentication_flow
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All fixes working correctly!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)
