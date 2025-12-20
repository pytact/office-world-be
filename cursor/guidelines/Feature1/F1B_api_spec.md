# API Specification: F-001B — User & Role Management (Lifecycle Operations)

## 1. Overview

The User & Role Management feature (F-001) enables invitation-based onboarding and lifecycle management of users within strict company and role boundaries. This specification (F-001B) covers advanced lifecycle operations: role changes, company reassignment, user activation/deactivation, and re-invitation.

**Note:** Core user management operations (listing, viewing, inviting, updating, reference data) are documented in F-001A.

### 1.1 Feature Capabilities (F-001B)
- **Role Changes**: Change user roles within the same company with CEO cardinality validation
- **Company Reassignment**: Reassign users to different companies with optional role changes (SuperAdmin only)
- **User Activation Management**: Deactivate and reactivate users to control login eligibility
- **Re-invitation**: Resend invitations to users (generates new token and expiry)

### 1.2 Business Value
Enables organizational flexibility by allowing role changes and company reassignments while maintaining strict business rules (CEO cardinality, role-based permissions). Provides control over user access through activation/deactivation and supports re-invitation for onboarding recovery.

### 1.3 Technical Scope
- Role change endpoint with CEO cardinality enforcement
- Company reassignment endpoint with optional role change
- User deactivation endpoint (blocks authentication)
- User reactivation endpoint (restores authentication)
- Re-invitation endpoint (generates new token and expiry)
- Business rule validation (CEO cardinality, role constraints)
- Concurrency control via ETags

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
- Change any user's role across any company
- Reassign users to different companies
- Deactivate and reactivate any user
- Resend invitations to any user

#### CEO (Company Admin)
**Access Scope:** Full company administration within own organization
**Capabilities:**
- Change user roles within own company
- Deactivate and reactivate users in own company
- Resend invitations to users in own company
- Cannot reassign users to different companies

#### HR (Company Level)
**Access Scope:** Employee management and HR operations within own company
**Capabilities:**
- Change user roles within own company
- Deactivate and reactivate users in own company
- Resend invitations to users in own company
- Cannot reassign users to different companies

#### Manager (Company Level)
**Access Scope:** Project/task management within own company
**Capabilities:**
- Cannot change user roles
- Cannot deactivate/reactivate users
- Cannot resend invitations
- Cannot reassign users

#### Employee (Company Level)
**Access Scope:** Personal data and assigned tasks within own company
**Capabilities:**
- Cannot change user roles
- Cannot deactivate/reactivate users
- Cannot resend invitations
- Cannot reassign users

### 3.2 Permission Matrix (F-001B Endpoints)

| Endpoint | SuperAdmin | CEO | HR | Manager | Employee |
|----------|------------|-----|----|---------|----------|
| PATCH /v1/users/{user_id}/role | ✅ (any company) | ✅ (own company) | ✅ (own company) | ❌ | ❌ |
| PATCH /v1/users/{user_id}/companies/{company_id}/reassign | ✅ | ❌ | ❌ | ❌ | ❌ |
| PATCH /v1/users/{user_id}/deactivate | ✅ (any company) | ✅ (own company) | ✅ (own company) | ❌ | ❌ |
| PATCH /v1/users/{user_id}/reactivate | ✅ (any company) | ✅ (own company) | ✅ (own company) | ❌ | ❌ |
| POST /v1/users/{user_id}/resend-invite | ✅ (any company) | ✅ (own company) | ✅ (own company) | ❌ | ❌ |

---

## 4. Resources & Endpoints

### 4.1 Resource Overview

#### User Resource
Represents a platform identity whose onboarding, activation, role assignment, visibility, and lifecycle are governed by strict rules.

