"""
Unit tests for the role-based permissions system.
Tests role checking, permission validation, caching, and hierarchy enforcement.
"""
import pytest
import uuid
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.permissions import (
    Role, Permission, has_permission, get_user_permissions,
    check_role_hierarchy, has_multiple_permissions, get_valid_next_statuses,
    ROLE_PERMISSIONS, ROLE_HIERARCHY
)
from app.models.user import User
from app.models.role_assignment import (
    RoleAssignment, get_user_role_in_guild, get_user_permissions_in_guild,
    assign_role_in_guild
)
from app.cache import (
    cache_user_permissions, get_cached_user_permissions,
    invalidate_user_permissions, get_user_permissions_cached,
    init_redis
)


class TestRolePermissions:
    """Test basic role and permission functionality."""
    
    def test_role_enum_values(self):
        """Test that role enum has correct values."""
        assert Role.ADMIN == "ADMIN"
        assert Role.STAFF == "STAFF"
        assert Role.USER == "USER"
    
    def test_permission_enum_values(self):
        """Test that permission enum has correct values."""
        assert Permission.CREATE_TICKET == "CREATE_TICKET"
        assert Permission.MANAGE_TICKETS == "MANAGE_TICKETS"
        assert Permission.VIEW_ANALYTICS == "VIEW_ANALYTICS"
        assert Permission.ADMIN_SETTINGS == "ADMIN_SETTINGS"
    
    def test_user_permissions(self):
        """Test that USER role has correct permissions."""
        user_perms = get_user_permissions("USER")
        expected = {Permission.CREATE_TICKET}
        assert user_perms == expected
    
    def test_staff_permissions(self):
        """Test that STAFF role has correct permissions."""
        staff_perms = get_user_permissions("STAFF")
        expected = {Permission.CREATE_TICKET, Permission.MANAGE_TICKETS}
        assert staff_perms == expected
    
    def test_admin_permissions(self):
        """Test that ADMIN role has all permissions."""
        admin_perms = get_user_permissions("ADMIN")
        expected = {
            Permission.CREATE_TICKET,
            Permission.MANAGE_TICKETS,
            Permission.VIEW_ANALYTICS,
            Permission.ADMIN_SETTINGS
        }
        assert admin_perms == expected
    
    def test_invalid_role_permissions(self):
        """Test that invalid role returns empty permissions."""
        invalid_perms = get_user_permissions("INVALID_ROLE")
        assert invalid_perms == set()
    
    def test_has_permission_user(self):
        """Test permission checking for USER role."""
        assert has_permission("USER", Permission.CREATE_TICKET) is True
        assert has_permission("USER", Permission.MANAGE_TICKETS) is False
        assert has_permission("USER", Permission.VIEW_ANALYTICS) is False
        assert has_permission("USER", Permission.ADMIN_SETTINGS) is False
    
    def test_has_permission_staff(self):
        """Test permission checking for STAFF role."""
        assert has_permission("STAFF", Permission.CREATE_TICKET) is True
        assert has_permission("STAFF", Permission.MANAGE_TICKETS) is True
        assert has_permission("STAFF", Permission.VIEW_ANALYTICS) is False
        assert has_permission("STAFF", Permission.ADMIN_SETTINGS) is False
    
    def test_has_permission_admin(self):
        """Test permission checking for ADMIN role."""
        assert has_permission("ADMIN", Permission.CREATE_TICKET) is True
        assert has_permission("ADMIN", Permission.MANAGE_TICKETS) is True
        assert has_permission("ADMIN", Permission.VIEW_ANALYTICS) is True
        assert has_permission("ADMIN", Permission.ADMIN_SETTINGS) is True
    
    def test_has_permission_invalid_role(self):
        """Test permission checking for invalid role."""
        assert has_permission("INVALID", Permission.CREATE_TICKET) is False


class TestRoleHierarchy:
    """Test role hierarchy functionality."""
    
    def test_role_hierarchy_levels(self):
        """Test that role hierarchy levels are correct."""
        assert ROLE_HIERARCHY[Role.USER] == 1
        assert ROLE_HIERARCHY[Role.STAFF] == 2
        assert ROLE_HIERARCHY[Role.ADMIN] == 3
    
    def test_check_role_hierarchy_equal(self):
        """Test hierarchy check with equal roles."""
        assert check_role_hierarchy("USER", "USER") is True
        assert check_role_hierarchy("STAFF", "STAFF") is True
        assert check_role_hierarchy("ADMIN", "ADMIN") is True
    
    def test_check_role_hierarchy_higher(self):
        """Test hierarchy check with higher roles."""
        assert check_role_hierarchy("STAFF", "USER") is True
        assert check_role_hierarchy("ADMIN", "USER") is True
        assert check_role_hierarchy("ADMIN", "STAFF") is True
    
    def test_check_role_hierarchy_lower(self):
        """Test hierarchy check with lower roles."""
        assert check_role_hierarchy("USER", "STAFF") is False
        assert check_role_hierarchy("USER", "ADMIN") is False
        assert check_role_hierarchy("STAFF", "ADMIN") is False
    
    def test_check_role_hierarchy_invalid(self):
        """Test hierarchy check with invalid roles."""
        assert check_role_hierarchy("INVALID", "USER") is False
        assert check_role_hierarchy("USER", "INVALID") is False
    
    def test_get_valid_next_statuses(self):
        """Test getting valid next roles in hierarchy."""
        user_next = get_valid_next_statuses("USER")
        assert Role.STAFF in user_next
        assert Role.ADMIN in user_next
        assert Role.USER not in user_next
        
        staff_next = get_valid_next_statuses("STAFF")
        assert Role.ADMIN in staff_next
        assert Role.STAFF not in staff_next
        assert Role.USER not in staff_next
        
        admin_next = get_valid_next_statuses("ADMIN")
        assert len(admin_next) == 0  # No higher role than admin


