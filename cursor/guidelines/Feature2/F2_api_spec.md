# API Specification: F-002 — RBAC & Permission Engine

## 1. Overview

The RBAC & Permission Engine (F-002) provides a centralized, deterministic authorization layer that enforces role-based access control consistently across all platform features. This feature establishes a permission evaluation engine that determines user access rights based on predefined roles, company scoping, and permission inheritance rules, enabling secure and auditable access control across the entire officeWorld SaaS platform.

### 1.1 Feature Capabilities
- **Centralized Permission Evaluation**: Deterministic permission engine that evaluates user access rights
- **Resource-Based Permissions**: Resource-action model (e.g., `tasks:create`, `salary:read`)
- **Company-Scoped Authorization**: All non-SuperAdmin permissions are company-scoped
- **Role Inheritance**: Design-time resolved inheritance (CEO → Manager → Employee, HR → Employee)
- **Permission Caching**: High-performance user-specific permission caching
- **Automatic Cache Invalidation**: Near-real-time invalidation on role, user, or company changes
- **UI Permission Visibility**: Permission data exposed to frontend for UI gating

### 1.2 Business Value
Provides a unified, consistent authorization foundation that prevents security risks and governance failures by eliminating duplicated, inconsistent access rules across the platform. Enables reliable permission enforcement for all business features while ensuring high performance through intelligent caching.

### 1.3 Technical Scope
- Permission evaluation engine with company scoping
- PermissionSet computation with role inheritance resolution
- Permission caching and automatic invalidation
- AuthContext retrieval for user metadata
- Integration with F-001 (User & Role Management) for cache invalidation triggers
- Integration with F-004 (Company Management) for company-scoped permission evaluation

**Note:** Permission enforcement on backend APIs and permission-based UI visibility are implementation concerns handled by other features. F-002 provides the permission data and evaluation engine.

---

## 2. Global API Rules

### 2.1 Authentication

**JWT Token Structure:**
All API endpoints require JWT Bearer token authentication.

**Required Claims in JWT Payload:**
- `sub` (string, UUID): User ID - **REQUIRED**
- `role` (string): User role - **REQUIRED**
  - Values: `"superadmin"`, `"ceo"`, `"hr"`, `"manager"`, `"employee"`
- `org_id` (string, UUID, nullable): Organization ID - **REQUIRED**
  - `null` for SuperAdmin (global access)
  - UUID for company-scoped users
- `exp` (integer): Token expiration (Unix timestamp) - **REQUIRED**
- `iat` (integer): Token issued at (Unix timestamp) - **RECOMMENDED**
- `jti` (string): JWT ID for token revocation - **RECOMMENDED**

**Token Expiration:**
- Access tokens: 15 minutes to 1 hour
- Token refresh: Supported via separate endpoint (implementation TBD)

**Multi-tenancy:**
- SuperAdmin (`org_id: null`): Global platform access, permissions evaluated without company scope
- Company users (`org_id: "<uuid>"`): Permissions evaluated within company scope

**Error Responses:**
- `401 UNAUTHENTICATED`: Missing/invalid/expired token
- `401 TOKEN_EXPIRED`: Token expired
- `401 INVALID_TOKEN`: Malformed token or missing required claims

### 2.2 General Rules
- **Versioning**: All endpoints use `/api/v1/` prefix
- **Content-Type**: `application/json` for all requests/responses
- **Character Encoding**: UTF-8
- **DateTime Format**: ISO 8601 UTC with Z suffix (e.g., `2024-01-20T10:30:00Z`)
- **Rate Limiting**: 100 requests per minute per user (configurable)
- **Request Size Limit**: 1MB maximum payload size
- **Response Headers**: All responses MUST include `X-Request-ID` header for debugging and support

---

## 3. Roles & Permissions

### 3.1 Role Definitions

#### SuperAdmin (Platform Level)
**Access Scope:** Global platform access, not tied to any company
**Permission Evaluation:**
- Permissions evaluated without company scope
- Global role with platform-wide access
- Governed by RBAC system for auditability

#### CEO (Company Level)
**Access Scope:** Full company administration within own organization
**Permission Inheritance:**
- Inherits all Manager permissions
- Inherits all Employee permissions
- Highest company-level role

#### HR (Company Level)
**Access Scope:** Employee management and HR operations within own company
**Permission Inheritance:**
- Inherits all Employee permissions
- Specialized employee-management authority