**Key Fields (relevant to F-001B):**
- `user_id` (UUID): Unique user identifier
- `email` (string): User email address (unique, immutable)
- `is_active` (boolean): Login eligibility (false blocks authentication)
- `role_code` (string): Current role code
- `company_id` (UUID, nullable): Current company identifier (null for SuperAdmin)
- `invite_at` (datetime, UTC): Initial invitation timestamp
- `activate_at` (datetime, UTC, nullable): Activation timestamp
- `expiry` (datetime, UTC): Invitation expiry timestamp (server-generated, 24 hours from invite_at)
- `reinvite_count` (integer): Number of re-invitations
- `last_reinvite_at` (datetime, UTC, nullable): Last re-invite timestamp
- `created_at` (datetime, UTC): Record creation timestamp
- `updated_at` (datetime, UTC): Record last update timestamp (used for ETag generation)

#### UserRoleAssignment Resource
Active association defining a user's role within a company context.

**Key Fields:**
- `user_id` (UUID): Assigned user
- `role_code` (string): Assigned role code
- `company_id` (UUID, nullable): Context company (null for SuperAdmin)
- `is_active` (boolean): Assignment status (one active per user)

### 4.2 Endpoint Summary

| Method | Path | Purpose | Authentication |
|--------|------|---------|----------------|
| PATCH | /api/v1/users/{user_id}/role | Change user role within same company | Required |
| PATCH | /api/v1/users/{user_id}/companies/{company_id}/reassign | Reassign user to different company with optional role change | Required |
| PATCH | /api/v1/users/{user_id}/deactivate | Deactivate user (set is_active=false) | Required |
| PATCH | /api/v1/users/{user_id}/reactivate | Reactivate user (set is_active=true) | Required |
| POST | /api/v1/users/{user_id}/resend-invite | Resend invitation (generate new token and expiry) | Required |

---

## 5. Endpoint Details

### 5.1 PATCH /api/v1/users/{user_id}/role

- **Purpose:** Change user role within the same company
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin, CEO, HR
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

**Note:** All path parameters MUST use snake_case (e.g., `user_id`, `org_id`, `role_id`) - see Rule 2.

**Query Parameters**  
None

**Request Body**

**Schema Table:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| role_code | string | Yes | New role code for user | Must be valid role code (ceo, hr, manager, employee, superadmin) |

**Request Example:**
```json
{
  "role_code": "hr"
}
```

**Success Response (200 OK)**

```json
{
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "expiry": "2024-01-21T10:00:00Z",
    "role": {
      "code": "hr",
      "name": "HR"
    },
    "company": {
      "company_id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Tech Corp",
      "slug": "tech-corp"
    }
  },
  "message": "User role updated successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)

**Business Rules:**
- Role must be valid role code
- User must exist and belong to a company (cannot change SuperAdmin role via this endpoint)
- **CEO Cardinality Rule**: If assigning CEO role, company must not already have an active CEO
  - If company already has an active CEO, return `422 BUSINESS_RULE_FAILED`
  - Exception: If the user being assigned CEO role is the current CEO, allow the change (no-op)
- SuperAdmin can change roles across any company
- CEO and HR can only change roles within their own company
- Cannot change user's own role (user cannot change their own role)
- Role change does not affect company assignment (user remains in same company)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks permission to change roles (Manager, Employee) or user is not in same company (CEO, HR) |
| 404 | USER_NOT_FOUND | User with specified user_id does not exist |
| 404 | ROLE_NOT_FOUND | Role with specified role_code does not exist |
| 400 | VALIDATION_FAILED | Invalid request format or validation error |
| 412 | PRECONDITION_FAILED | ETag mismatch (resource was modified since retrieval) |
| 422 | BUSINESS_RULE_FAILED | Business rule violation (e.g., company already has CEO) |
| 428 | PRECONDITION_REQUIRED | If-Match header missing but required |
| 500 | INTERNAL_ERROR | Server error during request processing |

Example error (422 Unprocessable Entity - CEO Cardinality):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [{"field": "role_code", "issue": "Company already has an active CEO. Only one CEO is allowed per company. Please deactivate the current CEO or reassign them to a different role first."}]
  },
  "message": "Business rule violation: Cannot assign CEO role to company that already has an active CEO."
}
```

