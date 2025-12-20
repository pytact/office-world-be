# API Specification: F-001A — User & Role Management (Core Operations)

## 1. Overview

The User & Role Management feature (F-001) enables invitation-based onboarding and lifecycle management of users within strict company and role boundaries. This specification (F-001A) covers core user management operations: listing users, viewing user details, inviting users, updating user information, and accessing reference data (roles and companies).

**Note:** Advanced lifecycle operations (role changes, company reassignment, activation/deactivation, re-invitation) are documented in F-001B.

### 1.1 Feature Capabilities (F-001A)
- **Platform-wide User Listing**: SuperAdmin can view all users across all companies
- **Company-scoped User Listing**: Company admins and managers can view users in their company
- **User Detail Viewing**: View individual user information with invitation status
- **User Invitation**: Create invitations for new users with role and company assignment
- **User Detail Updates**: Update user information (name, etc.)
- **Reference Data Access**: List available roles and companies for invitation forms

### 1.2 Business Value
Provides the foundation for user discovery, invitation-based onboarding, and basic user information management, enabling controlled access to user data based on role-based visibility rules.

### 1.3 Technical Scope
- User listing endpoints with pagination, filtering, and sorting
- User detail retrieval with invitation status
- User invitation creation with role assignment
- User information updates
- Role and company reference data endpoints
- Role-based field visibility enforcement (Manager restrictions, Employee access denial)

**Note:** User authentication and activation flows are handled in F-000 (Core Platform Foundation). F-001 focuses on user management operations.

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
- SuperAdmin (`org_id: null`): Global platform access
- Company users (`org_id: "<uuid>"`): Limited to specified organization

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
**Capabilities:**
- Platform-wide user and company management
- View all users across all companies
- Send invitations for any role across any company
- Update any user's information
- Access denied to company-specific business data (projects, tasks, attendance, leaves, salaries)

#### CEO (Company Admin)
**Access Scope:** Full company administration within own organization
**Capabilities:**
- View all users in own company
- Send invitations within own company
- Update user information in own company
- Manage employee lifecycle

#### HR (Company Level)
**Access Scope:** Employee management and HR operations within own company
**Capabilities:**
- View all users in own company
- Send invitations within own company
- Update user information in own company
- Manage employee data

#### Manager (Company Level)
**Access Scope:** Project/task management within own company
**Capabilities:**
- View users in own company (with restricted field set - list-level visibility only)
- Cannot view sensitive fields (salary, personal information)
- Cannot invite users
- Cannot update user information
- Cannot access user detail endpoints

#### Employee (Company Level)
**Access Scope:** Personal data and assigned tasks within own company
**Capabilities:**
- Cannot view user lists
- Cannot access user management endpoints
- Can only view/update own profile (handled in separate feature)

### 3.2 Permission Matrix (F-001A Endpoints)

| Endpoint | SuperAdmin | CEO | HR | Manager | Employee |
|----------|------------|-----|----|---------|----------|
| GET /v1/users | ✅ | ❌ | ❌ | ❌ | ❌ |
| GET /v1/company/users | ✅ | ✅ | ✅ | ✅ (restricted fields) | ❌ |
| GET /v1/users/{user_id} | ✅ | ✅ | ✅ | ✅ | ❌ |
| POST /v1/users/invite | ✅ | ✅ | ✅ | ❌ | ❌ |
| PATCH /v1/users/{user_id} | ✅ (any user) | ✅ (own company) | ✅ (own company) | ❌ | ✅ (own profile only) |
| GET /v1/roles | ✅ | ✅ | ✅ | ❌ | ❌ |
| GET /v1/companies | ✅ | ❌ | ❌ | ❌ | ❌ |

**Note:** Manager access to `GET /v1/company/users` returns restricted field set (list-level visibility only, excluding sensitive fields).

---

## 4. Resources & Endpoints

### 4.1 Resource Overview

