"""Tests for the permission manager."""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import discord
from typing import Dict, Any

# Add the parent directory to sys.path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Try the installed package path first, then fall back to relative path
try:
    from discord_bot.bot.permission_manager import PermissionManager
except ImportError:
    # Fall back to relative imports
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
    from bot.permission_manager import PermissionManager


@pytest.fixture
def mock_bot():
    """Create a mock bot for testing."""
    bot = MagicMock()
    return bot


@pytest.fixture
def mock_channel():
    """Create a mock channel for testing."""
    channel = AsyncMock()
    guild = MagicMock()
    channel.guild = guild
    
    # Create a mock default role
    default_role = MagicMock()
    guild.default_role = default_role
    
    # Create a mock bot member
    bot_member = MagicMock()
    guild.me = bot_member
    
    return channel


@pytest.mark.asyncio
async def test_permission_manager_initialization():
    """Test that the permission manager initializes correctly."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create the permission manager
    manager = PermissionManager(bot)
    
    # Check that the manager was initialized correctly
    assert manager.bot == bot
    assert hasattr(manager, 'staff_role_id')
    assert hasattr(manager, 'permission_cache')


@pytest.mark.asyncio
async def test_setup_ticket_permissions(mock_channel):
    """Test setting up ticket permissions."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create a mock user
    user = AsyncMock()
    user.send = AsyncMock()
    mock_channel.guild.get_member.return_value = user
    
    # Create a mock staff role
    staff_role = MagicMock()
    
    # Configure get_role to return different roles based on ID
    def get_role_side_effect(role_id):
        if role_id == 123456789:
            return staff_role
        return None
    
    mock_channel.guild.get_role.side_effect = get_role_side_effect
    
    # Create the permission manager with a mock staff role ID
    manager = PermissionManager(bot)
    manager.staff_role_id = 123456789
    manager.admin_role_id = None  # No admin role configured
    manager.support_team_ids = []  # No support team configured
    
    # Mock the _add_staff_members_to_channel method to avoid complex setup
    manager._add_staff_members_to_channel = AsyncMock()
    manager.auto_invite_available_staff = AsyncMock()
    
    # Set up permissions
    await manager.setup_ticket_permissions(mock_channel, 987654321)
    
    # Check that the guild's get_member method was called correctly
    mock_channel.guild.get_member.assert_called_with(987654321)
    
    # Check that the guild's get_role method was called correctly
    mock_channel.guild.get_role.assert_called_with(123456789)
    
    # Check that the channel's set_permissions method was called correctly
    assert mock_channel.set_permissions.call_count >= 3
    
    # Check that the default role permissions were set
    mock_channel.set_permissions.assert_any_call(
        mock_channel.guild.default_role,
        read_messages=False,
        send_messages=False
    )
    
    # Check that the user permissions were set
    mock_channel.set_permissions.assert_any_call(
        user,
        read_messages=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True
    )
    
    # Check that the staff role permissions were set
    mock_channel.set_permissions.assert_any_call(
        staff_role,
        read_messages=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        manage_messages=True
    )
    
    # Check that the permission cache was updated
    assert f"{mock_channel.id}_987654321" in manager.permission_cache


@pytest.mark.asyncio
async def test_update_ticket_permissions_closed(mock_channel):
    """Test updating ticket permissions when closed."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create a mock user
    user = MagicMock()
    mock_channel.guild.get_member.return_value = user
    
    # Create the permission manager
    manager = PermissionManager(bot)
    
    # Mock the bulk_update_permissions method since it's called for closed tickets
    manager.bulk_update_permissions = AsyncMock()
    
    # Update permissions
    await manager.update_ticket_permissions(mock_channel, user_id=987654321, is_closed=True)
    
    # Check that bulk_update_permissions was called
    manager.bulk_update_permissions.assert_called_once_with(mock_channel, True)


@pytest.mark.asyncio
async def test_update_ticket_permissions_staff(mock_channel):
    """Test updating ticket permissions for staff."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create a mock staff member
    staff = MagicMock()
    mock_channel.guild.get_member.return_value = staff
    
    # Create the permission manager
    manager = PermissionManager(bot)
    
    # Update permissions
    await manager.update_ticket_permissions(mock_channel, staff_id=123456789)
    
    # Check that the guild's get_member method was called correctly
    mock_channel.guild.get_member.assert_called_with(123456789)
    
    # Check that the channel's set_permissions method was called correctly
    mock_channel.set_permissions.assert_any_call(
        staff,
        read_messages=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        manage_messages=True
    )
    
    # Check that the permission cache was updated
    assert f"{mock_channel.id}_123456789" in manager.permission_cache


