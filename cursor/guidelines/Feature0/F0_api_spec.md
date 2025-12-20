# API Specification: F-000 — Core Platform Foundation

## 1. Overview

The Core Platform Foundation (F-000) provides the essential authentication and onboarding backbone for the officeWorld SaaS platform. This feature establishes secure user authentication, invitation-based account activation, password reset flows, and multi-tenant data isolation as the foundation for all other platform features.

### 1.1 Feature Capabilities
- **JWT-based Authentication**: Secure login/logout with role-based access tokens
- **Invitation-based Onboarding**: Time-bound token activation (24-hour expiry)
- **Password Management**: Secure password reset with email verification
- **SuperAdmin Support**: Global system user not tied to any company
- **Multi-tenant Isolation**: Company-level data access control
- **Role-based Authorization**: Predefined roles (SuperAdmin, CEO, HR, Manager, Employee)

### 1.2 Business Value
Provides a secure, consistent foundation that enables reliable user authentication and onboarding across all platform features, ensuring invitation-only access and proper data isolation.

### 1.3 Technical Scope
- Authentication endpoints (login, logout)
- User activation via invitation tokens
- Password reset with email verification
- JWT token management with role/org_id context
- Multi-tenant data isolation enforcement

**Note:** Invitation creation and user management (CRUD operations) are handled in F-001 (User & Role Management). F-000 focuses solely on the authentication foundation.

---

## 2. Global API Rules

### 2.1 Authentication

**JWT Token Structure:**
All API endpoints require JWT Bearer token authentication. Include JWT structure details here (see JWT Token Structure in Azure REST API Guidelines section).

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

---

## 3. Roles & Permissions

### 3.1 Role Definitions

#### SuperAdmin (Platform Level)
**Access Scope:** Global platform access, not tied to any company
**Capabilities:**
- Platform-wide user and company management
- View platform KPIs and company information
- Send invitations for any role across any company
- **Access denied to company-specific business data** (projects, tasks, attendance, leaves, salaries)

#### CEO (Company Admin)
**Access Scope:** Full company administration within own organization
**Capabilities:**
- All company management permissions
- Employee lifecycle management
- Project and task administration
- Approve leave requests and manage attendance

#### HR (Company Level)
**Access Scope:** Employee management and HR operations within own company
**Capabilities:**
- Employee CRUD operations
- Salary management and history
- Leave request approvals
- Attendance monitoring

#### Manager (Company Level)
**Access Scope:** Project/task management within own company
**Capabilities:**
- Project and task CRUD operations
- Task assignment with Viewer/Editor permissions
- Team performance monitoring
- Limited employee data access

#### Employee (Company Level)
**Access Scope:** Personal data and assigned tasks within own company
**Capabilities:**
- Personal profile management
- Task access based on assignments
- Leave applications and attendance marking
- View own salary information

### 3.2 Permission Inheritance
- **CEO** → Inherits Manager + Employee permissions
- **Manager** → Inherits Employee permissions
- **HR** → Inherits Employee permissions
- **No multiple roles**: Users have exactly one role per company

### 3.3 F-000 Specific Permissions
All F-000 endpoints require authentication. Permissions are role-based:

| Endpoint | SuperAdmin | CEO | HR | Manager | Employee |
|----------|------------|-----|----|---------|----------|
| POST /auth/login | ✅ | ✅ | ✅ | ✅ | ✅ |
| POST /auth/logout | ✅ | ✅ | ✅ | ✅ | ✅ |
| GET /auth/activation/{token} | ✅ | ✅ | ✅ | ✅ | ✅ |
| POST /auth/activation/{token} | ✅ | ✅ | ✅ | ✅ | ✅ |
| POST /auth/password-reset/request | ✅ | ✅ | ✅ | ✅ | ✅ |
| POST /auth/password-reset/{token} | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 4. Resources & Endpoints

### 4.1 Resource Overview

#### Authentication Resource
Represents user authentication sessions and credential management.

**Key Fields:**
- `email`: User login identifier (unique, RFC 5322 format)
- `password`: Authentication credential (hashed, minimum 8 characters, maximum 128 characters, must contain uppercase, lowercase, number, and special character)
- `is_active`: Account activation status
- `is_deleted`: Soft delete flag (authentication must fail if `true`)
- `role`: User role within company context
- `org_id`: Company identifier (nullable for SuperAdmin)
- `company_slug`: Company URL identifier (nullable for SuperAdmin)
- `company_is_active`: Company activation status (nullable for SuperAdmin)

#### Invitation Resource
Embedded lifecycle for user onboarding with time-bound tokens.

**Key Fields:**
- `invite_at`: Invitation timestamp
- `expiry`: Token expiration (24 hours from invite_at)
- `token`: Credential token for activation/reset
- `activate_at`: Account activation timestamp

