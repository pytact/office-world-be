# API Specification: F-011 — Audit Logging & Activity History

## 1. Overview

### 1.1 Feature Summary

The Audit Logging & Activity History feature provides a centralized, immutable, company-scoped record of critical system and user actions across all platform features. It supports governance, compliance, and traceability through read-only audit views with strict role-based visibility, while remaining asynchronous and non-blocking to business workflows.

### 1.2 Key Characteristics

- **Immutable**: Audit logs are append-only and cannot be edited or deleted
- **Company-Scoped**: All audit logs are strictly scoped to the authenticated user's company (from JWT `org_id` claim)
- **Read-Only API**: UI never creates, edits, or deletes audit records (system-generated only)
- **Asynchronous**: Audit logging is non-blocking and does not impact business operations
- **Role-Based Visibility**: Different roles see different subsets of audit logs based on business rules

### 1.3 Purpose

Provide a comprehensive audit trail for:
- Security and compliance requirements
- Incident investigation and verification
- Accountability and governance
- Traceability of critical actions across all features

---

## 2. Global API Rules

### 2.1 Authentication

**JWT Token Structure:**
All API endpoints require JWT Bearer token authentication.

**Token Format**: `Authorization: Bearer <jwt_token>`

**Required Claims in JWT Payload:**
- `sub` (subject): User ID (string, UUID format) - **REQUIRED**
- `role`: User role (string) - **REQUIRED** - Encoded in token, not database lookup
- `org_id`: Organization ID (string, UUID format, nullable) - **REQUIRED** - `null` for SuperAdmin, UUID for org-scoped users
- `exp`: Token expiration timestamp (integer, Unix timestamp) - **REQUIRED**
- `iat`: Token issued at timestamp (integer, Unix timestamp) - **RECOMMENDED**
- `jti`: JWT ID (string, unique token identifier) - **RECOMMENDED** for token revocation

**Example JWT Payload:**
```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "role": "ceo",
  "org_id": "770e8400-e29b-41d4-a716-446655440001",
  "exp": 1735689600,
  "iat": 1735686000,
  "jti": "jwt_abc123xyz789"
}
```

**Role Encoding:**
- Roles MUST be encoded in JWT token (not database lookup during request)
- Role values: Use lowercase (e.g., `"ceo"`, `"hr"`, `"manager"`, `"employee"`)
- Organization-scoped roles: `org_id` MUST contain organization UUID
- SuperAdmin role: `org_id` MUST be `null` (indicates global access) - **Out of scope for this feature**

**Token Validation:**
- Server MUST validate token signature, expiration, and required claims
- Missing or invalid token: Return `401 UNAUTHENTICATED`
- Missing required claims: Return `401 UNAUTHENTICATED` with error code `INVALID_TOKEN`
- Expired token: Return `401 UNAUTHENTICATED` with error code `TOKEN_EXPIRED`

### 2.2 Company Scoping

- **Company Context**: All audit log operations are scoped to the authenticated user's company
- **Company Extraction**: Company is determined from JWT `org_id` claim
- **SuperAdmin Restriction**: SuperAdmin (`org_id: null`) must be blocked from accessing audit logs (out of scope)

### 2.3 Response Format

**Success Response (200 OK):**
```json
{
  "data": { ... },
  "message": "Operation completed successfully"
}
```

**Error Response (400/401/403/404/etc.):**
```json
{
  "error": {
    "code": "ERROR_CODE",
    "details": [{"field": "field_name", "issue": "Error description"}]
  },
  "message": "Human-friendly error message"
}
```