Example error (403 Forbidden - Cannot change own role):
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "details": [{"field": "user_id", "issue": "You cannot change your own role."}]
  },
  "message": "You do not have permission to perform this action."
}
```

---

### 5.2 PATCH /api/v1/users/{user_id}/companies/{company_id}/reassign

- **Purpose:** Reassign user to different company with optional role change (SuperAdmin only)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin only
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
| company_id | string (UUID) | Yes | Target company identifier (RFC 4122 UUID v4 format) |

**Note:** All path parameters MUST use snake_case (e.g., `user_id`, `company_id`) - see Rule 2.

**Query Parameters**  
None

**Request Body**

**Schema Table:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| role_code | string | No | New role code for user in target company (if not provided, keeps current role) | Must be valid role code (ceo, hr, manager, employee, superadmin) |

**Request Example (with role change):**
```json
{
  "role_code": "manager"
}
```

**Request Example (without role change - keep current role):**
```json
{}
```

**Success Response (200 OK)**

```json
{
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "expiry": "2024-01-21T10:00:00Z",
    "role": {
      "code": "manager",
      "name": "Manager"
    },
    "company": {
      "company_id": "660e8400-e29b-41d4-a716-446655440002",
      "name": "Acme Inc",
      "slug": "acme-inc"
    }
  },
  "message": "User reassigned to company successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)

**Business Rules:**
- Only SuperAdmin can reassign users to different companies
- User must exist
- Target company must exist and be active
- If `role_code` is provided:
  - Role must be valid role code
  - **CEO Cardinality Rule**: If assigning CEO role, target company must not already have an active CEO
  - If company already has an active CEO, return `422 BUSINESS_RULE_FAILED`
- If `role_code` is not provided:
  - User keeps their current role in the new company
  - If current role is CEO and target company already has a CEO, return `422 BUSINESS_RULE_FAILED`
- Cannot reassign SuperAdmin users (SuperAdmin has null company_id)
- Cannot reassign user to their current company (no-op, but returns success)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 403 | INSUFFICIENT_PERMISSIONS | User is not SuperAdmin |
| 404 | USER_NOT_FOUND | User with specified user_id does not exist |
| 404 | COMPANY_NOT_FOUND | Company with specified company_id does not exist |
| 404 | ROLE_NOT_FOUND | Role with specified role_code does not exist (if provided) |
| 400 | VALIDATION_FAILED | Invalid request format or validation error |
| 412 | PRECONDITION_FAILED | ETag mismatch (resource was modified since retrieval) |
| 422 | BUSINESS_RULE_FAILED | Business rule violation (e.g., company already has CEO, cannot reassign SuperAdmin) |
| 428 | PRECONDITION_REQUIRED | If-Match header missing but required |
| 500 | INTERNAL_ERROR | Server error during request processing |

Example error (422 Unprocessable Entity - CEO Cardinality):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [{"field": "role_code", "issue": "Target company already has an active CEO. Only one CEO is allowed per company. Please deactivate the current CEO or choose a different role."}]
  },
  "message": "Business rule violation: Cannot assign CEO role to company that already has an active CEO."
}
```

Example error (422 Unprocessable Entity - Cannot reassign SuperAdmin):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [{"field": "user_id", "issue": "Cannot reassign SuperAdmin users. SuperAdmin users are not tied to any company."}]
  },
  "message": "Business rule violation: SuperAdmin users cannot be reassigned to companies."
}
```

---

### 5.3 PATCH /api/v1/users/{user_id}/deactivate

- **Purpose:** Deactivate user (set is_active=false, blocks authentication)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin, CEO, HR
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
None (no request body required)

**Success Response (200 OK)**