#### User Resource
Represents a platform identity whose onboarding, activation, role assignment, visibility, and lifecycle are governed by strict rules.

**Key Fields:**
- `user_id` (UUID): Unique user identifier
- `email` (string): User email address (unique, immutable, RFC 5322 format, max 254 characters)
- `first_name` (string): User first name (set at activation, max 255 characters)
- `last_name` (string): User last name (set at activation, max 255 characters)
- `is_active` (boolean): Login eligibility (false blocks authentication)
- `is_deleted` (boolean): Soft delete flag (retains historical data)
- `invite_at` (datetime, UTC): Initial invitation timestamp
- `activate_at` (datetime, UTC, nullable): Activation timestamp (null until activated)
- `expiry` (datetime, UTC): Invitation expiry timestamp (server-generated, 24 hours from invite_at)
- `reinvite_count` (integer): Number of re-invitations (default: 0)
- `last_reinvite_at` (datetime, UTC, nullable): Last re-invite timestamp
- `created_at` (datetime, UTC): Record creation timestamp
- `updated_at` (datetime, UTC): Record last update timestamp (used for ETag generation)

**Internal Fields (not exposed in API responses):**
- `token` (string): Credential token used for invitation activation and password reset (internal field, not returned in API responses)

**Embedded Domain Concepts:**
- **Invitation**: Lifecycle state derived from `invite_at`, `expiry`, `activate_at`
  - States: `pending`, `expired`, `activated`
- **Re-invitation**: Reuses same User record, generates new token and expiry

#### UserRoleAssignment Resource
Active association defining a user's role within a company context.

**Key Fields:**
- `user_id` (UUID): Assigned user
- `role_code` (string): Assigned role code (immutable system identifier)
- `role_name` (string): Assigned role name
- `company_id` (UUID, nullable): Context company (null for SuperAdmin)
- `company_name` (string, nullable): Company name
- `company_slug` (string, nullable): Company URL identifier
- `is_active` (boolean): Assignment status (one active per user)

#### Role Resource
Fixed and predefined role defining authority, visibility, and access boundaries.

**Key Fields:**
- `code` (string): System identifier (immutable)
- `name` (string): Role display name

#### Company Resource
Tenant boundary that constrains user management and visibility.

**Key Fields:**
- `company_id` (UUID): Unique company identifier
- `name` (string): Company name (unique, case-insensitive)
- `slug` (string): URL identifier (unique, case-insensitive)
- `is_active` (boolean): Company availability (blocks access if false)

### 4.2 Endpoint Summary

| Method | Path | Purpose | Authentication |
|--------|------|---------|----------------|
| GET | /api/v1/users | List all users across platform (SuperAdmin only) | Required |
| GET | /api/v1/company/users | List users in authenticated user's company | Required |
| GET | /api/v1/users/{user_id} | Get user details with invitation status | Required |
| POST | /api/v1/users/invite | Invite new user with role assignment | Required |
| PATCH | /api/v1/users/{user_id} | Update user information (name, etc.) | Required |
| GET | /api/v1/roles | List available roles for invitation form | Required |
| GET | /api/v1/companies | List all companies (SuperAdmin only) | Required |

---

## 5. Endpoint Details

### 5.1 GET /api/v1/users

- **Purpose:** List all users across the platform with pagination, filtering, and sorting (SuperAdmin only)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin only
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-None-Match: "20240120T103000Z"` (optional, for cache validation - returns 304 if unchanged)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
- **Idempotency:** Yes (GET operation)

**Path Parameters**  
None

**Query Parameters**  
**Note:** Query parameters MUST be defined using a query schema class with `Depends()` pattern (Rule 9), NOT individual `Query()` parameters in the router endpoint.

**Query Schema Class (REQUIRED):**
```python
class PlatformUserListQuery(BaseModel):
    """Query schema for listing platform users with pagination and filtering."""

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    search: Optional[str] = Field(None, description="Search by email, first_name, or last_name (case-insensitive partial match)")
    company_slug: Optional[str] = Field(None, description="Filter by company slug (exact match)")
    role_code: Optional[str] = Field(None, description="Filter by role code (exact match)")
    status: Optional[str] = Field(None, description="Filter by status: active, inactive, pending, expired, activated")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, email, first_name, last_name, role_code")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)