@pytest.mark.asyncio
async def test_add_staff_members_to_channel(mock_channel):
    """Test adding staff members to a channel."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create mock staff members
    staff1 = AsyncMock()
    staff1.send = AsyncMock()
    staff2 = AsyncMock()
    staff2.send = AsyncMock()
    
    # Configure get_member to return different staff members based on ID
    def get_member_side_effect(member_id):
        if member_id == 111111:
            return staff1
        elif member_id == 222222:
            return staff2
        return None
    
    mock_channel.guild.get_member.side_effect = get_member_side_effect
    
    # Create the permission manager
    manager = PermissionManager(bot)
    
    # Add staff members
    staff_ids = [111111, 222222, 333333]  # 333333 doesn't exist
    results = await manager._add_staff_members_to_channel(mock_channel, staff_ids)
    
    # Check that the guild's get_member method was called correctly
    assert mock_channel.guild.get_member.call_count == 3
    
    # Check that the channel's set_permissions method was called correctly
    assert mock_channel.set_permissions.call_count == 2
    
    # Check the results
    assert len(results) == 3
    assert results[0] == (111111, True)
    assert results[1] == (222222, True)
    assert results[2] == (333333, False)
    
    # Check that the permission cache was updated
    assert f"{mock_channel.id}_111111" in manager.permission_cache
    assert f"{mock_channel.id}_222222" in manager.permission_cache
    assert f"{mock_channel.id}_333333" not in manager.permission_cache


@pytest.mark.asyncio
async def test_update_all_staff_permissions(mock_channel):
    """Test updating permissions for all staff members."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create mock staff role and members
    staff_role = MagicMock()
    staff_role.id = 123456789
    
    staff_member = MagicMock()
    staff_member.roles = [staff_role]
    
    regular_member = MagicMock()
    regular_member.roles = []
    
    # Set up channel overwrites
    mock_channel.overwrites = {
        staff_role: MagicMock(),
        staff_member: MagicMock(),
        regular_member: MagicMock(),
        mock_channel.guild.default_role: MagicMock(),
        mock_channel.guild.me: MagicMock()
    }
    
    # Create the permission manager
    manager = PermissionManager(bot)
    manager.staff_role_id = 123456789
    
    # Configure get_role to return the staff role
    mock_channel.guild.get_role.return_value = staff_role
    
    # Update all staff permissions
    await manager._update_all_staff_permissions(mock_channel, is_closed=True)
    
    # Check that the channel's set_permissions method was called correctly
    assert mock_channel.set_permissions.call_count == 2
    
    # Check that the staff role permissions were updated
    mock_channel.set_permissions.assert_any_call(
        staff_role,
        read_messages=True,
        send_messages=False,
        embed_links=False,
        attach_files=False,
        read_message_history=True,
        manage_messages=True
    )
    
    # Check that the staff member permissions were updated
    mock_channel.set_permissions.assert_any_call(
        staff_member,
        read_messages=True,
        send_messages=False,
        embed_links=False,
        attach_files=False,
        read_message_history=True,
        manage_messages=True
    )