**Response Headers (REQUIRED):**
- `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**

**Note:**
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.

### 2.4 UTC Timezone Standard

All datetime fields MUST use UTC timezone (ISO 8601 format with `Z` suffix):
- Example: `2024-01-20T10:30:00Z`
- Query parameters for date filtering: ISO 8601 datetime with UTC (e.g., `2024-01-20T10:30:00Z`)

---

## 3. Roles & Permissions

### 3.1 Role-Based Access Control

| Role | Access Level | Visibility Scope |
|------|-------------|------------------|
| **CEO** | Full read access | All audit logs within their company |
| **HR** | Full read access | All audit logs within their company |
| **Manager** | Limited read access | Only audit logs where `table_name` ∈ {`tasks`, `projects`, `task_assignments`} |
| **Employee** | No access | Cannot access any audit logs |
| **SuperAdmin** | Blocked | Out of scope - must return 403 INSUFFICIENT_PERMISSIONS |

### 3.2 Visibility Rules

**CEO and HR:**
- Can view all audit logs within their company
- No filtering restrictions beyond company scope

**Manager:**
- Can view audit logs where `table_name` is one of:
  - `tasks`
  - `projects`
  - `task_assignments`
- Server MUST enforce this filter - Managers attempting to access logs outside this scope must receive 403 INSUFFICIENT_PERMISSIONS

**Employee:**
- No access to audit logs
- All requests must return 403 INSUFFICIENT_PERMISSIONS

**SuperAdmin:**
- Out of scope for this feature
- All requests must return 403 INSUFFICIENT_PERMISSIONS

### 3.3 Row-Level Security (RLS)

- **Company Scoping**: All audit log queries MUST be filtered by company (from JWT `org_id` claim)
- **Role-Based Filtering**: Manager role MUST have additional filter applied for `table_name` restriction
- **Server-Side Enforcement**: Visibility rules MUST be enforced server-side, not client-side

---

## 4. Resources & Endpoints

### 4.1 Resource Overview

#### AuditLog Resource

Represents an immutable, append-only record capturing a meaningful action performed within the system. Audit logs are written asynchronously and never block business operations.

**Key Fields:**
- `id` (UUID): Unique audit log identifier
- `actor_id` (UUID, nullable): User ID who performed the action (null for SYSTEM actions)
- `actor` (object, nullable): Actor information (user details and role) - null for SYSTEM actions
- `company_id` (UUID): Company identifier (mandatory)
- `action_code` (string): Free-text action identifier (feature-defined, e.g., `TASK_UPDATED`, `USER_INVITED`)
- `table_name` (string): Affected entity/table name (reference only, e.g., `tasks`, `users`, `employees`)
- `record_id` (UUID, nullable): Identifier of affected record (reference only)
- `old_values` (object, nullable): Changed fields before action (partial snapshot - only changed fields)
- `new_values` (object, nullable): Changed fields after action (partial snapshot - only changed fields)
- `ip_address` (string, nullable): Source IP address
- `user_agent` (string, nullable): Client metadata
- `description` (string, nullable): Human-readable summary
- `created_at` (datetime, UTC): Action timestamp (immutable)

**Field Categories:**
- **Immutable Fields**: All fields are immutable (audit logs are append-only)
- **Actor Information**: `actor_id` and `actor` are null for SYSTEM-generated actions
- **Value Snapshots**: `old_values` and `new_values` contain only changed fields (not full object snapshots)
- **Company Scoping**: `company_id` is mandatory and determines visibility scope

**Relationships:**
- Belongs to Company (1..*)
- Has Actor (User or SYSTEM) (0..*)

**Derived Fields:**
- `actor_display_name` (string): Human-readable actor name (e.g., "Jane Doe (HR)" or "SYSTEM")
- `has_value_changes` (boolean): True when `old_values` or `new_values` are non-empty

**ActionCode Examples:**
- `USER_INVITED`
- `ROLE_ASSIGNED`
- `TASK_CREATED`
- `TASK_UPDATED`
- `TASK_DELETED`
- `LEAVE_APPROVED`
- `SALARY_UPDATED`
- `ATTENDANCE_CHECK_IN`
- `SYSTEM_AUTO_CHECK_OUT`

**Value Storage Rules:**
- Only changed fields are stored in `old_values` / `new_values`
- No full object snapshots
- Format: JSON object (e.g., `{"status": "TODO", "priority": "high"}`)

### 4.2 Endpoint Summary

| Method | Path | Purpose | Authentication |
|--------|------|---------|----------------|
| GET | `/api/v1/company/audit-logs` | List audit logs with pagination, filtering, and sorting | Required |
| GET | `/api/v1/company/audit-logs/{audit_log_id}` | Get detailed audit log information | Required |

**Note:** All endpoints are read-only. Audit logs are system-generated only. UI never creates, edits, or deletes audit records.

### 4.3 API Documentation Class (Rule 10)

**Note:** All endpoint documentation MUST use the centralized `AuditLogApiDocs` class structure (Rule 10). Router endpoints MUST reference `summary` and `description` from this class, NOT hardcoded strings.

**Documentation Class Structure:**

```python
# src/audit_logs/documentations/audit_log_api_doc.py
from typing import ClassVar

