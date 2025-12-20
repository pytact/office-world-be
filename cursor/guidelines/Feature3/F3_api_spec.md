# API Specification: F-003 — Notifications System

## 1. Overview

The Notifications System (F-003) provides a centralized, asynchronous mechanism to inform users about onboarding and workflow events through email-first delivery and limited in-app notifications. This feature ensures users remain informed without blocking core business processes, while maintaining strict company scoping and predictable notification behavior.

### 1.1 Feature Capabilities
- **In-App Notification Management**: View, filter, and manage in-app notifications for task and leave events
- **Read/Unread State Management**: Mark notifications as read or unread (single and bulk operations)
- **Notification Filtering**: Filter by type, read status, with pagination and sorting
- **Unread Count**: Retrieve unread notification count for badge display
- **Company-Scoped Access**: All notifications are strictly company-scoped
- **User-Scoped Visibility**: Users can only view and manage their own notifications

### 1.2 Business Value
Provides reliable, email-first notifications for all critical user and workflow events, with lightweight in-app visibility for task and leave events. Ensures users stay informed without blocking core business workflows.

### 1.3 Technical Scope
- Read-only API endpoints for notification retrieval (notifications are created internally by async workers)
- Single and bulk mark-as-read/unread operations
- Pagination, filtering, and sorting for notification lists
- Unread count endpoint for UI badges
- Company and user-level data scoping

**Note:** Notification creation is handled internally by the system via asynchronous workers (Celery). This API provides read-only access to in-app notifications. Email notifications are delivered asynchronously and are not exposed via these endpoints. Invitation notifications are email-only and excluded from API responses.

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
- SuperAdmin (`org_id: null`): Global platform access, but notifications are company-scoped (must specify company context)
- Company users (`org_id: "<uuid>"`): Access limited to specified organization's notifications

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
**Access Scope:** Global platform access, but notifications are company-scoped
**Capabilities:**
- Can view notifications across all companies (with proper company context)
- Cannot create notifications via API (system-generated only)
- Cannot access notifications without company context

#### CEO (Company Admin)
**Access Scope:** Full company administration within own organization
**Capabilities:**
- Can view own notifications (company-scoped)
- Can mark own notifications as read/unread
- Receives notifications for leave approvals at manager level

#### HR (Human Resources)
**Access Scope:** Company-wide HR operations within own organization
**Capabilities:**
- Can view own notifications (company-scoped)
- Can mark own notifications as read/unread
- Receives notifications for leave approvals at manager level

#### Manager
**Access Scope:** Team management within own organization
**Capabilities:**
- Can view own notifications (company-scoped)
- Can mark own notifications as read/unread
- Receives notifications for leave requests from employees

#### Employee
**Access Scope:** Own data only within own organization
**Capabilities:**
- Can view own notifications (company-scoped)
- Can mark own notifications as read/unread
- Receives notifications for leave approvals/rejections and task assignments

### 3.2 Notification Visibility Rules
- **User-Scoped**: Users can only view and manage their own notifications
- **Company-Scoped**: All notifications are scoped to the user's company (from JWT `org_id`)
- **Channel Filtering**: API only returns in-app notifications (channel = "in_app")
- **Type Filtering**: API only returns task and leave type notifications (invitation notifications are email-only and excluded)

### 3.3 Permission Enforcement
- **RBAC Dependency**: Navigation to related records (tasks, leaves) requires RBAC permission checks (F-002)
- **RLS (Row-Level Security)**: Enforced at database/service layer - users can only access notifications where `user_id` matches authenticated user's ID
- **Company Isolation**: Notifications are filtered by `company_id` matching user's `org_id` from JWT token

---

## 4. Resources & Endpoints

### 4.1 Resource Overview

**Notification Resource:**
- Represents a persisted notification record delivered to a user through email and/or in-app channels
- Created internally by the system via async workers (not via API)
- Read-only via API (except for read/unread state updates)
- Company-scoped and user-scoped