@pytest.mark.asyncio
async def test_invite_user_to_channel(mock_channel):
    """Test inviting a user to a channel."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create a mock user
    user = AsyncMock()
    mock_channel.guild.get_member.return_value = user
    
    # Create the permission manager
    manager = PermissionManager(bot)
    
    # Invite user
    result = await manager.invite_user_to_channel(mock_channel, 987654321)
    
    # Check that the guild's get_member method was called correctly
    mock_channel.guild.get_member.assert_called_once_with(987654321)
    
    # Check that the channel's set_permissions method was called correctly
    mock_channel.set_permissions.assert_called_once_with(
        user,
        read_messages=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True
    )
    
    # Check that a message was sent to the channel
    mock_channel.send.assert_called_once()
    
    # Check that a DM was sent to the user
    user.send.assert_called_once()
    
    # Check the result
    assert result is True
    
    # Check that the permission cache was updated
    assert f"{mock_channel.id}_987654321" in manager.permission_cache


@pytest.mark.asyncio
async def test_invite_staff_to_channel(mock_channel):
    """Test inviting a staff member to a channel."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create a mock staff member
    staff = AsyncMock()
    mock_channel.guild.get_member.return_value = staff
    
    # Create the permission manager
    manager = PermissionManager(bot)
    
    # Invite staff
    result = await manager.invite_user_to_channel(mock_channel, 123456789, is_staff=True)
    
    # Check that the guild's get_member method was called correctly
    mock_channel.guild.get_member.assert_called_once_with(123456789)
    
    # Check that the channel's set_permissions method was called correctly
    mock_channel.set_permissions.assert_called_once_with(
        staff,
        read_messages=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        manage_messages=True
    )
    
    # Check that a message was sent to the channel
    mock_channel.send.assert_called_once()
    
    # Check that a DM was sent to the staff member
    staff.send.assert_called_once()
    
    # Check the result
    assert result is True
    
    # Check that the permission cache was updated
    assert f"{mock_channel.id}_123456789" in manager.permission_cache


@pytest.mark.asyncio
async def test_remove_user_from_channel(mock_channel):
    """Test removing a user from a channel."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create a mock user
    user = MagicMock()
    mock_channel.guild.get_member.return_value = user
    
    # Create the permission manager
    manager = PermissionManager(bot)
    
    # Add user to permission cache
    cache_key = f"{mock_channel.id}_987654321"
    manager.permission_cache[cache_key] = {
        "read_messages": True,
        "send_messages": True
    }
    
    # Remove user
    result = await manager.remove_user_from_channel(mock_channel, 987654321)
    
    # Check that the guild's get_member method was called correctly
    mock_channel.guild.get_member.assert_called_once_with(987654321)
    
    # Check that the channel's set_permissions method was called correctly
    mock_channel.set_permissions.assert_called_once_with(user, overwrite=None)
    
    # Check that a message was sent to the channel
    mock_channel.send.assert_called_once()
    
    # Check the result
    assert result is True
    
    # Check that the permission cache was updated
    assert cache_key not in manager.permission_cache


@pytest.mark.asyncio
async def test_get_channel_members(mock_channel):
    """Test getting channel members."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create mock staff role and members
    staff_role = MagicMock()
    staff_role.id = 123456789
    
    staff_member = MagicMock()
    staff_member.id = 111111
    staff_member.roles = [staff_role]
    
    regular_member1 = MagicMock()
    regular_member1.id = 222222
    regular_member1.roles = []
    
    regular_member2 = MagicMock()
    regular_member2.id = 333333
    regular_member2.roles = []
    
    # Create mock permission overwrites
    staff_overwrite = MagicMock()
    staff_overwrite.read_messages = True
    
    user1_overwrite = MagicMock()
    user1_overwrite.read_messages = True
    
    user2_overwrite = MagicMock()
    user2_overwrite.read_messages = False  # This user should be excluded
    
    # Set up channel overwrites
    mock_channel.overwrites = {
        staff_member: staff_overwrite,
        regular_member1: user1_overwrite,
        regular_member2: user2_overwrite
    }
    
    # Create the permission manager
    manager = PermissionManager(bot)
    manager.staff_role_id = 123456789
    
    # Configure get_role to return the staff role
    mock_channel.guild.get_role.return_value = staff_role
    
    # Get channel members
    result = manager.get_channel_members(mock_channel)
    
    # Check the result
    assert "users" in result
    assert "staff" in result
    assert len(result["users"]) == 1
    assert len(result["staff"]) == 1
    assert 222222 in result["users"]
    assert 111111 in result["staff"]
    assert 333333 not in result["users"]