class AuditLogApiDocs:
    """API documentation for AuditLog endpoints"""
    
    list: ClassVar[dict] = {
        "summary": "Purpose of this API is to list audit logs with pagination, filtering, and sorting",
        "description": "Retrieves a paginated list of audit logs for the authenticated user's company. Supports filtering by date range, action_code, and table_name. Supports sorting by created_at (default descending). CEO and HR see all company audit logs. Manager sees only logs where table_name is tasks, projects, or task_assignments. Employee role has no access. SuperAdmin is blocked. Company is determined from JWT org_id claim. Requires JWT authentication."
    }
    
    get: ClassVar[dict] = {
        "summary": "Purpose of this API is to get detailed audit log information",
        "description": "Retrieves detailed information for a specific audit log including old_values, new_values, IP address, and user agent. CEO and HR can access any company audit log. Manager can only access logs where table_name is tasks, projects, or task_assignments (returns 403 if outside scope). Employee role has no access. SuperAdmin is blocked. Company is determined from JWT org_id claim. Requires JWT authentication."
    }
```

**Router Endpoint Pattern (REQUIRED):**

```python
# src/audit_logs/routers.py
from src.audit_logs.documentations.audit_log_api_doc import AuditLogApiDocs

@router.get(
    "",
    response_model=StandardResponse[AuditLogPaginatedResponse[AuditLogSummary]],
    summary=AuditLogApiDocs.list["summary"],
    description=AuditLogApiDocs.list["description"]
)
async def list_audit_logs(...):
    """List audit logs with pagination, filtering, and sorting."""
    pass

@router.get(
    "/{audit_log_id}",
    response_model=StandardResponse[AuditLogDetail],
    summary=AuditLogApiDocs.get["summary"],
    description=AuditLogApiDocs.get["description"]
)
async def get_audit_log(...):
    """Get detailed audit log information."""
    pass
```

### 4.4 Endpoint Details

#### 4.4.1 GET /api/v1/company/audit-logs

- **Purpose:** List audit logs with pagination, filtering, and sorting for the authenticated user's company
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, HR (all logs), Manager (filtered by table_name), Employee (no access), SuperAdmin (blocked)
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
class AuditLogListQuery(BaseModel):
    """Query schema for listing audit logs with pagination and filtering."""

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    start_date: Optional[str] = Field(None, description="Filter by start date (ISO 8601 datetime with UTC, e.g., 2024-01-20T10:30:00Z)")
    end_date: Optional[str] = Field(None, description="Filter by end date (ISO 8601 datetime with UTC, e.g., 2024-01-20T10:30:00Z)")
    action_code: Optional[str] = Field(None, description="Filter by action code (exact match, case-sensitive)")
    table_name: Optional[str] = Field(None, description="Filter by table name (exact match, case-sensitive)")
    sort_by: str = Field("created_at", description="Sort field: created_at (only allowed field)")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)
```

**Router Endpoint Pattern (REQUIRED):**
```python
@router.get("", response_model=StandardResponse[AuditLogPaginatedResponse[AuditLogSummary]])
async def list_audit_logs(
    query: AuditLogListQuery = Depends(AuditLogListQuery),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List audit logs with pagination, filtering, and sorting."""
    # Access via query.page, query.page_size, query.start_date, etc.
```

**Query Parameters Table (for documentation only):**

