# API Specification: F-009 — Leave Management

## 1. Overview

### 1.1 Feature Summary
The Leave Management API provides a deterministic, role-driven workflow for employees to request time off and for organizations to approve or reject those requests through a structured approval chain. It enforces strict validation rules, mandatory rejection reasons, role-based visibility, and integrates notifications for key leave events without handling balances or payroll.

### 1.2 Key Capabilities
- Leave request submission with date range and half-day support
- Role-based approval workflows (Employee → Manager → HR, Manager → HR, HR → CEO)
- Mandatory validation rules (overlaps, non-working days)
- Leave cancellation by applicant
- Role-based visibility of leave requests
- Email and in-app notifications for leave workflow events (via F-003)

### 1.3 Out of Scope
- Leave balance tracking and accrual
- Editing leave requests after submission
- Approval for leave cancellation
- Notifications on leave cancellation
- Payroll or salary impact calculations

### 1.4 Dependencies
- **F-005 — Employee Management**: Employee data and relationships
- **F-002 — RBAC & Permission Engine**: Role-based access control
- **F-003 — Notifications System**: Email and in-app notifications

---

## 2. Global API Rules

### 2.1 Authentication

**JWT Token Structure:**
All API endpoints require JWT Bearer token authentication.

**Token Format:** `Authorization: Bearer <jwt_token>`

**Required Claims in JWT Payload:**
- `sub` (subject): User ID (string, UUID format) - **REQUIRED**
- `role`: User role (string) - **REQUIRED** - Encoded in token, not database lookup
  - Values: `"superadmin"`, `"ceo"`, `"hr"`, `"manager"`, `"employee"`
- `org_id`: Organization ID (string, UUID format, nullable) - **REQUIRED**
  - `null` for SuperAdmin (global access)
  - UUID for company-scoped users (CEO, HR, Manager, Employee)
- `exp`: Token expiration timestamp (integer, Unix timestamp) - **REQUIRED**
- `iat`: Token issued at timestamp (integer, Unix timestamp) - **RECOMMENDED**
- `jti`: JWT ID (string, unique token identifier) - **RECOMMENDED** for token revocation

**JWT Payload Structure:**
```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "role": "employee",
  "org_id": "660e8400-e29b-41d4-a716-446655440001",
  "exp": 1735689600,
  "iat": 1735686000,
  "jti": "jwt_abc123xyz789"
}
```

**Token Expiration:**
- Access tokens: 15 minutes to 1 hour
- Token refresh: Supported via separate endpoint (implementation TBD)

**Multi-tenancy:**
- Company context extracted from JWT token `org_id` claim
- All leave operations are scoped to the user's company (from token)
- SuperAdmin must specify company context for leave operations

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

#### Employee
**Access Scope:** Own leave requests only
**Capabilities:**
- Create leave requests
- View own leave requests
- Cancel own pending leave requests
- Cannot approve or reject any leave requests

#### Manager
**Access Scope:** Leave requests assigned to them for approval
**Capabilities:**
- View leave requests assigned to them for approval
- Approve or reject assigned employee leave requests
- Cannot approve or reject own leave requests
- Cannot view leave requests not assigned to them

#### HR
**Access Scope:** Company-wide leave visibility, final approver for employee and manager leave
**Capabilities:**
- View all company leave requests
- Approve or reject employee leave requests (after manager approval)
- Approve or reject manager leave requests
- Cannot approve or reject own leave requests
- Cannot approve at manager stage

#### CEO
**Access Scope:** Company-wide leave visibility, final approver for HR leave
**Capabilities:**
- View all company leave requests
- Approve or reject HR leave requests
- Cannot approve or reject own leave requests
- Cannot approve at manager or HR stage (only HR leave)

#### SuperAdmin
**Access Scope:** Global platform access, but leave operations are company-scoped
**Capabilities:**
- Can view leave requests across all companies (with proper company context)
- Cannot create leave requests (not an employee)
- Cannot approve or reject leave requests (not part of approval chain)

### 3.2 Permission Matrix

| Action | Employee | Manager | HR | CEO | SuperAdmin |
|--------|----------|---------|----|----|-----------|
| Create leave | ✅ | ✅ | ✅ | ✅ | ❌ |
| View own leaves | ✅ | ✅ | ✅ | ✅ | ❌ |
| View assigned leaves | ❌ | ✅ | ❌ | ❌ | ❌ |
| View all company leaves | ❌ | ❌ | ✅ | ✅ | ✅* |
| Approve (manager stage) | ❌ | ✅** | ❌ | ❌ | ❌ |
| Approve (HR stage) | ❌ | ❌ | ✅** | ❌ | ❌ |
| Approve (CEO stage) | ❌ | ❌ | ❌ | ✅** | ❌ |
| Reject (manager stage) | ❌ | ✅** | ❌ | ❌ | ❌ |
| Reject (HR stage) | ❌ | ❌ | ✅** | ❌ | ❌ |
| Reject (CEO stage) | ❌ | ❌ | ❌ | ✅** | ❌ |
| Cancel own pending leave | ✅ | ✅ | ✅ | ✅ | ❌ |