```

**Router Endpoint Pattern (REQUIRED):**
```python
@router.get("", response_model=StandardResponse[UserPaginatedResponse])
async def list_platform_users(
    query: PlatformUserListQuery = Depends(PlatformUserListQuery),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_superadmin),
):
    """List platform users with pagination and filtering."""
    # Access via query.page, query.page_size, query.search, etc.
```

**Query Parameters Table (for documentation only):**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number (≥ 1) |
| page_size | integer | No | 20 | Page size (1-100) |
| search | string | No | null | Search by email, first_name, or last_name (case-insensitive partial match) |
| company_slug | string | No | null | Filter by company slug (exact match) |
| role_code | string | No | null | Filter by role code (exact match) |
| status | string | No | null | Filter by status: active, inactive, pending, expired, activated |
| sort_by | string | No | created_at | Sort field: created_at, updated_at, email, first_name, last_name, role_code |
| sort_order | string | No | desc | Sort order: asc or desc |

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "items": [
      {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "is_active": true,
        "is_deleted": false,
        "invite_at": "2024-01-20T10:00:00Z",
        "activate_at": "2024-01-20T12:00:00Z",
        "expiry": "2024-01-21T10:00:00Z",
        "invitation_status": "activated",
        "role": {
          "code": "manager",
          "name": "Manager"
        },
        "company": {
          "company_id": "660e8400-e29b-41d4-a716-446655440001",
          "name": "Tech Corp",
          "slug": "tech-corp"
        }
      }
    ],
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8,
    "next_page": "/api/v1/users?page=2&page_size=20&sort_by=created_at&sort_order=desc",
    "prev_page": null
  },
  "message": "Users retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- `next_page` and `prev_page` include all query parameters (filters, sort, search) to preserve pagination state.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 403 | INSUFFICIENT_PERMISSIONS | User is not SuperAdmin |
| 400 | INVALID_REQUEST | Invalid query parameter format or value |
| 500 | INTERNAL_ERROR | Server error during request processing |

Example error (403 Forbidden):
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "details": [{"field": "role", "issue": "Only SuperAdmin can access platform-wide user list."}]
  },
  "message": "You do not have permission to perform this action."
}
```

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate error.

---

### 5.2 GET /api/v1/company/users

- **Purpose:** List users in authenticated user's company with pagination, filtering, and sorting
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin, CEO, HR, Manager (with field restrictions for Manager)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-None-Match: "20240120T103000Z"` (optional, for cache validation - returns 304 if unchanged)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
- **Idempotency:** Yes (GET operation)

**Path Parameters**  
None

**Query Parameters**  
**Note:** Query parameters MUST be defined using a query schema class with `Depends()` pattern (Rule 9), NOT individual `Query()` parameters in the router endpoint.

**Query Schema Class (REQUIRED):**
```python
class CompanyUserListQuery(BaseModel):
    """Query schema for listing company users with pagination and filtering."""

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    search: Optional[str] = Field(None, description="Search by email, first_name, or last_name (case-insensitive partial match)")
    role_code: Optional[str] = Field(None, description="Filter by role code (exact match)")
    status: Optional[str] = Field(None, description="Filter by status: active, inactive, pending, expired, activated")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, email, first_name, last_name, role_code")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)