| Name | Type | Required | Default | Description | Validation |
|------|------|----------|---------|-------------|------------|
| page | integer | No | 1 | Page number | ≥ 1 |
| page_size | integer | No | 20 | Page size | 1-100 |
| start_date | string | No | null | Filter by start date | ISO 8601 datetime with UTC (Z suffix), e.g., 2024-01-20T10:30:00Z |
| end_date | string | No | null | Filter by end date | ISO 8601 datetime with UTC (Z suffix), e.g., 2024-01-20T10:30:00Z |
| action_code | string | No | null | Filter by action code | Exact match, case-sensitive |
| table_name | string | No | null | Filter by table name | Exact match, case-sensitive |
| sort_by | string | No | created_at | Sort field | Enum: "created_at" (only allowed field) |
| sort_order | string | No | desc | Sort order | Enum: "asc" or "desc" |

**Query Parameter Validation:**
- `start_date` and `end_date`: Must be valid ISO 8601 datetime with UTC timezone (Z suffix). If both provided, `start_date` must be ≤ `end_date`.
- `action_code`: Case-sensitive exact match against stored action codes
- `table_name`: Case-sensitive exact match against stored table names
- `sort_by`: Only `created_at` is allowed (audit logs must always be ordered by created_at per UI data contract)
- `sort_order`: Must be `asc` or `desc` (default: `desc`)

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "action_code": "TASK_UPDATED",
        "table_name": "tasks",
        "record_id": "660e8400-e29b-41d4-a716-446655440001",
        "description": "Task status updated from TODO to IN_PROGRESS",
        "created_at": "2024-01-20T10:30:00Z",
        "actor": {
          "id": "770e8400-e29b-41d4-a716-446655440002",
          "first_name": "Jane",
          "last_name": "Doe",
          "role_code": "hr"
        },
        "actor_display_name": "Jane Doe (HR)"
      },
      {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "action_code": "SYSTEM_AUTO_CHECK_OUT",
        "table_name": "attendance",
        "record_id": "660e8400-e29b-41d4-a716-446655440004",
        "description": "Automatic check-out at end of day",
        "created_at": "2024-01-20T18:00:00Z",
        "actor": null,
        "actor_display_name": "SYSTEM"
      }
    ],
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8,
    "next_page": "/api/v1/company/audit-logs?page=2&page_size=20&sort_by=created_at&sort_order=desc&start_date=2024-01-20T00:00:00Z&end_date=2024-01-20T23:59:59Z",
    "prev_page": null
  },
  "message": "Audit logs retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- For paginated responses, `next_page` and `prev_page` should include all query parameters (filters, sort, search) to preserve pagination state.
- `actor` is null for SYSTEM-generated actions, and `actor_display_name` will be "SYSTEM" in such cases.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 Bad Request | `VALIDATION_FAILED` | Invalid query parameter format (e.g., invalid date format, invalid sort_by value) |
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid JWT token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 401 Unauthorized | `INVALID_TOKEN` | JWT token missing required claims |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User role does not have access (Employee, SuperAdmin, or Manager accessing non-allowed table_name) |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during audit log retrieval |

**Example Error Response (400 Bad Request - Validation Failed):**
```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "details": [
      {"field": "start_date", "issue": "Invalid date format. Must be ISO 8601 datetime with UTC (e.g., 2024-01-20T10:30:00Z)."},
      {"field": "sort_by", "issue": "Invalid sort field. Only 'created_at' is allowed."}
    ]
  },
  "message": "Query parameter validation failed."
}
```

**Example Error Response (403 Forbidden - Insufficient Permissions):**
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "details": [{"field": "role", "issue": "Employee role does not have access to audit logs."}]
  },
  "message": "You do not have permission to access audit logs."
}
```

**Example Error Response (403 Forbidden - Manager Access Restriction):**
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "details": [{"field": "table_name", "issue": "Manager role can only access audit logs for tasks, projects, or task_assignments."}]
  },
  "message": "You do not have permission to access audit logs for this table."
}
```

#### 4.4.2 GET /api/v1/company/audit-logs/{audit_log_id}

- **Purpose:** Get detailed audit log information including old_values, new_values, IP address, and user agent
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, HR (all logs), Manager (only if table_name allowed), Employee (no access), SuperAdmin (blocked)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-None-Match: "20240120T103000Z"` (optional, for cache validation - returns 304 if unchanged)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
    - `ETag: "20240120T103000Z"` (REQUIRED - resource version identifier based on `created_at` for cache validation)
    - `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (RECOMMENDED)