*SuperAdmin requires company context
**Only for assigned/eligible leave requests, cannot approve own leave

---

## 4. Resources & Endpoints

### 4.1 Resource Overview

#### LeaveRequest
**Description:** Represents a request for leave submitted by an employee. The request follows a role-based approval workflow and ends in a terminal state.

**Key Attributes:**
- `id` (UUID): Unique identifier
- `employee_id` (UUID): Applicant employee
- `company_id` (UUID): Owning company
- `leave_type` (ENUM): Type of leave (CASUAL, SICK, PAID, UNPAID)
- `start_date` (Date): Leave start date (inclusive, ISO 8601 format)
- `end_date` (Date): Leave end date (inclusive, ISO 8601 format)
- `day_type` (ENUM): Full or half day (FULL_DAY, FIRST_HALF, SECOND_HALF)
- `number_of_days` (Decimal): Calculated duration (derived)
- `reason` (String): Reason for leave (mandatory)
- `manager_status` (ENUM): Manager workflow status (PENDING_MANAGER, APPROVED_MANAGER, REJECTED_MANAGER, CANCELLED)
- `manager_approver_id` (UUID): Assigned manager approver
- `manager_approved_at` (DateTime): Approval timestamp (nullable, UTC)
- `manager_rejection_reason` (String): Reason for rejection (mandatory if rejected)
- `hr_status` (ENUM): HR workflow status (PENDING_HR, APPROVED_HR, REJECTED_HR, CANCELLED)
- `hr_approver_id` (UUID): Assigned HR approver
- `hr_approved_at` (DateTime): Approval timestamp (nullable, UTC)
- `hr_rejection_reason` (String): Reason for rejection (mandatory if rejected)
- `created_at` (DateTime): Submission time (immutable, UTC)
- `updated_at` (DateTime): Last update time (UTC)

**ENUM Definitions:**

**LeaveType:**
- `CASUAL`: Casual leave
- `SICK`: Sick leave
- `PAID`: Paid leave
- `UNPAID`: Unpaid leave

**DayType:**
- `FULL_DAY`: Full day leave
- `FIRST_HALF`: First half of the day
- `SECOND_HALF`: Second half of the day

**ManagerStatus:**
- `PENDING_MANAGER`: Awaiting manager approval
- `APPROVED_MANAGER`: Approved by manager
- `REJECTED_MANAGER`: Rejected by manager
- `CANCELLED`: Cancelled by applicant

**HrStatus:**
- `PENDING_HR`: Awaiting HR approval
- `APPROVED_HR`: Approved by HR
- `REJECTED_HR`: Rejected by HR
- `CANCELLED`: Cancelled by applicant

**Relationships:**
- LeaveRequest belongs to exactly one Employee (applicant)
- LeaveRequest belongs to exactly one Company
- LeaveRequest has exactly one Manager approver
- LeaveRequest has exactly one HR approver
- CEO acts as final approver for HR leave (no separate CEO approver field)

### 4.2 Endpoint Summary

| Method | Path | Purpose | Authentication |
|--------|------|---------|---------------|
| GET | `/api/v1/company/leaves` | List leave requests with pagination, filtering, sorting | Required |
| POST | `/api/v1/company/leaves` | Create new leave request | Required |
| GET | `/api/v1/company/leaves/{leave_id}` | Get leave request details | Required |
| POST | `/api/v1/company/leaves/{leave_id}/action` | Approve, reject, or cancel leave request | Required |

### 4.3 API Documentation Class (Rule 10)

**Note:** All endpoint documentation MUST use the centralized `LeaveApiDocs` class structure (Rule 10). Router endpoints MUST reference `summary` and `description` from this class, NOT hardcoded strings.

**Documentation Class Structure:**

