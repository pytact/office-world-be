# API Specification: F-008 — Task Management & Assignment

## 1. Overview

This API specification defines the RESTful endpoints for the Task Management & Assignment feature (F-008). Tasks are atomic units of work within a company, with strict ownership rules, fine-grained assignment permissions, and clear visibility boundaries. Tasks are independent units of work that may optionally belong to projects, without inheriting project visibility.

**Key Characteristics:**
- Company-scoped tasks (company context from JWT token `company_id`)
- Immutable task ownership (set at creation, cannot be changed)
- Multi-assignee support with granular permissions (VIEWER, EDITOR)
- Role-based visibility: CEO/Manager see all tasks; HR sees all (read-only); Employees see own/assigned tasks
- Task status lifecycle management (TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED)
- Optional project linkage (tasks do not inherit project visibility)
- Hard deletion (permanent removal with IsDeleted marker)

**Feature Dependencies:**
- F-002 — RBAC & Permission Engine
- F-003 — Notifications System
- F-007 — Project Management

### 1.1 In Scope
- Task creation, editing, and deletion
- Task ownership (creator as immutable owner)
- Multi-user task assignment with VIEWER and EDITOR permissions
- Task status lifecycle management
- Optional linkage of tasks to projects
- Task visibility based on role and assignment
- Email and in-app notifications for task events

### 1.2 Out of Scope
- Project-level permissions
- Task priority or due date management
- Task comments by viewers
- Bulk task operations
- Soft deletion of tasks
- Task reassignment of ownership

### 1.3 Cross-Feature API Usage
- **Project Selection (SCR_TASK_CREATE):** Frontend should use F-007 (Project Management) endpoint `GET /api/v1/company/projects?status=ACTIVE` to populate project selector dropdown. Only ACTIVE projects are selectable when creating tasks. This endpoint is provided by F-007 API specification.

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
- Company-scoped users: `company_id` MUST contain company UUID
- SuperAdmin: `company_id` MUST be `null` (global access, but tasks are company-scoped)

**Token Expiration:**
- Access tokens: 15 minutes to 1 hour
- Token refresh: Supported via separate endpoint (implementation TBD)

**Multi-tenancy:**
- Company context extracted from JWT token `company_id` claim
- All task operations are scoped to the user's company (from token)
- SuperAdmin must specify company context for task operations

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
- **Path Parameters**: All path parameters use snake_case (e.g., `task_id`, `company_id`)
- **Query Parameters**: All query parameters use snake_case (e.g., `page_size`, `sort_by`)
- **JSON Fields**: All JSON request/response fields use snake_case (e.g., `task_id`, `owner_id`, `created_at`)

---

## 3. Roles & Permissions

### 3.1 Role Definitions

#### CEO (Company Level)
**Access Scope:** Full control over all company tasks
**Capabilities:**
- Can create, view, edit, and delete all company tasks
- Can change status only for tasks they own (per domain model: only owner can change status)
- Can manage assignments for any company task
- Can view all tasks in the company (no filtering)

#### Manager (Company Level)
**Access Scope:** Full control over all company tasks
**Capabilities:**
- Can create, view, edit, and delete all company tasks
- Can change status only for tasks they own (per domain model: only owner can change status)
- Can manage assignments for any company task
- Can view all tasks in the company (no filtering)

#### HR (Company Level)
**Access Scope:** Read-only access to all company tasks
**Capabilities:**
- Can view all company tasks (read-only)
- Cannot create, edit, or delete tasks (blocked by RBAC)
- Cannot change task status
- Cannot manage task assignments

#### Employee (Company Level)
**Access Scope:** Limited to own tasks and assigned tasks
**Capabilities:**
- Can create tasks (becomes owner)
- Can view, edit, and delete tasks they own
- Can view tasks they are assigned to (based on TaskAssignment)
- Can change status only for tasks they own
- Can manage assignments only for tasks they own
- Cannot view tasks outside ownership or assignment

### 3.2 Permission Model

**Task Ownership:**
- Task owner is set at creation (authenticated user)
- Task owner is immutable (cannot be changed)
- Task owner has full control: edit, change status, manage assignments, delete

