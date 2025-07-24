"""Permission manager for Discord channel permissions."""

import logging
import discord
import asyncio
from typing import Dict, List, Optional, Any, Tuple

from discord_bot.config.settings import config, logger


class PermissionManager:
    """Manager for Discord channel permissions."""
    
    def __init__(self, bot):
        """Initialize the permission manager.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.staff_role_id = config.staff_role_id
        self.admin_role_id = getattr(config, 'admin_role_id', None)
        self.support_team_ids = getattr(config, 'support_team_ids', [])
        self.permission_cache = {}  # Cache for permission overrides
        self.ticket_permissions = {
            "user": {
                "read_messages": True,
                "send_messages": True,
                "embed_links": True,
                "attach_files": True,
                "read_message_history": True
            },
            "staff": {
                "read_messages": True,
                "send_messages": True,
                "embed_links": True,
                "attach_files": True,
                "read_message_history": True,
                "manage_messages": True
            },
            "admin": {
                "read_messages": True,
                "send_messages": True,
                "embed_links": True,
                "attach_files": True,
                "read_message_history": True,
                "manage_messages": True,
                "manage_channels": True
            },
            "closed_user": {
                "read_messages": True,
                "send_messages": False,
                "embed_links": False,
                "attach_files": False,
                "read_message_history": True
            },
            "closed_staff": {
                "read_messages": True,
                "send_messages": False,
                "embed_links": False,
                "attach_files": False,
                "read_message_history": True,
                "manage_messages": True
            }
        }
    
    async def setup_ticket_permissions(
        self, 
        channel: discord.TextChannel,
        user_id: int,
        staff_ids: Optional[List[int]] = None
    ) -> None:
        """Set up permissions for a ticket channel.
        
        Args:
            channel: The Discord text channel
            user_id: The user ID of the ticket creator
            staff_ids: Optional list of staff member IDs to add
        """
        guild = channel.guild
        
        try:
            # Get the staff role
            staff_role = None
            if self.staff_role_id:
                staff_role = guild.get_role(self.staff_role_id)
            
            # Get admin role if configured
            admin_role = None
            if self.admin_role_id:
                admin_role = guild.get_role(self.admin_role_id)
            
            # Set default permissions (hide from everyone)
            await channel.set_permissions(
                guild.default_role,
                read_messages=False,
                send_messages=False
            )
            
            # Allow the ticket creator to see and write in the channel
            user = guild.get_member(user_id)
            if user:
                await channel.set_permissions(
                    user,
                    **self.ticket_permissions["user"]
                )
                # Cache the user's permissions
                self.permission_cache[f"{channel.id}_{user_id}"] = self.ticket_permissions["user"]
                
                # Send a direct message to the user with the channel link
                try:
                    await user.send(
                        f"Your support ticket has been created in {channel.mention}. "
                        f"Click the link to access your ticket."
                    )
                    logger.info(f"Sent ticket channel notification to user {user_id}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    logger.warning(f"Could not send DM to user {user_id}: {e}")
            
            # Allow staff role to see and write in the channel
            if staff_role:
                await channel.set_permissions(
                    staff_role,
                    **self.ticket_permissions["staff"]
                )
            
            # Allow admin role if configured
            if admin_role:
                await channel.set_permissions(
                    admin_role,
                    **self.ticket_permissions["admin"]
                )
            
            # Allow specific staff members
            if staff_ids:
                await self._add_staff_members_to_channel(channel, staff_ids)
            
            # Add default support team members if configured
            if self.support_team_ids:
                await self._add_staff_members_to_channel(channel, self.support_team_ids)
            
            # Auto-invite available staff members if enabled
            auto_invite_staff = getattr(config, 'auto_invite_staff', False)
            if auto_invite_staff:
                # Exclude any explicitly specified staff IDs to avoid duplicates
                exclude_ids = staff_ids or []
                exclude_ids.extend(self.support_team_ids)
                await self.auto_invite_available_staff(channel, exclude_ids)
            
            # Always allow the bot to see and write in the channel
            await channel.set_permissions(
                guild.me,
                **self.ticket_permissions["admin"]
            )
            
            logger.info(f"Set up permissions for ticket channel: {channel.name}")
        except discord.Forbidden:
            logger.error(f"Missing permissions to set up ticket channel: {channel.name}")
        except Exception as e:
            logger.error(f"Error setting up ticket permissions: {e}")
    
    async def _add_staff_members_to_channel(
        self,
        channel: discord.TextChannel,
        staff_ids: List[int],
        is_closed: bool = False
    ) -> List[Tuple[int, bool]]:
        """Add staff members to a ticket channel.
        
        Args:
            channel: The Discord text channel
            staff_ids: List of staff member IDs to add
            is_closed: Whether the ticket is closed
            
        Returns:
            List of tuples containing staff ID and whether they were successfully added
        """
        guild = channel.guild
        results = []
        
        # Select the appropriate permission set
        perm_set = "closed_staff" if is_closed else "staff"
        
        for staff_id in staff_ids:
            staff_member = guild.get_member(staff_id)
            if staff_member:
                try:
                    # Apply permissions from the standardized set
                    await channel.set_permissions(
                        staff_member,
                        **self.ticket_permissions[perm_set]
                    )
                    
                    # Cache the staff member's permissions
                    self.permission_cache[f"{channel.id}_{staff_id}"] = self.ticket_permissions[perm_set]
                    
                    # Notify staff member about the ticket assignment
                    try:
                        await staff_member.send(
                            f"You have been added to a support ticket in {channel.mention}. "
                            f"Click the link to access the ticket."
                        )
                        logger.info(f"Sent ticket channel notification to staff {staff_id}")
                    except (discord.Forbidden, discord.HTTPException) as e:
                        logger.warning(f"Could not send DM to staff {staff_id}: {e}")
                    
                    results.append((staff_id, True))
                    logger.info(f"Added staff member {staff_id} to channel {channel.name}")
                except Exception as e:
                    logger.error(f"Error adding staff member {staff_id} to channel: {e}")
                    results.append((staff_id, False))
            else:
                logger.warning(f"Staff member {staff_id} not found in guild")
                results.append((staff_id, False))
        
        return results
    
    async def update_ticket_permissions(
        self,
        channel: discord.TextChannel,
        user_id: Optional[int] = None,
        staff_id: Optional[int] = None,
        is_closed: bool = False
    ) -> None:
        """Update permissions for a ticket channel.
        
        Args:
            channel: The Discord text channel
            user_id: Optional user ID to update permissions for
            staff_id: Optional staff ID to add to the channel
            is_closed: Whether the ticket is closed
        """
        guild = channel.guild
        
        try:
            # If the ticket is closed, update permissions for all members
            if is_closed:
                # Use bulk update for efficiency
                await self.bulk_update_permissions(channel, is_closed)
                logger.info(f"Bulk updated permissions for closed ticket in channel {channel.name}")
                return
            
            # Update user permissions if provided
            if user_id:
                user = guild.get_member(user_id)
                if user:
                    # Select the appropriate permission set
                    perm_set = "closed_user" if is_closed else "user"
                    
                    await channel.set_permissions(
                        user,
                        **self.ticket_permissions[perm_set]
                    )
                    # Update cache
                    self.permission_cache[f"{channel.id}_{user_id}"] = self.ticket_permissions[perm_set]
                    logger.info(f"Updated permissions for user {user_id} in channel {channel.name}")
            
            # If a staff member is assigned, add them to the channel
            if staff_id:
                staff_member = guild.get_member(staff_id)
                if staff_member:
                    # Select the appropriate permission set
                    perm_set = "closed_staff" if is_closed else "staff"
                    
                    await channel.set_permissions(
                        staff_member,
                        **self.ticket_permissions[perm_set]
                    )
                    # Update cache
                    self.permission_cache[f"{channel.id}_{staff_id}"] = self.ticket_permissions[perm_set]
                    
                    # Notify staff member about the ticket assignment
                    try:
                        await staff_member.send(
                            f"You have been assigned to a support ticket in {channel.mention}. "
                            f"Click the link to access the ticket."
                        )
                        logger.info(f"Sent ticket assignment notification to staff {staff_id}")
                    except (discord.Forbidden, discord.HTTPException) as e:
                        logger.warning(f"Could not send DM to staff {staff_id}: {e}")
                    
                    logger.info(f"Added staff member {staff_id} to channel {channel.name}")
        except discord.Forbidden:
            logger.error(f"Missing permissions to update ticket channel: {channel.name}")
        except Exception as e:
            logger.error(f"Error updating ticket permissions: {e}")
    
    async def _update_all_staff_permissions(
        self,
        channel: discord.TextChannel,
        is_closed: bool
    ) -> None:
        """Update permissions for all staff members in a channel.
        
        Args:
            channel: The Discord text channel
            is_closed: Whether the ticket is closed
        """
        guild = channel.guild
        
        # Select the appropriate permission set
        perm_set = "closed_staff" if is_closed else "staff"
        
        # Get all permission overwrites for the channel
        for target, overwrite in channel.overwrites.items():
            # Skip the default role and the bot
            if target == guild.default_role or target == guild.me:
                continue
            
            # Check if the target is a member and has the staff role
            if isinstance(target, discord.Member):
                staff_role = None
                if self.staff_role_id:
                    staff_role = guild.get_role(self.staff_role_id)
                
                if staff_role and staff_role in target.roles:
                    # Update permissions for staff member using standardized set
                    await channel.set_permissions(
                        target,
                        **self.ticket_permissions[perm_set]
                    )
                    # Update cache
                    self.permission_cache[f"{channel.id}_{target.id}"] = self.ticket_permissions[perm_set]
            # Check if the target is the staff role
            elif isinstance(target, discord.Role) and target.id == self.staff_role_id:
                # Update permissions for staff role using standardized set
                await channel.set_permissions(
                    target,
                    **self.ticket_permissions[perm_set]
                )
    
    async def invite_user_to_channel(
        self,
        channel: discord.TextChannel,
        user_id: int,
        is_staff: bool = False,
        is_closed: bool = False
    ) -> bool:
        """Invite a user to a ticket channel.
        
        Args:
            channel: The Discord text channel
            user_id: The user ID to invite
            is_staff: Whether the user is a staff member
            is_closed: Whether the ticket is closed
            
        Returns:
            True if the user was successfully invited, False otherwise
        """
        guild = channel.guild
        user = guild.get_member(user_id)
        
        if not user:
            logger.warning(f"User {user_id} not found in guild")
            return False
        
        try:
            # Select the appropriate permission set based on user type and ticket status
            if is_staff:
                perm_set = "closed_staff" if is_closed else "staff"
            else:
                perm_set = "closed_user" if is_closed else "user"
            
            # Set permissions using standardized set
            await channel.set_permissions(
                user,
                **self.ticket_permissions[perm_set]
            )
            # Update cache
            self.permission_cache[f"{channel.id}_{user_id}"] = self.ticket_permissions[perm_set]
            
            # Send a direct message to the user with the channel link
            try:
                if is_staff:
                    await user.send(
                        f"You have been invited to a support ticket in {channel.mention}. "
                        f"Click the link to access the ticket."
                    )
                else:
                    await user.send(
                        f"You have been added to a support ticket in {channel.mention}. "
                        f"Click the link to access your ticket."
                    )
                logger.info(f"Sent ticket channel invitation to user {user_id}")
            except (discord.Forbidden, discord.HTTPException) as e:
                logger.warning(f"Could not send DM to user {user_id}: {e}")
            
            # Send a message in the channel
            await channel.send(f"{user.mention} has been added to this ticket.")
            
            logger.info(f"Invited user {user_id} to channel {channel.name}")
            return True
        except discord.Forbidden:
            logger.error(f"Missing permissions to invite user {user_id} to channel {channel.name}")
            return False
        except Exception as e:
            logger.error(f"Error inviting user {user_id} to channel: {e}")
            return False
    
    async def remove_user_from_channel(
        self,
        channel: discord.TextChannel,
        user_id: int
    ) -> bool:
        """Remove a user from a ticket channel.
        
        Args:
            channel: The Discord text channel
            user_id: The user ID to remove
            
        Returns:
            True if the user was successfully removed, False otherwise
        """
        guild = channel.guild
        user = guild.get_member(user_id)
        
        if not user:
            logger.warning(f"User {user_id} not found in guild")
            return False
        
        try:
            # Remove permissions
            await channel.set_permissions(user, overwrite=None)
            
            # Remove from cache
            cache_key = f"{channel.id}_{user_id}"
            if cache_key in self.permission_cache:
                del self.permission_cache[cache_key]
            
            # Send a message in the channel
            await channel.send(f"{user.mention} has been removed from this ticket.")
            
            logger.info(f"Removed user {user_id} from channel {channel.name}")
            return True
        except discord.Forbidden:
            logger.error(f"Missing permissions to remove user {user_id} from channel {channel.name}")
            return False
        except Exception as e:
            logger.error(f"Error removing user {user_id} from channel: {e}")
            return False
    
    def get_channel_members(
        self,
        channel: discord.TextChannel
    ) -> Dict[str, List[int]]:
        """Get all members with access to a channel.
        
        Args:
            channel: The Discord text channel
            
        Returns:
            Dictionary with 'users' and 'staff' lists of user IDs
        """
        guild = channel.guild
        users = []
        staff = []
        
        # Get staff role
        staff_role = None
        if self.staff_role_id:
            staff_role = guild.get_role(self.staff_role_id)
        
        # Check all permission overwrites
        for target, overwrite in channel.overwrites.items():
            # Skip if the target doesn't have read permissions
            if not overwrite.read_messages:
                continue
            
            # Check if the target is a member
            if isinstance(target, discord.Member):
                # Check if the member has the staff role
                if staff_role and staff_role in target.roles:
                    staff.append(target.id)
                else:
                    users.append(target.id)
        
        return {
            "users": users,
            "staff": staff
        }
    
    async def sync_channel_permissions(
        self,
        channel: discord.TextChannel,
        ticket_data: Dict[str, Any]
    ) -> None:
        """Synchronize channel permissions with ticket data.
        
        This ensures that all users who should have access to the ticket
        have the correct permissions in the Discord channel.
        
        Args:
            channel: The Discord text channel
            ticket_data: Ticket data from the backend API
        """
        try:
            guild = channel.guild
            is_closed = ticket_data.get("status") == "closed"
            
            # Get current members with access
            current_members = self.get_channel_members(channel)
            
            # Get ticket creator
            creator_id = ticket_data.get("creator_discord_id")
            if creator_id:
                creator = guild.get_member(creator_id)
                if creator:
                    # Set creator permissions based on ticket status
                    perm_set = "closed_user" if is_closed else "user"
                    await channel.set_permissions(
                        creator,
                        **self.ticket_permissions[perm_set]
                    )
                    # Update cache
                    self.permission_cache[f"{channel.id}_{creator_id}"] = self.ticket_permissions[perm_set]
            
            # Get assigned staff
            assigned_staff_id = ticket_data.get("assigned_staff_id")
            if assigned_staff_id:
                staff_member = guild.get_member(assigned_staff_id)
                if staff_member:
                    # Set staff permissions based on ticket status
                    perm_set = "closed_staff" if is_closed else "staff"
                    await channel.set_permissions(
                        staff_member,
                        **self.ticket_permissions[perm_set]
                    )
                    # Update cache
                    self.permission_cache[f"{channel.id}_{assigned_staff_id}"] = self.ticket_permissions[perm_set]
            
            # Get staff role
            staff_role = None
            if self.staff_role_id:
                staff_role = guild.get_role(self.staff_role_id)
                if staff_role:
                    # Set staff role permissions based on ticket status
                    perm_set = "closed_staff" if is_closed else "staff"
                    await channel.set_permissions(
                        staff_role,
                        **self.ticket_permissions[perm_set]
                    )
            
            # Get admin role
            admin_role = None
            if self.admin_role_id:
                admin_role = guild.get_role(self.admin_role_id)
                if admin_role:
                    # Admins always have full permissions
                    await channel.set_permissions(
                        admin_role,
                        **self.ticket_permissions["admin"]
                    )
            
            logger.info(f"Synchronized permissions for channel {channel.name}")
        except discord.Forbidden:
            logger.error(f"Missing permissions to sync channel: {channel.name}")
        except Exception as e:
            logger.error(f"Error synchronizing channel permissions: {e}")
    
    async def bulk_update_permissions(
        self,
        channel: discord.TextChannel,
        is_closed: bool = False
    ) -> None:
        """Update permissions for all users in a channel at once.
        
        This is useful when a ticket is closed or reopened.
        
        Args:
            channel: The Discord text channel
            is_closed: Whether the ticket is closed
        """
        try:
            guild = channel.guild
            
            # Get current members with access
            current_members = self.get_channel_members(channel)
            
            # Update user permissions
            for user_id in current_members["users"]:
                user = guild.get_member(user_id)
                if user:
                    perm_set = "closed_user" if is_closed else "user"
                    await channel.set_permissions(
                        user,
                        **self.ticket_permissions[perm_set]
                    )
                    # Update cache
                    self.permission_cache[f"{channel.id}_{user_id}"] = self.ticket_permissions[perm_set]
            
            # Update staff permissions
            for staff_id in current_members["staff"]:
                staff = guild.get_member(staff_id)
                if staff:
                    perm_set = "closed_staff" if is_closed else "staff"
                    await channel.set_permissions(
                        staff,
                        **self.ticket_permissions[perm_set]
                    )
                    # Update cache
                    self.permission_cache[f"{channel.id}_{staff_id}"] = self.ticket_permissions[perm_set]
            
            # Update staff role
            staff_role = None
            if self.staff_role_id:
                staff_role = guild.get_role(self.staff_role_id)
                if staff_role:
                    perm_set = "closed_staff" if is_closed else "staff"
                    await channel.set_permissions(
                        staff_role,
                        **self.ticket_permissions[perm_set]
                    )
            
            logger.info(f"Bulk updated permissions for channel {channel.name}, closed: {is_closed}")
        except discord.Forbidden:
            logger.error(f"Missing permissions to bulk update channel: {channel.name}")
        except Exception as e:
            logger.error(f"Error bulk updating channel permissions: {e}")
    
    async def auto_invite_available_staff(
        self,
        channel: discord.TextChannel,
        exclude_ids: List[int] = None
    ) -> List[Tuple[int, bool]]:
        """Automatically invite available staff members to a ticket channel.
        
        Args:
            channel: The Discord text channel
            exclude_ids: List of user IDs to exclude from invitation
            
        Returns:
            List of tuples containing staff ID and whether they were successfully added
        """
        guild = channel.guild
        results = []
        exclude_ids = exclude_ids or []
        
        # Get staff role
        staff_role = None
        if self.staff_role_id:
            staff_role = guild.get_role(self.staff_role_id)
            if not staff_role:
                logger.warning(f"Staff role {self.staff_role_id} not found")
                return results
        else:
            logger.warning("Staff role ID not configured")
            return results
        
        # Get online staff members with the staff role
        online_staff = [
            member for member in guild.members
            if staff_role in member.roles
            and member.status != discord.Status.offline
            and member.id not in exclude_ids
        ]
        
        # Limit to a reasonable number of staff to invite
        max_staff_to_invite = getattr(config, 'max_auto_invite_staff', 3)
        staff_to_invite = online_staff[:max_staff_to_invite]
        
        # Add staff members to the channel
        if staff_to_invite:
            staff_ids = [staff.id for staff in staff_to_invite]
            results = await self._add_staff_members_to_channel(channel, staff_ids)
            logger.info(f"Auto-invited {len(results)} staff members to channel {channel.name}")
        
        return results