#### CredentialToken Resource
Time-bound tokens for account activation and password reset.

**Key Fields:**
- `token`: Secure random token string
- `purpose`: Token purpose ("activation" or "password_reset")
- `expiry`: Token expiration timestamp
- `is_used`: Token consumption status

### 4.2 Endpoint Summary

| Method | Path | Purpose | Authentication |
|--------|------|---------|----------------|
| POST | /api/v1/auth/login | Authenticate user and return JWT token | None (public) |
| POST | /api/v1/auth/logout | Invalidate user session | Required |
| GET | /api/v1/auth/activation/{token} | Validate invitation token | None (public) |
| POST | /api/v1/auth/activation/{token} | Activate user account | None (public) |
| POST | /api/v1/auth/password-reset/request | Request password reset | None (public) |
| POST | /api/v1/auth/password-reset/{token} | Reset password with token | None (public) |

### 4.4 Documentation Classes (Rule 10 Compliance)

**AuthApiDocs Class Structure:**
```python
class AuthApiDocs:
    """API documentation for Authentication endpoints"""

    login: ClassVar[dict] = {
        "summary": "Authenticate user with email and password",
        "description": "Validates user credentials and returns JWT access token with role and organization context."
    }

    logout: ClassVar[dict] = {
        "summary": "Invalidate user session",
        "description": "Logs out the authenticated user by invalidating their session token."
    }

    get_activation: ClassVar[dict] = {
        "summary": "Validate invitation token",
        "description": "Validates invitation token and returns activation details for account setup."
    }

    activate_account: ClassVar[dict] = {
        "summary": "Activate user account",
        "description": "Completes user account activation using invitation token and provided credentials."
    }

    request_password_reset: ClassVar[dict] = {
        "summary": "Request password reset",
        "description": "Initiates password reset process by sending reset token via email."
    }

    reset_password: ClassVar[dict] = {
        "summary": "Reset user password",
        "description": "Resets user password using valid reset token and new password."
    }
```

**Router Implementation Pattern:**
```python
@router.post("/login", summary=AuthApiDocs.login["summary"], description=AuthApiDocs.login["description"])
async def login(...):
    pass
```

### 4.5 Endpoint Details

#### 4.3.1 POST /api/v1/auth/login
- **Purpose:** Authenticate user with email/password and return JWT access token
- **Authentication:** None (public endpoint)
- **Authorization / Roles:** All roles can login
- **Headers:**
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
- **Idempotency:** Not applicable
- **Business Rules:**
  - Validates user credentials (email and password)
  - Validates user account is active (`is_active = true`)
  - Validates user account is not soft-deleted (`is_deleted = false`)
  - Validates company is active (`company.is_active = true`) for non-SuperAdmin users
  - Resolves company context from UserRoleAssignment (company.slug, company.is_active)
  - Returns company slug and active status in response for frontend routing and validation

**Path Parameters**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| N/A | N/A | N/A | N/A |

**Query Parameters**
| Name | Type | Required | Default | Description |
|------|------|----------|----------|-------------|
| N/A | N/A | N/A | N/A | N/A |

**Request Body**
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| email | string | Yes | User email address | RFC 5322 format, max 254 chars, unique |
| password | string | Yes | User password | Min 8 chars, max 128 chars, uppercase + lowercase + number + special char |

