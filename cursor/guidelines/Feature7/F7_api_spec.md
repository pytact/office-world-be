# API Specification: F-007 — Project Management

## 1. Overview

This API specification defines the RESTful endpoints for the Project Management feature (F-007). Projects are lightweight, company-scoped containers used to organize tasks into initiatives. Projects do not manage explicit membership or permissions; visibility and access are derived entirely from task associations.

**Key Characteristics:**
- Company-scoped projects (company context from JWT token `company_id`)
- Role-based visibility: CEO/Manager/HR see all projects; Employees see only projects with assigned tasks
- Lifecycle management through status (ACTIVE, INACTIVE, COMPLETED)
- Soft delete with cascade to associated tasks (IsDeleted marker)
- Task summaries included in project detail responses (read-only, from F-008)

**Feature Dependencies:**
- F-002 — RBAC & Permission Engine
- F-008 — Task Management & Assignment

---

## 2. Global API Rules

### 2.1 Authentication

**JWT Token Structure:**
All API endpoints require JWT Bearer token authentication.

**Token Format:** `Authorization: Bearer <jwt_token>`

**Required Claims in JWT Payload:**
- `sub` (subject): User ID (string, UUID format) - **REQUIRED**
- `role`: User role (string) - **REQUIRED** - Encoded in token, not database lookup
- `company_id`: Company ID (string, UUID format, nullable) - **REQUIRED** - `null` for SuperAdmin, UUID for company-scoped users
- `exp`: Token expiration timestamp (integer, Unix timestamp) - **REQUIRED**
- `iat`: Token issued at timestamp (integer, Unix timestamp) - **RECOMMENDED**
- `jti`: JWT ID (string, unique token identifier) - **RECOMMENDED** for token revocation

**JWT Payload Structure:**
```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "role": "ceo",
  "company_id": "660e8400-e29b-41d4-a716-446655440001",
  "exp": 1735689600,
  "iat": 1735686000,
  "jti": "jwt_abc123xyz789"
}
```

**Role Encoding:**
- Roles MUST be encoded in JWT token (not database lookup during request)
- Role values: Use lowercase (e.g., `"ceo"`, `"manager"`, `"hr"`, `"employee"`)
- Company-scoped roles: `company_id` MUST contain company UUID
- Token expiration: 15 minutes to 1 hour for access tokens

**Token Validation:**
- Server MUST validate token signature, expiration, and required claims
- Missing or invalid token: Return `401 UNAUTHENTICATED`
- Missing required claims: Return `401 UNAUTHENTICATED` with error code `INVALID_TOKEN`
- Expired token: Return `401 UNAUTHENTICATED` with error code `TOKEN_EXPIRED`

**Multi-Tenancy from Token:**
- Company context extracted from JWT token `company_id` claim
- All project operations are scoped to the user's company
- Cross-company access is prevented by authorization checks

### 2.2 Response Format

**Success Response (200/201):**
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
- `ETag`: Resource version identifier based on `updated_at` (for GET responses of resources that support updates)
- `Last-Modified`: Timestamp of last modification from `updated_at` field (for GET responses, optional)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.

### 2.3 Conditional Requests (ETags)

**ETag Generation:**
- ETag MUST be based on `updated_at` timestamp
- Format: Convert `updated_at` timestamp to ETag format (e.g., `"20240120T103000Z"`)
- ETag changes whenever `updated_at` changes

**ETag Requirements:**
- GET responses MUST include `ETag` header with resource version identifier (based on `updated_at`)
- GET responses SHOULD include `Last-Modified` header with `updated_at` timestamp
- PATCH/DELETE requests SHOULD include `If-Match` header with ETag value from GET
- GET requests MAY include `If-None-Match` header with ETag value for cache validation
- Server MUST return `412 Precondition Failed` if ETag doesn't match current resource version (for If-Match)
- Server MUST return `304 Not Modified` if ETag matches current resource version (for If-None-Match)

---

## 3. Roles & Permissions

### 3.1 Role Definitions

