"""Repository for staff database operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Staff, StaffRole
from backend.repositories.base import BaseRepository


class StaffRepository(BaseRepository[Staff]):
    """Repository for staff-specific database operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize staff repository."""
        super().__init__(Staff, session)
    
    async def get_by_discord_id(self, discord_id: int) -> Optional[Staff]:
        """Get staff member by Discord ID.
        
        Args:
            discord_id: Discord ID
            
        Returns:
            Staff instance or None if not found
        """
        result = await self.session.execute(
            select(self.model).where(self.model.discord_id == discord_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_role(
        self,
        role: StaffRole,
        active_only: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Staff]:
        """Get staff members by role.
        
        Args:
            role: Staff role
            active_only: If True, only return active staff members
            limit: Maximum number of staff members to return
            offset: Number of staff members to skip
            
        Returns:
            List of staff members
        """
        query = select(self.model).where(self.model.role == role.value)
        
        if active_only:
            query = query.where(self.model.active == True)
        
        query = query.order_by(self.model.username)
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_active_staff(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Staff]:
        """Get all active staff members.
        
        Args:
            limit: Maximum number of staff members to return
            offset: Number of staff members to skip
            
        Returns:
            List of active staff members
        """
        query = select(self.model).where(self.model.active == True)
        query = query.order_by(self.model.username)
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def search_staff(
        self,
        search_term: str,
        role: Optional[StaffRole] = None,
        active_only: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Staff]:
        """Search staff members by username.
        
        Args:
            search_term: Search term for username
            role: Optional role filter
            active_only: If True, only return active staff members
            limit: Maximum number of staff members to return
            offset: Number of staff members to skip
            
        Returns:
            List of matching staff members
        """
        query = select(self.model).where(
            self.model.username.ilike(f"%{search_term}%")
        )
        
        if role:
            query = query.where(self.model.role == role.value)
        
        if active_only:
            query = query.where(self.model.active == True)
        
        query = query.order_by(self.model.username)
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_staff_with_permission(
        self,
        permission: str,
        active_only: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Staff]:
        """Get staff members with a specific permission.
        
        Args:
            permission: Permission name
            active_only: If True, only return active staff members
            limit: Maximum number of staff members to return
            offset: Number of staff members to skip
            
        Returns:
            List of staff members with the permission
        """
        query = select(self.model).where(
            self.model.permissions[permission].astext == 'true'
        )
        
        if active_only:
            query = query.where(self.model.active == True)
        
        query = query.order_by(self.model.username)
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update_permissions(
        self,
        staff_id: UUID,
        permissions: Dict[str, bool]
    ) -> Optional[Staff]:
        """Update staff member permissions.
        
        Args:
            staff_id: Staff UUID
            permissions: Dictionary of permissions to update
            
        Returns:
            Updated staff instance or None if not found
        """
        staff = await self.get_by_id(staff_id)
        if not staff:
            return None
        
        # Merge with existing permissions
        current_permissions = staff.permissions or {}
        current_permissions.update(permissions)
        
        return await self.update(staff_id, permissions=current_permissions)
    
    async def deactivate_staff(self, staff_id: UUID) -> Optional[Staff]:
        """Deactivate a staff member.
        
        Args:
            staff_id: Staff UUID
            
        Returns:
            Updated staff instance or None if not found
        """
        return await self.update(staff_id, active=False)
    
    async def activate_staff(self, staff_id: UUID) -> Optional[Staff]:
        """Activate a staff member.
        
        Args:
            staff_id: Staff UUID
            
        Returns:
            Updated staff instance or None if not found
        """
        return await self.update(staff_id, active=True)
    
    async def get_staff_stats(self) -> Dict[str, Any]:
        """Get staff statistics.
        
        Returns:
            Dictionary with staff statistics
        """
        # Total staff count
        total_result = await self.session.execute(
            select(func.count(self.model.id))
        )
        total_staff = total_result.scalar()
        
        # Active staff count
        active_result = await self.session.execute(
            select(func.count(self.model.id)).where(self.model.active == True)
        )
        active_staff = active_result.scalar()
        
        # Count by role
        role_counts = {}
        for role in StaffRole:
            count_result = await self.session.execute(
                select(func.count(self.model.id)).where(
                    self.model.role == role.value,
                    self.model.active == True
                )
            )
            role_counts[role.value] = count_result.scalar()
        
        return {
            "total_staff": total_staff,
            "active_staff": active_staff,
            "inactive_staff": total_staff - active_staff,
            "role_counts": role_counts
        }
    
    async def is_staff_member(self, discord_id: int) -> bool:
        """Check if a Discord user is a staff member.
        
        Args:
            discord_id: Discord ID
            
        Returns:
            True if user is an active staff member, False otherwise
        """
        result = await self.session.execute(
            select(self.model.id).where(
                self.model.discord_id == discord_id,
                self.model.active == True
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None
    
    async def has_permission(self, discord_id: int, permission: str) -> bool:
        """Check if a staff member has a specific permission.
        
        Args:
            discord_id: Discord ID
            permission: Permission name
            
        Returns:
            True if staff member has the permission, False otherwise
        """
        staff = await self.get_by_discord_id(discord_id)
        if not staff or not staff.active:
            return False
        
        permissions = staff.permissions or {}
        return permissions.get(permission, False)