```python
# src/leaves/documentations/leave_api_doc.py
from typing import ClassVar

class LeaveApiDocs:
    """API documentation for Leave endpoints"""
    
    list: ClassVar[dict] = {
        "summary": "Purpose of this API is to list leave requests with pagination, filtering, and sorting",
        "description": "Retrieves a paginated list of leave requests based on user role. Employees see only their own leave requests. Managers see leave requests assigned to them for approval. HR and CEO see all company leave requests. Supports filtering by status, date range, employee, and pending_for_me flag. Includes pagination with navigation URLs. Requires JWT authentication."
    }
    
    create: ClassVar[dict] = {
        "summary": "Purpose of this API is to create a new leave request",
        "description": "Creates a new leave request for the authenticated user. Requires manager_approver_id and hr_approver_id (both must be in the same company). Validates overlapping leave requests, non-working days (weekends/holidays), and employee active status. Calculates number_of_days from date range and day_type. Sets initial manager_status to PENDING_MANAGER and hr_status to PENDING_HR. Triggers notification to manager approver. Only active employees can create leave requests."
    }
    
    get: ClassVar[dict] = {
        "summary": "Purpose of this API is to get leave request details",
        "description": "Retrieves detailed leave request information. Employees can view only their own leave requests. Managers can view leave requests assigned to them. HR and CEO can view all company leave requests. Includes both manager_status and hr_status. Supports ETag-based cache validation with If-None-Match header. Requires JWT authentication."
    }
    
    action: ClassVar[dict] = {
        "summary": "Purpose of this API is to approve, reject, or cancel a leave request",
        "description": "Performs approve, reject, or cancel action on a leave request. Approve: User must be the assigned approver at the current workflow stage. Reject: User must be the assigned approver at the current workflow stage, rejection_reason is mandatory. Cancel: Only the applicant can cancel, and only if status is pending. Requires If-Match header for concurrency control. Triggers notifications on approve/reject (not on cancel). Updates workflow status and timestamps accordingly."
    }
```

### 4.4 Endpoint Details

#### 4.4.1 GET /api/v1/company/leaves

- **Purpose:** List leave requests with pagination, filtering, and sorting
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** 
  - Employee: Own leave requests only
  - Manager: Leave requests assigned to them for approval
  - HR: All company leave requests
  - CEO: All company leave requests
  - SuperAdmin: All companies (requires company context)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-None-Match`: ETag value from previous GET (optional, for cache validation - returns 304 if unchanged)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
- **Idempotency:** Yes (GET is idempotent)

**Path Parameters**  
None

**Query Parameters**  
**Note:** Query parameters MUST be defined using a query schema class with `Depends()` pattern (Rule 9), NOT individual `Query()` parameters in the router endpoint.

**Query Schema Class (REQUIRED):**
```python
class LeaveListQuery(BaseModel):
    """Query schema for listing leave requests with pagination and filtering."""

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    status: Optional[str] = Field(None, description="Filter by manager_status or hr_status: PENDING_MANAGER, APPROVED_MANAGER, REJECTED_MANAGER, PENDING_HR, APPROVED_HR, REJECTED_HR, CANCELLED")
    start_date: Optional[str] = Field(None, description="Filter by start_date (ISO 8601 date format: YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Filter by end_date (ISO 8601 date format: YYYY-MM-DD)")
    employee_id: Optional[str] = Field(None, description="Filter by employee_id (UUID format, HR/CEO only)")
    pending_for_me: Optional[bool] = Field(None, description="Filter to show only leave requests awaiting current user's approval (true/false)")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, start_date, end_date")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)