**Assignment Permissions:**
- **VIEWER**: Can view task only (read-only access)
- **EDITOR**: Can edit task name and description only
  - Editors ❌ cannot:
    - Add/remove assignees
    - Change task status
    - Remove themselves
    - Delete the task

**Derived Permissions:**
- `is_owner` (boolean): True if authenticated user is task owner
- `user_permission` (enum): OWNER | EDITOR | VIEWER (derived from ownership and TaskAssignment)
- `can_edit_task` (boolean): True if owner or editor
- `can_change_status` (boolean): True if owner only
- `can_manage_assignments` (boolean): True if owner only
- `is_task_read_only` (boolean): True if task is in terminal state (DONE, CANCELLED) or user is VIEWER

### 3.3 Visibility Rules

**Task List Filtering:**
- **CEO / Manager**: All company tasks (no filtering)
- **HR**: All company tasks (read-only, no filtering)
- **Employee**: Tasks they own OR tasks they are assigned to (via TaskAssignment)

**Task Detail Access:**
- **CEO / Manager**: Can access any company task
- **HR**: Can access any company task (read-only)
- **Employee**: Can access only tasks they own or are assigned to
- **Error**: `403 INSUFFICIENT_PERMISSIONS` if employee tries to access task outside ownership/assignment

---

## 4. Resources & Endpoints

### 4.1 Resource Overview

#### Task
Represents a single unit of work within a company. Tasks are company-scoped, have one immutable owner, may have multiple assignees, and optionally belong to a project.

**Key Fields:**
- `task_id` (UUID): Unique task identifier
- `company_id` (UUID): Owning company (from JWT token)
- `owner_id` (UUID): Task creator/owner (immutable)
- `name` (string): Task title (required, min 1, max 255 characters)
- `description` (string): Task details (optional, max 5000 characters)
- `status` (enum): Task lifecycle state (TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED)
- `project_id` (UUID, nullable): Optional project linkage
- `is_deleted` (boolean): Hard delete marker (permanent)
- `created_at` (datetime, UTC): Creation timestamp
- `updated_at` (datetime, UTC): Last modification timestamp
- `created_by` (UUID): Creator user ID
- `updated_by` (UUID): Last modifier user ID

#### TaskAssignment
Represents assignment of an employee to a task with a specific permission level.

**Key Fields:**
- `task_id` (UUID): Assigned task
- `employee_id` (UUID): Assigned employee
- `permission` (enum): Assignment permission (VIEWER, EDITOR)

### 4.2 Endpoint Summary

| Method | Path | Purpose | Auth | Roles |
|--------|------|---------|------|-------|
| GET | `/api/v1/company/tasks` | List tasks with pagination and filtering | Required | CEO, Manager, HR (read-only), Employee |
| POST | `/api/v1/company/tasks` | Create new task | Required | CEO, Manager, Employee |
| GET | `/api/v1/company/tasks/{task_id}` | Get task details | Required | Based on visibility rules |
| PATCH | `/api/v1/company/tasks/{task_id}` | Update task name and description | Required | Owner, Editor |
| PATCH | `/api/v1/company/tasks/{task_id}/status` | Change task status | Required | Owner only |
| PATCH | `/api/v1/company/tasks/{task_id}/assignments` | Update task assignments | Required | Owner only |
| DELETE | `/api/v1/company/tasks/{task_id}` | Hard delete task | Required | Owner, CEO, Manager |

### 4.3 Endpoint Details

#### 4.3.1 GET /api/v1/company/tasks

- **Purpose:** List tasks with pagination, filtering, search, and sorting
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, Manager, HR (read-only), Employee
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
class TaskListQuery(BaseModel):
    """Query schema for listing tasks with pagination and filtering."""

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    status: Optional[str] = Field(None, description="Filter by task status: TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED")
    project_id: Optional[str] = Field(None, description="Filter by project ID (UUID format)")
    search: Optional[str] = Field(None, description="Search by task name (case-insensitive partial match)")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, name, status")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)