@pytest.mark.asyncio
async def test_sync_channel_permissions(mock_channel):
    """Test synchronizing channel permissions with ticket data."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create mock user and staff member
    user = MagicMock()
    user.id = 987654321
    
    staff = MagicMock()
    staff.id = 123456789
    
    # Configure get_member to return different users based on ID
    def get_member_side_effect(member_id):
        if member_id == 987654321:
            return user
        elif member_id == 123456789:
            return staff
        return None
    
    mock_channel.guild.get_member.side_effect = get_member_side_effect
    
    # Create mock roles
    staff_role = MagicMock()
    staff_role.id = 111111
    
    admin_role = MagicMock()
    admin_role.id = 222222
    
    # Configure get_role to return different roles based on ID
    def get_role_side_effect(role_id):
        if role_id == 111111:
            return staff_role
        elif role_id == 222222:
            return admin_role
        return None
    
    mock_channel.guild.get_role.side_effect = get_role_side_effect
    
    # Create the permission manager
    manager = PermissionManager(bot)
    manager.staff_role_id = 111111
    manager.admin_role_id = 222222
    
    # Create ticket data
    ticket_data = {
        "id": "ticket-123",
        "creator_discord_id": 987654321,
        "assigned_staff_id": 123456789,
        "status": "open"
    }
    
    # Sync permissions
    await manager.sync_channel_permissions(mock_channel, ticket_data)
    
    # Check that the channel's set_permissions method was called correctly
    assert mock_channel.set_permissions.call_count == 4
    
    # Check that the user permissions were set
    mock_channel.set_permissions.assert_any_call(
        user,
        **manager.ticket_permissions["user"]
    )
    
    # Check that the staff permissions were set
    mock_channel.set_permissions.assert_any_call(
        staff,
        **manager.ticket_permissions["staff"]
    )
    
    # Check that the staff role permissions were set
    mock_channel.set_permissions.assert_any_call(
        staff_role,
        **manager.ticket_permissions["staff"]
    )
    
    # Check that the admin role permissions were set
    mock_channel.set_permissions.assert_any_call(
        admin_role,
        **manager.ticket_permissions["admin"]
    )


@pytest.mark.asyncio
async def test_sync_channel_permissions_closed_ticket(mock_channel):
    """Test synchronizing channel permissions with closed ticket data."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create mock user and staff member
    user = MagicMock()
    user.id = 987654321
    
    staff = MagicMock()
    staff.id = 123456789
    
    # Configure get_member to return different users based on ID
    def get_member_side_effect(member_id):
        if member_id == 987654321:
            return user
        elif member_id == 123456789:
            return staff
        return None
    
    mock_channel.guild.get_member.side_effect = get_member_side_effect
    
    # Create mock roles
    staff_role = MagicMock()
    staff_role.id = 111111
    
    # Configure get_role to return different roles based on ID
    def get_role_side_effect(role_id):
        if role_id == 111111:
            return staff_role
        return None
    
    mock_channel.guild.get_role.side_effect = get_role_side_effect
    
    # Create the permission manager
    manager = PermissionManager(bot)
    manager.staff_role_id = 111111
    
    # Create ticket data for a closed ticket
    ticket_data = {
        "id": "ticket-123",
        "creator_discord_id": 987654321,
        "assigned_staff_id": 123456789,
        "status": "closed"
    }
    
    # Sync permissions
    await manager.sync_channel_permissions(mock_channel, ticket_data)
    
    # Check that the channel's set_permissions method was called correctly
    assert mock_channel.set_permissions.call_count == 3
    
    # Check that the user permissions were set with closed permissions
    mock_channel.set_permissions.assert_any_call(
        user,
        **manager.ticket_permissions["closed_user"]
    )
    
    # Check that the staff permissions were set with closed permissions
    mock_channel.set_permissions.assert_any_call(
        staff,
        **manager.ticket_permissions["closed_staff"]
    )
    
    # Check that the staff role permissions were set with closed permissions
    mock_channel.set_permissions.assert_any_call(
        staff_role,
        **manager.ticket_permissions["closed_staff"]
    )