```

**Query Parameters Table (for documentation only):**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number (≥ 1) |
| page_size | integer | No | 20 | Page size (1-100) |
| search | string | No | null | Search by email, first_name, or last_name (case-insensitive partial match) |
| role_code | string | No | null | Filter by role code (exact match) |
| status | string | No | null | Filter by status: active, inactive, pending, expired, activated |
| sort_by | string | No | created_at | Sort field: created_at, updated_at, email, first_name, last_name, role_code |
| sort_order | string | No | desc | Sort order: asc or desc |

**Request Body**  
None

**Success Response (200 OK)**

For SuperAdmin, CEO, HR (full field set):
```json
{
  "data": {
    "items": [
      {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "is_active": true,
        "invite_at": "2024-01-20T10:00:00Z",
        "activate_at": "2024-01-20T12:00:00Z",
        "expiry": "2024-01-21T10:00:00Z",
        "invitation_status": "activated",
        "role": {
          "code": "manager",
          "name": "Manager"
        }
      }
    ],
    "total": 50,
    "page": 1,
    "page_size": 20,
    "total_pages": 3,
    "next_page": "/api/v1/company/users?page=2&page_size=20&sort_by=created_at&sort_order=desc",
    "prev_page": null
  },
  "message": "Users retrieved successfully"
}
```

For Manager (restricted field set - list-level visibility only):
```json
{
  "data": {
    "items": [
      {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "is_active": true,
        "role": {
          "code": "manager",
          "name": "Manager"
        }
      }
    ],
    "total": 50,
    "page": 1,
    "page_size": 20,
    "total_pages": 3,
    "next_page": "/api/v1/company/users?page=2&page_size=20&sort_by=created_at&sort_order=desc",
    "prev_page": null
  },
  "message": "Users retrieved successfully"
}
```

**Note:** Manager response excludes `invite_at`, `activate_at`, `invitation_status`, and other sensitive fields. Only list-level visibility fields are included.

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 403 | INSUFFICIENT_PERMISSIONS | User is Employee (no access to user lists) |
| 400 | INVALID_REQUEST | Invalid query parameter format or value |
| 500 | INTERNAL_ERROR | Server error during request processing |

---

### 5.3 GET /api/v1/users/{user_id}

- **Purpose:** Get user details with invitation status and re-invitation eligibility
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin, CEO, HR, Manager
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-None-Match: "20240120T103000Z"` (optional, for cache validation - returns 304 if unchanged)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
    - `ETag: "20240120T103000Z"` (REQUIRED - resource version identifier based on `updated_at`)
    - `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (RECOMMENDED)
- **Idempotency:** Yes (GET operation)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| user_id | string (UUID) | Yes | User identifier (RFC 4122 UUID v4 format) |

**Note:** All path parameters MUST use snake_case (e.g., `user_id`, `org_id`, `role_id`) - see Rule 2.

**Query Parameters**  
None

**Request Body**  
None

**Success Response (200 OK)**

For SuperAdmin, CEO, HR (full field set):
```json
{
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "is_deleted": false,
    "invite_at": "2024-01-20T10:00:00Z",
    "activate_at": "2024-01-20T12:00:00Z",
    "expiry": "2024-01-21T10:00:00Z",
    "reinvite_count": 0,
    "last_reinvite_at": null,
    "invitation_status": "activated",
    "can_resend_invite": false,
    "role": {
      "code": "manager",
      "name": "Manager"
    },
    "company": {
      "company_id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Tech Corp",
      "slug": "tech-corp"
    }
  },
  "message": "User retrieved successfully"
}
```

For Manager (restricted field set - excludes sensitive fields):
```json
{
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "role": {
      "code": "manager",
      "name": "Manager"
    }
  },
  "message": "User retrieved successfully"
}
```

**Note:** Manager response excludes `is_deleted`, `invite_at`, `activate_at`, `reinvite_count`, `last_reinvite_at`, `invitation_status`, `can_resend_invite`, and `company` details.

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103000Z"` (REQUIRED - resource version identifier based on `updated_at`)
- `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (RECOMMENDED)

**Derived Fields:**
- `invitation_status` (string, enum): Derived from `invite_at`, `activate_at`, and `expiry`
  - Values: `"pending"` (invited but not activated and not expired), `"expired"` (invited but expired), `"activated"` (user has activated account)
- `can_resend_invite` (boolean): Indicates if re-invitation is allowed
  - `true` if user is inactive (`is_active=false`) OR invitation is expired
  - `false` if user is active and invitation is not expired

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 403 | INSUFFICIENT_PERMISSIONS | User is Employee (no access to user detail) |
| 404 | USER_NOT_FOUND | User with specified user_id does not exist |
| 400 | INVALID_REQUEST | Invalid user_id format (not valid UUID) |
| 500 | INTERNAL_ERROR | Server error during request processing |

Example error (404 Not Found):
```json
{
  "error": {
    "code": "USER_NOT_FOUND",
    "details": [{"field": "user_id", "issue": "User with ID '550e8400-e29b-41d4-a716-446655440000' does not exist."}]
  },
  "message": "User not found."
}
```

---

### 5.4 POST /api/v1/users/invite

- **Purpose:** Invite new user with role and company assignment
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin, CEO, HR
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
- **Idempotency:** No (creates new invitation)

**Path Parameters**  
None

**Query Parameters**  
None

**Request Body**

**Schema Table:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| email | string | Yes | User email address | RFC 5322 format, max 254 characters, case-insensitive unique |
| role_code | string | Yes | Role code for assignment | Must be valid role code (ceo, hr, manager, employee, superadmin) |
| company_slug | string | No | Company slug (required for non-SuperAdmin roles, optional for SuperAdmin) | Must be valid company slug if provided, null allowed only for SuperAdmin role |

**Note:** 
- `company_slug` is required for all roles except SuperAdmin
- For SuperAdmin role, `company_slug` must be null or omitted
- For CEO, HR, Manager, Employee roles, `company_slug` is required
- SuperAdmin can invite to any company
- CEO and HR can only invite to their own company (company_slug is ignored, inferred from token)

**Request Example:**
```json
{
  "email": "newuser@example.com",
  "role_code": "manager",
  "company_slug": "tech-corp"
}
```

**Success Response (201 Created)**

```json
{
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "newuser@example.com",
    "first_name": null,
    "last_name": null,
    "is_active": false,
    "invite_at": "2024-01-20T10:00:00Z",
    "activate_at": null,
    "expiry": "2024-01-21T10:00:00Z",
    "invitation_status": "pending",
    "role": {
      "code": "manager",
      "name": "Manager"
    },
    "company": {
      "company_id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Tech Corp",
      "slug": "tech-corp"
    }
  },
  "message": "User invitation sent successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Business Rules:**