```

**Router Endpoint Pattern (REQUIRED):**
```python
@router.get("", response_model=StandardResponse[TaskPaginatedResponse])
async def list_tasks(
    query: TaskListQuery = Depends(TaskListQuery),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List tasks with pagination, filtering, search, and sorting."""
    # Access via query.page, query.page_size, query.status, etc.
```

**Query Parameters Table (for documentation only):**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number (≥ 1) |
| page_size | integer | No | 20 | Page size (1-100) |
| status | string | No | null | Filter by task status (TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED) |
| project_id | string (UUID) | No | null | Filter by project ID (RFC 4122 UUID v4 format) |
| search | string | No | null | Search by task name (case-insensitive partial match) |
| sort_by | string | No | created_at | Sort field: created_at, updated_at, name, status |
| sort_order | string | No | desc | Sort order: asc or desc |

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "items": [
      {
        "task_id": "770e8400-e29b-41d4-a716-446655440001",
        "name": "Fix login bug",
        "status": "IN_PROGRESS",
        "project_id": "880e8400-e29b-41d4-a716-446655440002",
        "owner_id": "550e8400-e29b-41d4-a716-446655440000",
        "project": {
          "id": "880e8400-e29b-41d4-a716-446655440002",
          "name": "Q1 Bug Fixes"
        },
        "is_owner": true,
        "user_permission": "OWNER",
        "can_edit_task": true,
        "can_change_status": true,
        "created_at": "2024-01-20T10:00:00Z",
        "updated_at": "2024-01-20T15:30:00Z"
      }
    ],
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8,
    "next_page": "/api/v1/company/tasks?page=2&page_size=20&status=IN_PROGRESS&sort_by=created_at&sort_order=desc",
    "prev_page": null
  },
  "message": "Tasks retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- For paginated responses, `next_page` and `prev_page` should include all query parameters (filters, sort, search) to preserve pagination state.
- Tasks are filtered by visibility rules: CEO/Manager see all, HR sees all (read-only), Employee sees own/assigned only.
- Deleted tasks (is_deleted=true) are excluded from results.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | VALIDATION_FAILED | Invalid query parameter format or value |
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 401 | INVALID_TOKEN | Malformed token or missing required claims |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks required permissions |
| 422 | VALIDATION_ERROR | Invalid status enum value or project_id format |

---

#### 4.3.2 POST /api/v1/company/tasks

- **Purpose:** Create a new task
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, Manager, Employee (HR blocked by RBAC - read-only default)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
- **Idempotency:** No (creates new resource each time)

**Path Parameters**  
None

**Query Parameters**  
None

**Request Body**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| name | string | Yes | Task title | Min 1 character, max 255 characters |
| description | string | No | Task details | Max 5000 characters |
| status | string | No | Initial task status | Enum: "TODO" (default), must be TODO if provided |
| project_id | string (UUID) | No | Optional project linkage | RFC 4122 UUID v4 format, must reference ACTIVE project |

**Request Body Example:**
```json
{
  "name": "Fix login bug",
  "description": "Users are unable to log in with their credentials. Need to investigate and fix authentication flow.",
  "status": "TODO",
  "project_id": "880e8400-e29b-41d4-a716-446655440002"
}
```

**Note:** 
- Task owner is automatically set to authenticated user (immutable)
- Company ID is extracted from JWT token `company_id` claim
- Initial status must be TODO (cannot create task with other statuses)
- Project ID must reference an ACTIVE project (if provided)
- If project_id is provided but project is INACTIVE or COMPLETED, return 422 error

**Success Response (201 Created)**

```json
{
  "data": {
    "task_id": "770e8400-e29b-41d4-a716-446655440001",
    "company_id": "660e8400-e29b-41d4-a716-446655440001",
    "owner_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Fix login bug",
    "description": "Users are unable to log in with their credentials. Need to investigate and fix authentication flow.",
    "status": "TODO",
    "project_id": "880e8400-e29b-41d4-a716-446655440002",
    "is_deleted": false,
    "created_at": "2024-01-20T10:00:00Z",
    "updated_at": "2024-01-20T10:00:00Z",
    "created_by": "550e8400-e29b-41d4-a716-446655440000",
    "updated_by": "550e8400-e29b-41d4-a716-446655440000",
    "assignments": []
  },
  "message": "Task created successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | VALIDATION_FAILED | Invalid request body format |
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 401 | INVALID_TOKEN | Malformed token or missing required claims |
| 403 | INSUFFICIENT_PERMISSIONS | HR role cannot create tasks (read-only) |
| 404 | PROJECT_NOT_FOUND | Project ID provided but project does not exist |
| 422 | VALIDATION_ERROR | Field validation failed (name length, description length, invalid status) |
| 422 | BUSINESS_RULE_FAILED | Project is not ACTIVE (INACTIVE or COMPLETED) |
| 422 | INVALID_STATE_TRANSITION | Initial status is not TODO |

Example error (422 Unprocessable Entity - Validation Error):
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "details": [
      {"field": "name", "issue": "Task name is required and must be between 1 and 255 characters."},
      {"field": "status", "issue": "Initial task status must be TODO. Cannot create task with other statuses."}
    ]
  },
  "message": "Task creation validation failed."
}
```

Example error (422 Unprocessable Entity - Business Rule):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [
      {"field": "project_id", "issue": "Cannot link task to project. Project is INACTIVE. Only ACTIVE projects can have tasks."}
    ]
  },
  "message": "Business rule violation: Project must be ACTIVE to link tasks."
}
```

---

#### 4.3.3 GET /api/v1/company/tasks/{task_id}

- **Purpose:** Get task details with assignments, project info, and derived permission fields
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** Based on visibility rules (owner, assignee, CEO, Manager, HR)
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
| task_id | string (UUID) | Yes | Task identifier (RFC 4122 UUID v4 format) |

**Note:** All path parameters MUST use snake_case (e.g., `task_id`, `company_id`) - see Rule 2.

**Query Parameters**  
None

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "task_id": "770e8400-e29b-41d4-a716-446655440001",
    "company_id": "660e8400-e29b-41d4-a716-446655440001",
    "owner_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Fix login bug",
    "description": "Users are unable to log in with their credentials. Need to investigate and fix authentication flow.",
    "status": "IN_PROGRESS",
    "project_id": "880e8400-e29b-41d4-a716-446655440002",
    "is_deleted": false,
    "created_at": "2024-01-20T10:00:00Z",
    "updated_at": "2024-01-20T15:30:00Z",
    "created_by": "550e8400-e29b-41d4-a716-446655440000",
    "updated_by": "550e8400-e29b-41d4-a716-446655440000",
    "project": {
      "id": "880e8400-e29b-41d4-a716-446655440002",
      "name": "Q1 Bug Fixes",
      "status": "ACTIVE"
    },
    "assignments": [
      {
        "employee_id": "990e8400-e29b-41d4-a716-446655440003",
        "permission": "EDITOR"
      },
      {
        "employee_id": "aa0e8400-e29b-41d4-a716-446655440004",
        "permission": "VIEWER"
      }
    ],
    "is_owner": true,
    "user_permission": "OWNER",
    "can_edit_task": true,
    "can_change_status": true,
    "can_manage_assignments": true,
    "is_task_read_only": false
  },
  "message": "Task retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103000Z"` (REQUIRED - resource version identifier based on `updated_at`)
- `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (RECOMMENDED)

**Conditional GET (304 Not Modified):**
If request includes `If-None-Match` header with matching ETag, return `304 Not Modified` with no response body.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 304 | Not Modified | Resource unchanged (If-None-Match header matches ETag) |
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 401 | INVALID_TOKEN | Malformed token or missing required claims |
| 403 | INSUFFICIENT_PERMISSIONS | Employee trying to access task outside ownership/assignment |
| 404 | TASK_NOT_FOUND | Task does not exist or is deleted |

Example error (403 Forbidden):
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "details": [
      {"field": "task", "issue": "You do not have permission to access this task. You can only access tasks you own or are assigned to."}
    ]
  },
  "message": "Insufficient permissions to access this task."
}
```

---

#### 4.3.4 PATCH /api/v1/company/tasks/{task_id}

- **Purpose:** Update task name and description (owner and editors can edit)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** Owner or Editor (permission-based)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-Match: "20240120T103000Z"` (REQUIRED - ETag from GET response, based on `updated_at`, see Rule 8)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
    - `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)
- **Idempotency:** Yes (with same ETag)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| task_id | string (UUID) | Yes | Task identifier (RFC 4122 UUID v4 format) |

**Query Parameters**  
None

**Request Body**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| name | string | No | Task title | Min 1 character, max 255 characters (if provided) |
| description | string | No | Task details | Max 5000 characters (if provided) |

**Request Body Example:**
```json
{
  "name": "Fix login bug - Updated",
  "description": "Users are unable to log in with their credentials. Need to investigate and fix authentication flow. Priority: High."
}
```

**Note:** 
- Partial update supported (only provided fields are updated)
- Owner can update name and description
- Editor can update name and description (permission-based)
- Viewer cannot update (403 error)
- Cannot update status via this endpoint (use PATCH /status endpoint)
- Cannot update assignments via this endpoint (use PATCH /assignments endpoint)
- Tasks in terminal states (DONE, CANCELLED) are read-only (422 error)
- Tasks linked to INACTIVE or COMPLETED projects may have restrictions (422 error)

**Success Response (200 OK)**

```json
{
  "data": {
    "task_id": "770e8400-e29b-41d4-a716-446655440001",
    "company_id": "660e8400-e29b-41d4-a716-446655440001",
    "owner_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Fix login bug - Updated",
    "description": "Users are unable to log in with their credentials. Need to investigate and fix authentication flow. Priority: High.",
    "status": "IN_PROGRESS",
    "project_id": "880e8400-e29b-41d4-a716-446655440002",
    "is_deleted": false,
    "created_at": "2024-01-20T10:00:00Z",
    "updated_at": "2024-01-20T16:00:00Z",
    "created_by": "550e8400-e29b-41d4-a716-446655440000",
    "updated_by": "550e8400-e29b-41d4-a716-446655440000"
  },
  "message": "Task updated successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | VALIDATION_FAILED | Invalid request body format |
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 401 | INVALID_TOKEN | Malformed token or missing required claims |
| 403 | INSUFFICIENT_PERMISSIONS | User is VIEWER or not owner/assignee |
| 404 | TASK_NOT_FOUND | Task does not exist or is deleted |
| 412 | PRECONDITION_FAILED | ETag mismatch (If-Match header does not match current resource version) |
| 422 | VALIDATION_ERROR | Field validation failed (name length, description length) |
| 422 | BUSINESS_RULE_FAILED | Task is in terminal state (DONE, CANCELLED) - read-only |
| 422 | BUSINESS_RULE_FAILED | Task linked to INACTIVE or COMPLETED project - cannot edit |

Example error (412 Precondition Failed - ETag mismatch):
```json
{
  "error": {
    "code": "PRECONDITION_FAILED",
    "details": [
      {"field": "etag", "issue": "Resource has been modified since retrieval. Please fetch the latest version and retry."}
    ]
  },
  "message": "Resource version mismatch. The resource was modified by another user."
}
```

Example error (422 Unprocessable Entity - Terminal State):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [
      {"field": "status", "issue": "Cannot edit task. Task is in terminal state (DONE). Tasks in DONE or CANCELLED states are read-only."}
    ]
  },
  "message": "Business rule violation: Task in terminal state cannot be modified."
}
```

---

#### 4.3.5 PATCH /api/v1/company/tasks/{task_id}/status

- **Purpose:** Change task status (owner only)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** Owner only
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-Match: "20240120T103000Z"` (REQUIRED - ETag from GET response, based on `updated_at`, see Rule 8)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
    - `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)
- **Idempotency:** Yes (with same ETag and status)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| task_id | string (UUID) | Yes | Task identifier (RFC 4122 UUID v4 format) |

**Query Parameters**  
None

**Request Body**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| status | string | Yes | New task status | Enum: "TODO", "IN_PROGRESS", "HALT", "REVIEW", "DONE", "CANCELLED" (case-sensitive) |

**Request Body Example:**
```json
{
  "status": "DONE"
}
```

**Note:** 
- Only task owner can change status
- Owner can move task to any status at any time
- DONE and CANCELLED are terminal states (task becomes read-only after reaching these states)
- Editors cannot change status (403 error)
- Viewers cannot change status (403 error)

**Success Response (200 OK)**

```json
{
  "data": {
    "task_id": "770e8400-e29b-41d4-a716-446655440001",
    "company_id": "660e8400-e29b-41d4-a716-446655440001",
    "owner_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Fix login bug",
    "description": "Users are unable to log in with their credentials.",
    "status": "DONE",
    "project_id": "880e8400-e29b-41d4-a716-446655440002",
    "is_deleted": false,
    "created_at": "2024-01-20T10:00:00Z",
    "updated_at": "2024-01-20T16:30:00Z",
    "created_by": "550e8400-e29b-41d4-a716-446655440000",
    "updated_by": "550e8400-e29b-41d4-a716-446655440000"
  },
  "message": "Task status updated successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | VALIDATION_FAILED | Invalid request body format |
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 401 | INVALID_TOKEN | Malformed token or missing required claims |
| 403 | INSUFFICIENT_PERMISSIONS | User is not task owner (Editor/Viewer cannot change status) |
| 404 | TASK_NOT_FOUND | Task does not exist or is deleted |
| 412 | PRECONDITION_FAILED | ETag mismatch (If-Match header does not match current resource version) |
| 422 | VALIDATION_ERROR | Invalid status enum value |

Example error (403 Forbidden - Not Owner):
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "details": [
      {"field": "status", "issue": "Only the task owner can change task status. You are assigned as EDITOR and do not have permission to change status."}
    ]
  },
  "message": "Insufficient permissions to change task status."
}
```

---

#### 4.3.6 PATCH /api/v1/company/tasks/{task_id}/assignments

- **Purpose:** Add or remove task assignments (owner only)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** Owner only
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-Match: "20240120T103000Z"` (REQUIRED - ETag from GET response, based on `updated_at`, see Rule 8)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
    - `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)
- **Idempotency:** Yes (with same ETag and assignments)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| task_id | string (UUID) | Yes | Task identifier (RFC 4122 UUID v4 format) |

**Query Parameters**  
None

**Request Body**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| add | array | No | Assignments to add | Array of assignment objects (employee_id, permission) |
| remove | array | No | Assignments to remove | Array of employee_id objects |

**Assignment Object (for add):**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| employee_id | string (UUID) | Yes | Employee to assign | RFC 4122 UUID v4 format, must be employee in same company |
| permission | string | Yes | Assignment permission | Enum: "VIEWER", "EDITOR" (case-sensitive) |

**Remove Object:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| employee_id | string (UUID) | Yes | Employee to unassign | RFC 4122 UUID v4 format, must be existing assignment |

**Request Body Example:**
```json
{
  "add": [
    {
      "employee_id": "990e8400-e29b-41d4-a716-446655440003",
      "permission": "EDITOR"
    },
    {
      "employee_id": "aa0e8400-e29b-41d4-a716-446655440004",
      "permission": "VIEWER"
    }
  ],
  "remove": [
    {
      "employee_id": "bb0e8400-e29b-41d4-a716-446655440005"
    }
  ]
}
```

**Note:** 
- Only task owner can manage assignments
- At least one of `add` or `remove` must be provided (cannot be both empty/omitted)
- Empty arrays `[]` are allowed if only one operation is needed
- Can add and remove assignments in the same request
- Cannot add duplicate assignment (employee already assigned) - return 409 error
- Cannot remove non-existent assignment - return 404 error
- Editors cannot remove themselves (business rule enforced)
- Owner cannot remove themselves (must remain owner)
- Employee must be in same company (validation)

**Success Response (200 OK)**

```json
{
  "data": {
    "task_id": "770e8400-e29b-41d4-a716-446655440001",
    "assignments": [
      {
        "employee_id": "990e8400-e29b-41d4-a716-446655440003",
        "permission": "EDITOR"
      },
      {
        "employee_id": "aa0e8400-e29b-41d4-a716-446655440004",
        "permission": "VIEWER"
      }
    ]
  },
  "message": "Task assignments updated successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | VALIDATION_FAILED | Invalid request body format or both `add` and `remove` are empty/omitted |
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 401 | INVALID_TOKEN | Malformed token or missing required claims |
| 403 | INSUFFICIENT_PERMISSIONS | User is not task owner |
| 404 | TASK_NOT_FOUND | Task does not exist or is deleted |
| 404 | ASSIGNMENT_NOT_FOUND | Employee ID in remove array is not assigned to task |
| 404 | EMPLOYEE_NOT_FOUND | Employee ID does not exist or is not in same company |
| 409 | DUPLICATE_ASSIGNMENT | Employee ID in add array is already assigned to task |
| 412 | PRECONDITION_FAILED | ETag mismatch (If-Match header does not match current resource version) |
| 422 | VALIDATION_ERROR | Invalid permission enum value or employee_id format |
| 422 | BUSINESS_RULE_FAILED | Editor attempting to remove themselves (not allowed) |

Example error (409 Conflict - Duplicate Assignment):
```json
{
  "error": {
    "code": "DUPLICATE_ASSIGNMENT",
    "details": [
      {"field": "add[0].employee_id", "issue": "Employee is already assigned to this task. Cannot add duplicate assignment."}
    ]
  },
  "message": "Duplicate assignment: Employee is already assigned to this task."
}
```

Example error (422 Unprocessable Entity - Business Rule):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [
      {"field": "remove[0].employee_id", "issue": "Editors cannot remove themselves from task assignments. Only the task owner can remove editors."}
    ]
  },
  "message": "Business rule violation: Editors cannot remove themselves."
}
```

---

#### 4.3.7 DELETE /api/v1/company/tasks/{task_id}

- **Purpose:** Hard delete task (permanent removal)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** Owner, CEO, Manager
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-Match: "20240120T103000Z"` (REQUIRED - ETag from GET response, based on `updated_at`, see Rule 8)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
- **Idempotency:** Yes (returns 204 if already deleted)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| task_id | string (UUID) | Yes | Task identifier (RFC 4122 UUID v4 format) |

**Query Parameters**  
None

**Request Body**  
None

**Note:** 
- Task owner, CEO, and Manager can delete tasks
- CEO and Manager can delete any company task (not limited to tasks they own)
- Hard deletion (permanent) - sets IsDeleted marker
- Deleted tasks are not returned in list or detail queries
- Cannot be undone (no soft delete)
- Editors cannot delete (403 error)
- Viewers cannot delete (403 error)
- HR cannot delete (403 error)

**Success Response (204 No Content)**

No response body. Task is permanently deleted.

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 401 | INVALID_TOKEN | Malformed token or missing required claims |
| 403 | INSUFFICIENT_PERMISSIONS | User is not task owner, CEO, or Manager (Editor/Viewer/HR cannot delete) |
| 404 | TASK_NOT_FOUND | Task does not exist or is already deleted |
| 412 | PRECONDITION_FAILED | ETag mismatch (If-Match header does not match current resource version) |

Example error (403 Forbidden - Not Authorized):
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "details": [
      {"field": "task", "issue": "Only task owners, CEOs, and Managers can delete tasks. You are assigned as EDITOR and do not have permission to delete."}
    ]
  },
  "message": "Insufficient permissions to delete this task."
}
```

---

## 5. Webhooks / Async Behavior

### 5.1 Notifications Integration

**Task Events Triggering Notifications (F-003):**
- Task created: Notify task owner (optional, since owner is creator)
- Task assigned: Notify assigned employee when added to task
- Task unassigned: Notify employee when removed from task
- Task permission changed: Notify employee when permission level changes (VIEWER ↔ EDITOR)
- Task status changed: Notify task owner and all assignees when status changes
- Task deleted: Notify all assignees when task is deleted

**Notification Channels:**
- Email notifications (via F-003)
- In-app notifications (via F-003)

**Note:** Notification implementation details are handled by F-003 (Notifications System). This API spec assumes notifications are triggered asynchronously after successful task operations.

---

## 6. Rate Limiting & Performance

### 6.1 Rate Limiting
- **Default Limit**: 100 requests per minute per user
- **Burst Allowance**: Up to 20 requests in a single second
- **Rate Limit Headers**: 
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Unix timestamp when rate limit resets
- **Rate Limit Exceeded**: Return `429 Too Many Requests` with error code `RATE_LIMIT_EXCEEDED`

### 6.2 Performance Considerations
- **Pagination**: Default page size 20, maximum 100 items per page
- **Database Indexing**: Recommended indexes on:
  - `company_id`, `owner_id`, `status`, `project_id` (for filtering)
  - `created_at`, `updated_at` (for sorting)
  - `is_deleted` (for exclusion)
- **Caching**: ETag-based conditional requests (If-None-Match) reduce bandwidth
- **Query Optimization**: Visibility rules (CEO/Manager vs Employee) affect query complexity

---

## 7. Open Questions

None identified at this stage.

---

## 8. Assumptions

1. **Company Context**: Company ID is extracted from JWT token `company_id` claim (not from path parameter)
2. **Task Ownership**: Task owner is automatically set to authenticated user at creation and cannot be changed
3. **Initial Status**: Tasks must be created with status TODO (cannot create with other statuses)
4. **Project Validation**: When linking task to project, project must exist and be ACTIVE
5. **Hard Deletion**: Tasks use hard deletion (IsDeleted marker) - no soft delete support
6. **Notifications**: Notifications are handled asynchronously by F-003 (Notifications System)
7. **RBAC Integration**: Role-based access control is handled by F-002 (RBAC & Permission Engine)
8. **Project Status Impact**: Tasks linked to INACTIVE or COMPLETED projects may have edit restrictions (business rule)
9. **Terminal States**: Tasks in DONE or CANCELLED states are read-only (cannot be edited)
10. **Assignment Management**: Add/remove assignments individually (not replace all at once)

---

## 9. Documentation Class Structure

### 9.1 TaskApiDocs Class

**Location:** `src/tasks/documentations/task_api_doc.py`

**Structure:**
```python
from typing import ClassVar

class TaskApiDocs:
    """API documentation for Task endpoints"""
    
    list: ClassVar[dict] = {
        "summary": "Purpose of this API is to list tasks with pagination and filtering",
        "description": "Retrieves a paginated list of tasks. Supports filtering by status and project, search by name, and sorting. Visibility is role-based: CEO/Manager see all tasks, HR sees all (read-only), Employees see own/assigned tasks only."
    }
    
    create: ClassVar[dict] = {
        "summary": "Purpose of this API is to create a new task",
        "description": "Creates a new task with required name and optional description. Task owner is automatically set to authenticated user (immutable). Initial status must be TODO. Project linkage is optional but must reference an ACTIVE project."
    }
    
    get: ClassVar[dict] = {
        "summary": "Purpose of this API is to get task details",
        "description": "Retrieves full task details including assignments, project info, and derived permission fields. Access is based on visibility rules: owner, assignee, or CEO/Manager/HR roles."
    }
    
    update: ClassVar[dict] = {
        "summary": "Purpose of this API is to update task name and description",
        "description": "Updates task name and/or description. Owner and Editors can edit. Viewers cannot edit. Tasks in terminal states (DONE, CANCELLED) are read-only. Requires If-Match header for concurrency control."
    }
    
    change_status: ClassVar[dict] = {
        "summary": "Purpose of this API is to change task status",
        "description": "Changes task status. Only task owner can change status. Owner can move task to any status at any time. DONE and CANCELLED are terminal states. Requires If-Match header for concurrency control."
    }
    
    update_assignments: ClassVar[dict] = {
        "summary": "Purpose of this API is to update task assignments",
        "description": "Adds or removes task assignments. Only task owner can manage assignments. Supports adding multiple assignments and removing multiple assignments in a single request. Prevents duplicate assignments. Editors cannot remove themselves. Requires If-Match header for concurrency control."
    }
    
    delete: ClassVar[dict] = {
        "summary": "Purpose of this API is to hard delete a task",
        "description": "Permanently deletes a task (hard deletion with IsDeleted marker). Task owner, CEO, and Manager can delete tasks. CEO and Manager can delete any company task (not limited to tasks they own). Deleted tasks are not returned in queries. Cannot be undone. Requires If-Match header for concurrency control."
    }
```

**Router Usage:**
```python
from src.tasks.documentations.task_api_doc import TaskApiDocs

@router.get(
    "",
    response_model=StandardResponse[TaskPaginatedResponse],
    summary=TaskApiDocs.list["summary"],
    description=TaskApiDocs.list["description"]
)
async def list_tasks(...):
    """List tasks with pagination and filtering."""
    pass
```

---

**End of API Specification**