@pytest.mark.asyncio
async def test_bulk_update_permissions(mock_channel):
    """Test bulk updating permissions for all users in a channel."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create mock users
    user1 = MagicMock()
    user1.id = 111111
    
    user2 = MagicMock()
    user2.id = 222222
    
    staff1 = MagicMock()
    staff1.id = 333333
    
    staff2 = MagicMock()
    staff2.id = 444444
    
    # Configure get_member to return different users based on ID
    def get_member_side_effect(member_id):
        if member_id == 111111:
            return user1
        elif member_id == 222222:
            return user2
        elif member_id == 333333:
            return staff1
        elif member_id == 444444:
            return staff2
        return None
    
    mock_channel.guild.get_member.side_effect = get_member_side_effect
    
    # Create mock staff role
    staff_role = MagicMock()
    staff_role.id = 555555
    
    # Configure get_role to return the staff role
    mock_channel.guild.get_role.return_value = staff_role
    
    # Create the permission manager
    manager = PermissionManager(bot)
    manager.staff_role_id = 555555
    
    # Mock the get_channel_members method
    manager.get_channel_members = MagicMock(return_value={
        "users": [111111, 222222],
        "staff": [333333, 444444]
    })
    
    # Bulk update permissions for a closed ticket
    await manager.bulk_update_permissions(mock_channel, is_closed=True)
    
    # Check that the channel's set_permissions method was called correctly
    assert mock_channel.set_permissions.call_count == 5
    
    # Check that the user permissions were set with closed permissions
    mock_channel.set_permissions.assert_any_call(
        user1,
        **manager.ticket_permissions["closed_user"]
    )
    
    mock_channel.set_permissions.assert_any_call(
        user2,
        **manager.ticket_permissions["closed_user"]
    )
    
    # Check that the staff permissions were set with closed permissions
    mock_channel.set_permissions.assert_any_call(
        staff1,
        **manager.ticket_permissions["closed_staff"]
    )
    
    mock_channel.set_permissions.assert_any_call(
        staff2,
        **manager.ticket_permissions["closed_staff"]
    )
    
    # Check that the staff role permissions were set with closed permissions
    mock_channel.set_permissions.assert_any_call(
        staff_role,
        **manager.ticket_permissions["closed_staff"]
    )


@pytest.mark.asyncio
async def test_auto_invite_available_staff(mock_channel):
    """Test automatically inviting available staff members to a ticket channel."""
    # Create a mock bot
    bot = MagicMock()
    
    # Create mock staff members with different statuses
    online_staff1 = MagicMock()
    online_staff1.id = 111111
    online_staff1.status = discord.Status.online
    
    online_staff2 = MagicMock()
    online_staff2.id = 222222
    online_staff2.status = discord.Status.idle
    
    offline_staff = MagicMock()
    offline_staff.id = 333333
    offline_staff.status = discord.Status.offline
    
    # Create mock staff role
    staff_role = MagicMock()
    
    # Set up roles for staff members
    online_staff1.roles = [staff_role]
    online_staff2.roles = [staff_role]
    offline_staff.roles = [staff_role]
    
    # Set up guild members
    mock_channel.guild.members = [online_staff1, online_staff2, offline_staff]
    
    # Configure get_role to return the staff role
    mock_channel.guild.get_role.return_value = staff_role
    
    # Create the permission manager
    manager = PermissionManager(bot)
    manager.staff_role_id = 555555
    
    # Mock the _add_staff_members_to_channel method
    manager._add_staff_members_to_channel = AsyncMock(return_value=[
        (111111, True),
        (222222, True)
    ])
    
    # Auto-invite available staff
    results = await manager.auto_invite_available_staff(mock_channel)
    
    # Check that _add_staff_members_to_channel was called with the correct staff IDs
    manager._add_staff_members_to_channel.assert_called_once()
    call_args = manager._add_staff_members_to_channel.call_args[0]
    assert call_args[0] == mock_channel
    assert set(call_args[1]) == {111111, 222222}
    
    # Check the results
    assert len(results) == 2
    assert (111111, True) in results
    assert (222222, True) in results