#### Manager (Company Level)
**Access Scope:** Project/task management within own company
**Permission Inheritance:**
- Inherits all Employee permissions
- Mid-level company role

#### Employee (Company Level)
**Access Scope:** Personal data and assigned tasks within own company
**Permission Inheritance:**
- Base company role (no inheritance)
- Lowest privilege level

### 3.2 Permission Inheritance Rules
- **CEO** → Inherits Manager + Employee permissions (resolved at seed time)
- **HR** → Inherits Employee permissions (resolved at seed time)
- **Manager** → Inherits Employee permissions (resolved at seed time)
- **Employee** → Base role (no inheritance)
- **SuperAdmin** → Global role (no inheritance, evaluated separately)
- **No runtime role traversal**: Inheritance is resolved at seed time, not at runtime
- **Additive only**: No permission denies or overrides

### 3.3 Permission Model

**Resource-Action Structure:**
Permissions follow a resource-based model with explicit actions:
- **Resource**: Domain object being protected (e.g., `tasks`, `salary`, `users`, `employees`)
- **Action**: Operation performed on a resource (e.g., `create`, `read`, `update`, `delete`, `approve`)
- **Permission Format**: `{resource}:{action}` (e.g., `tasks:create`, `salary:read`)

**Permission Storage:**
- Permissions are stored as JSON within the `roles` table
- Role inheritance is resolved at seed time (not runtime)
- No new persisted entities for permissions

**Company Scoping:**
- All non-SuperAdmin permissions are company-scoped
- Permission evaluation includes company_id match
- SuperAdmin permissions are evaluated without company scope

**Permission Evaluation:**
- Permissions are evaluated on every API request
- Backend authorization is the source of truth
- Frontend permission checks mirror backend rules exactly (advisory only)

### 3.4 F-002 Specific Permissions
All F-002 endpoints require authentication. Permissions are role-based:

| Endpoint | SuperAdmin | CEO | HR | Manager | Employee |
|----------|------------|-----|----|---------|----------|
| GET /api/v1/auth/me | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 4. Resources & Endpoints

### 4.1 Resource Overview

#### PermissionSet Resource
Represents the final evaluated permissions for a user, after role inheritance resolution, company scope resolution, and user activation checks.

**Key Fields:**
- `permissions` (object): Resource-action mapping
  - Keys: Resource names (string)
  - Values: Arrays of allowed actions (string[])
- Structure: `{"tasks": ["create", "read", "update", "delete"], "salary": ["read"]}`

**Evaluation Rules:**
- Role inheritance resolved at seed time (not runtime)
- Company scope applied for non-SuperAdmin users
- User activation status checked (deactivated users receive empty PermissionSet)
- Company activation status checked (inactive companies invalidate company-scoped permissions)

#### AuthContext Resource
Represents contextual information about the authenticated user used to qualify permission evaluation.

**Key Fields:**
- `user_id` (UUID): Current user identifier
- `role` (object): User role information
  - `code` (string): Role code (e.g., "ceo", "hr", "manager", "employee", "superadmin")
- `company` (object, nullable): Company information
  - `slug` (string, nullable): Company slug identifier (null for SuperAdmin)
- `is_super_admin` (boolean): Whether user is SuperAdmin
- `is_user_active` (boolean): Whether user account is active
- `is_company_active` (boolean): Whether user's company is active (null for SuperAdmin)

### 4.2 Endpoint Summary

| Method | Path | Purpose | Authentication |
|--------|------|---------|----------------|
| GET | /api/v1/auth/me | Retrieve current user's permissions and context | Required |

### 4.3 Endpoint Details

#### 4.3.1 GET /api/v1/auth/me

- **Purpose:**
  Retrieve the current authenticated user's combined PermissionSet and AuthContext in a single response. This endpoint provides all authorization data needed by the frontend for UI gating and permission checks.

- **Authentication:**
  Required (JWT Bearer token)

- **Authorization / Roles:**
  All authenticated users (SuperAdmin, CEO, HR, Manager, Employee)

- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <jwt_token>` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
    - `Content-Type: application/json`

- **Idempotency:**
  Idempotent (GET operation)

**Path Parameters**
None

**Query Parameters**
None

**Note:** Permission data is always resolved in the context of the authenticated user. No query parameters are needed.

**Request Body**
None (GET request)

**Success Response (200 OK)**

```json
{
  "data": {
    "permissions": {
      "tasks": ["create", "read", "update", "delete"],
      "salary": ["read"],
      "users": ["create", "read", "update"],
      "employees": ["create", "read", "update", "delete"],
      "leaves": ["create", "read", "approve"],
      "attendance": ["create", "read", "update"]
    },
    "context": {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "role": {
        "code": "ceo",
        "name": "CEO"
      },
      "company": {
        "slug": "acme-corp"
      },
      "is_super_admin": false,
      "is_user_active": true,
      "is_company_active": true
    }
  },
  "message": "User permissions and context retrieved successfully"
}
```

**Example Response for SuperAdmin (200 OK):**
```json
{
  "data": {
    "permissions": {
      "users": ["create", "read", "update", "delete"],
      "companies": ["create", "read", "update", "delete"]
    },
    "context": {
      "user_id": "660e8400-e29b-41d4-a716-446655440001",
      "role": {
        "code": "superadmin",
        "name": "SuperAdmin"
      },
      "company": null,
      "is_super_admin": true,
      "is_user_active": true,
      "is_company_active": null
    }
  },
  "message": "User permissions and context retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `Content-Type: application/json`

**Response Schema:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| data | object | Yes | Response data container | - |
| data.permissions | object | Yes | Resource-action permission mapping | Keys: resource names (string), Values: arrays of action strings (string[]) |
| data.permissions.{resource} | string[] | Yes | Allowed actions for resource | Array of action strings (e.g., "create", "read", "update", "delete", "approve") |
| data.context | object | Yes | User authentication context | - |
| data.context.user_id | string (UUID) | Yes | Current user identifier | RFC 4122 UUID v4 format |
| data.context.role | object | Yes | User role information | - |
| data.context.role.code | string | Yes | Role code identifier | Enum: "superadmin", "ceo", "hr", "manager", "employee" (case-sensitive) |
| data.context.role.name | string | Yes | Role display name | String (e.g., "SuperAdmin", "CEO", "HR", "Manager", "Employee") |
| data.context.company | object | No | Company information (null for SuperAdmin) | Object, nullable (null for SuperAdmin users) |
| data.context.company.slug | string | No | Company slug identifier | String, nullable (null for SuperAdmin), case-insensitive unique within companies table |
| data.context.is_super_admin | boolean | Yes | Whether user is SuperAdmin | Boolean (true/false) |
| data.context.is_user_active | boolean | Yes | Whether user account is active | Boolean (true/false) |
| data.context.is_company_active | boolean | Yes | Whether user's company is active | Boolean (true/false, nullable for SuperAdmin) |
| message | string | Yes | Success message | String |

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- For SuperAdmin users: `data.context.company` will be `null` (entire object is null, not just the slug), and `is_company_active` will be `null`.
- For company-scoped users: `data.context.company` is an object with `slug` field, and `is_company_active` is a boolean.
- `data.context.role.name` provides the display name for the role (e.g., "CEO", "HR", "Manager") for UI purposes.
- Deactivated users receive an empty `permissions` object: `{}`.
- Inactive companies result in empty `permissions` object for company-scoped users.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing, invalid, or expired JWT token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 401 | INVALID_TOKEN | Malformed token or missing required claims |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks required permissions (should not occur for this endpoint) |
| 500 | INTERNAL_ERROR | Server error during permission evaluation or cache retrieval |

**Example Error Response (401 UNAUTHENTICATED):**
```json
{
  "error": {
    "code": "UNAUTHENTICATED",
    "details": [{"field": "authorization", "issue": "Missing or invalid authentication token"}]
  },
  "message": "Authentication required. Please provide a valid JWT token."
}
```

**Example Error Response (401 TOKEN_EXPIRED):**
```json
{
  "error": {
    "code": "TOKEN_EXPIRED",
    "details": [{"field": "token", "issue": "JWT token has expired. Please refresh your token."}]
  },
  "message": "Your session has expired. Please log in again."
}
```

**Example Error Response (500 INTERNAL_ERROR):**
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "details": [{"field": "permissions", "issue": "An error occurred while evaluating permissions. Please try again."}]
  },
  "message": "An internal server error occurred. Please contact support if the issue persists."
}
```

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate error.

**Cache Behavior:**
- Permission data is cached per user for performance
- Cache is automatically invalidated on:
  - User role change (F-001)
  - User activation/deactivation (F-001)
  - User company reassignment (F-001)
  - Company deactivation (F-004)
- After cache invalidation, permissions are automatically recomputed on the next GET request
- No explicit refresh endpoint is needed - cache invalidation triggers automatic recomputation

**Edge Cases:**
- **SuperAdmin**: Permissions evaluated without company scope, `company` field is `null`
- **Deactivated User**: Returns empty `permissions` object `{}`, `is_user_active: false`
- **Inactive Company**: Returns empty `permissions` object `{}` for company-scoped users, `is_company_active: false`
- **Stale Cache**: Automatically recomputed on next GET request after invalidation
- **UI Rendering Before Load**: Frontend should default to deny (no permissions) until data is loaded

---

## 5. Webhooks / Async Behavior

**Cache Invalidation:**
Permission cache invalidation is triggered reactively by other features:
- **F-001 (User & Role Management)**: Triggers invalidation on role change, user activation/deactivation, company reassignment
- **F-004 (Company Management)**: Triggers invalidation on company deactivation

Invalidation is near-real-time and automatic. No webhooks or async operations are exposed via F-002 API endpoints.

---

## 6. Rate Limiting & Performance

### 6.1 Rate Limiting
- **Default Limit**: 100 requests per minute per user
- **Endpoint-Specific**: No special rate limits for F-002 endpoints
- **Rate Limit Headers**: Standard rate limit headers included in responses

### 6.2 Performance Considerations
- **Permission Caching**: User-specific permission cache (Redis or similar) for high performance
- **Cache TTL**: Cache persists until invalidation (no time-based expiration)
- **Cache Invalidation**: Near-real-time invalidation on permission-affecting changes
- **Computation**: PermissionSet computed on cache miss or after invalidation
- **Response Time**: Target < 50ms for cached responses, < 200ms for cache miss (including computation)

### 6.3 Optimization Strategies
- Permission inheritance resolved at seed time (not runtime)
- Company scope filtering applied efficiently
- User activation checks short-circuited early
- Permission cache keyed by user_id for fast lookup

---

## 7. Open Questions

None identified at this stage.

---

## 8. Assumptions

### 8.1 Technical Assumptions
- Permission cache is user-specific (keyed by user_id)
- Cache invalidation is near-real-time (within seconds of triggering event)
- Permission checks occur on every API request (enforced by other features)
- Frontend permission checks mirror backend rules exactly (advisory only, backend is source of truth)

### 8.2 Business Assumptions
- Permissions are predefined and fixed in V1 (no dynamic permission creation)
- All non-SuperAdmin permissions are company-scoped
- Role inheritance is additive only (no denies or overrides)
- Permission data must be available at initial app load and immediately after login
- UI must default to deny (no permissions) until permission data is loaded

### 8.3 Integration Assumptions
- F-001 (User & Role Management) triggers cache invalidation on relevant changes
- F-004 (Company Management) triggers cache invalidation on company deactivation
- Other features (F-005, F-006, F-007, F-008) consume permission data for authorization enforcement
- Frontend consumes permission data for UI visibility gating

---

## 9. Documentation Classes (Rule 10 Compliance)

**PermissionApiDocs Class Structure:**
```python
class PermissionApiDocs:
    """API documentation for RBAC & Permission Engine endpoints"""

    get_me: ClassVar[dict] = {
        "summary": "Retrieve current user's permissions and context",
        "description": "Returns the authenticated user's combined PermissionSet (resource-action mappings) and AuthContext (user metadata, role, company, status flags) in a single response. This endpoint provides all authorization data needed by the frontend for UI gating and permission checks. Permission data is cached per user and automatically recomputed after cache invalidation triggered by role changes, user activation/deactivation, or company reassignment."
    }