**Key Fields:**
- `id` (UUID): Unique notification identifier
- `type` (string): Notification event type (enum - see Notification Types below)
- `title` (string): Short message title
- `message` (string): Notification body content
- `channel` (string): Delivery channel - "email" or "in_app"
- `is_read` (boolean): Read state (in-app only)
- `read_at` (datetime, nullable): Read timestamp (in-app only, UTC)
- `status` (string): Delivery state - "sent" or "failed"
- `related_record_id` (UUID, nullable): Related domain record ID (leave_id, task_id)
- `related_table` (string, nullable): Source table name ("leaves", "tasks")
- `data` (object, nullable): Structured payload (includes rejection reason, etc.) - See Data Field Structure below
- `user_id` (UUID): Recipient user ID (implicit in user-scoped queries, but included in responses for clarity)
- `company_id` (UUID): Company ID (implicit in company-scoped queries, but included in responses for clarity)
- `created_at` (datetime): Creation timestamp (UTC)
- `updated_at` (datetime): Last update timestamp (UTC)

**Data Field Structure:**
The `data` field contains type-specific structured information. Common structures:

- **Leave notifications** (`leave_request`, `leave_approval`, `leave_rejection`, `leave_manager_approval`):
  ```json
  {
    "approver_name": "John Doe",
    "rejector_name": "John Doe",  // for rejection
    "rejection_reason": "Leave request overlaps with critical project deadline",  // for rejection
    "leave_dates": "2024-01-15 to 2024-01-20",
    "leave_type": "annual",
    "employee_name": "Jane Smith"  // for manager_approval
  }
  ```

- **Task notifications** (`task_assignment`, `task_permission_change`, `task_status_change`):
  ```json
  {
    "task_name": "Complete Project Documentation",
    "assigner_name": "Jane Smith",
    "permission_level": "editor",  // "viewer" or "editor"
    "due_date": "2024-01-25T17:00:00Z",
    "old_status": "pending",  // for status_change
    "new_status": "in_progress"  // for status_change
  }
  ```

- **User notifications** (`user_activation`, `user_deactivation`):
  ```json
  {
    "activated_by": "Admin User",  // for activation
    "deactivated_by": "Admin User"  // for deactivation
  }
  ```

**Notification Types (Specific Event Types - Option B):**
- `leave_request`: Manager receives when employee applies for leave
- `leave_approval`: Employee receives when leave is approved
- `leave_rejection`: Employee receives when leave is rejected
- `leave_manager_approval`: CEO/HR receives when manager approves leave (for final approval)
- `task_assignment`: Assigned user receives when task is assigned
- `task_permission_change`: Assigned user receives when task permission changes (Viewer ↔ Editor)
- `task_status_change`: Assigned user receives when task status changes
- `user_activation`: User receives when account is activated
- `user_deactivation`: User receives when account is deactivated

**Note:** Invitation notification types (`user_invitation`, `invitation_resend`) are email-only and excluded from API responses.

### 4.2 Endpoint Summary

| Method | Endpoint | Purpose | Auth Required |
|--------|----------|---------|---------------|
| GET | `/api/v1/notifications` | List in-app notifications with pagination, filtering, sorting | Yes |
| GET | `/api/v1/notifications/{notification_id}` | Retrieve single notification by ID | Yes |
| PATCH | `/api/v1/notifications/{notification_id}/read` | Mark single notification as read | Yes |
| PATCH | `/api/v1/notifications/read` | Bulk mark notifications as read/unread | Yes |
| GET | `/api/v1/notifications/count` | Get unread notification count | Yes |

### 4.3 Endpoint Details

#### 4.3.1 GET /api/v1/notifications

- **Purpose:** List in-app notifications for the authenticated user with pagination, filtering, and sorting
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** All authenticated users (company-scoped, user-scoped)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-None-Match: "20240120T103000Z"` (optional, for cache validation - returns 304 if unchanged)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
  - **For GET responses:**
    - `ETag`: Resource version identifier based on `updated_at` (optional, for list endpoints)
    - `Last-Modified`: Timestamp of last modification (optional)
- **Idempotency:** Yes (GET operation)

**Path Parameters**  
None

**Note:** All path parameters MUST use snake_case (e.g., `user_id`, `org_id`, `role_id`) - see Rule 2.

**Query Parameters**  
**Note:** Query parameters MUST be defined using a query schema class with `Depends()` pattern (Rule 9), NOT individual `Query()` parameters in the router endpoint.

**Query Schema Class (REQUIRED):**
```python
class NotificationListQuery(BaseModel):
    """Query schema for listing notifications with pagination and filtering."""

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    is_read: Optional[bool] = Field(None, description="Filter by read status: true (read), false (unread)")
    type: Optional[str] = Field(None, description="Filter by notification type: leave_request, leave_approval, leave_rejection, leave_manager_approval, task_assignment, task_permission_change, task_status_change, user_activation, user_deactivation", pattern="^(leave_request|leave_approval|leave_rejection|leave_manager_approval|task_assignment|task_permission_change|task_status_change|user_activation|user_deactivation)$")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, read_at")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)