- **Idempotency:** Yes (GET operation)

**Path Parameters**

| Name | Type | Required | Description | Validation |
|------|------|----------|-------------|------------|
| audit_log_id | string (UUID) | Yes | Audit log identifier | RFC 4122 UUID v4 format |

**Note:** All path parameters MUST use snake_case (e.g., `audit_log_id`) - see Rule 2.

**Query Parameters**  
None

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "action_code": "TASK_UPDATED",
    "table_name": "tasks",
    "record_id": "660e8400-e29b-41d4-a716-446655440001",
    "description": "Task status updated from TODO to IN_PROGRESS",
    "old_values": {
      "status": "TODO",
      "priority": "low"
    },
    "new_values": {
      "status": "IN_PROGRESS",
      "priority": "high"
    },
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "created_at": "2024-01-20T10:30:00Z",
    "actor": {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "first_name": "Jane",
      "last_name": "Doe",
      "role_code": "hr"
    },
    "actor_display_name": "Jane Doe (HR)",
    "has_value_changes": true
  },
  "message": "Audit log retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103000Z"` (REQUIRED - resource version identifier based on `created_at` for cache validation)
- `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (RECOMMENDED)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- `old_values` and `new_values` are JSON objects containing only changed fields (not full object snapshots).
- `old_values` and `new_values` may be null if no field changes occurred.
- `ip_address` and `user_agent` may be null if not captured.
- `actor` is null for SYSTEM-generated actions, and `actor_display_name` will be "SYSTEM" in such cases.
- `has_value_changes` is true when `old_values` or `new_values` are non-empty.
- Sensitive fields (e.g., salary, bank info) may be masked at presentation layer before returning to UI.

**Conditional GET (304 Not Modified):**
If request includes `If-None-Match: "20240120T103000Z"` header and ETag matches current resource version, return:
- HTTP Status: `304 Not Modified`
- Response Body: None
- Response Headers: `X-Request-ID` (REQUIRED)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid JWT token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 401 Unauthorized | `INVALID_TOKEN` | JWT token missing required claims |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User role does not have access (Employee, SuperAdmin, or Manager accessing non-allowed table_name) |
| 404 Not Found | `AUDIT_LOG_NOT_FOUND` | Audit log not found or does not belong to user's company |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during audit log retrieval |