```json
{
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": false,
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
  "message": "User deactivated successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)

**Business Rules:**
- User must exist
- Deactivated users cannot log in (is_active=false blocks authentication)
- Deactivated users retain all historical data (soft deactivation)
- SuperAdmin can deactivate any user across any company
- CEO and HR can only deactivate users in their own company
- Cannot deactivate your own account (user cannot deactivate themselves)
- If user is already deactivated, operation is idempotent (returns success)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks permission to deactivate users (Manager, Employee) or user is not in same company (CEO, HR) |
| 404 | USER_NOT_FOUND | User with specified user_id does not exist |
| 400 | VALIDATION_FAILED | Invalid request format |
| 412 | PRECONDITION_FAILED | ETag mismatch (resource was modified since retrieval) |
| 422 | BUSINESS_RULE_FAILED | Business rule violation (e.g., cannot deactivate own account) |
| 428 | PRECONDITION_REQUIRED | If-Match header missing but required |
| 500 | INTERNAL_ERROR | Server error during request processing |

Example error (422 Unprocessable Entity - Cannot deactivate own account):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [{"field": "user_id", "issue": "You cannot deactivate your own account."}]
  },
  "message": "Business rule violation: Users cannot deactivate their own accounts."
}
```

---

### 5.4 PATCH /api/v1/users/{user_id}/reactivate

- **Purpose:** Reactivate user (set is_active=true, restores authentication)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin, CEO, HR
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
None (no request body required)

**Success Response (200 OK)**

