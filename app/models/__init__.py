"""
Models package initialization.
Exports all models for easy importing.
"""
from app.models.user import User
from app.models.role_assignment import RoleAssignment
from app.models.ticket import Ticket

__all__ = ["User", "RoleAssignment", "Ticket"]