- Email must be unique (case-insensitive). If user with email already exists:
  - If user is active: Return `409 Conflict` with `DUPLICATE_EMAIL` error
  - If user is inactive: Re-invitation logic applies (see F-001B for resend-invite endpoint)
- Role must be valid role code
- Company must exist and be active
- For CEO role: Company must not already have an active CEO (enforced in F-001B role change endpoint)
- SuperAdmin can invite to any company
- CEO and HR can only invite to their own company (company_slug is ignored, inferred from authenticated user's org_id)
- `expiry` is server-generated: Automatically set to 24 hours from `invite_at` timestamp (not user-provided)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 403 | INSUFFICIENT_PERMISSIONS | User is Manager or Employee (cannot invite users) |
| 400 | VALIDATION_FAILED | Invalid request format or missing required fields |
| 409 | DUPLICATE_EMAIL | Email already exists for active user |
| 404 | COMPANY_NOT_FOUND | Company with specified company_slug does not exist |
| 404 | ROLE_NOT_FOUND | Role with specified role_code does not exist |
| 422 | BUSINESS_RULE_FAILED | Business rule violation (e.g., company already has CEO) |
| 500 | INTERNAL_ERROR | Server error during request processing |

Example error (409 Conflict - Duplicate Email):
```json
{
  "error": {
    "code": "DUPLICATE_EMAIL",
    "details": [{"field": "email", "issue": "A user with this email already exists and is active."}]
  },
  "message": "Email address is already in use."
}
```

Example error (422 Unprocessable Entity - Business Rule):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [{"field": "role_code", "issue": "Company already has an active CEO. Only one CEO is allowed per company."}]
  },
  "message": "Business rule violation: Cannot assign CEO role to company that already has an active CEO."
}
```

---

### 5.5 PATCH /api/v1/users/{user_id}

- **Purpose:** Update user information (name, etc.)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** 
  - Users can update their own details
  - SuperAdmin can update any user's details
  - CEO and HR can update any user's details in their own company
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-Match: "20240120T103000Z"` (REQUIRED - ETag from GET response, based on `updated_at`, see Rule 8)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
    - `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)
- **Idempotency:** Yes (conditional on ETag)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| user_id | string (UUID) | Yes | User identifier (RFC 4122 UUID v4 format) |

**Query Parameters**  
None

**Request Body**

**Schema Table:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| first_name | string | No | User first name | Min 1 character, max 255 characters, alphanumeric and spaces only |
| last_name | string | No | User last name | Min 1 character, max 255 characters, alphanumeric and spaces only |

**Note:** 
- At least one field (first_name or last_name) must be provided
- Email is immutable and cannot be updated
- Other fields (is_active, role, company) are updated via separate endpoints (see F-001B)

**Request Example:**
```json
{
  "first_name": "Jane",
  "last_name": "Smith"
}
```

**Success Response (200 OK)**

```json
{
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "is_active": true,
    "is_deleted": false,
    "invite_at": "2024-01-20T10:00:00Z",
    "activate_at": "2024-01-20T12:00:00Z",
    "expiry": "2024-01-21T10:00:00Z",
    "role": {
      "code": "manager",
      "name": "Manager"
    },
    "company": {
      "company_id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Tech Corp",
      "slug": "tech-corp"
    }
  },
  "message": "User updated successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)