class TestMultiplePermissions:
    """Test bulk permission checking."""
    
    def test_has_multiple_permissions_user(self):
        """Test bulk permission check for USER role."""
        # User should have CREATE_TICKET but not MANAGE_TICKETS
        perms_user_has = [Permission.CREATE_TICKET]
        perms_user_lacks = [Permission.CREATE_TICKET, Permission.MANAGE_TICKETS]
        
        assert has_multiple_permissions("USER", perms_user_has) is True
        assert has_multiple_permissions("USER", perms_user_lacks) is False
    
    def test_has_multiple_permissions_staff(self):
        """Test bulk permission check for STAFF role."""
        perms_staff_has = [Permission.CREATE_TICKET, Permission.MANAGE_TICKETS]
        perms_staff_lacks = [Permission.MANAGE_TICKETS, Permission.ADMIN_SETTINGS]
        
        assert has_multiple_permissions("STAFF", perms_staff_has) is True
        assert has_multiple_permissions("STAFF", perms_staff_lacks) is False
    
    def test_has_multiple_permissions_admin(self):
        """Test bulk permission check for ADMIN role."""
        all_perms = list(Permission)
        assert has_multiple_permissions("ADMIN", all_perms) is True
    
    def test_has_multiple_permissions_empty_list(self):
        """Test bulk permission check with empty list."""
        assert has_multiple_permissions("USER", []) is True
        assert has_multiple_permissions("STAFF", []) is True
        assert has_multiple_permissions("ADMIN", []) is True


class TestRoleAssignmentModel:
    """Test role assignment database model."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_user_id(self):
        """Sample user UUID."""
        return uuid.uuid4()
    
    @pytest.fixture
    def sample_guild_id(self):
        """Sample guild ID."""
        return 123456789012345678
    
    def test_get_user_role_in_guild_with_assignment(self, mock_db_session, sample_user_id, sample_guild_id):
        """Test getting user role when assignment exists."""
        # Mock role assignment
        mock_assignment = Mock()
        mock_assignment.role = "STAFF"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_assignment
        
        role = get_user_role_in_guild(mock_db_session, sample_user_id, sample_guild_id)
        assert role == "STAFF"
    
    def test_get_user_role_in_guild_fallback_to_global(self, mock_db_session, sample_user_id, sample_guild_id):
        """Test getting user role falls back to global role."""
        # Mock no role assignment, but user exists with global role
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [None, Mock(role="USER")]
        
        role = get_user_role_in_guild(mock_db_session, sample_user_id, sample_guild_id)
        assert role == "USER"
    
    def test_get_user_role_in_guild_default(self, mock_db_session, sample_user_id, sample_guild_id):
        """Test getting user role defaults to USER."""
        # Mock no assignment and no user
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        role = get_user_role_in_guild(mock_db_session, sample_user_id, sample_guild_id)
        assert role == "USER"


class TestPermissionCaching:
    """Test Redis caching functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_redis_mock(self):
        """Setup Redis mock for all cache tests."""
        with patch('app.cache.redis_client') as mock_redis:
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = None
            mock_redis.delete.return_value = True
            mock_redis.keys.return_value = []
            yield mock_redis
    
    def test_cache_user_permissions(self, setup_redis_mock):
        """Test caching user permissions."""
        user_id = str(uuid.uuid4())
        permissions = {Permission.CREATE_TICKET, Permission.MANAGE_TICKETS}
        
        cache_user_permissions(user_id, permissions, 12345)
        
        setup_redis_mock.setex.assert_called_once()
        args = setup_redis_mock.setex.call_args[0]
        assert f"permissions:user:{user_id}:guild:12345" in args[0]
    
    def test_get_cached_user_permissions_hit(self, setup_redis_mock):
        """Test getting cached permissions when cache hit."""
        user_id = str(uuid.uuid4())
        cached_data = '["CREATE_TICKET", "MANAGE_TICKETS"]'
        setup_redis_mock.get.return_value = cached_data
        
        permissions = get_cached_user_permissions(user_id, 12345)
        
        expected = {Permission.CREATE_TICKET, Permission.MANAGE_TICKETS}
        assert permissions == expected
    
    def test_get_cached_user_permissions_miss(self, setup_redis_mock):
        """Test getting cached permissions when cache miss."""
        user_id = str(uuid.uuid4())
        setup_redis_mock.get.return_value = None
        
        permissions = get_cached_user_permissions(user_id, 12345)
        
        assert permissions is None
    
    def test_invalidate_user_permissions_specific_guild(self, setup_redis_mock):
        """Test invalidating permissions for specific guild."""
        user_id = str(uuid.uuid4())
        
        invalidate_user_permissions(user_id, 12345)
        
        setup_redis_mock.delete.assert_called_once()
        args = setup_redis_mock.delete.call_args[0]
        assert f"permissions:user:{user_id}:guild:12345" in args[0]
    
    def test_invalidate_user_permissions_all_guilds(self, setup_redis_mock):
        """Test invalidating permissions for all guilds."""
        user_id = str(uuid.uuid4())
        setup_redis_mock.keys.return_value = [
            f"permissions:user:{user_id}:guild:12345",
            f"permissions:user:{user_id}:global"
        ]
        
        invalidate_user_permissions(user_id)
        
        setup_redis_mock.keys.assert_called_once_with(f"permissions:user:{user_id}:*")
        setup_redis_mock.delete.assert_called_once()
    
    @patch('app.cache.get_cached_user_permissions')
    @patch('app.cache.cache_user_permissions')
    def test_get_user_permissions_cached_cache_hit(self, mock_cache_set, mock_cache_get):
        """Test cached permission retrieval with cache hit."""
        user_id = str(uuid.uuid4())
        expected_perms = {Permission.CREATE_TICKET}
        mock_cache_get.return_value = expected_perms
        
        result = get_user_permissions_cached(Mock(), user_id, 12345)
        
        assert result == expected_perms
        mock_cache_set.assert_not_called()  # Should not set cache on hit
    
    @patch('app.cache.get_cached_user_permissions')
    @patch('app.cache.cache_user_permissions')
    @patch('app.models.role_assignment.get_user_permissions_in_guild')
    def test_get_user_permissions_cached_cache_miss(self, mock_get_perms, mock_cache_set, mock_cache_get):
        """Test cached permission retrieval with cache miss."""
        user_id = str(uuid.uuid4())
        expected_perms = {Permission.CREATE_TICKET, Permission.MANAGE_TICKETS}
        mock_cache_get.return_value = None  # Cache miss
        mock_get_perms.return_value = expected_perms
        
        result = get_user_permissions_cached(Mock(), user_id, 12345)
        
        assert result == expected_perms
        mock_cache_set.assert_called_once_with(user_id, expected_perms, 12345)


