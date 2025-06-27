# Role-Based Permissions System

This document describes the role-based permissions system implemented for the Discord Ticket Bot.

## Overview

The permissions system provides fine-grained access control with three main components:
- **Roles**: Hierarchical user roles (USER, STAFF, ADMIN)
- **Permissions**: Specific actions that can be granted or denied
- **Caching**: Redis-based caching for performance optimization

## Roles

### Role Hierarchy

The system implements a hierarchical role system where higher roles inherit permissions from lower roles:

```
ADMIN (Level 3)
  ├── All permissions
  └── Can manage all tickets and settings

STAFF (Level 2)
  ├── User permissions
  ├── Can manage tickets
  └── Cannot access admin settings

USER (Level 1)
  └── Can create tickets only
```

### Role Constants

```python
from app.permissions import Role

Role.USER    # "USER"
Role.STAFF   # "STAFF" 
Role.ADMIN   # "ADMIN"
```

## Permissions

### Available Permissions

- `CREATE_TICKET`: Create new support tickets
- `MANAGE_TICKETS`: Manage and assign tickets
- `VIEW_ANALYTICS`: Access analytics and reports
- `ADMIN_SETTINGS`: Access administrative settings

### Permission Constants

```python
from app.permissions import Permission

Permission.CREATE_TICKET
Permission.MANAGE_TICKETS
Permission.VIEW_ANALYTICS
Permission.ADMIN_SETTINGS
```

## Usage

### Basic Permission Checking

```python
from app.permissions import has_permission, Permission

# Check if a user role has a specific permission
if has_permission("STAFF", Permission.MANAGE_TICKETS):
    # User can manage tickets
    pass
```

### Role Hierarchy Checking

```python
from app.permissions import check_role_hierarchy

# Check if user meets minimum role requirement
if check_role_hierarchy("STAFF", "USER"):
    # STAFF role meets USER requirement
    pass
```

### Multiple Permission Checking

```python
from app.permissions import has_multiple_permissions

required_perms = [Permission.CREATE_TICKET, Permission.MANAGE_TICKETS]
if has_multiple_permissions("STAFF", required_perms):
    # User has all required permissions
    pass
```

## Guild-Specific Roles

The system supports guild-specific role assignments, allowing users to have different roles in different Discord servers.

### Role Assignment

```python
from app.models.role_assignment import assign_role_in_guild
import uuid

# Assign STAFF role to user in specific guild
assign_role_in_guild(
    db=db_session,
    user_id=uuid.UUID("user-uuid"),
    guild_id=123456789012345678,
    role="STAFF",
    assigned_by=uuid.UUID("admin-uuid")
)
```

### Getting User Role in Guild

```python
from app.models.role_assignment import get_user_role_in_guild

user_role = get_user_role_in_guild(db_session, user_id, guild_id)
# Returns: "STAFF", "ADMIN", or "USER"
```

## FastAPI Integration

### Permission Decorators

The system provides FastAPI dependencies for protecting endpoints:

```python
from fastapi import Depends
from app.decorators import require_permissions, require_role, require_staff

@app.get("/tickets")
async def list_tickets(user=Depends(require_authenticated())):
    # Requires valid authentication
    pass

@app.post("/tickets")
async def create_ticket(user=Depends(require_permissions(Permission.CREATE_TICKET))):
    # Requires CREATE_TICKET permission
    pass

@app.delete("/tickets/{ticket_id}")
async def delete_ticket(user=Depends(require_staff())):
    # Requires STAFF role or higher
    pass

@app.get("/admin/settings")
async def admin_settings(user=Depends(require_admin())):
    # Requires ADMIN role
    pass
```

### Custom Permission Combinations

```python
from app.decorators import PermissionDependency

# Custom dependency for ticket management
ticket_manager = PermissionDependency(
    required_permissions=[Permission.MANAGE_TICKETS],
    required_role=Role.STAFF
)

@app.patch("/tickets/{ticket_id}")
async def update_ticket(user=Depends(ticket_manager)):
    # Requires both STAFF role AND MANAGE_TICKETS permission
    pass
```

## Caching

### Redis Configuration

The system uses Redis for caching user permissions with a 1-hour TTL:

```python
from app.cache import init_redis

# Initialize Redis connection
init_redis("redis://localhost:6379/0")
```

### Cached Permission Retrieval

```python
from app.cache import get_user_permissions_cached

# Get permissions with automatic caching
permissions = get_user_permissions_cached(
    db_session=db,
    user_id="user-uuid",
    guild_id=123456789012345678  # Optional
)
```

### Cache Invalidation

```python
from app.cache import invalidate_user_permissions

# Invalidate cache when user role changes
invalidate_user_permissions("user-uuid", guild_id=123456789012345678)

# Invalidate all guild caches for user
invalidate_user_permissions("user-uuid")
```

## Database Models

### User Model

The `User` model includes a global role field:

```python
from app.models.user import User

user = User(
    discord_id=123456789,
    email="user@example.com",
    role="USER"  # Global role
)
```

### Role Assignment Model

The `RoleAssignment` model manages guild-specific roles:

```python
from app.models.role_assignment import RoleAssignment

assignment = RoleAssignment(
    user_id=user.id,
    guild_id=123456789012345678,
    role="STAFF",
    assigned_by=admin_user.id
)
```

## Security Considerations

1. **Token Validation**: All endpoints validate JWT tokens before checking permissions
2. **Hierarchy Enforcement**: Higher roles automatically inherit lower role permissions
3. **Guild Isolation**: Role assignments are isolated per Discord guild
4. **Audit Trail**: Role assignments track who made the assignment and when
5. **Cache Security**: Cached permissions expire after 1 hour to prevent stale data

## Error Handling

The system provides appropriate HTTP status codes:

- `401 Unauthorized`: Invalid or missing JWT token
- `403 Forbidden`: Valid token but insufficient permissions
- `404 Not Found`: User not found in database

## Adding New Permissions

To add a new permission:

1. Add to the `Permission` enum in `app/permissions.py`
2. Update the `ROLE_PERMISSIONS` mapping
3. Create appropriate decorator functions if needed
4. Update tests and documentation

Example:

```python
# 1. Add to enum
class Permission(str, Enum):
    # ... existing permissions ...
    EXPORT_DATA = "EXPORT_DATA"

# 2. Update role permissions
ROLE_PERMISSIONS = {
    Role.USER: {Permission.CREATE_TICKET},
    Role.STAFF: {Permission.CREATE_TICKET, Permission.MANAGE_TICKETS},
    Role.ADMIN: {
        Permission.CREATE_TICKET,
        Permission.MANAGE_TICKETS,
        Permission.VIEW_ANALYTICS,
        Permission.ADMIN_SETTINGS,
        Permission.EXPORT_DATA  # New permission for admins only
    }
}

# 3. Create decorator
def require_data_export():
    return require_permissions(Permission.EXPORT_DATA)
```

## Testing

The permissions system includes comprehensive unit tests covering:

- Role hierarchy validation
- Permission checking logic
- Guild-specific role assignments
- Redis caching functionality
- FastAPI decorator behavior

Run tests with:

```bash
python -m pytest tests/test_permissions.py -v
```