**Business Rules:**
- Users can update their own details (user_id matches token's sub claim)
- SuperAdmin can update any user's details
- CEO and HR can update any user's details in their own company
- Manager and Employee can only update their own details
- Email is immutable and cannot be changed

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks permission to update this user |
| 404 | USER_NOT_FOUND | User with specified user_id does not exist |
| 400 | VALIDATION_FAILED | Invalid request format or validation error |
| 412 | PRECONDITION_FAILED | ETag mismatch (resource was modified since retrieval) |
| 428 | PRECONDITION_REQUIRED | If-Match header missing but required |
| 500 | INTERNAL_ERROR | Server error during request processing |

Example error (412 Precondition Failed - ETag mismatch):
```json
{
  "error": {
    "code": "PRECONDITION_FAILED",
    "details": [{"field": "etag", "issue": "Resource has been modified since retrieval. Please fetch the latest version and retry."}]
  },
  "message": "Resource version mismatch. The resource was modified by another user."
}
```

---

### 5.6 GET /api/v1/roles

- **Purpose:** List available roles for invitation form dropdown
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin, CEO, HR
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
- **Idempotency:** Yes (GET operation)

**Path Parameters**  
None

**Query Parameters**  
None

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "items": [
      {
        "code": "superadmin",
        "name": "SuperAdmin"
      },
      {
        "code": "ceo",
        "name": "CEO"
      },
      {
        "code": "hr",
        "name": "HR"
      },
      {
        "code": "manager",
        "name": "Manager"
      },
      {
        "code": "employee",
        "name": "Employee"
      }
    ]
  },
  "message": "Roles retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Note:** 
- Response is not paginated (small, fixed list of roles)
- Role codes are immutable system identifiers
- Role permissions are fixed in V1

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 403 | INSUFFICIENT_PERMISSIONS | User is Manager or Employee (cannot access roles) |
| 500 | INTERNAL_ERROR | Server error during request processing |

