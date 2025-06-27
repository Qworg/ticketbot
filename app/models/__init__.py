"""
Models package initialization.
Exports all models for easy importing.
"""
from app.models.user import User
from app.models.role_assignment import RoleAssignment

__all__ = ["User", "RoleAssignment"]
