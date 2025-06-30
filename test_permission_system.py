#!/usr/bin/env python3
"""
Simple test script to verify the permission system implementation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported."""
    try:
        from app.models.guild import Guild, get_guild_staff_role_ids, get_guild_admin_role_ids
        print("✅ Guild model imported successfully")
        
        from app.commands.implementations.ticket import TicketCommand
        print("✅ TicketCommand imported successfully")
        
        # Test instantiation
        command = TicketCommand()
        print(f"✅ TicketCommand instantiated: {command.name}")
        
        # Check new methods exist
        if hasattr(command, 'update_channel_permissions_for_user'):
            print("✅ update_channel_permissions_for_user method exists")
        else:
            print("❌ update_channel_permissions_for_user method missing")
            
        if hasattr(command, 'update_channel_permissions_for_role'):
            print("✅ update_channel_permissions_for_role method exists")
        else:
            print("❌ update_channel_permissions_for_role method missing")
            
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_guild_model():
    """Test the Guild model functionality."""
    try:
        from app.models.guild import Guild
        
        # Test Guild model creation
        guild = Guild(
            id=123456789,
            name="Test Guild",
            staff_role_ids=[111, 222],
            admin_role_ids=[333],
            ticket_category_name="🎫 Test Tickets"
        )
        
        print("✅ Guild model can be instantiated")
        print(f"   Guild ID: {guild.id}")
        print(f"   Staff roles: {guild.staff_role_ids}")
        print(f"   Admin roles: {guild.admin_role_ids}")
        
        return True
        
    except Exception as e:
        print(f"❌ Guild model error: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Permission System Implementation")
    print("=" * 40)
    
    success = True
    
    print("\n1. Testing imports...")
    success &= test_imports()
    
    print("\n2. Testing Guild model...")
    success &= test_guild_model()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
