#!/usr/bin/env python3
"""
Manual integration test for the ticket update endpoint.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.schemas import TicketUpdateRequest, TicketUpdateResponse
from app.status import TicketStatus

def test_schema_validation():
    """Test the schema validation works properly."""
    print("=== Testing Schema Validation ===")
    
    # Test 1: Valid update request
    try:
        req = TicketUpdateRequest(
            status="in_progress",
            category="bug", 
            assigned_to=123456789012345678,
            close_reason=None
        )
        print("✓ Valid request created successfully")
        print(f"  Status: {req.status}")
        print(f"  Category: {req.category}")
        print(f"  Assigned to: {req.assigned_to}")
    except Exception as e:
        print(f"✗ Error creating valid request: {e}")
        return False
    
    # Test 2: Close with reason
    try:
        req = TicketUpdateRequest(
            status="closed",
            category=None,
            assigned_to=None,
            close_reason="Issue resolved"
        )
        print("✓ Close with reason validation passed")
    except Exception as e:
        print(f"✗ Error with close reason: {e}")
        return False
    
    # Test 3: Close without reason (should fail)
    try:
        req = TicketUpdateRequest(
            status="closed",
            category=None,
            assigned_to=None,
            close_reason=None
        )
        print("✗ Close without reason should have failed")
        return False
    except ValueError as e:
        print("✓ Close without reason properly rejected")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False
    
    # Test 4: Invalid status
    try:
        req = TicketUpdateRequest(
            status="invalid_status",
            category=None,
            assigned_to=None,
            close_reason=None
        )
        print("✗ Invalid status should have failed")
        return False
    except ValueError as e:
        print("✓ Invalid status properly rejected")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False
    
    print("All schema validation tests passed!")
    return True

def test_status_transitions():
    """Test status transition validation."""
    print("\n=== Testing Status Transitions ===")
    
    from app.status import validate_status_transition, get_valid_next_statuses
    
    # Test valid transitions
    valid_transitions = [
        ("open", "in_progress"),
        ("open", "closed"),
        ("in_progress", "resolved"),
        ("in_progress", "closed"),
        ("resolved", "closed"),
        ("resolved", "in_progress"),
        ("in_progress", "open"),
    ]
    
    for current, new in valid_transitions:
        if validate_status_transition(current, new):
            print(f"✓ {current} → {new}: Valid")
        else:
            print(f"✗ {current} → {new}: Should be valid but was rejected")
            return False
    
    # Test invalid transitions
    invalid_transitions = [
        ("closed", "open"),
        ("closed", "in_progress"),
        ("closed", "resolved"),
        ("open", "resolved"),  # Should go through in_progress first
    ]
    
    for current, new in invalid_transitions:
        if not validate_status_transition(current, new):
            print(f"✓ {current} → {new}: Properly rejected")
        else:
            print(f"✗ {current} → {new}: Should be invalid but was allowed")
            return False
    
    print("All status transition tests passed!")
    return True

if __name__ == "__main__":
    print("Running Ticket Update Integration Tests...")
    
    success = True
    success &= test_schema_validation()
    success &= test_status_transitions()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