```

**Router Endpoint Pattern (REQUIRED):**
```python
@router.get("", response_model=StandardResponse[LeavePaginatedResponse])
async def list_leaves(
    query: LeaveListQuery = Depends(LeaveListQuery),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List leave requests with pagination and filtering."""
    # Access via query.page, query.page_size, query.status, etc.
```

**Query Parameters Table (for documentation only):**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number (≥ 1) |
| page_size | integer | No | 20 | Page size (1-100) |
| status | string | No | null | Filter by status (PENDING_MANAGER, APPROVED_MANAGER, REJECTED_MANAGER, PENDING_HR, APPROVED_HR, REJECTED_HR, CANCELLED) |
| start_date | string | No | null | Filter by start_date (ISO 8601: YYYY-MM-DD) |
| end_date | string | No | null | Filter by end_date (ISO 8601: YYYY-MM-DD) |
| employee_id | string (UUID) | No | null | Filter by employee_id (HR/CEO only, validated server-side) |
| pending_for_me | boolean | No | null | Filter to show only leave requests awaiting current user's approval |
| sort_by | string | No | created_at | Sort field: created_at, updated_at, start_date, end_date |
| sort_order | string | No | desc | Sort order: asc or desc |

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "items": [
      {
        "id": "770e8400-e29b-41d4-a716-446655440000",
        "employee_id": "550e8400-e29b-41d4-a716-446655440000",
        "employee": {
          "id": "550e8400-e29b-41d4-a716-446655440000",
          "first_name": "John",
          "last_name": "Doe"
        },
        "leave_type": "CASUAL",
        "start_date": "2024-02-15",
        "end_date": "2024-02-17",
        "day_type": "FULL_DAY",
        "number_of_days": 3.0,
        "manager_status": "APPROVED_MANAGER",
        "hr_status": "PENDING_HR",
        "created_at": "2024-02-10T10:30:00Z"
      }
    ],
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8,
    "next_page": "/api/v1/company/leaves?page=2&page_size=20&sort_by=created_at&sort_order=desc",
    "prev_page": null
  },
  "message": "Leave requests retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- For paginated responses, `next_page` and `prev_page` should include all query parameters (filters, sort, search) to preserve pagination state.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | INVALID_REQUEST | Invalid query parameter format |
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks required permissions (e.g., Employee trying to filter by employee_id) |
| 304 | Not Modified | GET request with If-None-Match - resource unchanged, ETag matches (no response body) |

Example error (400 Bad Request):
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "details": [{"field": "start_date", "issue": "Invalid date format. Expected ISO 8601 format (YYYY-MM-DD)."}]
  },
  "message": "Invalid request parameters."
}
```

---

#### 4.4.2 POST /api/v1/company/leaves

- **Purpose:** Create a new leave request
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** 
  - Employee, Manager, HR, CEO: Can create leave requests
  - SuperAdmin: Cannot create leave requests (not an employee)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
- **Idempotency:** No (POST is not idempotent)

**Path Parameters**  
None

**Query Parameters**  
None

**Request Body**

**Schema Table:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| leave_type | string | Yes | Type of leave | Enum: CASUAL, SICK, PAID, UNPAID (case-sensitive) |
| start_date | string | Yes | Leave start date (inclusive) | ISO 8601 date format (YYYY-MM-DD), must be working day (not weekend/holiday), must be >= today |
| end_date | string | Yes | Leave end date (inclusive) | ISO 8601 date format (YYYY-MM-DD), must be >= start_date, must be working day (not weekend/holiday) |
| day_type | string | Yes | Full or half day | Enum: FULL_DAY, FIRST_HALF, SECOND_HALF (case-sensitive) |
| reason | string | Yes | Reason for leave | Min 10 characters, max 500 characters |
| manager_approver_id | string (UUID) | Yes | Manager approver ID | RFC 4122 UUID v4 format, must exist in same company, must have Manager role |
| hr_approver_id | string (UUID) | Yes | HR approver ID | RFC 4122 UUID v4 format, must exist in same company, must have HR role |

**Request Body Example:**
```json
{
  "leave_type": "CASUAL",
  "start_date": "2024-02-15",
  "end_date": "2024-02-17",
  "day_type": "FULL_DAY",
  "reason": "Family vacation planned for long weekend",
  "manager_approver_id": "880e8400-e29b-41d4-a716-446655440000",
  "hr_approver_id": "990e8400-e29b-41d4-a716-446655440000"
}
```

**Success Response (201 Created)**

```json
{
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "employee_id": "550e8400-e29b-41d4-a716-446655440000",
    "company_id": "660e8400-e29b-41d4-a716-446655440001",
    "leave_type": "CASUAL",
    "start_date": "2024-02-15",
    "end_date": "2024-02-17",
    "day_type": "FULL_DAY",
    "number_of_days": 3.0,
    "reason": "Family vacation planned for long weekend",
    "manager_status": "PENDING_MANAGER",
    "manager_approver_id": "880e8400-e29b-41d4-a716-446655440000",
    "hr_status": "PENDING_HR",
    "hr_approver_id": "990e8400-e29b-41d4-a716-446655440000",
    "created_at": "2024-02-10T10:30:00Z",
    "updated_at": "2024-02-10T10:30:00Z"
  },
  "message": "Leave request created successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | INVALID_REQUEST | Invalid request format or missing required fields |
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks required permissions (e.g., SuperAdmin) |
| 404 | EMPLOYEE_NOT_FOUND | Authenticated user is not an employee |
| 422 | VALIDATION_ERROR | Field validation failed (date format, enum values, etc.) |
| 422 | BUSINESS_RULE_FAILED | Business rule violation (overlapping leave, non-working day, inactive employee, invalid approver) |
| 409 | OVERLAPPING_LEAVE_REQUEST | Leave request overlaps with existing leave for same employee |
| 409 | INVALID_WORKING_DAY | Leave request includes weekend or holiday |
| 409 | INVALID_APPROVER | Approver ID is invalid (wrong company, wrong role, or does not exist) |

Example error (422 Validation Error):
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "details": [
      {"field": "start_date", "issue": "Invalid date format. Expected ISO 8601 format (YYYY-MM-DD)."},
      {"field": "reason", "issue": "Reason must be at least 10 characters."}
    ]
  },
  "message": "Validation failed."
}
```

Example error (422 Business Rule Failed):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [
      {"field": "employee", "issue": "Employee is not active. Deactivated employees cannot submit leave requests."}
    ]
  },
  "message": "Business rule violation: Employee must be active to submit leave requests."
}
```

Example error (409 Overlapping Leave):
```json
{
  "error": {
    "code": "OVERLAPPING_LEAVE_REQUEST",
    "details": [
      {"field": "date_range", "issue": "Leave request overlaps with existing leave request (2024-02-14 to 2024-02-16). Overlapping leave requests for the same employee are not allowed."}
    ]
  },
  "message": "Leave request overlaps with existing leave request."
}
```

Example error (409 Invalid Approver):
```json
{
  "error": {
    "code": "INVALID_APPROVER",
    "details": [
      {"field": "manager_approver_id", "issue": "Manager approver does not exist, is not in the same company, or does not have Manager role."}
    ]
  },
  "message": "Invalid approver specified."
}
```

**Business Rules:**
- Overlapping leave requests for the same employee are not allowed
- Leave on weekends or holidays is not allowed
- Deactivated employees cannot submit leave requests
- `manager_approver_id` and `hr_approver_id` must exist in the same company
- `manager_approver_id` must have Manager role
- `hr_approver_id` must have HR role
- `number_of_days` is calculated from date range and `day_type` (half-days count as 0.5)
- Initial `manager_status` is set to `PENDING_MANAGER`
- Initial `hr_status` is set to `PENDING_HR`
- Notification is triggered to manager approver (via F-003)

---

#### 4.4.3 GET /api/v1/company/leaves/{leave_id}

- **Purpose:** Get leave request details
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** 
  - Employee: Own leave requests only
  - Manager: Leave requests assigned to them for approval
  - HR: All company leave requests
  - CEO: All company leave requests
  - SuperAdmin: All companies (requires company context)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-None-Match`: ETag value from previous GET (optional, for cache validation - returns 304 if unchanged)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
    - `ETag`: Resource version identifier based on `updated_at` (REQUIRED for resources that support updates)
    - `Last-Modified`: Timestamp of last modification from `updated_at` field (RECOMMENDED)
- **Idempotency:** Yes (GET is idempotent)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| leave_id | string (UUID) | Yes | Leave request ID |

**Note:** All path parameters MUST use snake_case (e.g., `leave_id`) - see Rule 2.

**Query Parameters**  
None

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "employee_id": "550e8400-e29b-41d4-a716-446655440000",
    "employee": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "first_name": "John",
      "last_name": "Doe"
    },
    "company_id": "660e8400-e29b-41d4-a716-446655440001",
    "leave_type": "CASUAL",
    "start_date": "2024-02-15",
    "end_date": "2024-02-17",
    "day_type": "FULL_DAY",
    "number_of_days": 3.0,
    "reason": "Family vacation planned for long weekend",
    "manager_status": "APPROVED_MANAGER",
    "manager_approver_id": "880e8400-e29b-41d4-a716-446655440000",
    "manager_approved_at": "2024-02-11T14:30:00Z",
    "manager_rejection_reason": null,
    "hr_status": "PENDING_HR",
    "hr_approver_id": "990e8400-e29b-41d4-a716-446655440000",
    "hr_approved_at": null,
    "hr_rejection_reason": null,
    "created_at": "2024-02-10T10:30:00Z",
    "updated_at": "2024-02-11T14:30:00Z"
  },
  "message": "Leave request retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240211T143000Z"` (REQUIRED for resources that support updates, based on `updated_at`)
- `Last-Modified: Wed, 11 Feb 2024 14:30:00 GMT` (RECOMMENDED)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks required permissions (e.g., Employee trying to view another employee's leave) |
| 404 | LEAVE_REQUEST_NOT_FOUND | Leave request not found or user does not have access |
| 304 | Not Modified | GET request with If-None-Match - resource unchanged, ETag matches (no response body) |

Example error (404 Not Found):
```json
{
  "error": {
    "code": "LEAVE_REQUEST_NOT_FOUND",
    "details": [{"field": "leave_id", "issue": "Leave request not found or you do not have access to this leave request."}]
  },
  "message": "Leave request not found."
}
```

---

#### 4.4.4 POST /api/v1/company/leaves/{leave_id}/action

- **Purpose:** Approve, reject, or cancel a leave request
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** 
  - Employee: Can cancel own pending leave requests
  - Manager: Can approve/reject assigned employee leave requests at manager stage
  - HR: Can approve/reject employee/manager leave requests at HR stage
  - CEO: Can approve/reject HR leave requests at CEO stage
  - Cannot approve/reject own leave requests
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-Match`: ETag value from GET response (REQUIRED for concurrency control - ETag from GET response, based on `updated_at`)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **MUST be present in ALL responses**
- **Idempotency:** No (POST is not idempotent, but action validation prevents duplicate approvals)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| leave_id | string (UUID) | Yes | Leave request ID |

**Note:** All path parameters MUST use snake_case (e.g., `leave_id`) - see Rule 2.

**Query Parameters**  
None

**Request Body**

**Schema Table:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| action | string | Yes | Action to perform | Enum: approve, reject, cancel (case-sensitive, lowercase) |
| rejection_reason | string | No | Reason for rejection | Required if action is "reject", min 10 characters, max 500 characters |

**Request Body Examples:**

Approve:
```json
{
  "action": "approve"
}
```

Reject:
```json
{
  "action": "reject",
  "rejection_reason": "Critical project deadline during requested leave period. Cannot approve due to work dependency."
}
```

Cancel:
```json
{
  "action": "cancel"
}
```

**Success Response (200 OK)**

```json
{
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "employee_id": "550e8400-e29b-41d4-a716-446655440000",
    "company_id": "660e8400-e29b-41d4-a716-446655440001",
    "leave_type": "CASUAL",
    "start_date": "2024-02-15",
    "end_date": "2024-02-17",
    "day_type": "FULL_DAY",
    "number_of_days": 3.0,
    "reason": "Family vacation planned for long weekend",
    "manager_status": "APPROVED_MANAGER",
    "manager_approver_id": "880e8400-e29b-41d4-a716-446655440000",
    "manager_approved_at": "2024-02-11T14:30:00Z",
    "manager_rejection_reason": null,
    "hr_status": "APPROVED_HR",
    "hr_approver_id": "990e8400-e29b-41d4-a716-446655440000",
    "hr_approved_at": "2024-02-12T09:15:00Z",
    "hr_rejection_reason": null,
    "created_at": "2024-02-10T10:30:00Z",
    "updated_at": "2024-02-12T09:15:00Z"
  },
  "message": "Leave request approved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240212T091500Z"` (New ETag after update, based on new `updated_at`)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | INVALID_REQUEST | Invalid request format or missing required fields |
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks required permissions (e.g., Employee trying to approve, Manager trying to approve at HR stage) |
| 404 | LEAVE_REQUEST_NOT_FOUND | Leave request not found or user does not have access |
| 412 | PRECONDITION_FAILED | ETag mismatch (If-Match header provided but resource was modified since retrieval) |
| 422 | VALIDATION_ERROR | Field validation failed (action enum, rejection_reason format) |
| 422 | BUSINESS_RULE_FAILED | Business rule violation (cannot approve own leave, cannot cancel after approval/rejection, cannot approve at wrong stage, action not allowed in current state) |
| 428 | PRECONDITION_REQUIRED | Missing required If-Match header |

Example error (412 Precondition Failed):
```json
{
  "error": {
    "code": "PRECONDITION_FAILED",
    "details": [{"field": "etag", "issue": "Resource has been modified since retrieval. Please fetch the latest version and retry."}]
  },
  "message": "Resource version mismatch. The resource was modified by another user."
}
```

Example error (422 Business Rule Failed - Cannot Approve Own Leave):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [{"field": "action", "issue": "Cannot approve or reject your own leave request. Approvers must not approve their own leave."}]
  },
  "message": "Business rule violation: Cannot approve own leave request."
}
```

Example error (422 Business Rule Failed - Invalid Action State):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [{"field": "action", "issue": "Cannot cancel leave request. Leave request is already approved or rejected. Only pending leave requests can be cancelled."}]
  },
  "message": "Business rule violation: Leave request cannot be cancelled in current state."
}
```

Example error (422 Business Rule Failed - Wrong Approval Stage):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [{"field": "action", "issue": "Cannot approve at this stage. Leave request is at HR stage, but you are a Manager. Managers can only approve at manager stage."}]
  },
  "message": "Business rule violation: Cannot approve at incorrect workflow stage."
}
```

Example error (422 Validation Error - Missing Rejection Reason):
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "details": [{"field": "rejection_reason", "issue": "Rejection reason is mandatory when action is 'reject'."}]
  },
  "message": "Validation failed: Rejection reason is required for reject action."
}
```

**Business Rules:**

**Approve Action:**
- User must be the assigned approver at the current workflow stage
- Cannot approve own leave request
- Manager can only approve at manager stage (`manager_status = PENDING_MANAGER`)
- HR can only approve at HR stage (`hr_status = PENDING_HR` and `manager_status = APPROVED_MANAGER`)
- CEO can only approve HR leave at CEO stage (`hr_status = PENDING_HR` and applicant role is HR)
- Updates appropriate status to `APPROVED_*` and sets `*_approved_at` timestamp
- If manager approves, workflow moves to HR stage (`hr_status` remains `PENDING_HR`)
- If HR approves, workflow completes (`hr_status = APPROVED_HR`)
- Triggers notification to next approver or applicant (via F-003)

**Reject Action:**
- User must be the assigned approver at the current workflow stage
- Cannot reject own leave request
- `rejection_reason` is mandatory
- Manager can only reject at manager stage
- HR can only reject at HR stage
- CEO can only reject HR leave at CEO stage
- Updates appropriate status to `REJECTED_*` and sets `*_rejection_reason`
- Workflow terminates (no further approvals possible)
- Triggers notification to applicant (via F-003)

**Cancel Action:**
- Only the applicant (employee who created the leave request) can cancel
- Can only cancel if leave request is pending (not approved or rejected)
- Sets both `manager_status` and `hr_status` to `CANCELLED`
- Does not trigger notification (per feature brief)
- Workflow terminates

**Workflow State Transitions:**

**Employee Leave:**
1. Created → `manager_status = PENDING_MANAGER`, `hr_status = PENDING_HR`
2. Manager approves → `manager_status = APPROVED_MANAGER`, `hr_status = PENDING_HR`
3. HR approves → `hr_status = APPROVED_HR` (complete)
4. Manager rejects → `manager_status = REJECTED_MANAGER` (terminated)
5. HR rejects → `hr_status = REJECTED_HR` (terminated)

**Manager Leave:**
1. Created → `manager_status = PENDING_MANAGER`, `hr_status = PENDING_HR`
2. Manager stage skipped (manager is applicant) → `manager_status = APPROVED_MANAGER`, `hr_status = PENDING_HR`
3. HR approves → `hr_status = APPROVED_HR` (complete)
4. HR rejects → `hr_status = REJECTED_HR` (terminated)

**HR Leave:**
1. Created → `manager_status = PENDING_MANAGER`, `hr_status = PENDING_HR`
2. Manager stage skipped → `manager_status = APPROVED_MANAGER`, `hr_status = PENDING_HR`
3. HR stage skipped (HR is applicant) → `hr_status = APPROVED_HR` (CEO approval required, but no CEO approver field - handled via role check)
4. CEO approves → `hr_status = APPROVED_HR` (complete)
5. CEO rejects → `hr_status = REJECTED_HR` (terminated)

---

## 5. Webhooks / Async Behavior

### 5.1 Notifications (F-003 Integration)

**Trigger Events:**
- Leave request created → Notification to manager approver
- Leave request approved (manager stage) → Notification to HR approver and applicant
- Leave request approved (HR stage) → Notification to applicant
- Leave request rejected (manager stage) → Notification to applicant
- Leave request rejected (HR stage) → Notification to applicant

**Not Triggered:**
- Leave request cancelled → No notification (per feature brief)

**Notification Details:**
- Notification system (F-003) handles email and in-app notifications
- Notification payload includes leave request details and action taken
- Implementation details are in F-003 specification

---

## 6. Rate Limiting & Performance

### 6.1 Rate Limiting
- **Default**: 100 requests per minute per user (configurable)
- **Burst**: Up to 10 requests per second
- **Rate Limit Headers**: Included in responses (if applicable)

### 6.2 Performance Considerations
- List endpoint supports pagination to limit response size
- Filtering and sorting are performed server-side
- ETag-based cache validation reduces bandwidth for unchanged resources
- Database indexes recommended on: `employee_id`, `company_id`, `manager_status`, `hr_status`, `start_date`, `end_date`

---

## 7. Open Questions

None identified at this stage.

---

## 8. Assumptions

1. **Employee Management (F-005)**: Employee data, manager relationships, and active status are available
2. **RBAC (F-002)**: Role-based permissions and access control are enforced
3. **Notifications (F-003)**: Notification system handles email and in-app notifications for leave events
4. **Working Days**: System has access to working day calendar (weekends and holidays are excluded)
5. **Company Context**: All operations are scoped to the company from JWT token `org_id` claim
6. **Approver Assignment**: Users provide `manager_approver_id` and `hr_approver_id` during creation, validated to be in same company with correct roles
7. **Number of Days Calculation**: Calculated from date range and `day_type` (half-days = 0.5, full days = 1.0 per day)
8. **Concurrency Control**: ETags based on `updated_at` timestamp prevent lost updates
9. **Status Representation**: Both `manager_status` and `hr_status` are exposed separately (no computed overall status)
10. **Cancellation**: Only applicant can cancel, only while pending, no notification triggered

---

## 9. Response Schema Definitions

### 9.1 LeaveSummary (List Item)

```json
{
  "id": "string (UUID)",
  "employee_id": "string (UUID)",
  "employee": {
    "id": "string (UUID)",
    "first_name": "string",
    "last_name": "string"
  },
  "leave_type": "string (ENUM)",
  "start_date": "string (ISO 8601 date)",
  "end_date": "string (ISO 8601 date)",
  "day_type": "string (ENUM)",
  "number_of_days": "number (decimal)",
  "manager_status": "string (ENUM)",
  "hr_status": "string (ENUM)",
  "created_at": "string (ISO 8601 datetime UTC)"
}
```

### 9.2 LeaveDetail (Detail Response)

```json
{
  "id": "string (UUID)",
  "employee_id": "string (UUID)",
  "employee": {
    "id": "string (UUID)",
    "first_name": "string",
    "last_name": "string"
  },
  "company_id": "string (UUID)",
  "leave_type": "string (ENUM)",
  "start_date": "string (ISO 8601 date)",
  "end_date": "string (ISO 8601 date)",
  "day_type": "string (ENUM)",
  "number_of_days": "number (decimal)",
  "reason": "string",
  "manager_status": "string (ENUM)",
  "manager_approver_id": "string (UUID)",
  "manager_approved_at": "string (ISO 8601 datetime UTC) | null",
  "manager_rejection_reason": "string | null",
  "hr_status": "string (ENUM)",
  "hr_approver_id": "string (UUID)",
  "hr_approved_at": "string (ISO 8601 datetime UTC) | null",
  "hr_rejection_reason": "string | null",
  "created_at": "string (ISO 8601 datetime UTC)",
  "updated_at": "string (ISO 8601 datetime UTC)"
}
```

### 9.3 LeaveCreateRequest

```json
{
  "leave_type": "string (ENUM: CASUAL, SICK, PAID, UNPAID)",
  "start_date": "string (ISO 8601 date: YYYY-MM-DD)",
  "end_date": "string (ISO 8601 date: YYYY-MM-DD)",
  "day_type": "string (ENUM: FULL_DAY, FIRST_HALF, SECOND_HALF)",
  "reason": "string (min 10, max 500 characters)",
  "manager_approver_id": "string (UUID)",
  "hr_approver_id": "string (UUID)"
}
```

### 9.4 LeaveActionRequest

```json
{
  "action": "string (ENUM: approve, reject, cancel)",
  "rejection_reason": "string (min 10, max 500 characters) | null (required if action is reject)"
}
```

### 9.5 LeavePaginatedResponse

```json
{
  "items": "array of LeaveSummary",
  "total": "integer",
  "page": "integer",
  "page_size": "integer",
  "total_pages": "integer",
  "next_page": "string (URL) | null",
  "prev_page": "string (URL) | null"
}
```

---

## 10. Error Code Reference

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| UNAUTHENTICATED | 401 | Missing or invalid authentication token |
| TOKEN_EXPIRED | 401 | JWT token has expired |
| INVALID_TOKEN | 401 | Malformed token or missing required claims |
| INSUFFICIENT_PERMISSIONS | 403 | User lacks required permissions |
| LEAVE_REQUEST_NOT_FOUND | 404 | Leave request not found or user does not have access |
| EMPLOYEE_NOT_FOUND | 404 | Authenticated user is not an employee |
| INVALID_REQUEST | 400 | Invalid request format or missing required fields |
| VALIDATION_ERROR | 422 | Field validation failed |
| BUSINESS_RULE_FAILED | 422 | Business rule violation |
| OVERLAPPING_LEAVE_REQUEST | 409 | Leave request overlaps with existing leave |
| INVALID_WORKING_DAY | 409 | Leave request includes weekend or holiday |
| INVALID_APPROVER | 409 | Approver ID is invalid (wrong company, wrong role, or does not exist) |
| PRECONDITION_FAILED | 412 | ETag mismatch in conditional request |
| PRECONDITION_REQUIRED | 428 | Missing required If-Match header |
| INTERNAL_ERROR | 500 | Server error |

---

**End of API Specification**