---

### 5.7 GET /api/v1/companies

- **Purpose:** List all companies for SuperAdmin invitation form
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin only
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
- **Idempotency:** Yes (GET operation)

**Path Parameters**  
None

**Query Parameters**  
None

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "items": [
      {
        "company_id": "660e8400-e29b-41d4-a716-446655440001",
        "name": "Tech Corp",
        "slug": "tech-corp",
        "is_active": true
      },
      {
        "company_id": "660e8400-e29b-41d4-a716-446655440002",
        "name": "Acme Inc",
        "slug": "acme-inc",
        "is_active": true
      }
    ]
  },
  "message": "Companies retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Note:** 
- Response is not paginated (typically small number of companies)
- Only active companies are returned
- SuperAdmin uses this list to select company when inviting users

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 403 | INSUFFICIENT_PERMISSIONS | User is not SuperAdmin |
| 500 | INTERNAL_ERROR | Server error during request processing |

---

## 6. Documentation Classes (Rule 10 Compliance)

**UserApiDocs Class Structure:**
```python
class UserApiDocs:
    """API documentation for User & Role Management endpoints"""

    list_platform_users: ClassVar[dict] = {
        "summary": "Purpose of this API is to list all users across the platform",
        "description": "Retrieves a paginated list of all users across all companies. Only SuperAdmin can access this endpoint. Supports filtering by company, role, status, and search by name/email. Includes pagination, sorting, and navigation URLs."
    }

    list_company_users: ClassVar[dict] = {
        "summary": "Purpose of this API is to list users in authenticated user's company",
        "description": "Retrieves a paginated list of users in the authenticated user's company. Accessible by SuperAdmin, CEO, HR, and Manager. Managers receive restricted field sets (list-level visibility only, excluding sensitive fields). Employees cannot access this endpoint. Supports filtering by role, status, and search by name/email."
    }

    get_user_detail: ClassVar[dict] = {
        "summary": "Purpose of this API is to get user details with invitation status",
        "description": "Retrieves detailed information about a specific user, including invitation status and re-invitation eligibility. Accessible by SuperAdmin, CEO, HR, and Manager. Managers receive restricted field sets (excluding sensitive fields). Employees cannot access this endpoint."
    }

    invite_user: ClassVar[dict] = {
        "summary": "Purpose of this API is to invite a new user with role and company assignment",
        "description": "Creates a new user invitation with role and company assignment. Accessible by SuperAdmin, CEO, and HR. SuperAdmin can invite to any company. CEO and HR can only invite to their own company. Generates invitation token with 24-hour expiry. Returns 409 Conflict if email already exists for active user."
    }

    update_user: ClassVar[dict] = {
        "summary": "Purpose of this API is to update user information",
        "description": "Updates user information such as first name and last name. Users can update their own details. SuperAdmin can update any user's details. CEO and HR can update any user's details in their own company. Requires If-Match header for concurrency control. Email is immutable and cannot be updated."
    }

    list_roles: ClassVar[dict] = {
        "summary": "Purpose of this API is to list available roles for invitation form",
        "description": "Retrieves a list of all available roles (code and name) for use in invitation form dropdowns. Accessible by SuperAdmin, CEO, and HR. Role codes are immutable system identifiers."
    }

    list_companies: ClassVar[dict] = {
        "summary": "Purpose of this API is to list all companies for SuperAdmin invitation form",
        "description": "Retrieves a list of all active companies (name and slug) for use in SuperAdmin invitation form. Only SuperAdmin can access this endpoint. Returns only active companies."
    }
```

**Router Endpoint Pattern (REQUIRED):**
```python
from src.users.documentations.user_api_doc import UserApiDocs

@router.get(
    "",
    response_model=StandardResponse[UserPaginatedResponse],
    summary=UserApiDocs.list_platform_users["summary"],
    description=UserApiDocs.list_platform_users["description"]
)
async def list_platform_users(...):
    """List platform users with pagination and filtering."""
    pass
```

