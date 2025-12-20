# RBAC (Role-Based Access Control) + OBAC (Object-Based Access Control) Implementation Guide

## Overview

This document defines the implementation strategy for **two-layer access control**:

1. **Resource-Based Access Control (RBAC)**: Determines if a user can access a resource type (e.g., "Can this user access the Content module?")
2. **Object-Level Permission (OBAC)**: Determines if a user can perform actions on specific object instances (e.g., "Can this user edit Content #10?")

Both layers are cached in Redis with PostgreSQL fallback for optimal performance.

---

## Architecture

### Two-Layer Permission Check

```
API Request
    │
    ▼
Layer 1: RBAC Check (Resource-Level)
    ├── Check if user has permission for resource + action
    ├── Get permission_summary from Redis → PostgreSQL fallback
    └── If false → Deny immediately
    │
    ▼
Layer 2: OBAC Check (Object-Level) [Only if object_id provided]
    ├── Check if user can perform action on specific object
    ├── Check Redis cache for computed permission result
    ├── If cache miss → Compute from permission_summary + object ownership
    ├── Cache result in Redis
    └── Return allow/deny
```

---

## Project Configuration Questions

**⚠️ IMPORTANT: Answer these questions before implementing OBAC in your project.**

### 1. Resources and Object-Level Permissions

**Question:** Which resources in your system require object-level permission checks?

**Instructions:** List all resources that need object-level access control. For each resource, specify if it requires object-level checks.

**Example:**
```
Resources requiring object-level permissions:
- ✅ Content (requires object-level checks)
- ✅ Users (requires object-level checks)
- ❌ Organizations (only SuperAdmin, no object-level needed)
- ✅ Audit Logs (requires object-level checks - org scoping)
- ❌ Roles (only SuperAdmin, no object-level needed)
```

**Your Answer:**
```
[ ] Content
[ ] Users
[ ] Organizations
[ ] Roles
[ ] Permissions
[ ] Audit Logs
[ ] [Add other resources]
```

---

### 2. Object-Level Access Rules

**Question:** For each resource that requires object-level permissions, define the access rules for each role.

**Instructions:** For each resource, specify what object-level rules apply to each role. Common patterns:
- `all_global` - Access all objects (SuperAdmin)
- `all_in_org` - Access all objects in user's organization (Admin)
- `assigned_or_own` - Access objects assigned to user or created by user (Creator)
- `own_only` - Access only objects created by user
- `assigned_only` - Access only objects assigned to user
- `custom` - Define custom rule

**Example Template:**
```
Resource: Content
- SuperAdmin: all_global
- Admin: all_in_org
- Creator: assigned_or_own

Resource: Users
- SuperAdmin: all_global
- Admin: all_in_org
- Creator: [no access]

Resource: [Your Resource]
- SuperAdmin: [rule]
- Admin: [rule]
- Creator: [rule]
```

**Your Answer:**
```
Resource: Content
- SuperAdmin: 
- Admin: 
- Creator: 

Resource: Users
- SuperAdmin: 
- Admin: 
- Creator: 

[Add more resources as needed]
```

---

### 3. Object-Level Permission Storage

**Question:** Where should object-level access rules be stored?

**Options:**
- **Option A:** In `permission_summary` JSON (e.g., `"access_rule": "assigned_or_own"`)
  - Pros: Centralized, easy to modify per-user
  - Cons: Requires parsing JSON for each check
  
- **Option B:** In a separate `ObjectPermissions` table
  - Pros: Explicit, queryable, can have complex rules
  - Cons: Additional table to maintain
  
- **Option C:** Computed dynamically from ownership/assignment tables
  - Pros: Always accurate, no duplication
  - Cons: Requires database queries for each check (unless cached)

**Your Choice:** [ ] Option A  [ ] Option B  [ ] Option C  [ ] Hybrid (specify)

**If Option A:** Specify the JSON structure in `permission_summary`:
```json
{
  "permissions": {
    "content": {
      "edit": {
        "allowed_statuses": ["draft", "reject"],
        "access_rule": "assigned_or_own"  // ← Object-level rule
      }
    }
  }
}
```

**If Option B:** Define the `ObjectPermissions` table structure:
```
[Define table schema here]
```

**If Option C:** Specify which tables determine ownership/assignment:
```
[Specify tables and relationships]
```

---

## Permission Check Structure

### Function Signature

