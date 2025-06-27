"""
Role-based permissions system for the ticketbot application.
Defines roles, permissions, and permission checking functionality.
"""
from enum import Enum
from typing import Dict, List, Set
import logging

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles in the system with hierarchical ordering."""
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    USER = "USER"


class Permission(str, Enum):
    """Available permissions in the system."""
    CREATE_TICKET = "CREATE_TICKET"
    MANAGE_TICKETS = "MANAGE_TICKETS"
    VIEW_ANALYTICS = "VIEW_ANALYTICS"
    ADMIN_SETTINGS = "ADMIN_SETTINGS"


# Role hierarchy - higher roles inherit permissions from lower roles
ROLE_HIERARCHY = {
    Role.ADMIN: 3,
    Role.STAFF: 2,
    Role.USER: 1
}

# Permissions mapping for each role
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.USER: {
        Permission.CREATE_TICKET,
    },
    Role.STAFF: {
        Permission.CREATE_TICKET,
        Permission.MANAGE_TICKETS,
    },
    Role.ADMIN: {
        Permission.CREATE_TICKET,
        Permission.MANAGE_TICKETS,
        Permission.VIEW_ANALYTICS,
        Permission.ADMIN_SETTINGS,
    }
}


def has_permission(user_role: str, required_permission: Permission) -> bool:
    """
    Check if a user role has a specific permission.
    
    Args:
        user_role: The user's role as a string
        required_permission: The permission to check for
        
    Returns:
        bool: True if the user has the permission, False otherwise
    """
    try:
        role = Role(user_role)
        return required_permission in ROLE_PERMISSIONS.get(role, set())
    except ValueError:
        logger.warning(f"Invalid role provided: {user_role}")
        return False


def get_user_permissions(user_role: str) -> Set[Permission]:
    """
    Get all permissions for a user role.
    
    Args:
        user_role: The user's role as a string
        
    Returns:
        Set[Permission]: Set of permissions for the role
    """
    try:
        role = Role(user_role)
        return ROLE_PERMISSIONS.get(role, set())
    except ValueError:
        logger.warning(f"Invalid role provided: {user_role}")
        return set()


def check_role_hierarchy(user_role: str, required_role: str) -> bool:
    """
    Check if user role meets the hierarchy requirement.
    
    Args:
        user_role: The user's current role
        required_role: The minimum required role
        
    Returns:
        bool: True if user role is equal or higher than required role
    """
    try:
        user_level = ROLE_HIERARCHY.get(Role(user_role), 0)
        required_level = ROLE_HIERARCHY.get(Role(required_role), 0)
        return user_level >= required_level
    except ValueError:
        logger.warning(f"Invalid role provided: user_role={user_role}, required_role={required_role}")
        return False


def has_multiple_permissions(user_role: str, required_permissions: List[Permission]) -> bool:
    """
    Check if a user has multiple permissions (bulk permission checker).
    
    Args:
        user_role: The user's role as a string
        required_permissions: List of permissions to check
        
    Returns:
        bool: True if user has ALL the permissions, False otherwise
    """
    user_perms = get_user_permissions(user_role)
    return all(perm in user_perms for perm in required_permissions)


def get_valid_next_statuses(current_role: str) -> List[Role]:
    """
    Get valid next roles in hierarchy (for potential role upgrades).
    
    Args:
        current_role: The user's current role
        
    Returns:
        List[Role]: List of roles that are higher in hierarchy
    """
    try:
        current_level = ROLE_HIERARCHY.get(Role(current_role), 0)
        return [role for role, level in ROLE_HIERARCHY.items() if level > current_level]
    except ValueError:
        logger.warning(f"Invalid role provided: {current_role}")
        return []