```json
{
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
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
  "message": "User reactivated successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)

**Business Rules:**
- User must exist
- Reactivated users can log in (is_active=true restores authentication)
- Reactivated users do not need to reset passwords (assumption from feature brief)
- SuperAdmin can reactivate any user across any company
- CEO and HR can only reactivate users in their own company
- If user is already active, operation is idempotent (returns success)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks permission to reactivate users (Manager, Employee) or user is not in same company (CEO, HR) |
| 404 | USER_NOT_FOUND | User with specified user_id does not exist |
| 400 | VALIDATION_FAILED | Invalid request format |
| 412 | PRECONDITION_FAILED | ETag mismatch (resource was modified since retrieval) |
| 428 | PRECONDITION_REQUIRED | If-Match header missing but required |
| 500 | INTERNAL_ERROR | Server error during request processing |

---

### 5.5 POST /api/v1/users/{user_id}/resend-invite

- **Purpose:** Resend invitation to user (generates new token and expiry, increments reinvite_count)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin, CEO, HR
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
- **Idempotency:** No (generates new token each time)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| user_id | string (UUID) | Yes | User identifier (RFC 4122 UUID v4 format) |

**Query Parameters**  
None

**Request Body**  
None (no request body required)

**Success Response (200 OK)**

```json
{
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": null,
    "last_name": null,
    "is_active": false,
    "invite_at": "2024-01-20T10:00:00Z",
    "activate_at": null,
    "expiry": "2024-01-21T10:00:00Z",
    "reinvite_count": 1,
    "last_reinvite_at": "2024-01-20T14:00:00Z",
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
  "message": "Invitation resent successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Business Rules:**
- User must exist
- **Re-invitation is allowed for any user** (even if previously activated and deactivated)
- Generates new invitation token
- Sets new expiry (24 hours from current time)
- Increments `reinvite_count`
- Updates `last_reinvite_at` to current timestamp
- Updates `invite_at` if this is the first invitation (user was created without invitation)
- SuperAdmin can resend invitations to any user across any company
- CEO and HR can only resend invitations to users in their own company
- Re-invitation does not change user's role or company assignment
- Re-invitation does not change `is_active` status (user remains inactive until they activate)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks permission to resend invitations (Manager, Employee) or user is not in same company (CEO, HR) |
| 404 | USER_NOT_FOUND | User with specified user_id does not exist |
| 400 | VALIDATION_FAILED | Invalid request format |
| 500 | INTERNAL_ERROR | Server error during request processing |

**Note:** Unlike other PATCH endpoints, this POST endpoint does not require If-Match header because it's an action (resend invitation) rather than a resource field update. However, it still generates a new token and updates invitation-related fields.

---

## 6. Documentation Classes (Rule 10 Compliance)

**UserApiDocs Class Structure (F-001B additions):**
```python
class UserApiDocs:
    """API documentation for User & Role Management endpoints"""

    change_user_role: ClassVar[dict] = {
        "summary": "Purpose of this API is to change user role within the same company",
        "description": "Changes a user's role within their current company. Accessible by SuperAdmin, CEO, and HR. SuperAdmin can change roles across any company. CEO and HR can only change roles within their own company. Enforces CEO cardinality rule (only one CEO per company). Requires If-Match header for concurrency control. Users cannot change their own role."
    }

    reassign_user_company: ClassVar[dict] = {
        "summary": "Purpose of this API is to reassign user to different company with optional role change",
        "description": "Reassigns a user to a different company with an optional role change. Only SuperAdmin can access this endpoint. If role_code is provided, assigns the specified role in the target company. If role_code is not provided, user keeps their current role. Enforces CEO cardinality rule for target company. Cannot reassign SuperAdmin users. Requires If-Match header for concurrency control."
    }

    deactivate_user: ClassVar[dict] = {
        "summary": "Purpose of this API is to deactivate user and block authentication",
        "description": "Deactivates a user by setting is_active=false, which blocks authentication. Accessible by SuperAdmin, CEO, and HR. SuperAdmin can deactivate any user across any company. CEO and HR can only deactivate users in their own company. Deactivated users retain all historical data. Users cannot deactivate their own accounts. Requires If-Match header for concurrency control."
    }

    reactivate_user: ClassVar[dict] = {
        "summary": "Purpose of this API is to reactivate user and restore authentication",
        "description": "Reactivates a user by setting is_active=true, which restores authentication. Accessible by SuperAdmin, CEO, and HR. SuperAdmin can reactivate any user across any company. CEO and HR can only reactivate users in their own company. Reactivated users do not need to reset passwords. Requires If-Match header for concurrency control."
    }

    resend_invitation: ClassVar[dict] = {
        "summary": "Purpose of this API is to resend invitation to user with new token",
        "description": "Resends an invitation to a user by generating a new invitation token and expiry (24 hours from current time). Accessible by SuperAdmin, CEO, and HR. SuperAdmin can resend invitations to any user across any company. CEO and HR can only resend invitations to users in their own company. Re-invitation is allowed for any user (even if previously activated and deactivated). Increments reinvite_count and updates last_reinvite_at. Does not change user's role, company, or is_active status."
    }
```

**Router Endpoint Pattern (REQUIRED):**
```python
from src.users.documentations.user_api_doc import UserApiDocs

@router.patch(
    "/{user_id}/role",
    response_model=StandardResponse[UserDetail],
    summary=UserApiDocs.change_user_role["summary"],
    description=UserApiDocs.change_user_role["description"]
)
async def change_user_role(...):
    """Change user role within same company."""
    pass
```

---

## 7. Business Rules & Validations

### 7.1 CEO Cardinality Rule
- **Rule**: Each company can have only one active CEO at any given time
- **Enforcement**:
  - When assigning CEO role via `PATCH /v1/users/{user_id}/role`: Check if company already has an active CEO
  - When reassigning user with CEO role via `PATCH /v1/users/{user_id}/companies/{company_id}/reassign`: Check if target company already has an active CEO
  - Exception: If the user being assigned CEO role is the current CEO, allow the change (no-op)
- **Error Response**: `422 BUSINESS_RULE_FAILED` with message about existing CEO

### 7.2 Role Change Permissions
- **SuperAdmin**: Can change any user's role across any company
- **CEO**: Can change any user's role within own company only
- **HR**: Can change any user's role within own company only
- **Manager/Employee**: Cannot change user roles
- **Self-change restriction**: Users cannot change their own role

### 7.3 Company Reassignment Rules
- **SuperAdmin only**: Only SuperAdmin can reassign users to different companies
- **SuperAdmin users**: Cannot reassign SuperAdmin users (they have null company_id)
- **Role preservation**: If role_code is not provided, user keeps current role
- **CEO cardinality**: If user has CEO role and target company already has a CEO, return error

### 7.4 Activation/Deactivation Rules
- **Deactivation**: Sets `is_active=false`, blocks authentication
- **Reactivation**: Sets `is_active=true`, restores authentication
- **Self-deactivation**: Users cannot deactivate their own accounts
- **Data retention**: Deactivated users retain all historical data
- **Password retention**: Reactivated users do not need to reset passwords

### 7.5 Re-invitation Rules
- **Eligibility**: Re-invitation is allowed for any user (even if previously activated and deactivated)
- **Token generation**: Generates new invitation token each time
- **Expiry**: Sets new expiry to 24 hours from current time
- **Count tracking**: Increments `reinvite_count` and updates `last_reinvite_at`
- **No state changes**: Re-invitation does not change role, company, or `is_active` status

---

## 8. Edge Cases & Special Scenarios

### 8.1 CEO Cardinality Edge Cases
- **Current CEO reassignment**: If current CEO is being reassigned to a different company, the original company no longer has a CEO (allowed)
- **CEO role change**: If current CEO's role is changed to non-CEO, the company no longer has a CEO (allowed)
- **Multiple CEO assignment attempt**: If trying to assign CEO role when company already has an active CEO, return `422 BUSINESS_RULE_FAILED`

### 8.2 Company Reassignment Edge Cases
- **Reassigning to same company**: If user is already in target company, operation is idempotent (returns success)
- **SuperAdmin reassignment**: Cannot reassign SuperAdmin users (they have null company_id), return `422 BUSINESS_RULE_FAILED`
- **CEO with existing CEO**: If user has CEO role and target company already has a CEO, return `422 BUSINESS_RULE_FAILED`

### 8.3 Activation/Deactivation Edge Cases
- **Already deactivated**: If user is already deactivated, operation is idempotent (returns success with is_active=false)
- **Already activated**: If user is already activated, operation is idempotent (returns success with is_active=true)
- **Self-deactivation attempt**: User cannot deactivate their own account, return `422 BUSINESS_RULE_FAILED`

### 8.4 Re-invitation Edge Cases
- **Never invited user**: If user was created without invitation (invite_at is null), first re-invitation sets invite_at
- **Previously activated user**: Re-invitation is allowed even if user was previously activated and then deactivated
- **Multiple re-invitations**: Each re-invitation increments reinvite_count and generates new token
- **Expired invitation**: Re-invitation can be sent even if previous invitation expired

### 8.5 Role Change Edge Cases
- **Self-role change**: User cannot change their own role, return `403 INSUFFICIENT_PERMISSIONS`
- **Same role assignment**: If assigning user to their current role, operation is idempotent (returns success)
- **CEO to CEO (same user)**: If current CEO is being assigned CEO role again, operation is idempotent (allowed, no-op)

---

## 9. Open Questions

None identified at this stage.

---

## 10. Assumptions

1. Re-invitation is allowed for any user (even if previously activated and deactivated)
2. Reactivated users do not need to reset passwords
3. Deactivated users retain all historical data
4. CEO cardinality rule is enforced at role assignment time (not at invitation time)
5. Users cannot change their own role
6. Users cannot deactivate their own accounts
7. SuperAdmin users cannot be reassigned to companies (they have null company_id)
8. Role changes do not affect company assignment (user remains in same company)
9. Company reassignment can optionally change role (if role_code is provided)
10. Re-invitation does not change user's role, company, or is_active status

---

**End of F-001B API Specification**

**Related:** F-001A API Specification covers core user management operations (listing, viewing, inviting, updating, reference data).