```python
def check_permission(
    user_id: int,
    organization_id: int | None,
    resource: str,           # "content", "user", "org", etc.
    action: str,             # "view", "edit", "delete", "create", etc.
    object_id: int | None = None  # Optional: for object-level checks
) -> bool:
    """
    Check if user has permission to perform action on resource.
    
    Args:
        user_id: User ID from JWT token
        organization_id: Organization ID from JWT token (None for SuperAdmin)
        resource: Resource type (e.g., "content", "user")
        action: Action to perform (e.g., "view", "edit", "delete")
        object_id: Optional object ID for object-level checks
    
    Returns:
        True if permission granted, False otherwise
    """
    pass
```

### Usage Examples

```python
# Resource-level check (RBAC only)
has_permission = check_permission(
    user_id=3,
    organization_id=1,
    resource="content",
    action="create"
)

# Object-level check (RBAC + OBAC)
can_edit = check_permission(
    user_id=3,
    organization_id=1,
    resource="content",
    action="edit",
    object_id=10  # Content ID
)
```

---

## Cache Strategy

### Cache Key Structure

#### 1. Resource-Level Permissions (RBAC)
**Key Pattern:** `permission:{user_id}:{organization_id}`

**Value:** Complete `permission_summary` JSON from `OrganizationMembers` table.

**Examples:**
- `permission:1:null` - SuperAdmin permissions
- `permission:2:1` - Admin permissions (org_id=1)
- `permission:3:1` - Creator permissions (org_id=1)

**Source:** `REDIS_PERMISSION_CACHING.md`

---

#### 2. Object-Level Permission Checks (OBAC)
**Key Pattern:** `obj_permission_check:{user_id}:{org_id}:{resource}:{action}:{object_id}`

**Value:** Boolean result (`"true"` or `"false"`) of the permission check.

**Examples:**
- `obj_permission_check:3:1:content:edit:10` - Can Creator (user_id=3) edit Content #10?
- `obj_permission_check:2:1:user:view:5` - Can Admin (user_id=2) view User #5?
- `obj_permission_check:1:null:content:delete:20` - Can SuperAdmin delete Content #20?

**TTL:** Infinite (no expiration) - Cache stays until invalidated.

---

### Cache Flow

```
Permission Check Request
    │
    ├── Has object_id?
    │   │
    │   ├── YES → Object-Level Check (OBAC)
    │   │   │
    │   │   ├── Check Redis: obj_permission_check:{user_id}:{org_id}:{resource}:{action}:{object_id}
    │   │   │   │
    │   │   │   ├── Cache Hit → Return cached boolean
    │   │   │   │
    │   │   │   └── Cache Miss → 
    │   │   │       ├── Get permission_summary from Redis/PostgreSQL
    │   │   │       ├── Get object ownership/assignment from PostgreSQL
    │   │   │       ├── Compute permission result (boolean)
    │   │   │       ├── Cache result in Redis
    │   │   │       └── Return result
    │   │   │
    │   │   └── Return boolean result
    │   │
    │   └── NO → Resource-Level Check (RBAC only)
    │       │
    │       ├── Get permission_summary from Redis
    │       │   │
    │       │   ├── Cache Hit → Parse JSON, check resource+action
    │       │   │
    │       │   └── Cache Miss → 
    │       │       ├── Query OrganizationMembers table
    │       │       ├── Get permission_summary JSON
    │       │       ├── Cache in Redis
    │       │       └── Parse JSON, check resource+action
    │       │
    │       └── Return boolean result
```

---

## Fallback Logic

### Object-Level Permission Check (OBAC)

**Strategy:** Compute-on-demand with caching

1. **Check Redis cache** for computed result:
   ```
   obj_permission_check:{user_id}:{org_id}:{resource}:{action}:{object_id}
   ```

2. **If cache hit:** Return cached boolean result immediately.

3. **If cache miss:**
   - Get `permission_summary` from Redis (or PostgreSQL fallback)
   - Query object ownership/assignment from PostgreSQL
   - Compute permission result based on:
     - Resource-level permission from `permission_summary`
     - Object-level rule (e.g., `assigned_or_own`, `all_in_org`)
     - Object ownership/assignment data
   - Cache computed result in Redis (boolean)
   - Return result

**Why this approach?**
- ✅ Caches computed boolean result (fast lookups)
- ✅ Avoids repeated database queries for same check
- ✅ Automatically invalidates when ownership changes
- ✅ Always uses latest permission_summary from cache

---

## Cache Invalidation Rules

### When to Invalidate Object-Level Permission Cache

Invalidate object-level permission cache in the following scenarios:

#### 1. User Permissions Change
**Trigger:** When `permission_summary` is updated in `OrganizationMembers` table.

**Action:** 
- Invalidate all object-level caches for that user:
  ```
  Pattern: obj_permission_check:{user_id}:{org_id}:*:*
  Action: Delete all matching keys
  ```