---

## 7. Business Rules & Validations

### 7.1 Email Uniqueness
- Email addresses must be unique across all users (case-insensitive)
- If invitation is sent to existing email:
  - If user is active: Return `409 Conflict` with `DUPLICATE_EMAIL` error
  - If user is inactive: Re-invitation logic applies (see F-001B)

### 7.2 Invitation State Management
- Invitation status is derived from `invite_at`, `activate_at`, and `expiry`:
  - `pending`: Invited but not activated and not expired
  - `expired`: Invited but expired (expiry < current time)
  - `activated`: User has activated account (activate_at is not null)
- Invitation expiry is 24 hours from `invite_at`

### 7.3 Role-Based Field Visibility
- **SuperAdmin, CEO, HR**: Full field access (all user fields)
- **Manager**: Restricted field set (list-level visibility only):
  - Included: `user_id`, `email`, `first_name`, `last_name`, `is_active`, `role`
  - Excluded: `is_deleted`, `invite_at`, `activate_at`, `reinvite_count`, `last_reinvite_at`, `invitation_status`, `can_resend_invite`, `company` details
- **Employee**: No access to user management endpoints

### 7.4 Company Context Rules
- SuperAdmin: Can access all companies (org_id is null in token)
- Company users: Limited to their own company (org_id in token)
- CEO and HR: Can only invite to their own company (company_slug is ignored, inferred from token)
- SuperAdmin: Can invite to any company (company_slug is required in request)

### 7.5 User Update Permissions
- Users can update their own details (user_id matches token's sub claim)
- SuperAdmin can update any user's details
- CEO and HR can update any user's details in their own company
- Manager and Employee can only update their own details

---

## 8. Edge Cases & Special Scenarios

### 8.1 Duplicate Invitations
- If invitation is sent to email that already exists:
  - Active user: Return `409 Conflict` with `DUPLICATE_EMAIL`
  - Inactive user: Re-invitation logic (see F-001B resend-invite endpoint)

### 8.2 Manager Field Restrictions
- Manager accessing `GET /v1/company/users` or `GET /v1/users/{user_id}` receives restricted field set
- Server must filter out sensitive fields before returning response
- Manager cannot see invitation details, re-invitation counts, or company details

### 8.3 Employee Access Denial
- Employee attempting to access any user management endpoint receives `403 INSUFFICIENT_PERMISSIONS`
- Employee can only access their own profile (handled in separate feature)

### 8.4 Company Context Inference
- For `GET /v1/company/users`, company context is inferred from authenticated user's `org_id` claim
- SuperAdmin can access this endpoint but sees all companies (or filtered by query params)
- CEO, HR, Manager see only their own company's users

### 8.5 Invitation Status Calculation
- `invitation_status` is calculated server-side based on:
  - `invite_at`: When invitation was sent
  - `expiry`: When invitation expires (24 hours from invite_at)
  - `activate_at`: When user activated (null if not activated)
- Logic:
  - If `activate_at` is not null: `"activated"`
  - Else if current time > `expiry`: `"expired"`
  - Else: `"pending"`

---

## 9. Open Questions

None identified at this stage.

---

## 10. Assumptions

1. Role and permission definitions are fixed in V1 (no customization)
2. Invitation expiry is 24 hours from invitation time
3. Manager user visibility is list-level only, excluding sensitive fields
4. Employee cannot access any user management endpoints
5. Company context is inferred from authenticated user's `org_id` claim for company-scoped endpoints
6. SuperAdmin can access all companies and all users
7. Email is immutable and cannot be changed after user creation
8. Re-invitation is allowed for any user (even previously activated and deactivated) - see F-001B

---

**End of F-001A API Specification**

**Next:** F-001B API Specification covers advanced lifecycle operations (role changes, company reassignment, activation/deactivation, re-invitation).