**Example Error Response (403 Forbidden - Manager Access Restriction):**
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "details": [{"field": "audit_log", "issue": "Manager role can only access audit logs for tasks, projects, or task_assignments. This audit log is for table 'employees'."}]
  },
  "message": "You do not have permission to access this audit log."
}
```

**Example Error Response (404 Not Found):**
```json
{
  "error": {
    "code": "AUDIT_LOG_NOT_FOUND",
    "details": [{"field": "audit_log_id", "issue": "Audit log not found or does not belong to your company."}]
  },
  "message": "Audit log not found."
}
```

---

## 5. Response Schema Details

### 5.1 AuditLogSummary (List Response)

Used in paginated list responses.

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| id | string (UUID) | Yes | Audit log identifier | RFC 4122 UUID v4 format |
| action_code | string | Yes | Action identifier | Free-text, feature-defined |
| table_name | string | Yes | Affected table name | Reference only |
| record_id | string (UUID, nullable) | No | Affected record identifier | RFC 4122 UUID v4 format (nullable) |
| description | string (nullable) | No | Human-readable summary | Optional |
| created_at | string (datetime) | Yes | Action timestamp | ISO 8601 format, UTC timezone (Z suffix) |
| actor | object (nullable) | No | Actor information | Null for SYSTEM actions |
| actor_display_name | string | Yes | Human-readable actor name | Derived field: "FirstName LastName (Role)" or "SYSTEM" |

**Actor Object (nullable):**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string (UUID) | Yes | User ID |
| first_name | string | Yes | User first name |
| last_name | string | Yes | User last name |
| role_code | string | Yes | Role code (e.g., "ceo", "hr", "manager") |

### 5.2 AuditLogDetail (Detail Response)

Used in single audit log detail responses.

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| id | string (UUID) | Yes | Audit log identifier | RFC 4122 UUID v4 format |
| action_code | string | Yes | Action identifier | Free-text, feature-defined |
| table_name | string | Yes | Affected table name | Reference only |
| record_id | string (UUID, nullable) | No | Affected record identifier | RFC 4122 UUID v4 format (nullable) |
| description | string (nullable) | No | Human-readable summary | Optional |
| old_values | object (nullable) | No | Changed fields before action | JSON object, only changed fields |
| new_values | object (nullable) | No | Changed fields after action | JSON object, only changed fields |
| ip_address | string (nullable) | No | Source IP address | Optional |
| user_agent | string (nullable) | No | Client metadata | Optional |
| created_at | string (datetime) | Yes | Action timestamp | ISO 8601 format, UTC timezone (Z suffix) |
| actor | object (nullable) | No | Actor information | Null for SYSTEM actions |
| actor_display_name | string | Yes | Human-readable actor name | Derived field: "FirstName LastName (Role)" or "SYSTEM" |
| has_value_changes | boolean | Yes | Indicates if values changed | Derived field: true when old_values or new_values are non-empty |

**Actor Object (nullable):**
Same structure as AuditLogSummary actor object.

**old_values and new_values:**
- Format: JSON object (e.g., `{"status": "TODO", "priority": "high"}`)
- Content: Only changed fields (not full object snapshots)
- Nullable: May be null if no field changes occurred
- Sensitive fields: May be masked at presentation layer before returning to UI

### 5.3 Pagination Response Structure

**AuditLogPaginatedResponse:**
```json
{
  "items": [AuditLogSummary, ...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8,
  "next_page": "/api/v1/company/audit-logs?page=2&page_size=20&sort_by=created_at&sort_order=desc",
  "prev_page": null
}
```

**Pagination Fields:**
- `items`: Array of AuditLogSummary objects
- `total`: Total number of audit logs across all pages
- `page`: Current page number
- `page_size`: Number of items per page
- `total_pages`: Total number of pages
- `next_page`: Full relative URL for next page (includes all query parameters) or `null` if no next page
- `prev_page`: Full relative URL for previous page (includes all query parameters) or `null` if no previous page

---

## 6. Business Rules & Constraints

### 6.1 Immutability

- **BR-1101**: Audit logs are append-only and immutable
  - Audit logs cannot be edited
  - Audit logs cannot be deleted
  - Audit logs are permanently retained

### 6.2 Asynchronous Processing

- **BR-1102**: Audit logging is asynchronous and non-blocking
  - Audit logs are written asynchronously
  - Failure to log does NOT fail the originating action
  - Audit logging must not impact system performance

### 6.3 Value Storage

- **BR-1103**: Only changed fields are stored in values
  - `old_values` and `new_values` contain only changed fields
  - No full object snapshots are stored

### 6.4 Company Scoping

- **BR-1104**: Audit logs are strictly company-scoped
  - All audit log queries MUST be filtered by company (from JWT `org_id` claim)
  - Cross-company or global audit views are out of scope

### 6.5 Visibility Restrictions

- **BR-1105**: Managers have limited audit visibility
  - Managers can only view audit logs where `table_name` ∈ {`tasks`, `projects`, `task_assignments`}
  - Server MUST enforce this restriction

### 6.6 SuperAdmin Restriction

- SuperAdmin role (`org_id: null`) is out of scope for this feature
- All SuperAdmin requests must return 403 INSUFFICIENT_PERMISSIONS

---

## 7. Edge Cases & Special Scenarios

### 7.1 SYSTEM-Generated Audit Logs

- `actor_id` and `actor` are null for SYSTEM-generated actions
- `actor_display_name` must be "SYSTEM" for SYSTEM actions
- Example: `SYSTEM_AUTO_CHECK_OUT`, `SYSTEM_SCHEDULED_TASK`

### 7.2 Deleted Record References

- Audit logs may reference records that have been deleted
- `record_id` may point to a non-existent record
- This is acceptable - audit logs preserve historical references

### 7.3 Manager Access Attempts

- Manager attempting to access audit log with `table_name` outside allowed scope
- Must return 403 INSUFFICIENT_PERMISSIONS
- Error message must clearly indicate the restriction

### 7.4 High-Volume Audit Periods

- Pagination is required for high-volume periods
- Default `page_size` is 20, maximum is 100
- Server-side pagination ensures performance

### 7.5 Sensitive Field Masking

- Sensitive fields (e.g., salary, bank info) may be masked at presentation layer
- Masked fields in `old_values` and `new_values` may result in partial data
- Masking is implementation-specific and not part of API contract

### 7.6 Concurrent Actions

- Multiple actions may generate audit logs with near-identical timestamps
- Sorting by `created_at` (with optional secondary sort by `id`) ensures consistent ordering

### 7.7 Direct URL Access

- Manager accessing audit log detail via direct URL for non-allowed table_name
- Must return 403 INSUFFICIENT_PERMISSIONS
- Server MUST validate access even for direct URL access

---

## 8. ETags & Conditional Requests (Rule 8)

### 8.1 ETag Generation

- **ETag MUST be based on `created_at` timestamp** (since audit logs are immutable)
- **Format**: Convert `created_at` timestamp to ETag format (e.g., `"20240120T103000Z"`)
- **ETag changes**: ETag changes only if `created_at` changes (which should never happen for immutable resources, but included for cache validation)

### 8.2 Conditional GET Requests

- GET requests MAY include `If-None-Match` header with ETag value from previous GET
- If ETag matches current resource version: Return `304 Not Modified` (no response body)
- If ETag doesn't match: Return `200 OK` with full resource data and new ETag
- Purpose: Saves bandwidth for unchanged resources

### 8.3 ETag Requirements

- GET responses MUST include `ETag` header with resource version identifier (based on `created_at`)
- GET responses SHOULD include `Last-Modified` header with `created_at` timestamp
- GET requests MAY include `If-None-Match` header for cache validation

**Example Flow:**
1. Client GET `/api/v1/company/audit-logs/123` → Receives `ETag: "20240120T103000Z"` and resource data
2. Client caches resource and ETag
3. Client GET with `If-None-Match: "20240120T103000Z"` → 304 Not Modified (no body, saves bandwidth)
4. Resource is immutable, so ETag should never change, but cache validation still works

---

## 9. Rate Limiting & Performance

### 9.1 Performance Considerations

- Audit log queries may involve large datasets
- Server-side pagination is required (default: 20 items per page, max: 100)
- Filtering by date range, action_code, and table_name should be indexed for performance
- Company scoping and role-based filtering must be efficient

### 9.2 Rate Limiting

- Standard rate limiting applies (if implemented)
- No special rate limiting requirements for audit log endpoints

---

## 10. Open Questions

None identified at this stage.

---

## 11. Assumptions

1. **Audit logs are for governance and diagnostics only** - No UI-based editing or export is required initially
2. **System actions use a virtual SYSTEM actor** - SYSTEM-generated actions have null `actor_id` and `actor`
3. **Cross-company or global audit views are out of scope** - All audit logs are company-scoped
4. **Sensitive fields may be masked at presentation layer** - Masking is implementation-specific
5. **Audit logs are retained indefinitely** - No retention policy or deletion mechanism
6. **SuperAdmin is out of scope** - SuperAdmin must be blocked from accessing audit logs
7. **All datetime fields use UTC timezone** - ISO 8601 format with Z suffix
8. **old_values and new_values are JSON objects** - Not JSON strings, containing only changed fields

---

## 12. Dependencies

This feature depends on:
- **F-001** — User & Role Management (for actor information)
- **F-002** — RBAC & Permission Engine (for role-based access control)
- **F-004** — Platform Company Management (for company scoping)
- **F-005** — Employee Management (for employee-related audit logs)
- **F-006** — Salary & History Management (for salary-related audit logs)
- **F-007** — Project Management (for project-related audit logs)
- **F-008** — Task Management & Assignment (for task-related audit logs)
- **F-009** — Leave Management Workflow (for leave-related audit logs)
- **F-010** — Attendance Management (for attendance-related audit logs)

**Note:** This feature acts as a consumer of audit events from all other features (F-001 through F-010). The API endpoints defined here are read-only and do not create audit logs. Audit logs are created asynchronously by other features when significant actions occur.