**Implementation:**
```python
def invalidate_user_object_permissions(user_id, organization_id):
    org_key = str(organization_id) if organization_id else "null"
    pattern = f"obj_permission_check:{user_id}:{org_key}:*"
    # Delete all keys matching pattern
    redis_client.delete_pattern(pattern)
```

---

#### 2. Object Ownership/Assignment Changes
**Trigger:** When object ownership or assignment is modified.

**Examples:**
- Content assignment changed (ContentAssignments table updated)
- User created_by changed
- Object moved to different organization

**Action:**
- Invalidate cache for that specific object:
  ```
  Pattern: obj_permission_check:*:*:{resource}:*:{object_id}
  Action: Delete all keys matching pattern
  ```

**Implementation:**
```python
def invalidate_object_permissions(resource, object_id):
    pattern = f"obj_permission_check:*:*:{resource}:*:{object_id}"
    # Delete all keys matching pattern
    redis_client.delete_pattern(pattern)
```

---

#### 3. Object Deleted/Soft-Deleted
**Trigger:** When object is deleted or soft-deleted (`is_del = true`).

**Action:**
- Invalidate cache for that object (same as #2)

---

#### 4. Organization Membership Changes
**Trigger:** When user's organization membership changes (role change, org change, membership deleted).

**Action:**
- Invalidate all object-level caches for that user (same as #1)

---

#### 5. Object Status Changes (If Relevant)
**Trigger:** When object status changes and status affects permissions.

**Example:** Content status changes from "draft" to "submit" - Creator can no longer edit.

**Action:**
- Invalidate cache for that object (same as #2)

**Note:** Only invalidate if status change affects permission rules. If status is checked dynamically during permission computation, this may not be needed.

---

#### 6. User Becomes Inactive
**Trigger:** When user status changes to "inactive".

**Action:**
- Invalidate all caches for that user (resource-level + object-level)

**Implementation:**
```python
def invalidate_user_all_permissions(user_id, organization_id):
    # Invalidate resource-level cache
    org_key = str(organization_id) if organization_id else "null"
    redis_client.delete(f"permission:{user_id}:{org_key}")
    
    # Invalidate all object-level caches
    invalidate_user_object_permissions(user_id, organization_id)
```

---

#### 7. Organization Status Changes
**Trigger:** When organization status changes to "inactive" or is deleted.

**Action:**
- Invalidate all object-level caches for all users in that organization

**Implementation:**
```python
def invalidate_organization_object_permissions(organization_id):
    pattern = f"obj_permission_check:*:{organization_id}:*"
    # Delete all keys matching pattern
    redis_client.delete_pattern(pattern)
```

---

## Implementation Examples

### Example 1: Resource-Level Check (RBAC)

```python
def check_permission(user_id, organization_id, resource, action, object_id=None):
    # Step 1: Get permission_summary from cache
    org_key = str(organization_id) if organization_id else "null"
    cache_key = f"permission:{user_id}:{org_key}"
    
    cached_permissions = redis_client.get(cache_key)
    
    if cached_permissions:
        permission_summary = json.loads(cached_permissions)
    else:
        # Fallback to PostgreSQL
        member = db.query(OrganizationMembers).filter(
            OrganizationMembers.user_id == user_id,
            OrganizationMembers.organization_id == organization_id if organization_id else None
        ).first()
        
        if not member:
            return False
        
        permission_summary = member.permission_summary
        
        # Cache for future use
        redis_client.set(cache_key, json.dumps(permission_summary))
    
    # Step 2: Check resource-level permission
    resource_perms = permission_summary.get("permissions", {}).get(resource, {})
    action_permission = resource_perms.get(action, False)
    
    if action_permission is False:
        return False
    
    # Step 3: If no object_id, return resource-level result
    if object_id is None:
        return True if action_permission is True else False
    
    # Step 4: Object-level check (see Example 2)
    return check_object_permission(
        user_id, organization_id, resource, action, object_id, 
        permission_summary, action_permission
    )
```

---

### Example 2: Object-Level Check (OBAC)

```python
def check_object_permission(
    user_id, organization_id, resource, action, object_id,
    permission_summary, action_permission
):
    # Step 1: Check Redis cache for computed result
    org_key = str(organization_id) if organization_id else "null"
    obj_cache_key = f"obj_permission_check:{user_id}:{org_key}:{resource}:{action}:{object_id}"
    
    cached_result = redis_client.get(obj_cache_key)
    if cached_result:
        return cached_result == "true"
    
    # Step 2: Get object-level rule from permission_summary
    # Example: "assigned_or_own", "all_in_org", "all_global"
    access_rule = None
    if isinstance(action_permission, dict):
        access_rule = action_permission.get("access_rule")
    
    # Step 3: Get object ownership/assignment from database
    if resource == "content":
        content = db.query(Content).filter(Content.id == object_id).first()
        if not content:
            return False
        
        # Check organization scope
        if organization_id and content.org_id != organization_id:
            return False
        
        # Check access rule
        if access_rule == "assigned_or_own":
            is_owner = content.created_by == user_id
            is_assigned = db.query(ContentAssignments).filter(
                ContentAssignments.content_id == object_id,
                ContentAssignments.assigned_to == user_id,
                ContentAssignments.is_del == False
            ).first() is not None
            
            result = is_owner or is_assigned
        
        elif access_rule == "all_in_org":
            result = content.org_id == organization_id
        
        elif access_rule == "all_global":
            result = True  # SuperAdmin
        
        else:
            result = False
    
    elif resource == "user":
        # Similar logic for user resource
        target_user = db.query(Users).filter(Users.id == object_id).first()
        if not target_user:
            return False
        
        # Get target user's organization
        target_member = db.query(OrganizationMembers).filter(
            OrganizationMembers.user_id == object_id
        ).first()
        
        if access_rule == "all_in_org":
            result = target_member.organization_id == organization_id
        
        elif access_rule == "all_global":
            result = True  # SuperAdmin
        
        else:
            result = False
    
    # Step 4: Cache result
    redis_client.set(obj_cache_key, "true" if result else "false")
    
    return result
```

---

### Example 3: Cache Invalidation on Permission Update

```python
def update_user_permissions(user_id, organization_id, new_permissions):
    # Update database
    member = db.query(OrganizationMembers).filter(
        OrganizationMembers.user_id == user_id,
        OrganizationMembers.organization_id == organization_id
    ).first()
    
    member.permission_summary = new_permissions
    member.updated_at = datetime.utcnow()
    member.updated_by = current_user_id
    db.commit()
    
    # Update resource-level cache
    org_key = str(organization_id) if organization_id else "null"
    cache_key = f"permission:{user_id}:{org_key}"
    redis_client.set(cache_key, json.dumps(new_permissions))
    
    # Invalidate all object-level caches for this user
    invalidate_user_object_permissions(user_id, organization_id)
    
    return new_permissions
```

---

### Example 4: Cache Invalidation on Content Assignment Change

```python
def assign_content(content_id, assigned_to_user_ids, assigned_by_user_id):
    # Update ContentAssignments table
    # ... (delete old, insert new assignments)
    db.commit()
    
    # Invalidate object-level cache for this content
    invalidate_object_permissions("content", content_id)
    
    # Optionally: Invalidate for all users who had access
    # (if you want to be more granular)
```

---

## Summary

### Key Points

1. **Two-Layer System:**
   - **RBAC:** Resource-level permissions (cached in `permission:{user_id}:{org_id}`)
   - **OBAC:** Object-level permissions (cached in `obj_permission_check:{user_id}:{org_id}:{resource}:{action}:{object_id}`)

2. **Cache Strategy:**
   - Resource-level: Stores full `permission_summary` JSON
   - Object-level: Stores computed boolean result
   - Both have infinite TTL (invalidated manually)

3. **Fallback Logic:**
   - Redis first → PostgreSQL fallback → Cache result

4. **Invalidation Triggers:**
   - User permissions change
   - Object ownership/assignment changes
   - Object deleted/soft-deleted
   - Organization membership changes
   - Object status changes (if relevant)
   - User becomes inactive
   - Organization status changes

5. **Permission Check Flow:**
   - Check resource-level permission first (RBAC)
   - If object_id provided, check object-level permission (OBAC)
   - Cache results for future requests

---

## Next Steps

1. **Answer Configuration Questions:**
   - Complete sections 1, 2, and 3 (Resources, Access Rules, Storage)

2. **Implement Permission Check Function:**
   - Use `check_permission()` function signature
   - Implement resource-level checks
   - Implement object-level checks based on your access rules

3. **Implement Cache Invalidation:**
   - Add invalidation calls in relevant API endpoints
   - Test cache invalidation on permission/ownership changes

4. **Add Examples:**
   - Document 2-3 concrete examples for your project
   - Test permission checks with real scenarios

---

## Related Documents

- `REDIS_PERMISSION_CACHING.md` - Resource-level permission caching strategy
- `TABLES_AND_PERMISSIONS.md` - Database schema and permission structures