```

**Router Endpoint Pattern (REQUIRED):**
```python
@router.get("", response_model=StandardResponse[NotificationPaginatedResponse])
async def list_notifications(
    query: NotificationListQuery = Depends(NotificationListQuery),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List notifications with pagination, filtering, and sorting."""
    # Access via query.page, query.page_size, query.is_read, query.type, etc.
```

**Query Parameters Table (for documentation only):**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number (≥ 1) |
| page_size | integer | No | 20 | Page size (1-100) |
| is_read | boolean | No | null | Filter by read status: true (read), false (unread) |
| type | string | No | null | Filter by notification type (enum values - see Notification Types above). Validation: Must be one of: leave_request, leave_approval, leave_rejection, leave_manager_approval, task_assignment, task_permission_change, task_status_change, user_activation, user_deactivation |
| sort_by | string | No | created_at | Sort field: created_at, updated_at, read_at |
| sort_order | string | No | desc | Sort order: asc or desc |

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "leave_approval",
        "title": "Leave Request Approved",
        "message": "Your leave request from 2024-01-15 to 2024-01-20 has been approved by John Doe.",
        "channel": "in_app",
        "is_read": false,
        "read_at": null,
        "status": "sent",
        "related_record_id": "660e8400-e29b-41d4-a716-446655440001",
        "related_table": "leaves",
        "data": {
          "approver_name": "John Doe",
          "leave_dates": "2024-01-15 to 2024-01-20",
          "leave_type": "annual"
        },
        "user_id": "880e8400-e29b-41d4-a716-446655440004",
        "company_id": "990e8400-e29b-41d4-a716-446655440005",
        "created_at": "2024-01-20T10:30:00Z",
        "updated_at": "2024-01-20T10:30:00Z"
      },
      {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "type": "task_assignment",
        "title": "New Task Assigned",
        "message": "You have been assigned to task 'Complete Project Documentation' with Editor permissions.",
        "channel": "in_app",
        "is_read": true,
        "read_at": "2024-01-20T11:00:00Z",
        "status": "sent",
        "related_record_id": "770e8400-e29b-41d4-a716-446655440003",
        "related_table": "tasks",
        "data": {
          "task_name": "Complete Project Documentation",
          "assigner_name": "Jane Smith",
          "permission_level": "editor",
          "due_date": "2024-01-25T17:00:00Z"
        },
        "user_id": "880e8400-e29b-41d4-a716-446655440004",
        "company_id": "990e8400-e29b-41d4-a716-446655440005",
        "created_at": "2024-01-20T09:15:00Z",
        "updated_at": "2024-01-20T11:00:00Z"
      }
    ],
    "total": 45,
    "page": 1,
    "page_size": 20,
    "total_pages": 3,
    "next_page": "/api/v1/notifications?page=2&page_size=20&sort_by=created_at&sort_order=desc",
    "prev_page": null
  },
  "message": "Notifications retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- Only in-app notifications (task and leave types) are returned. Invitation notifications are email-only and excluded.
- `next_page` and `prev_page` include all query parameters (filters, sort) to preserve pagination state.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 Bad Request | `INVALID_REQUEST` | Invalid query parameters (e.g., invalid type value, invalid sort_by) |
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 401 Unauthorized | `INVALID_TOKEN` | Malformed token or missing required claims |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User lacks required permissions |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during request processing |

Example error (400 Bad Request):
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "details": [{"field": "type", "issue": "Invalid notification type. Allowed values: leave_request, leave_approval, leave_rejection, leave_manager_approval, task_assignment, task_permission_change, task_status_change, user_activation, user_deactivation"}]
  },
  "message": "Invalid query parameter value."
}
```

Example error (401 Unauthorized):
```json
{
  "error": {
    "code": "UNAUTHENTICATED",
    "details": []
  },
  "message": "Authentication required. Please provide a valid JWT token."
}
```

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate error.

---

#### 4.3.2 GET /api/v1/notifications/{notification_id}

- **Purpose:** Retrieve a single notification by ID
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** All authenticated users (can only retrieve own notifications)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-None-Match: "20240120T103000Z"` (optional, for cache validation - returns 304 if unchanged)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
  - **For GET responses:**
    - `ETag`: Resource version identifier based on `updated_at` (for resources that support updates)
    - `Last-Modified`: Timestamp of last modification from `updated_at` field (optional)
- **Idempotency:** Yes (GET operation)

**Path Parameters**

| Name | Type | Required | Description | Validation |
|------|------|----------|-------------|-----------|
| notification_id | string (UUID) | Yes | Notification identifier | RFC 4122 UUID v4 format |

**Note:** All path parameters MUST use snake_case (e.g., `user_id`, `org_id`, `role_id`, `notification_id`) - see Rule 2. The path parameter `{notification_id}` follows snake_case convention and is more explicit than `{id}` for clarity.

**Query Parameters**  
None

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "leave_rejection",
    "title": "Leave Request Rejected",
    "message": "Your leave request from 2024-01-15 to 2024-01-20 has been rejected by John Doe.",
    "channel": "in_app",
    "is_read": false,
    "read_at": null,
    "status": "sent",
    "related_record_id": "660e8400-e29b-41d4-a716-446655440001",
    "related_table": "leaves",
    "data": {
      "rejector_name": "John Doe",
      "rejection_reason": "Leave request overlaps with critical project deadline",
      "leave_dates": "2024-01-15 to 2024-01-20",
      "leave_type": "annual"
    },
    "user_id": "880e8400-e29b-41d4-a716-446655440004",
    "company_id": "990e8400-e29b-41d4-a716-446655440005",
    "created_at": "2024-01-20T10:30:00Z",
    "updated_at": "2024-01-20T10:30:00Z"
  },
  "message": "Notification retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103000Z"` (REQUIRED for resources that support updates, based on `updated_at`)
- `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (RECOMMENDED)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User lacks required permissions or notification belongs to another user |
| 404 Not Found | `NOTIFICATION_NOT_FOUND` | Notification not found or does not belong to user |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during request processing |

Example error (404 Not Found):
```json
{
  "error": {
    "code": "NOTIFICATION_NOT_FOUND",
    "details": [{"field": "notification_id", "issue": "Notification not found or you do not have access to this notification."}]
  },
  "message": "Notification not found."
}
```

Example error (304 Not Modified - Conditional GET):
- **Status:** 304 Not Modified
- **Response Body:** None (empty body)
- **Headers:** `X-Request-ID`, `ETag` (unchanged)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate error.

---

#### 4.3.3 PATCH /api/v1/notifications/{notification_id}/read

- **Purpose:** Mark a single notification as read
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** All authenticated users (can only update own notifications)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-Match: "20240120T103000Z"` (REQUIRED for concurrency control - ETag from GET response, based on `updated_at`)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
- **Idempotency:** Yes (idempotent update - setting is_read=true multiple times has same effect)

**Path Parameters**

| Name | Type | Required | Description | Validation |
|------|------|----------|-------------|-----------|
| notification_id | string (UUID) | Yes | Notification identifier | RFC 4122 UUID v4 format |

**Note:** All path parameters MUST use snake_case (e.g., `user_id`, `org_id`, `role_id`, `notification_id`) - see Rule 2. The path parameter `{notification_id}` follows snake_case convention and is more explicit than `{id}` for clarity.

**Query Parameters**  
None

**Request Body**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| (none) | - | - | No request body required - endpoint marks notification as read by default | - |

**Note:** This endpoint marks the notification as read by default. No request body is required. The `is_read` field is set to `true` and `read_at` is set to current timestamp.

**Success Response (200 OK)**

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "leave_approval",
    "title": "Leave Request Approved",
    "message": "Your leave request from 2024-01-15 to 2024-01-20 has been approved by John Doe.",
    "channel": "in_app",
    "is_read": true,
    "read_at": "2024-01-20T12:00:00Z",
    "status": "sent",
    "related_record_id": "660e8400-e29b-41d4-a716-446655440001",
    "related_table": "leaves",
    "data": {
      "approver_name": "John Doe",
      "leave_dates": "2024-01-15 to 2024-01-20",
      "leave_type": "annual"
    },
    "user_id": "880e8400-e29b-41d4-a716-446655440004",
    "company_id": "990e8400-e29b-41d4-a716-446655440005",
    "created_at": "2024-01-20T10:30:00Z",
    "updated_at": "2024-01-20T12:00:00Z"
  },
  "message": "Notification marked as read successfully"
}
```

**Request Headers:**
- `If-Match: "20240120T103000Z"` (REQUIRED for update operations to prevent lost updates - ETag from GET response, based on `updated_at`)

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T120000Z"` (New ETag after update, based on new `updated_at`)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User lacks required permissions or notification belongs to another user |
| 404 Not Found | `NOTIFICATION_NOT_FOUND` | Notification not found or does not belong to user |
| 412 Precondition Failed | `PRECONDITION_FAILED` | ETag mismatch (If-Match header value does not match current resource version) |
| 428 Precondition Required | `PRECONDITION_REQUIRED` | Missing required If-Match header |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during request processing |

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

Example error (428 Precondition Required):
```json
{
  "error": {
    "code": "PRECONDITION_REQUIRED",
    "details": [{"field": "If-Match", "issue": "If-Match header is required for update operations."}]
  },
  "message": "Precondition required. Please provide If-Match header with ETag value."
}
```

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate error.

---

#### 4.3.4 PATCH /api/v1/notifications/read

- **Purpose:** Bulk mark notifications as read or unread
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** All authenticated users (can only update own notifications)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
- **Idempotency:** Yes (idempotent update - setting same read state multiple times has same effect)

**Path Parameters**  
None

**Query Parameters**  
None

**Request Body**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| action | string | Yes | Action to perform: "read" or "unread" | Enum: "read", "unread" (case-sensitive) |
| notification_ids | array[string] | Yes | Array of notification IDs to update | Array of UUIDs (RFC 4122 UUID v4 format), min 1 item, max 100 items |

**Schema Table Format:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| action | string | Yes | Action to perform | Enum: "read" (marks as read), "unread" (marks as unread) - case-sensitive |
| notification_ids | array[string] | Yes | Array of notification IDs to update | Array of UUIDs (RFC 4122 UUID v4 format), min 1 item, max 100 items, all must belong to authenticated user |

**Request Body Example:**
```json
{
  "action": "read",
  "notification_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001",
    "550e8400-e29b-41d4-a716-446655440002"
  ]
}
```

**Success Response (200 OK)**

```json
{
  "data": {
    "updated_count": 3,
    "action": "read",
    "notification_ids": [
      "550e8400-e29b-41d4-a716-446655440000",
      "550e8400-e29b-41d4-a716-446655440001",
      "550e8400-e29b-41d4-a716-446655440002"
    ]
  },
  "message": "3 notifications marked as read successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- Only notifications belonging to the authenticated user are updated. Invalid or inaccessible notification IDs are silently skipped (not included in `updated_count`).

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 Bad Request | `INVALID_REQUEST` | Invalid request format (e.g., missing action, empty notification_ids) |
| 400 Bad Request | `VALIDATION_FAILED` | Invalid field values (e.g., invalid action value, invalid UUID format, too many IDs) |
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User lacks required permissions |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during request processing |

Example error (400 Bad Request - Validation Failed):
```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "details": [
      {"field": "action", "issue": "Invalid action value. Must be 'read' or 'unread'."},
      {"field": "notification_ids", "issue": "Array must contain between 1 and 100 items."}
    ]
  },
  "message": "Request validation failed."
}
```

Example error (400 Bad Request - Invalid UUID):
```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "details": [{"field": "notification_ids[0]", "issue": "Invalid UUID format. Must be RFC 4122 UUID v4 format."}]
  },
  "message": "Request validation failed."
}
```

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate error.

---

#### 4.3.5 GET /api/v1/notifications/count

- **Purpose:** Get unread notification count for badge display
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** All authenticated users (company-scoped, user-scoped)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
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
    "unread_count": 5
  },
  "message": "Unread notification count retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- Count only includes in-app notifications (task and leave types) that are unread and belong to the authenticated user.
- Invitation notifications are email-only and excluded from count.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User lacks required permissions |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during request processing |

Example error (401 Unauthorized):
```json
{
  "error": {
    "code": "UNAUTHENTICATED",
    "details": []
  },
  "message": "Authentication required. Please provide a valid JWT token."
}
```

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate error.

---

## 5. Webhooks / Async Behavior

### 5.1 Notification Creation
- **Internal Process**: Notifications are created internally by the system via asynchronous workers (Celery)
- **Trigger Events**: Business events trigger notification creation (leave requests, task assignments, user activations, etc.)
- **Email Delivery**: Email notifications are sent asynchronously via Celery workers
- **In-App Persistence**: In-app notifications are persisted to the database for API retrieval
- **No API Creation**: Notification creation is not exposed via API endpoints (system-generated only)

### 5.2 Notification Delivery
- **Email-First**: Email is the primary notification channel
- **In-App Secondary**: In-app notifications are created for task and leave events only
- **Channel Filtering**: API only returns in-app notifications (email-only notifications are excluded)
- **Type Filtering**: API only returns task and leave type notifications (invitation notifications are email-only)

### 5.3 Failure Handling
- **No Retries**: No automatic email retries are performed (as per feature brief)
- **Failure Logging**: Failed notifications are logged only (status = "failed")
- **Non-Blocking**: Notification delivery failures do not block core business workflows

---

## 6. Rate Limiting & Performance

### 6.1 Rate Limiting
- **Default Limit**: 100 requests per minute per user (configurable)
- **Scope**: Per authenticated user (based on JWT `sub` claim)
- **Rate Limit Headers**: Standard rate limit headers may be included in responses (implementation TBD)

### 6.2 Performance Considerations
- **Pagination**: All list endpoints use server-side pagination (default page_size: 20, max: 100)
- **Filtering**: Efficient filtering by `is_read`, `type` using database indexes
- **Company Scoping**: Notifications are filtered by `company_id` matching user's `org_id` from JWT token
- **User Scoping**: Notifications are filtered by `user_id` matching authenticated user's ID
- **Indexing**: Recommended database indexes on `user_id`, `company_id`, `is_read`, `type`, `created_at` for optimal query performance

### 6.3 Caching
- **ETag Support**: GET endpoints support ETags for cache validation (304 Not Modified responses)
- **Cache Headers**: Optional `Cache-Control` headers may be included (implementation TBD)

---

## 7. Open Questions

None identified at this stage.

---

## 8. Assumptions

### 8.1 Notification Creation
- Notifications are created internally by the system via async workers (Celery)
- Notification creation is not exposed via API endpoints
- Business events (leave requests, task assignments, etc.) trigger notification creation

### 8.2 Notification Visibility
- Only in-app notifications (task and leave types) are returned via API
- Invitation notifications are email-only and excluded from API responses
- Users can only view and manage their own notifications
- All notifications are company-scoped (filtered by user's `org_id` from JWT token)

### 8.3 Notification Types
- Notification types use specific event types (Option B): `leave_request`, `leave_approval`, `leave_rejection`, `leave_manager_approval`, `task_assignment`, `task_permission_change`, `task_status_change`, `user_activation`, `user_deactivation`
- Invitation types (`user_invitation`, `invitation_resend`) are email-only and excluded from API

### 8.4 Read/Unread State
- Read/unread state is only applicable to in-app notifications
- Email notifications do not have read/unread state
- `read_at` timestamp is set when notification is marked as read
- Bulk operations support both read and unread actions

### 8.5 Related Records
- Notifications may reference related records (tasks, leaves) via `related_record_id` and `related_table`
- Navigation to related records requires RBAC permission checks (F-002)
- Users may receive notifications for records they cannot access due to RBAC (UI handles this gracefully)

### 8.6 Data Scoping
- Notifications are strictly company-scoped (multi-tenant isolation)
- SuperAdmin users must specify company context to view notifications
- Company users are automatically scoped to their organization (`org_id` from JWT token)

---

**End of API Specification**

