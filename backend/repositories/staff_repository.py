"""
Staff repository for database operations.
Handles CRUD operations for staff members.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.models import Staff
from backend.repositories.base_repository import BaseRepository


class StaffRepository(BaseRepository[Staff]):
    """Repository for staff database operations."""
    
    def __init__(self, db: Session):
        """Initialize the staff repository."""
        super().__init__(db, Staff)
    
    def get_by_discord_id(self, discord_id: int) -> Optional[Staff]:
        """
        Get a staff member by their Discord ID.
        
        Args:
            discord_id: Discord ID of the staff member
            
        Returns:
            Staff object if found, None otherwise
        """
        return self.db.query(Staff).filter(Staff.discord_id == discord_id).first()
    
    def get_active_staff(self) -> List[Staff]:
        """
        Get all active staff members.
        
        Returns:
            List of active staff members
        """
        return self.db.query(Staff).filter(Staff.active == True).all()
    
    def get_by_role(self, role: str) -> List[Staff]:
        """
        Get all staff members with a specific role.
        
        Args:
            role: Staff role to filter by
            
        Returns:
            List of staff members with the specified role
        """
        return self.db.query(Staff).filter(
            and_(Staff.role == role, Staff.active == True)
        ).all()
    
    def search_staff(
        self, 
        query: str, 
        role: Optional[str] = None,
        active_only: bool = True
    ) -> List[Staff]:
        """
        Search staff members by username.
        
        Args:
            query: Search query for username
            role: Optional role filter
            active_only: Whether to include only active staff
            
        Returns:
            List of matching staff members
        """
        filters = [Staff.username.ilike(f"%{query}%")]
        
        if role:
            filters.append(Staff.role == role)
        
        if active_only:
            filters.append(Staff.active == True)
        
        return self.db.query(Staff).filter(and_(*filters)).all()
    
    def create(self, staff_data: Dict[str, Any]) -> Staff:
        """
        Create a new staff member.
        
        Args:
            staff_data: Dictionary containing staff data
            
        Returns:
            Created staff object
            
        Raises:
            IntegrityError: If Discord ID already exists
        """
        try:
            staff = Staff(**staff_data)
            self.db.add(staff)
            self.db.commit()
            self.db.refresh(staff)
            return staff
        except IntegrityError as e:
            self.db.rollback()
            if "discord_id" in str(e):
                raise ValueError("Staff member with this Discord ID already exists")
            raise e
    
    def update(self, staff_id: UUID, update_data: Dict[str, Any]) -> Optional[Staff]:
        """
        Update a staff member.
        
        Args:
            staff_id: ID of the staff member to update
            update_data: Dictionary containing update data
            
        Returns:
            Updated staff object if found, None otherwise
        """
        staff = self.get_by_id(staff_id)
        if not staff:
            return None
        
        for key, value in update_data.items():
            if hasattr(staff, key):
                setattr(staff, key, value)
        
        try:
            self.db.commit()
            self.db.refresh(staff)
            return staff
        except IntegrityError as e:
            self.db.rollback()
            if "discord_id" in str(e):
                raise ValueError("Staff member with this Discord ID already exists")
            raise e
    
    def deactivate(self, staff_id: UUID) -> bool:
        """
        Deactivate a staff member (soft delete).
        
        Args:
            staff_id: ID of the staff member to deactivate
            
        Returns:
            True if staff member was deactivated, False if not found
        """
        staff = self.get_by_id(staff_id)
        if not staff:
            return False
        
        staff.active = False
        self.db.commit()
        return True
    
    def activate(self, staff_id: UUID) -> bool:
        """
        Activate a staff member.
        
        Args:
            staff_id: ID of the staff member to activate
            
        Returns:
            True if staff member was activated, False if not found
        """
        staff = self.get_by_id(staff_id)
        if not staff:
            return False
        
        staff.active = True
        self.db.commit()
        return True
    
    def update_permissions(
        self, 
        staff_id: UUID, 
        permissions: Dict[str, bool]
    ) -> Optional[Staff]:
        """
        Update staff member permissions.
        
        Args:
            staff_id: ID of the staff member
            permissions: New permissions dictionary
            
        Returns:
            Updated staff object if found, None otherwise
        """
        return self.update(staff_id, {"permissions": permissions})
    
    def get_staff_with_permission(self, permission: str) -> List[Staff]:
        """
        Get all active staff members with a specific permission.
        
        Args:
            permission: Permission to check for
            
        Returns:
            List of staff members with the specified permission
        """
        staff_members = self.get_active_staff()
        return [
            staff for staff in staff_members
            if staff.permissions.get(permission, False)
        ]