```

**Router Endpoint Pattern:**
```python
@router.get(
    "/me",
    response_model=StandardResponse[UserPermissionsResponse],
    summary=PermissionApiDocs.get_me["summary"],
    description=PermissionApiDocs.get_me["description"]
)
async def get_user_permissions(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Retrieve current user's permissions and context."""
    # Implementation
```

---

## 10. Query Schema Classes (Rule 9 Compliance)

**Note:** The `GET /api/v1/auth/me` endpoint does not require query parameters, as permission data is always resolved in the context of the authenticated user. No query schema class is needed for this endpoint.

If future endpoints require query parameters, they MUST follow Rule 9:
- Create a Pydantic BaseModel schema class in `schemas.py`
- Use `Depends(QuerySchema)` in router endpoint
- Do NOT use individual `Query()` parameters in router function signature

---

## 11. Integration Points

### 11.1 F-001 (User & Role Management) Integration
- **Cache Invalidation Triggers:**
  - User role change → Invalidate user's permission cache
  - User activation → Invalidate user's permission cache
  - User deactivation → Invalidate user's permission cache
  - User company reassignment → Invalidate user's permission cache

### 11.2 F-004 (Company Management) Integration
- **Cache Invalidation Triggers:**
  - Company deactivation → Invalidate all company-scoped users' permission caches

### 11.3 Other Features (F-005, F-006, F-007, F-008) Integration
- **Permission Consumption:**
  - Features consume permission data for backend authorization enforcement
  - Features may call `GET /api/v1/auth/me` or use internal permission evaluation service
  - Backend authorization is the source of truth for access control

### 11.4 Frontend Integration
- **Permission Consumption:**
  - Frontend calls `GET /api/v1/auth/me` at initial app load
  - Frontend calls `GET /api/v1/auth/me` immediately after login
  - Frontend calls `GET /api/v1/auth/me` after any permission-affecting change
  - Frontend uses permission data for UI visibility gating (advisory only)
  - Frontend derives `can_<action>_<resource>` boolean flags from PermissionSet

---

## 12. Security Considerations

### 12.1 Authorization
- All endpoints require JWT Bearer token authentication
- Permission evaluation is server-authoritative (backend is source of truth)
- Frontend permission checks are advisory only
- Company scoping enforced for all non-SuperAdmin users

### 12.2 Data Isolation
- SuperAdmin permissions evaluated without company scope
- Company-scoped users only see permissions for their company
- Permission cache is user-specific (no cross-user data leakage)

### 12.3 Cache Security
- Permission cache keyed by user_id (prevents unauthorized access)
- Cache invalidation ensures stale permissions are not served
- Deactivated users receive empty PermissionSet (no access)

### 12.4 Auditability
- All permission evaluations are logged for audit purposes
- SuperAdmin actions are governed through RBAC system for auditability
- Permission changes are tracked through cache invalidation events

---

## 13. Error Handling

### 13.1 Standard Error Responses
All error responses follow the standard format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "details": [{"field": "field_name", "issue": "Error description"}]
  },
  "message": "Human-friendly error message"
}
```

### 13.2 Error Codes
- `UNAUTHENTICATED`: Missing, invalid, or expired authentication token
- `TOKEN_EXPIRED`: JWT token has expired
- `INVALID_TOKEN`: Malformed token or missing required claims
- `INSUFFICIENT_PERMISSIONS`: User lacks required permissions (should not occur for GET /me)
- `INTERNAL_ERROR`: Server error during permission evaluation or cache retrieval

### 13.3 Error Response Headers
All error responses MUST include:
- `X-Request-ID`: Unique request identifier for debugging
- `Content-Type: application/json`

---

## 14. Versioning & Compatibility

### 14.1 API Versioning
- Current version: `/api/v1/`
- Future versions: `/api/v2/`, etc.
- Version changes require backward compatibility considerations

### 14.2 Response Compatibility
- New permission resources may be added without breaking changes
- New context fields may be added without breaking changes
- Existing fields will not be removed without version bump

---

## 15. Testing Considerations

### 15.1 Test Scenarios
- SuperAdmin permission evaluation (no company scope)
- Company-scoped user permission evaluation
- Role inheritance verification (CEO, HR, Manager inheritance)
- Deactivated user (empty PermissionSet)
- Inactive company (empty PermissionSet for company users)
- Cache invalidation and recomputation
- Token expiration handling
- Invalid token handling

### 15.2 Performance Testing
- Cache hit response time (< 50ms)
- Cache miss response time (< 200ms)
- Concurrent request handling
- Cache invalidation performance

---

## 16. Future Enhancements (Out of Scope for V1)

The following are explicitly out of scope for F-002 V1:
- Dynamic permission creation or customization
- Conditional or context-based permissions
- Attribute-based access control (ABAC)
- Partial permission overrides or denies
- Feature-level permission configuration via UI
- Explicit permission refresh endpoint (automatic on next GET)
- Permission history or audit trail API endpoints
- Permission comparison or diff endpoints

---

**End of API Specification: F-002 — RBAC & Permission Engine**