| Role | Description | Project Access |
|------|-------------|----------------|
| CEO | Chief Executive Officer | Full access: create, read, update, delete all company projects |
| Manager | Project/Team Manager | Full access: create, read, update, delete all company projects |
| HR | Human Resources | Read-only access: view all company projects (cannot modify) |
| Employee | Regular Employee | Read-only access: view only projects where they have assigned tasks |

### 3.2 Permission Matrix

| Operation | CEO | Manager | HR | Employee |
|-----------|-----|---------|----|----------| 
| List Projects | ✅ All | ✅ All | ✅ All | ✅ Assigned only |
| Create Project | ✅ | ✅ | ❌ | ❌ |
| Get Project Detail | ✅ All | ✅ All | ✅ All | ✅ If has tasks |
| Update Project | ✅ | ✅ | ❌ | ❌ |
| Delete Project | ✅ | ✅ | ❌ | ❌ |

### 3.3 Visibility Rules

**CEO / Manager / HR:**
- See all projects within their company
- No filtering based on task assignment

**Employee:**
- See only projects where they have at least one assigned task
- Projects with zero tasks assigned to the employee are hidden
- If all assigned tasks are removed from a project, the project disappears from the employee's view

**Company Scoping:**
- All operations are scoped to the company from JWT token `company_id`
- Users cannot access projects from other companies
- Cross-company access attempts return `403 INSUFFICIENT_PERMISSIONS` or `404 PROJECT_NOT_FOUND`

---

## 4. Resources & Endpoints

### 4.1 Resource Overview

**Project Resource:**
- Represents a company-scoped container for organizing tasks
- No explicit membership or permissions
- Visibility derived from task associations
- Lifecycle controlled by status (ACTIVE, INACTIVE, COMPLETED)

**Key Fields:**
- `id`: UUID identifier
- `company_id`: Owning company (from JWT token, not in request/response)
- `name`: Project name (company-unique, case-insensitive)
- `status`: Lifecycle state (ACTIVE, INACTIVE, COMPLETED)
- `is_deleted`: Soft delete marker (not exposed in API responses)
- `task_count`: Aggregated count of associated tasks (derived field)
- `created_at`, `updated_at`: Audit timestamps (UTC)
- `created_by`, `updated_by`: Audit user references (UUID)

**Status Semantics:**
- **ACTIVE**: Project is editable; tasks can be added, moved, or removed
- **INACTIVE**: Project is frozen; no task changes allowed
- **COMPLETED**: Project is frozen and read-only; retained for reference

**Task Summaries (Nested):**
- Included in project detail responses
- Read-only data from F-008 (Task Management)
- Fields: `id`, `title`, `status`, `assignee_id`

### 4.2 Endpoint Summary

| Method | Endpoint | Purpose | Auth Required | Roles |
|--------|----------|---------|---------------|-------|
| GET | `/api/v1/company/projects` | List projects with pagination and filtering | Yes | All (with visibility rules) |
| POST | `/api/v1/company/projects` | Create new project | Yes | CEO, Manager |
| GET | `/api/v1/company/projects/{project_id}` | Get project detail with task summaries | Yes | All (with visibility rules) |
| PATCH | `/api/v1/company/projects/{project_id}` | Update project (name and/or status) | Yes | CEO, Manager |
| DELETE | `/api/v1/company/projects/{project_id}` | Delete project (soft delete with cascade) | Yes | CEO, Manager |

### 4.3 Endpoint Details

#### 4.3.1 GET /api/v1/company/projects

- **Purpose:** List projects with pagination, filtering, search, and sorting. Visibility is role-based: CEO/Manager/HR see all company projects; Employees see only projects with assigned tasks.

- **Authentication:** Required (JWT Bearer token)

- **Authorization / Roles:** 
  - CEO: All company projects
  - Manager: All company projects
  - HR: All company projects (read-only)
  - Employee: Only projects with assigned tasks

- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-None-Match: "20240120T103000Z"` (optional, for cache validation - returns 304 if unchanged)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

- **Idempotency:** Yes (GET operation)

**Path Parameters:** None

**Query Parameters**

**Note:** Query parameters MUST be defined using a query schema class with `Depends()` pattern (Rule 9), NOT individual `Query()` parameters in the router endpoint.

**Query Schema Class (REQUIRED):**
```python
class ProjectListQuery(BaseModel):
    """Query schema for listing projects with pagination and filtering."""

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    status: Optional[str] = Field(None, description="Filter by project status: ACTIVE, INACTIVE, COMPLETED (case-sensitive)")
    search: Optional[str] = Field(None, description="Search by project name (case-insensitive partial match)")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, name, status, task_count")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)
```

**Router Endpoint Pattern (REQUIRED):**
```python
@router.get("", response_model=StandardResponse[ProjectPaginatedResponse])
async def list_projects(
    query: ProjectListQuery = Depends(ProjectListQuery),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List projects with pagination, filtering, search, and sorting."""
    # Access via query.page, query.page_size, query.status, query.search, etc.
```

**Query Parameters Table (for documentation only):**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number (≥ 1) |
| page_size | integer | No | 20 | Number of items per page (1-100) |
| status | string | No | null | Filter by project status: ACTIVE, INACTIVE, COMPLETED (case-sensitive) |
| search | string | No | null | Search by project name (case-insensitive partial match) |
| sort_by | string | No | created_at | Sort field: created_at, updated_at, name, status, task_count |
| sort_order | string | No | desc | Sort order: asc or desc |

**Request Body:** None

**Success Response (200 OK)**

```json
{
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Website Revamp",
        "status": "ACTIVE",
        "task_count": 15,
        "created_at": "2024-01-20T10:30:00Z",
        "updated_at": "2024-01-20T15:45:00Z"
      },
      {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "name": "Mobile App Development",
        "status": "INACTIVE",
        "task_count": 8,
        "created_at": "2024-01-15T09:00:00Z",
        "updated_at": "2024-01-18T14:20:00Z"
      }
    ],
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8,
    "next_page": "/api/v1/company/projects?page=2&page_size=20&status=ACTIVE&sort_by=created_at&sort_order=desc",
    "prev_page": null
  },
  "message": "Projects retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159).
- For paginated responses, `next_page` and `prev_page` include all query parameters (filters, sort, search) to preserve pagination state.

**Cache Validation Response (304 Not Modified)**

If `If-None-Match` header is provided and ETag matches current resource version:
- Status: `304 Not Modified`
- No response body
- Headers: `X-Request-ID`, `ETag`, `Last-Modified`

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 Bad Request | `INVALID_REQUEST` | Invalid query parameter format or value |
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid JWT token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 401 Unauthorized | `INVALID_TOKEN` | JWT token missing required claims |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User lacks required permissions |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during processing |

**Example Error Response (400 Bad Request):**
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "details": [{"field": "page_size", "issue": "Page size must be between 1 and 100"}]
  },
  "message": "Invalid query parameter value."
}
```

---

#### 4.3.2 POST /api/v1/company/projects

- **Purpose:** Create a new project within the user's company. Only CEO and Manager can create projects.

- **Authentication:** Required (JWT Bearer token)

- **Authorization / Roles:** CEO, Manager

- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `Content-Type: application/json` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

- **Idempotency:** No (creates new resource)

**Path Parameters:** None

**Query Parameters:** None

**Request Body**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| name | string | Yes | Project name | Min 1 character, max 255 characters, case-insensitive unique within company |
| status | string | Yes | Initial project status | Enum: "ACTIVE", "INACTIVE", "COMPLETED" (case-sensitive) |

**Request Body Example:**
```json
{
  "name": "Website Revamp",
  "status": "ACTIVE"
}
```

**Success Response (201 Created)**

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Website Revamp",
    "status": "ACTIVE",
    "task_count": 0,
    "created_at": "2024-01-20T10:30:00Z",
    "updated_at": "2024-01-20T10:30:00Z",
    "created_by": "660e8400-e29b-41d4-a716-446655440001",
    "updated_by": "660e8400-e29b-41d4-a716-446655440001"
  },
  "message": "Project created successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED)
- `ETag: "20240120T103000Z"` (REQUIRED - based on `updated_at`)
- `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (RECOMMENDED)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 Bad Request | `VALIDATION_FAILED` | Request body validation failed |
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid JWT token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User is not CEO or Manager |
| 409 Conflict | `DUPLICATE_PROJECT_NAME` | Project name already exists in company (case-insensitive) |
| 422 Unprocessable Entity | `VALIDATION_ERROR` | Field validation failed (name length, status enum) |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during creation |

**Example Error Response (409 Conflict - Duplicate Name):**
```json
{
  "error": {
    "code": "DUPLICATE_PROJECT_NAME",
    "details": [{"field": "name", "issue": "A project with this name already exists in your company."}]
  },
  "message": "Project name must be unique within the company."
}
```

**Example Error Response (422 Unprocessable Entity - Validation Error):**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "details": [
      {"field": "name", "issue": "Project name must be between 1 and 255 characters"},
      {"field": "status", "issue": "Status must be one of: ACTIVE, INACTIVE, COMPLETED"}
    ]
  },
  "message": "Request validation failed."
}
```

---

#### 4.3.3 GET /api/v1/company/projects/{project_id}

- **Purpose:** Get project detail including task summaries. Employees can only access projects where they have assigned tasks.

- **Authentication:** Required (JWT Bearer token)

- **Authorization / Roles:** 
  - CEO: All company projects
  - Manager: All company projects
  - HR: All company projects (read-only)
  - Employee: Only if they have assigned tasks in the project

- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-None-Match: "20240120T103000Z"` (optional, for cache validation - returns 304 if unchanged)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
    - `ETag: "20240120T103000Z"` (REQUIRED - based on `updated_at`)
    - `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (RECOMMENDED)

- **Idempotency:** Yes (GET operation)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| project_id | string (UUID) | Yes | Project identifier |

**Note:** All path parameters MUST use snake_case (e.g., `project_id`) - see Rule 2.

**Query Parameters:** None

**Request Body:** None

**Success Response (200 OK)**

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Website Revamp",
    "status": "ACTIVE",
    "task_count": 15,
    "is_frozen": false,
    "tasks": [
      {
        "id": "770e8400-e29b-41d4-a716-446655440002",
        "title": "Design homepage mockup",
        "status": "IN_PROGRESS",
        "assignee_id": "880e8400-e29b-41d4-a716-446655440003"
      },
      {
        "id": "770e8400-e29b-41d4-a716-446655440004",
        "title": "Implement responsive layout",
        "status": "TODO",
        "assignee_id": "880e8400-e29b-41d4-a716-446655440003"
      }
    ],
    "created_at": "2024-01-20T10:30:00Z",
    "updated_at": "2024-01-20T15:45:00Z",
    "created_by": "660e8400-e29b-41d4-a716-446655440001",
    "updated_by": "660e8400-e29b-41d4-a716-446655440001"
  },
  "message": "Project retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED)
- `ETag: "20240120T103000Z"` (REQUIRED - based on `updated_at`)
- `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (RECOMMENDED)

**Note:** 
- `is_frozen` is derived from status: `true` if status is INACTIVE or COMPLETED, `false` if ACTIVE
- `tasks` array contains task summaries (read-only data from F-008)
- Field order shown is for readability only. JSON objects are unordered (RFC 7159).

**Cache Validation Response (304 Not Modified)**

If `If-None-Match` header is provided and ETag matches current resource version:
- Status: `304 Not Modified`
- No response body
- Headers: `X-Request-ID`, `ETag`, `Last-Modified`

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid JWT token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | Employee attempting to access project without assigned tasks |
| 404 Not Found | `PROJECT_NOT_FOUND` | Project not found or belongs to different company |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during retrieval |

**Example Error Response (404 Not Found):**
```json
{
  "error": {
    "code": "PROJECT_NOT_FOUND",
    "details": [{"field": "project_id", "issue": "Project not found or you do not have access to it."}]
  },
  "message": "Project not found."
}
```

**Example Error Response (403 Forbidden - Employee Access):**
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "details": [{"field": "project", "issue": "You can only access projects where you have assigned tasks."}]
  },
  "message": "Insufficient permissions to access this project."
}
```

---

#### 4.3.4 PATCH /api/v1/company/projects/{project_id}

- **Purpose:** Update project name and/or status. Only CEO and Manager can update projects. Status updates follow Rule 6 (PATCH for resource field updates).

- **Authentication:** Required (JWT Bearer token)

- **Authorization / Roles:** CEO, Manager

- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `Content-Type: application/json` (REQUIRED)
    - `If-Match: "20240120T103000Z"` (REQUIRED - ETag from GET response, based on `updated_at`, for concurrency control)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
    - `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)

- **Idempotency:** Yes (idempotent update operation)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| project_id | string (UUID) | Yes | Project identifier |

**Note:** All path parameters MUST use snake_case (e.g., `project_id`) - see Rule 2.

**Query Parameters:** None

**Request Body**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| name | string | No | Project name | Min 1 character, max 255 characters, case-insensitive unique within company (if provided) |
| status | string | No | Project status | Enum: "ACTIVE", "INACTIVE", "COMPLETED" (case-sensitive, if provided) |

**Note:** At least one field (name or status) must be provided.

**Request Body Example (Update Name Only):**
```json
{
  "name": "Website Revamp 2.0"
}
```

**Request Body Example (Update Status Only):**
```json
{
  "status": "COMPLETED"
}
```

**Request Body Example (Update Both):**
```json
{
  "name": "Website Revamp 2.0",
  "status": "COMPLETED"
}
```

**Success Response (200 OK)**

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Website Revamp 2.0",
    "status": "COMPLETED",
    "task_count": 15,
    "created_at": "2024-01-20T10:30:00Z",
    "updated_at": "2024-01-20T16:00:00Z",
    "created_by": "660e8400-e29b-41d4-a716-446655440001",
    "updated_by": "660e8400-e29b-41d4-a716-446655440001"
  },
  "message": "Project updated successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED)
- `ETag: "20240120T160000Z"` (New ETag after update, based on new `updated_at`)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 Bad Request | `VALIDATION_FAILED` | Request body validation failed or no fields provided |
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid JWT token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User is not CEO or Manager |
| 404 Not Found | `PROJECT_NOT_FOUND` | Project not found or belongs to different company |
| 409 Conflict | `DUPLICATE_PROJECT_NAME` | Project name already exists in company (case-insensitive, if name is updated) |
| 412 Precondition Failed | `PRECONDITION_FAILED` | ETag mismatch - resource was modified since retrieval |
| 422 Unprocessable Entity | `VALIDATION_ERROR` | Field validation failed (name length, status enum) |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during update |

**Example Error Response (412 Precondition Failed - ETag Mismatch):**
```json
{
  "error": {
    "code": "PRECONDITION_FAILED",
    "details": [{"field": "etag", "issue": "Resource has been modified since retrieval. Please fetch the latest version and retry."}]
  },
  "message": "Resource version mismatch. The resource was modified by another user."
}
```

**Example Error Response (409 Conflict - Duplicate Name):**
```json
{
  "error": {
    "code": "DUPLICATE_PROJECT_NAME",
    "details": [{"field": "name", "issue": "A project with this name already exists in your company."}]
  },
  "message": "Project name must be unique within the company."
}
```

---

#### 4.3.5 DELETE /api/v1/company/projects/{project_id}

- **Purpose:** Delete a project using soft delete (IsDeleted marker). Cascades soft delete to all associated tasks. Only CEO and Manager can delete projects.

- **Authentication:** Required (JWT Bearer token)

- **Authorization / Roles:** CEO, Manager

- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-Match: "20240120T103000Z"` (REQUIRED - ETag from GET response, based on `updated_at`, for concurrency control)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

- **Idempotency:** Yes (idempotent delete operation - returns 204 if already deleted)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| project_id | string (UUID) | Yes | Project identifier |

**Note:** All path parameters MUST use snake_case (e.g., `project_id`) - see Rule 2.

**Query Parameters:** None

**Request Body:** None

**Success Response (204 No Content)**

- Status: `204 No Content`
- No response body
- Headers: `X-Request-ID: req_abc123xyz789` (REQUIRED)

**Cascade Deletion Behavior:**
- Sets `is_deleted = true` on the project
- Sets `is_deleted = true` on all associated tasks (cascade)
- Project and tasks are not permanently removed from database
- Deleted projects are excluded from list and detail endpoints (unless explicitly filtered)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid JWT token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User is not CEO or Manager |
| 404 Not Found | `PROJECT_NOT_FOUND` | Project not found, already deleted, or belongs to different company |
| 412 Precondition Failed | `PRECONDITION_FAILED` | ETag mismatch - resource was modified since retrieval |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during deletion |

**Example Error Response (404 Not Found):**
```json
{
  "error": {
    "code": "PROJECT_NOT_FOUND",
    "details": [{"field": "project_id", "issue": "Project not found or already deleted."}]
  },
  "message": "Project not found."
}
```

**Example Error Response (412 Precondition Failed - ETag Mismatch):**
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

## 5. Data Models

### 5.1 Project Summary (List Response)

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| id | string (UUID) | Yes | Project identifier | RFC 4122 UUID v4 format |
| name | string | Yes | Project name | Min 1 character, max 255 characters |
| status | string | Yes | Project status | Enum: "ACTIVE", "INACTIVE", "COMPLETED" (case-sensitive) |
| task_count | integer | Yes | Number of associated tasks | Integer, min 0 |
| created_at | string (datetime) | Yes | Creation timestamp | ISO 8601 format, UTC timezone (Z suffix) |
| updated_at | string (datetime) | Yes | Last update timestamp | ISO 8601 format, UTC timezone (Z suffix) |

### 5.2 Project Detail (Detail Response)

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| id | string (UUID) | Yes | Project identifier | RFC 4122 UUID v4 format |
| name | string | Yes | Project name | Min 1 character, max 255 characters |
| status | string | Yes | Project status | Enum: "ACTIVE", "INACTIVE", "COMPLETED" (case-sensitive) |
| task_count | integer | Yes | Number of associated tasks | Integer, min 0 |
| is_frozen | boolean | Yes | Whether project is frozen | Derived: true if status is INACTIVE or COMPLETED |
| tasks | array | Yes | Task summaries (read-only) | Array of TaskSummary objects (from F-008) |
| created_at | string (datetime) | Yes | Creation timestamp | ISO 8601 format, UTC timezone (Z suffix) |
| updated_at | string (datetime) | Yes | Last update timestamp | ISO 8601 format, UTC timezone (Z suffix) |
| created_by | string (UUID) | Yes | Creator user ID | RFC 4122 UUID v4 format |
| updated_by | string (UUID) | Yes | Last updater user ID | RFC 4122 UUID v4 format |

### 5.3 Task Summary (Nested in Project Detail)

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| id | string (UUID) | Yes | Task identifier | RFC 4122 UUID v4 format |
| title | string | Yes | Task title | From F-008 (read-only) |
| status | string | Yes | Task status | From F-008 (read-only) |
| assignee_id | string (UUID) | Yes | Assigned user ID | RFC 4122 UUID v4 format, from F-008 (read-only) |

**Note:** Task summary fields are read-only and governed by F-008 (Task Management & Assignment). This feature only includes them for project context.

### 5.4 Project Create Request

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| name | string | Yes | Project name | Min 1 character, max 255 characters, case-insensitive unique within company |
| status | string | Yes | Initial project status | Enum: "ACTIVE", "INACTIVE", "COMPLETED" (case-sensitive) |

### 5.5 Project Update Request

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| name | string | No | Project name | Min 1 character, max 255 characters, case-insensitive unique within company (if provided) |
| status | string | No | Project status | Enum: "ACTIVE", "INACTIVE", "COMPLETED" (case-sensitive, if provided) |

**Note:** At least one field (name or status) must be provided.

### 5.6 Paginated Response Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| items | array | Yes | Array of ProjectSummary objects |
| total | integer | Yes | Total number of items across all pages |
| page | integer | Yes | Current page number |
| page_size | integer | Yes | Number of items per page |
| total_pages | integer | Yes | Total number of pages |
| next_page | string (URL) or null | Yes | Full relative URL for next page (or null if no next page) |
| prev_page | string (URL) or null | Yes | Full relative URL for previous page (or null if no previous page) |

**Note:** Navigation URLs (`next_page`, `prev_page`) MUST preserve all query parameters (filters, sort, search) to maintain pagination state.

---

## 6. Business Rules & Validation

### 6.1 Project Name Uniqueness

- **Rule:** Project names must be unique within a company (case-insensitive)
- **Scope:** Company-scoped (from JWT token `company_id`)
- **Case Sensitivity:** Case-insensitive (e.g., "Website Revamp" and "website revamp" are considered duplicates)
- **Error Response:** `409 Conflict` with error code `DUPLICATE_PROJECT_NAME`
- **Applies To:** POST (create) and PATCH (update name)

### 6.2 Project Status Transitions

- **Allowed Statuses:** ACTIVE, INACTIVE, COMPLETED
- **Status Semantics:**
  - **ACTIVE:** Project is editable; tasks can be added, moved, or removed
  - **INACTIVE:** Project is frozen; no task changes allowed
  - **COMPLETED:** Project is frozen and read-only; retained for reference
- **Status Updates:** Can be changed to any status via PATCH (no transition restrictions)
- **Frozen Projects:** Projects with status INACTIVE or COMPLETED are considered "frozen" (`is_frozen = true`)

### 6.3 Role-Based Visibility

**CEO / Manager / HR:**
- See all projects within their company
- No filtering based on task assignment
- Can access projects with zero tasks

**Employee:**
- See only projects where they have at least one assigned task
- Projects with zero tasks assigned to the employee are hidden
- If all assigned tasks are removed from a project, the project disappears from the employee's view
- Cannot access project detail if they have no assigned tasks in the project

### 6.4 Cascade Deletion

- **Rule:** Deleting a project (soft delete) cascades to all associated tasks
- **Behavior:** Sets `is_deleted = true` on project and all associated tasks
- **Permanence:** Soft delete only (not permanent removal from database)
- **Visibility:** Deleted projects and tasks are excluded from list and detail endpoints

### 6.5 Company Scoping

- **Rule:** All project operations are scoped to the company from JWT token `company_id`
- **Enforcement:** Users cannot access projects from other companies
- **Error Response:** `403 INSUFFICIENT_PERMISSIONS` or `404 PROJECT_NOT_FOUND` for cross-company access attempts

### 6.6 Field Validation Rules

**Project Name:**
- Minimum length: 1 character
- Maximum length: 255 characters
- Uniqueness: Case-insensitive unique within company
- Format: No specific format restrictions (alphanumeric, spaces, special characters allowed)

**Project Status:**
- Enum values: "ACTIVE", "INACTIVE", "COMPLETED"
- Case-sensitive (must match exactly)
- Required on create, optional on update (but at least one field must be provided on update)

---

## 7. Error Handling

### 7.1 Standard Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `UNAUTHENTICATED` | 401 | Missing or invalid JWT token |
| `TOKEN_EXPIRED` | 401 | JWT token has expired |
| `INVALID_TOKEN` | 401 | JWT token missing required claims |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions for operation |
| `PROJECT_NOT_FOUND` | 404 | Project not found, deleted, or belongs to different company |
| `INVALID_REQUEST` | 400 | Invalid request format or query parameter |
| `VALIDATION_FAILED` | 400 | Request body validation failed |
| `VALIDATION_ERROR` | 422 | Field validation failed (name length, status enum) |
| `DUPLICATE_PROJECT_NAME` | 409 | Project name already exists in company (case-insensitive) |
| `PRECONDITION_FAILED` | 412 | ETag mismatch - resource was modified since retrieval |
| `INTERNAL_ERROR` | 500 | Server error during processing |

### 7.2 Error Response Format

All error responses follow this structure:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "details": [
      {"field": "field_name", "issue": "Error description"}
    ]
  },
  "message": "Human-friendly error message"
}
```

**Note:** Field order shown is for readability only. JSON objects are unordered (RFC 7159).

---

## 8. Swagger Documentation

### 8.1 Documentation Class Structure

**Location:** `src/projects/documentations/project_api_doc.py`

**Required Pattern:**
```python
from typing import ClassVar

class ProjectApiDocs:
    """API documentation for Project endpoints"""
    
    list: ClassVar[dict] = {
        "summary": "Purpose of this API is to list projects with pagination and filtering",
        "description": "Retrieves a paginated list of projects. Supports filtering by status, search by name, and sorting. Visibility is role-based: CEO/Manager/HR see all company projects; Employees see only projects with assigned tasks."
    }
    
    create: ClassVar[dict] = {
        "summary": "Purpose of this API is to create a new project",
        "description": "Creates a new project within the user's company. Only CEO and Manager can create projects. Project name must be unique within the company (case-insensitive)."
    }
    
    get: ClassVar[dict] = {
        "summary": "Purpose of this API is to get project detail with task summaries",
        "description": "Retrieves project detail including task summaries. Employees can only access projects where they have assigned tasks."
    }
    
    update: ClassVar[dict] = {
        "summary": "Purpose of this API is to update project name and/or status",
        "description": "Updates project name and/or status. Only CEO and Manager can update projects. Requires If-Match header (ETag) for concurrency control."
    }
    
    delete: ClassVar[dict] = {
        "summary": "Purpose of this API is to delete a project with cascade to tasks",
        "description": "Deletes a project using soft delete (IsDeleted marker). Cascades soft delete to all associated tasks. Only CEO and Manager can delete projects. Requires If-Match header (ETag) for concurrency control."
    }
```

**Router Usage:**
```python
from src.projects.documentations.project_api_doc import ProjectApiDocs

@router.get(
    "",
    response_model=StandardResponse[ProjectPaginatedResponse],
    summary=ProjectApiDocs.list["summary"],
    description=ProjectApiDocs.list["description"]
)
async def list_projects(...):
    """List projects with pagination and filtering."""
    pass
```

---

## 9. Query Schema Implementation

### 9.1 ProjectListQuery Schema

**Location:** `src/projects/schemas.py`

**Required Implementation:**
```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class ProjectListQuery(BaseModel):
    """Query schema for listing projects with pagination and filtering."""

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    status: Optional[str] = Field(None, description="Filter by project status: ACTIVE, INACTIVE, COMPLETED (case-sensitive)")
    search: Optional[str] = Field(None, description="Search by project name (case-insensitive partial match)")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, name, status, task_count")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)
```

**Router Usage:**
```python
from src.projects.schemas import ProjectListQuery
from fastapi import Depends

@router.get("", response_model=StandardResponse[ProjectPaginatedResponse])
async def list_projects(
    query: ProjectListQuery = Depends(ProjectListQuery),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List projects with pagination, filtering, search, and sorting."""
    # Access via query.page, query.page_size, query.status, query.search, etc.
    pass
```

---

## 10. Assumptions

1. **Project Name Uniqueness:** Case-insensitive within company scope (standard practice for names)
2. **Cascade Deletion:** Soft delete (IsDeleted marker) for both project and associated tasks
3. **Company Context:** Extracted from JWT token `company_id` claim (not from path parameter)
4. **Task Summaries:** Read-only data from F-008, included for project context only
5. **Status Transitions:** No restrictions on status transitions (can change to any status)
6. **Audit Fields:** All datetime fields use UTC timezone (ISO 8601 with Z suffix)
7. **ETag Format:** Based on `updated_at` timestamp in format `"YYYYMMDDTHHMMSSZ"` (e.g., `"20240120T103000Z"`)

---

## 11. Open Questions

None identified at this stage.

---

## 12. Dependencies

- **F-002 — RBAC & Permission Engine:** Required for role-based access control and permissions
- **F-008 — Task Management & Assignment:** Required for task summaries in project detail responses

---

**End of API Specification**