**Success Response (200 OK)**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "employee",
      "org_id": "123e4567-e89b-12d3-a456-426614174000",
      "company_slug": "tech-corp",
      "company_is_active": true,
      "is_super_admin": false
    }
  },
  "message": "Login successful"
}
```
**Note:** For SuperAdmin users (`org_id: null`), `company_slug` and `company_is_active` will be `null`.
**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Error Responses**
| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | INVALID_REQUEST | Malformed request or missing required fields |
| 401 | INVALID_CREDENTIALS | Invalid email or password, or user account is soft-deleted |
| 403 | ACCOUNT_INACTIVE | User account is deactivated (`is_active = false`) |
| 403 | ACCOUNT_DELETED | User account is soft-deleted (`is_deleted = true`) |
| 403 | COMPANY_INACTIVE | User's company is inactive (`company.is_active = false`) |
| 500 | INTERNAL_ERROR | Server error during authentication |

**Validation Rules:**
- Authentication must fail if `user.is_active = false` → Return `403 ACCOUNT_INACTIVE`
- Authentication must fail if `user.is_deleted = true` → Return `403 ACCOUNT_DELETED` (or `401 INVALID_CREDENTIALS` for security)
- Authentication must fail if `company.is_active = false` (for non-SuperAdmin users) → Return `403 COMPANY_INACTIVE`
- Company context must be resolved server-side from UserRoleAssignment

**Example Error (401 UNAUTHORIZED):**
```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "details": []
  },
  "message": "Invalid email or password."
}
```

#### 4.3.2 POST /api/v1/auth/logout
- **Purpose:** Invalidate user session and logout
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** All authenticated users
- **Headers:**
  - `Authorization: Bearer <jwt_token>` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
- **Idempotency:** Idempotent (multiple calls have same effect)

**Path Parameters**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| N/A | N/A | N/A | N/A |

**Query Parameters**
| Name | Type | Required | Default | Description |
|------|------|----------|----------|-------------|
| N/A | N/A | N/A | N/A | N/A |

**Request Body**
Empty request body (logout is stateless action)

**Success Response (200 OK)**
```json
{
  "data": null,
  "message": "Logout successful"
}
```
**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Error Responses**
| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid JWT token |
| 500 | INTERNAL_ERROR | Server error during logout |

#### 4.3.3 GET /api/v1/auth/activation/{token}
- **Purpose:** Validate invitation token and retrieve activation details
- **Authentication:** None (public endpoint for invited users)
- **Authorization / Roles:** Public access for token validation
- **Headers:**
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
- **Idempotency:** Idempotent (same token always returns same validation result)

**Path Parameters**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| token | string | Yes | Invitation token | RFC 4122 UUID v4 format |

**Query Parameters**
| Name | Type | Required | Default | Description |
|------|------|----------|----------|-------------|
| N/A | N/A | N/A | N/A | N/A |

**Request Body**
Empty request body (GET request)

**Success Response (200 OK)**
```json
{
  "data": {
    "email": "user@example.com",
    "company_name": "Tech Corp",
    "role": "employee",
    "invitation_status": "valid",
    "expires_at": "2024-01-20T10:30:00Z"
  },
  "message": "Invitation token is valid"
}
```
**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Error Responses**
| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | INVALID_TOKEN | Malformed token format |
| 404 | INVITATION_NOT_FOUND | Token does not exist |
| 410 | INVITATION_EXPIRED | Token expired (24 hours from invite_at) |
| 409 | ACCOUNT_ALREADY_ACTIVATED | User already activated |
| 500 | INTERNAL_ERROR | Server error during token validation |

**Example Error (410 GONE):**
```json
{
  "error": {
    "code": "INVITATION_EXPIRED",
    "details": []
  },
  "message": "Invitation has expired. Please request a new invitation."
}
```

#### 4.3.4 POST /api/v1/auth/activation/{token}
- **Purpose:** Activate user account with name and password using invitation token
- **Authentication:** None (public endpoint for account activation)
- **Authorization / Roles:** Public access for invited users
- **Headers:**
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
- **Idempotency:** Not idempotent (single-use token)

**Path Parameters**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| token | string | Yes | Invitation token | RFC 4122 UUID v4 format |

**Query Parameters**
| Name | Type | Required | Default | Description |
|------|------|----------|----------|-------------|
| N/A | N/A | N/A | N/A | N/A |

**Request Body**
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| first_name | string | Yes | User first name | Min 1 char, max 50 chars, alphanumeric and spaces |
| last_name | string | Yes | User last name | Min 1 char, max 50 chars, alphanumeric and spaces |
| password | string | Yes | Account password | Min 8 chars, max 128 chars, uppercase + lowercase + number + special char |
| password_confirm | string | Yes | Password confirmation | Must match password field |

**Success Response (201 Created)**
```json
{
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "employee",
    "org_id": "123e4567-e89b-12d3-a456-426614174000",
    "activated_at": "2024-01-20T10:30:00Z"
  },
  "message": "Account activated successfully"
}
```
**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Error Responses**
| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | INVALID_REQUEST | Malformed request or missing required fields |
| 400 | PASSWORD_MISMATCH | Password confirmation doesn't match |
| 400 | PASSWORD_WEAK | Password doesn't meet complexity requirements |
| 404 | INVITATION_NOT_FOUND | Token does not exist |
| 410 | INVITATION_EXPIRED | Token expired (24 hours from invite_at) |
| 409 | ACCOUNT_ALREADY_ACTIVATED | User already activated |
| 422 | VALIDATION_ERROR | Field validation failed |
| 500 | INTERNAL_ERROR | Server error during activation |

**Example Error (422 Unprocessable Entity):**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "details": [
      {"field": "password", "issue": "Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character."}
    ]
  },
  "message": "Account activation failed due to validation errors."
}
```

#### 4.3.5 POST /api/v1/auth/password-reset/request
- **Purpose:** Request password reset and send email with reset token
- **Authentication:** None (public endpoint)
- **Authorization / Roles:** All users (active and inactive)
- **Headers:**
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
- **Idempotency:** Idempotent (multiple requests for same email have same effect)