class TestPermissionDecorators:
    """Test permission decorators and FastAPI dependencies."""
    
    @pytest.fixture
    def mock_user(self):
        """Mock user object."""
        user = Mock()
        user.id = uuid.uuid4()
        user.role = "STAFF"
        user.discord_id = 123456789
        return user
    
    @pytest.fixture
    def mock_user_info(self, mock_user):
        """Mock user info dict from middleware."""
        return {
            "is_authenticated": True,
            "user_id": str(mock_user.id),
            "user": mock_user,
            "role": "STAFF",
            "discord_id": mock_user.discord_id
        }
    
    @patch('app.decorators.get_user_permissions_cached')
    def test_permission_dependency_success(self, mock_get_perms, mock_user_info):
        """Test successful permission check."""
        from app.decorators import PermissionDependency
        
        mock_get_perms.return_value = {Permission.CREATE_TICKET, Permission.MANAGE_TICKETS}
        
        mock_db = Mock()
        
        dependency = PermissionDependency(required_permissions=[Permission.CREATE_TICKET])
        
        result = dependency(mock_user_info, mock_db)
        
        assert result["user_id"] == mock_user_info["user_id"]
        assert result["role"] == "STAFF"
    
    def test_permission_dependency_unauthenticated(self):
        """Test permission check with unauthenticated user."""
        from app.decorators import PermissionDependency
        from fastapi import HTTPException
        
        unauthenticated_user = {"is_authenticated": False}
        
        dependency = PermissionDependency()
        
        with pytest.raises(HTTPException) as exc_info:
            dependency(unauthenticated_user, Mock())
        
        assert exc_info.value.status_code == 401
        assert "Authentication required" in str(exc_info.value.detail)
    
    @patch('app.decorators.get_user_permissions_cached')
    def test_permission_dependency_insufficient_permissions(self, mock_get_perms, mock_user_info):
        """Test permission check with insufficient permissions."""
        from app.decorators import PermissionDependency
        from fastapi import HTTPException
        
        mock_get_perms.return_value = {Permission.CREATE_TICKET}  # Missing MANAGE_TICKETS
        
        mock_db = Mock()
        
        dependency = PermissionDependency(required_permissions=[Permission.MANAGE_TICKETS])
        
        with pytest.raises(HTTPException) as exc_info:
            dependency(mock_user_info, mock_db)
        
        assert exc_info.value.status_code == 403
        assert "Missing permissions" in str(exc_info.value.detail)