**Path Parameters**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| N/A | N/A | N/A | N/A |

**Query Parameters**
| Name | Type | Required | Default | Description |
|------|------|----------|----------|-------------|
| N/A | N/A | N/A | N/A | N/A |

**Request Body**
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| email | string | Yes | User email address | RFC 5322 format, max 254 chars |

**Success Response (200 OK)**
```json
{
  "data": {
    "email": "user@example.com",
    "reset_requested": true
  },
  "message": "Password reset email sent successfully"
}
```
**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Error Responses**
| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | INVALID_REQUEST | Malformed request or missing email |
| 422 | VALIDATION_ERROR | Invalid email format |
| 500 | INTERNAL_ERROR | Server error during email sending |

**Note:** Response is identical regardless of whether email exists to prevent email enumeration attacks.

#### 4.3.6 POST /api/v1/auth/password-reset/{token}
- **Purpose:** Reset user password using reset token
- **Authentication:** None (public endpoint)
- **Authorization / Roles:** Users with valid reset tokens
- **Headers:**
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
- **Idempotency:** Not idempotent (single-use token)

**Path Parameters**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| token | string | Yes | Password reset token | RFC 4122 UUID v4 format |

**Query Parameters**
| Name | Type | Required | Default | Description |
|------|------|----------|----------|-------------|
| N/A | N/A | N/A | N/A | N/A |

**Request Body**
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| password | string | Yes | New password | Min 8 chars, max 128 chars, uppercase + lowercase + number + special char |
| password_confirm | string | Yes | Password confirmation | Must match password field |

**Success Response (200 OK)**
```json
{
  "data": {
    "email": "user@example.com",
    "password_reset": true,
    "reset_at": "2024-01-20T10:30:00Z"
  },
  "message": "Password reset successfully"
}
```
**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Error Responses**
| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | INVALID_REQUEST | Malformed request or missing required fields |
| 400 | PASSWORD_MISMATCH | Password confirmation doesn't match |
| 400 | PASSWORD_WEAK | Password doesn't meet complexity requirements |
| 404 | RESET_TOKEN_NOT_FOUND | Token does not exist |
| 410 | RESET_TOKEN_EXPIRED | Token expired (24 hours from request) |
| 409 | RESET_TOKEN_USED | Token already used |
| 422 | VALIDATION_ERROR | Field validation failed |
| 500 | INTERNAL_ERROR | Server error during password reset |

---

## Query Schema Classes

All query parameters must use schema classes with `Depends()` pattern. **F-000 does not include query parameters** - all endpoints are simple POST/GET operations for authentication flows, so query schema classes are not required.

---

## 5. Webhooks / Async Behavior

F-000 does not include webhooks or complex async operations. All authentication operations are synchronous.

**Email Delivery:** Password reset and invitation emails are sent asynchronously via background job queue to ensure reliable delivery without blocking API responses.

---

## 6. Rate Limiting & Performance

### 6.1 Rate Limits
- **Authentication endpoints**: 5 attempts per minute per IP address
- **Password reset request**: 3 requests per hour per email address
- **Token validation**: 10 requests per minute per token
- **General API**: 100 requests per minute per authenticated user

### 6.2 Performance Considerations
- JWT token validation cached in Redis for sub-second performance
- Password hashing uses bcrypt with appropriate cost factor
- Token validation queries optimized with database indexes
- Email delivery handled asynchronously to prevent response delays

---

## 7. Open Questions

1. **Token Refresh Mechanism**: Should F-000 include refresh token endpoints, or will this be handled in a separate authentication service?

2. **Password Complexity Rules**: What are the exact password requirements (special characters, length, etc.)?

3. **Email Template Management**: How will invitation and password reset email templates be managed and customized?

4. **Audit Logging**: Should F-000 include authentication audit logging, or is this handled at the infrastructure level?

---

## 8. Assumptions

1. **Email Delivery**: Email service is reliable and configured at the infrastructure level
2. **Token Security**: UUID v4 tokens provide sufficient entropy for security
3. **Password Storage**: Bcrypt hashing is used for password storage
4. **Session Management**: Stateless JWT-based authentication (no server-side sessions)
5. **Multi-tenancy**: Company isolation enforced at the application level via org_id claims
6. **Role Seeding**: Roles and permissions are pre-seeded at platform bootstrap
7. **SuperAdmin Creation**: Initial SuperAdmin user is created via database seeding or manual setup
8. **Invitation Expiry**: 24-hour expiry is sufficient for invitation tokens
9. **No MFA**: Multi-factor authentication is out of scope for F-000
10. **No Social Login**: Only email/password authentication supported
