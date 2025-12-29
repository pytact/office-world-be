# API Specification: F-010 — Attendance Management

## 1. Overview

The Attendance Management API provides a server-time–driven, immutable system to track daily employee presence via check-in and check-out events. It ensures accurate worked-time calculation across refreshes and sessions, enforces strict role-based visibility (excluding SuperAdmin), automatically handles missed check-outs at midnight, and avoids approvals, edits, or payroll coupling.

**Key Features:**
- Server-time–based attendance tracking (UTC timestamps)
- Immutable attendance records (no edits after CHECKED_OUT)
- Mandatory check-out (auto check-out at employee's local midnight if missed)
- Live working-time counter (calculated client-side using check-in time from API)
- Role-based access control (Employee, Manager, HR, CEO)
- SuperAdmin explicitly excluded from all attendance endpoints
- Deactivated employees cannot access attendance features

**Out of Scope:**
- Break tracking
- Manual attendance edits or corrections
- Attendance approval workflows
- Payroll or salary calculations
- SuperAdmin access to attendance data

---

## 2. Global API Rules

### 2.1 Authentication

**JWT Token Structure:**
All API endpoints require JWT Bearer token authentication.

**Token Format:** `Authorization: Bearer <jwt_token>`

**Required Claims in JWT Payload:**
- `sub` (subject): User ID (string, UUID format) - **REQUIRED**
- `role`: User role (string) - **REQUIRED** - Encoded in token, not database lookup
- `org_id`: Organization ID (string, UUID format, nullable) - **REQUIRED** - `null` for SuperAdmin, UUID for org-scoped users
- `exp`: Token expiration timestamp (integer, Unix timestamp) - **REQUIRED**
- `iat`: Token issued at timestamp (integer, Unix timestamp) - **RECOMMENDED**
- `jti`: JWT ID (string, unique token identifier) - **RECOMMENDED** for token revocation

**JWT Payload Example:**
```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "role": "employee",
  "org_id": "123e4567-e89b-12d3-a456-426614174000",
  "exp": 1735689600,
  "iat": 1735686000,
  "jti": "jwt_abc123xyz789"
}
```

**Role Encoding:**
- Roles MUST be encoded in JWT token (not database lookup during request)
- Role values: Use lowercase (e.g., `"superadmin"`, `"employee"`, `"manager"`, `"hr"`, `"ceo"`)
- SuperAdmin role: `org_id` MUST be `null` (indicates global access)
- Organization-scoped roles: `org_id` MUST contain organization UUID

**Token Validation:**
- Server MUST validate token signature, expiration, and required claims
- Missing or invalid token: Return `401 UNAUTHENTICATED`
- Expired token: Return `401 UNAUTHENTICATED` with error code `TOKEN_EXPIRED`
- Missing required claims: Return `401 UNAUTHENTICATED` with error code `INVALID_TOKEN`

**Error Responses for Authentication:**
- `401 UNAUTHENTICATED`: Missing, invalid, or expired token
  - Error code: `UNAUTHENTICATED`, `TOKEN_EXPIRED`, or `INVALID_TOKEN`
  - Example: `{"error": {"code": "TOKEN_EXPIRED", "details": []}, "message": "JWT token has expired. Please refresh your token."}`

### 2.2 Multi-Tenancy

- **SuperAdmin**: `org_id: null` - Has access to all organizations (but explicitly excluded from attendance endpoints)
- **Organization-scoped users** (Employee, Manager, HR, CEO): `org_id: "<uuid>"` - Access limited to specified organization
- Server MUST extract `org_id` from token for authorization checks
- All attendance data is scoped to the organization from the token's `org_id` claim

### 2.3 Timezone Standard

**All datetime fields MUST use UTC timezone** (ISO 8601 format with `Z` suffix).

- Format: `YYYY-MM-DDTHH:mm:ssZ` (e.g., `2024-01-20T10:30:00Z`)
- All `created_at`, `updated_at`, `check_in_time`, `check_out_time`, `action_time` fields are in UTC
- Date-only fields: `YYYY-MM-DD` format (e.g., `2024-01-20`)
- Employee timezone is used for:
  - Determining local calendar date (attendance_date)
  - Auto check-out timing (local midnight)
  - Display purposes (client converts UTC to local timezone)

### 2.4 Response Headers

**ALL responses MUST include:**
- `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`) - **REQUIRED in ALL responses**

**For GET responses (resources that support updates):**
- `ETag`: Resource version identifier based on `updated_at` timestamp (e.g., `"20240120T103000Z"`)
- `Last-Modified`: Timestamp of last modification from `updated_at` field (optional, RFC 1123 format)

**For PATCH/PUT/DELETE requests:**
- `If-Match`: ETag value from GET response (REQUIRED for concurrency control)

**For GET requests (cache validation):**
- `If-None-Match`: ETag value from previous GET (optional, returns 304 if unchanged)

---

## 3. Roles & Permissions

| Role | View Today's Attendance | View Own History | Check-In/Check-Out | View Company Attendance List | View Company Attendance Detail |
|------|------------------------|------------------|-------------------|------------------------------|-------------------------------|
| **Employee** | Own only | Own only | Own only | ❌ No access | ❌ No access |
| **Manager** | Own only | Own only | Own only | ✅ Employees in scope | ✅ Employees in scope |
| **HR** | Own only | Own only | Own only | ✅ Full company | ✅ Full company |
| **CEO** | Own only | Own only | Own only | ✅ Full company | ✅ Full company |
| **SuperAdmin** | ❌ Explicitly excluded | ❌ Explicitly excluded | ❌ Explicitly excluded | ❌ Explicitly excluded | ❌ Explicitly excluded |
| **Deactivated Employee** | ❌ No access | ❌ No access | ❌ No access | ❌ No access | ❌ No access |

**Access Control Rules:**
- **Employees**: Can view only their own attendance (today and history), can check-in/out for themselves only
- **Managers**: Can view attendance for all employees in their scope (via company endpoints), can check-in/out for themselves only
- **HR/CEO**: Full attendance visibility across the company (via company endpoints), can check-in/out for themselves only
- **SuperAdmin**: Cannot access or view attendance data (explicitly excluded from all endpoints)
- **Deactivated Employees**: Cannot view attendance history or perform check-in/check-out actions

**Business Rules:**
- Historical attendance data remains stored even after employee deactivation
- Deactivated employees cannot view their own attendance history
- SuperAdmin must never receive attendance data (explicitly excluded from all attendance endpoints)

---

## 4. Resources & Endpoints

### 4.1 Resource Overview

**Attendance Resource:**
- Represents a single employee's attendance for one calendar day
- Exactly one attendance record exists per employee per day
- Status transitions: `NOT_STARTED` → `CHECKED_IN` → `CHECKED_OUT`
- Immutable after `CHECKED_OUT` status
- Auto check-out occurs at employee's local midnight if manual check-out is missed

**AttendanceLog Resource:**
- Immutable, append-only event log for attendance actions
- Records every attendance action with contextual metadata
- Action types: `CHECK_IN`, `CHECK_OUT`, `AUTO_CHECK_OUT`
- Includes location, IP address, device info for audit purposes

### 4.2 Endpoint Summary

| Method | Path | Purpose | Auth | Roles |
|--------|------|---------|------|-------|
| GET | `/v1/attendance/today` | Get today's attendance for authenticated employee | Required | Employee, Manager, HR, CEO |
| GET | `/v1/attendance` | Get paginated attendance history for authenticated employee | Required | Employee, Manager, HR, CEO |
| POST | `/v1/attendance/check-in` | Record employee check-in for current day | Required | Employee, Manager, HR, CEO |
| POST | `/v1/attendance/check-out` | Record employee check-out for current day | Required | Employee, Manager, HR, CEO |
| GET | `/v1/company/attendance` | Get paginated attendance records with filters | Required | Manager, HR, CEO |
| GET | `/v1/company/attendance/{employee_id}/{date}` | Get detailed attendance for specific employee and date | Required | Manager, HR, CEO |

**Note:** All endpoints explicitly exclude SuperAdmin and deactivated employees.

---

## 4.3 Endpoint Details

### 4.3.1 GET /v1/attendance/today

- **Purpose:** Get today's attendance data for the authenticated employee (only for today's local date)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** Employee, Manager, HR, CEO (own attendance only)
- **SuperAdmin:** Explicitly excluded
- **Deactivated Employees:** Cannot access

**Headers:**
- **Request Headers:**
  - `Authorization: Bearer <token>` (REQUIRED)
  - `If-None-Match`: ETag value from previous GET (optional, for cache validation - returns 304 if unchanged)
- **Response Headers (REQUIRED):**
  - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`)
  - `ETag`: Resource version identifier based on `updated_at` (e.g., `"20240120T103000Z"`)
  - `Last-Modified`: Timestamp of last modification (optional)

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
    "attendance": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "employee_id": "123e4567-e89b-12d3-a456-426614174000",
      "company_id": "789e0123-e45b-67c8-d901-234567890abc",
      "attendance_date": "2024-01-20",
      "check_in_time": "2024-01-20T09:12:00Z",
      "check_out_time": null,
      "status": "CHECKED_IN",
      "worked_time": null,
      "is_auto_check_out": false,
      "created_at": "2024-01-20T09:12:00Z",
      "updated_at": "2024-01-20T09:12:00Z"
    },
    "context": {
      "server_time": "2024-01-20T14:30:00Z",
      "employee_timezone": "Asia/Kolkata"
    }
  },
  "message": "Today's attendance retrieved successfully"
}
```

**Response Schema:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| attendance | object | Yes | Attendance record for today | - |
| attendance.id | string (UUID) | Yes | Attendance record ID | RFC 4122 UUID v4 format |
| attendance.employee_id | string (UUID) | Yes | Employee ID | RFC 4122 UUID v4 format |
| attendance.company_id | string (UUID) | Yes | Company ID | RFC 4122 UUID v4 format |
| attendance.attendance_date | string (date) | Yes | Local calendar date | ISO 8601 date format (YYYY-MM-DD) |
| attendance.check_in_time | string (datetime) | No | Server timestamp of check-in | ISO 8601 format, UTC timezone (Z suffix), nullable |
| attendance.check_out_time | string (datetime) | No | Server timestamp of check-out | ISO 8601 format, UTC timezone (Z suffix), nullable |
| attendance.status | string (ENUM) | Yes | Attendance lifecycle state | Enum: "NOT_STARTED", "CHECKED_IN", "CHECKED_OUT" |
| attendance.worked_time | string | No | Derived duration (e.g., "9h 29m") | Read-only, nullable if not checked out |
| attendance.is_auto_check_out | boolean | Yes | Flag indicating if check-out was automatic | Boolean |
| attendance.created_at | string (datetime) | Yes | Creation timestamp | ISO 8601 format, UTC timezone (Z suffix) |
| attendance.updated_at | string (datetime) | Yes | Last update timestamp | ISO 8601 format, UTC timezone (Z suffix) |
| context | object | Yes | Contextual information | - |
| context.server_time | string (datetime) | Yes | Current server time (UTC) | ISO 8601 format, UTC timezone (Z suffix) |
| context.employee_timezone | string | Yes | Employee's configured timezone | IANA timezone identifier (e.g., "Asia/Kolkata") |

**Note:** 
- Returns `null` for `check_in_time` and `check_out_time` if not yet set
- `worked_time` is `null` if status is `NOT_STARTED` or `CHECKED_IN`
- `worked_time` is calculated only after check-out
- UI calculates live counter by comparing `check_in_time` (from API) with current client time

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 401 | `INVALID_TOKEN` | JWT token is invalid or missing required claims |
| 403 | `INSUFFICIENT_PERMISSIONS` | SuperAdmin attempting to access (explicitly excluded) |
| 403 | `INSUFFICIENT_PERMISSIONS` | Deactivated employee attempting to access |
| 404 | `ATTENDANCE_NOT_FOUND` | No attendance record exists for today (status: NOT_STARTED) |
| 500 | `INTERNAL_ERROR` | Server error |

**Example Error Response (404):**
```json
{
  "error": {
    "code": "ATTENDANCE_NOT_FOUND",
    "details": [{"field": "attendance", "issue": "No attendance record found for today. Please check in to start tracking."}]
  },
  "message": "Attendance record not found for today."
}
```

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159).
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- Returns 404 if no attendance record exists for today (employee hasn't checked in yet).

---

### 4.3.2 GET /v1/attendance

- **Purpose:** Get paginated attendance history for the authenticated employee (own records only)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** Employee, Manager, HR, CEO (own attendance only)
- **SuperAdmin:** Explicitly excluded
- **Deactivated Employees:** Cannot access

**Headers:**
- **Request Headers:**
  - `Authorization: Bearer <token>` (REQUIRED)
- **Response Headers (REQUIRED):**
  - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`)

**Path Parameters**  
None

**Query Parameters**  
**Note:** Query parameters MUST be defined using a query schema class with `Depends()` pattern (Rule 9), NOT individual `Query()` parameters in the router endpoint.

**Query Schema Class (REQUIRED):**
```python
class AttendanceHistoryQuery(BaseModel):
    """Query schema for listing employee's own attendance history with pagination and filtering."""

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    start_date: Optional[str] = Field(None, description="Filter by start date (ISO 8601 date format: YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Filter by end date (ISO 8601 date format: YYYY-MM-DD)")
    status: Optional[str] = Field(None, description="Filter by status: NOT_STARTED, CHECKED_IN, CHECKED_OUT")
    sort_by: str = Field("attendance_date", description="Sort field: attendance_date, check_in_time, check_out_time, worked_time")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)
```

**Router Endpoint Pattern (REQUIRED):**
```python
@router.get("", response_model=StandardResponse[AttendancePaginatedResponse[AttendanceSummary]])
async def get_attendance_history(
    query: AttendanceHistoryQuery = Depends(AttendanceHistoryQuery),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_employee),
):
    """Get paginated attendance history for authenticated employee."""
    # Access via query.page, query.page_size, query.start_date, etc.
```

**Query Parameters Table (for documentation only):**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number (≥ 1) |
| page_size | integer | No | 20 | Page size (1-100) |
| start_date | string (date) | No | null | Filter by start date (ISO 8601: YYYY-MM-DD) |
| end_date | string (date) | No | null | Filter by end date (ISO 8601: YYYY-MM-DD) |
| status | string (ENUM) | No | null | Filter by status: NOT_STARTED, CHECKED_IN, CHECKED_OUT |
| sort_by | string | No | attendance_date | Sort field: attendance_date, check_in_time, check_out_time, worked_time |
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
        "attendance_date": "2024-01-20",
        "check_in_time": "2024-01-20T09:12:00Z",
        "check_out_time": "2024-01-20T18:41:00Z",
        "status": "CHECKED_OUT",
        "worked_time": "9h 29m",
        "is_auto_check_out": false
      },
      {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "attendance_date": "2024-01-19",
        "check_in_time": "2024-01-19T09:15:00Z",
        "check_out_time": "2024-01-20T00:00:00Z",
        "status": "CHECKED_OUT",
        "worked_time": "14h 45m",
        "is_auto_check_out": true
      }
    ],
    "total": 45,
    "page": 1,
    "page_size": 20,
    "total_pages": 3,
    "next_page": "/v1/attendance?page=2&page_size=20&sort_by=attendance_date&sort_order=desc",
    "prev_page": null
  },
  "message": "Attendance history retrieved successfully"
}
```

**Response Schema:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| items | array | Yes | Array of attendance records | - |
| items[].id | string (UUID) | Yes | Attendance record ID | RFC 4122 UUID v4 format |
| items[].attendance_date | string (date) | Yes | Local calendar date | ISO 8601 date format (YYYY-MM-DD) |
| items[].check_in_time | string (datetime) | No | Server timestamp of check-in | ISO 8601 format, UTC timezone (Z suffix), nullable |
| items[].check_out_time | string (datetime) | No | Server timestamp of check-out | ISO 8601 format, UTC timezone (Z suffix), nullable |
| items[].status | string (ENUM) | Yes | Attendance lifecycle state | Enum: "NOT_STARTED", "CHECKED_IN", "CHECKED_OUT" |
| items[].worked_time | string | No | Derived duration (e.g., "9h 29m") | Read-only, nullable if not checked out |
| items[].is_auto_check_out | boolean | Yes | Flag indicating if check-out was automatic | Boolean |
| total | integer | Yes | Total number of items across all pages | Integer, ≥ 0 |
| page | integer | Yes | Current page number | Integer, ≥ 1 |
| page_size | integer | Yes | Number of items per page | Integer, 1-100 |
| total_pages | integer | Yes | Total number of pages | Integer, ≥ 0 |
| next_page | string \| null | Yes | URL for next page (or null) | Full relative URL or null |
| prev_page | string \| null | Yes | URL for previous page (or null) | Full relative URL or null |

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159).
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- `next_page` and `prev_page` include all query parameters (filters, sort, search) to preserve pagination state.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 401 | `INVALID_TOKEN` | JWT token is invalid or missing required claims |
| 403 | `INSUFFICIENT_PERMISSIONS` | SuperAdmin attempting to access (explicitly excluded) |
| 403 | `INSUFFICIENT_PERMISSIONS` | Deactivated employee attempting to access |
| 400 | `VALIDATION_FAILED` | Invalid query parameters (invalid date format, invalid status, etc.) |
| 500 | `INTERNAL_ERROR` | Server error |

---

### 4.3.3 POST /v1/attendance/check-in

- **Purpose:** Record employee check-in for the current day
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** Employee, Manager, HR, CEO (own attendance only)
- **SuperAdmin:** Explicitly excluded
- **Deactivated Employees:** Cannot access
- **Idempotency:** Yes - If already checked in for today, returns existing attendance record (200 OK)

**Headers:**
- **Request Headers:**
  - `Authorization: Bearer <token>` (REQUIRED)
- **Response Headers (REQUIRED):**
  - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`)

**Path Parameters**  
None

**Query Parameters**  
None

**Request Body**

```json
{
  "location": "Office Building A, Floor 3",
  "device_info": "Chrome 120.0 on Windows 11"
}
```

**Request Schema:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| location | string | No | Optional location information | Free text, max 500 characters, nullable |
| device_info | string | No | Optional device information | Free text, max 255 characters, nullable |

**Note:** 
- `location` and `device_info` are optional fields
- `ip_address` is automatically captured server-side from request headers
- If employee is already checked in for today, returns existing attendance record (idempotent)

**Success Response (200 OK)**

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "employee_id": "123e4567-e89b-12d3-a456-426614174000",
    "company_id": "789e0123-e45b-67c8-d901-234567890abc",
    "attendance_date": "2024-01-20",
    "check_in_time": "2024-01-20T09:12:00Z",
    "check_out_time": null,
    "status": "CHECKED_IN",
    "worked_time": null,
    "is_auto_check_out": false,
    "created_at": "2024-01-20T09:12:00Z",
    "updated_at": "2024-01-20T09:12:00Z"
  },
  "message": "Check-in recorded successfully"
}
```

**Response Schema:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| id | string (UUID) | Yes | Attendance record ID | RFC 4122 UUID v4 format |
| employee_id | string (UUID) | Yes | Employee ID | RFC 4122 UUID v4 format |
| company_id | string (UUID) | Yes | Company ID | RFC 4122 UUID v4 format |
| attendance_date | string (date) | Yes | Local calendar date | ISO 8601 date format (YYYY-MM-DD) |
| check_in_time | string (datetime) | Yes | Server timestamp of check-in | ISO 8601 format, UTC timezone (Z suffix) |
| check_out_time | string (datetime) | No | Server timestamp of check-out | ISO 8601 format, UTC timezone (Z suffix), nullable |
| status | string (ENUM) | Yes | Attendance lifecycle state | Enum: "CHECKED_IN" |
| worked_time | string | No | Derived duration | Read-only, null until check-out |
| is_auto_check_out | boolean | Yes | Flag indicating if check-out was automatic | Boolean (false for check-in) |
| created_at | string (datetime) | Yes | Creation timestamp | ISO 8601 format, UTC timezone (Z suffix) |
| updated_at | string (datetime) | Yes | Last update timestamp | ISO 8601 format, UTC timezone (Z suffix) |

**Business Rules:**
- Only one check-in per day per employee
- Check-in creates or updates attendance record to `CHECKED_IN` status
- If already checked in for today, returns existing attendance record (idempotent)
- Attendance date is determined using employee's local timezone
- Server timestamp (UTC) is authoritative for `check_in_time`
- Creates AttendanceLog entry with action type `CHECK_IN`

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 401 | `INVALID_TOKEN` | JWT token is invalid or missing required claims |
| 403 | `INSUFFICIENT_PERMISSIONS` | SuperAdmin attempting to access (explicitly excluded) |
| 403 | `INSUFFICIENT_PERMISSIONS` | Deactivated employee attempting to access |
| 409 | `ALREADY_CHECKED_OUT` | Employee already checked out for today (cannot check in again) |
| 400 | `VALIDATION_FAILED` | Invalid request body (field validation errors) |
| 422 | `BUSINESS_RULE_FAILED` | Business rule violation (e.g., attempting check-in on future date) |
| 500 | `INTERNAL_ERROR` | Server error |

**Example Error Response (409):**
```json
{
  "error": {
    "code": "ALREADY_CHECKED_OUT",
    "details": [{"field": "attendance", "issue": "You have already checked out for today. Check-in is only allowed once per day."}]
  },
  "message": "Cannot check in. You have already checked out for today."
}
```

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159).
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- Returns 409 if employee already checked out for today (cannot check in again on same day).

---

### 4.3.4 POST /v1/attendance/check-out

- **Purpose:** Record employee check-out for the current day
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** Employee, Manager, HR, CEO (own attendance only)
- **SuperAdmin:** Explicitly excluded
- **Deactivated Employees:** Cannot access
- **Idempotency:** Yes - If already checked out for today, returns existing attendance record (200 OK)

**Headers:**
- **Request Headers:**
  - `Authorization: Bearer <token>` (REQUIRED)
- **Response Headers (REQUIRED):**
  - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`)

**Path Parameters**  
None

**Query Parameters**  
None

**Request Body**

```json
{
  "location": "Office Building A, Floor 3",
  "device_info": "Chrome 120.0 on Windows 11"
}
```

**Request Schema:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| location | string | No | Optional location information | Free text, max 500 characters, nullable |
| device_info | string | No | Optional device information | Free text, max 255 characters, nullable |

**Note:** 
- `location` and `device_info` are optional fields
- `ip_address` is automatically captured server-side from request headers
- If employee is already checked out for today, returns existing attendance record (idempotent)

**Success Response (200 OK)**

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "employee_id": "123e4567-e89b-12d3-a456-426614174000",
    "company_id": "789e0123-e45b-67c8-d901-234567890abc",
    "attendance_date": "2024-01-20",
    "check_in_time": "2024-01-20T09:12:00Z",
    "check_out_time": "2024-01-20T18:41:00Z",
    "status": "CHECKED_OUT",
    "worked_time": "9h 29m",
    "is_auto_check_out": false,
    "created_at": "2024-01-20T09:12:00Z",
    "updated_at": "2024-01-20T18:41:00Z"
  },
  "message": "Check-out recorded successfully"
}
```

**Response Schema:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| id | string (UUID) | Yes | Attendance record ID | RFC 4122 UUID v4 format |
| employee_id | string (UUID) | Yes | Employee ID | RFC 4122 UUID v4 format |
| company_id | string (UUID) | Yes | Company ID | RFC 4122 UUID v4 format |
| attendance_date | string (date) | Yes | Local calendar date | ISO 8601 date format (YYYY-MM-DD) |
| check_in_time | string (datetime) | Yes | Server timestamp of check-in | ISO 8601 format, UTC timezone (Z suffix) |
| check_out_time | string (datetime) | Yes | Server timestamp of check-out | ISO 8601 format, UTC timezone (Z suffix) |
| status | string (ENUM) | Yes | Attendance lifecycle state | Enum: "CHECKED_OUT" |
| worked_time | string | Yes | Derived duration (e.g., "9h 29m") | Read-only, calculated from check_in_time and check_out_time |
| is_auto_check_out | boolean | Yes | Flag indicating if check-out was automatic | Boolean (false for manual check-out) |
| created_at | string (datetime) | Yes | Creation timestamp | ISO 8601 format, UTC timezone (Z suffix) |
| updated_at | string (datetime) | Yes | Last update timestamp | ISO 8601 format, UTC timezone (Z suffix) |

**Business Rules:**
- Only one check-out per day per employee
- Check-out requires prior check-in (cannot check out without checking in)
- Check-out updates attendance record to `CHECKED_OUT` status
- If already checked out for today, returns existing attendance record (idempotent)
- Attendance becomes immutable after `CHECKED_OUT` status
- `worked_time` is calculated as duration between `check_in_time` and `check_out_time`
- Server timestamp (UTC) is authoritative for `check_out_time`
- Creates AttendanceLog entry with action type `CHECK_OUT`

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 401 | `INVALID_TOKEN` | JWT token is invalid or missing required claims |
| 403 | `INSUFFICIENT_PERMISSIONS` | SuperAdmin attempting to access (explicitly excluded) |
| 403 | `INSUFFICIENT_PERMISSIONS` | Deactivated employee attempting to access |
| 404 | `ATTENDANCE_NOT_FOUND` | No attendance record exists for today (employee hasn't checked in) |
| 422 | `BUSINESS_RULE_FAILED` | Business rule violation (e.g., attempting check-out without check-in) |
| 400 | `VALIDATION_FAILED` | Invalid request body (field validation errors) |
| 500 | `INTERNAL_ERROR` | Server error |

**Example Error Response (404):**
```json
{
  "error": {
    "code": "ATTENDANCE_NOT_FOUND",
    "details": [{"field": "attendance", "issue": "No attendance record found for today. Please check in first."}]
  },
  "message": "Cannot check out. You must check in first."
}
```

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159).
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- Returns 404 if employee hasn't checked in for today.

---

### 4.3.5 GET /v1/company/attendance

- **Purpose:** Get paginated attendance records list with filters (Manager/HR/CEO only)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** Manager (employees in scope), HR (full company), CEO (full company)
- **SuperAdmin:** Explicitly excluded
- **Employees:** No access to this endpoint
- **Deactivated Employees:** Cannot access

**Headers:**
- **Request Headers:**
  - `Authorization: Bearer <token>` (REQUIRED)
- **Response Headers (REQUIRED):**
  - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`)

**Path Parameters**  
None

**Query Parameters**  
**Note:** Query parameters MUST be defined using a query schema class with `Depends()` pattern (Rule 9), NOT individual `Query()` parameters in the router endpoint.

**Query Schema Class (REQUIRED):**
```python
class CompanyAttendanceListQuery(BaseModel):
    """Query schema for listing company attendance records with pagination and filtering."""

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    employee_id: Optional[str] = Field(None, description="Filter by employee ID (UUID format, HR/CEO only)")
    start_date: Optional[str] = Field(None, description="Filter by start date (ISO 8601 date format: YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Filter by end date (ISO 8601 date format: YYYY-MM-DD)")
    status: Optional[str] = Field(None, description="Filter by status: NOT_STARTED, CHECKED_IN, CHECKED_OUT")
    sort_by: str = Field("attendance_date", description="Sort field: attendance_date, check_in_time, check_out_time, worked_time, employee_name")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)
```

**Router Endpoint Pattern (REQUIRED):**
```python
@router.get("", response_model=StandardResponse[CompanyAttendancePaginatedResponse[CompanyAttendanceSummary]])
async def list_company_attendance(
    query: CompanyAttendanceListQuery = Depends(CompanyAttendanceListQuery),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_manager_hr_ceo),
):
    """List company attendance records with pagination, filtering, search, and sorting."""
    # Access via query.page, query.page_size, query.employee_id, etc.
```

**Query Parameters Table (for documentation only):**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number (≥ 1) |
| page_size | integer | No | 20 | Page size (1-100) |
| employee_id | string (UUID) | No | null | Filter by employee ID (HR/CEO only, Manager cannot filter by employee_id) |
| start_date | string (date) | No | null | Filter by start date (ISO 8601: YYYY-MM-DD) |
| end_date | string (date) | No | null | Filter by end date (ISO 8601: YYYY-MM-DD) |
| status | string (ENUM) | No | null | Filter by status: NOT_STARTED, CHECKED_IN, CHECKED_OUT |
| sort_by | string | No | attendance_date | Sort field: attendance_date, check_in_time, check_out_time, worked_time, employee_name |
| sort_order | string | No | desc | Sort order: asc or desc |

**Note:** 
- `employee_id` filter is only available for HR and CEO roles
- Managers can view all employees in their scope but cannot filter by specific employee_id
- All data is strictly company-scoped (from token's `org_id`)

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "employee": {
          "id": "123e4567-e89b-12d3-a456-426614174000",
          "first_name": "John",
          "last_name": "Doe"
        },
        "attendance_date": "2024-01-20",
        "status": "CHECKED_OUT",
        "worked_time": "9h 29m",
        "is_auto_check_out": false
      },
      {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "employee": {
          "id": "234e5678-e89b-12d3-a456-426614174001",
          "first_name": "Jane",
          "last_name": "Smith"
        },
        "attendance_date": "2024-01-20",
        "status": "CHECKED_OUT",
        "worked_time": "8h 15m",
        "is_auto_check_out": true
      }
    ],
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8,
    "next_page": "/v1/company/attendance?page=2&page_size=20&sort_by=attendance_date&sort_order=desc&status=CHECKED_OUT",
    "prev_page": null
  },
  "message": "Attendance records retrieved successfully"
}
```

**Response Schema:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| items | array | Yes | Array of attendance records | - |
| items[].id | string (UUID) | Yes | Attendance record ID | RFC 4122 UUID v4 format |
| items[].employee | object | Yes | Employee information | - |
| items[].employee.id | string (UUID) | Yes | Employee ID | RFC 4122 UUID v4 format |
| items[].employee.first_name | string | Yes | Employee first name | Max 255 characters |
| items[].employee.last_name | string | Yes | Employee last name | Max 255 characters |
| items[].attendance_date | string (date) | Yes | Local calendar date | ISO 8601 date format (YYYY-MM-DD) |
| items[].status | string (ENUM) | Yes | Attendance lifecycle state | Enum: "NOT_STARTED", "CHECKED_IN", "CHECKED_OUT" |
| items[].worked_time | string | No | Derived duration (e.g., "9h 29m") | Read-only, nullable if not checked out |
| items[].is_auto_check_out | boolean | Yes | Flag indicating if check-out was automatic | Boolean |
| total | integer | Yes | Total number of items across all pages | Integer, ≥ 0 |
| page | integer | Yes | Current page number | Integer, ≥ 1 |
| page_size | integer | Yes | Number of items per page | Integer, 1-100 |
| total_pages | integer | Yes | Total number of pages | Integer, ≥ 0 |
| next_page | string \| null | Yes | URL for next page (or null) | Full relative URL or null |
| prev_page | string \| null | Yes | URL for previous page (or null) | Full relative URL or null |

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159).
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- `next_page` and `prev_page` include all query parameters (filters, sort, search) to preserve pagination state.
- Attendance records remain visible even after employee deactivation (but deactivated employees cannot access).

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 401 | `INVALID_TOKEN` | JWT token is invalid or missing required claims |
| 403 | `INSUFFICIENT_PERMISSIONS` | SuperAdmin attempting to access (explicitly excluded) |
| 403 | `INSUFFICIENT_PERMISSIONS` | Employee attempting to access (no access to company endpoints) |
| 403 | `INSUFFICIENT_PERMISSIONS` | Deactivated employee attempting to access |
| 400 | `VALIDATION_FAILED` | Invalid query parameters (invalid date format, invalid status, invalid employee_id, etc.) |
| 500 | `INTERNAL_ERROR` | Server error |

---

### 4.3.6 GET /v1/company/attendance/{employee_id}/{date}

- **Purpose:** Get detailed attendance for specific employee and date (Manager/HR/CEO only)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** Manager (employees in scope), HR (full company), CEO (full company)
- **SuperAdmin:** Explicitly excluded
- **Employees:** No access to this endpoint
- **Deactivated Employees:** Cannot access

**Headers:**
- **Request Headers:**
  - `Authorization: Bearer <token>` (REQUIRED)
  - `If-None-Match`: ETag value from previous GET (optional, for cache validation - returns 304 if unchanged)
- **Response Headers (REQUIRED):**
  - `X-Request-ID`: Unique request identifier for debugging (e.g., `req_abc123xyz789`)
  - `ETag`: Resource version identifier based on `updated_at` (e.g., `"20240120T103000Z"`)
  - `Last-Modified`: Timestamp of last modification (optional)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| employee_id | string (UUID) | Yes | Employee ID | RFC 4122 UUID v4 format |
| date | string (date) | Yes | Attendance date | ISO 8601 date format (YYYY-MM-DD) |

**Note:** All path parameters MUST use snake_case (e.g., `employee_id`) - see Rule 2.

**Query Parameters**  
None

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "attendance": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "employee_id": "123e4567-e89b-12d3-a456-426614174000",
      "company_id": "789e0123-e45b-67c8-d901-234567890abc",
      "attendance_date": "2024-01-20",
      "check_in_time": "2024-01-20T09:12:00Z",
      "check_out_time": "2024-01-20T18:41:00Z",
      "status": "CHECKED_OUT",
      "worked_time": "9h 29m",
      "is_auto_check_out": false,
      "created_at": "2024-01-20T09:12:00Z",
      "updated_at": "2024-01-20T18:41:00Z"
    },
    "employee": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "first_name": "John",
      "last_name": "Doe"
    },
    "logs": [
      {
        "id": "770e8400-e29b-41d4-a716-446655440002",
        "action_type": "CHECK_IN",
        "action_time": "2024-01-20T09:12:00Z",
        "location": "Office Building A, Floor 3",
        "ip_address": "192.168.1.100",
        "device_info": "Chrome 120.0 on Windows 11",
        "notes": null,
        "is_auto_action": false
      },
      {
        "id": "880e8400-e29b-41d4-a716-446655440003",
        "action_type": "CHECK_OUT",
        "action_time": "2024-01-20T18:41:00Z",
        "location": "Office Building A, Floor 3",
        "ip_address": "192.168.1.100",
        "device_info": "Chrome 120.0 on Windows 11",
        "notes": null,
        "is_auto_action": false
      }
    ]
  },
  "message": "Attendance detail retrieved successfully"
}
```

**Response Schema:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| attendance | object | Yes | Attendance record | - |
| attendance.id | string (UUID) | Yes | Attendance record ID | RFC 4122 UUID v4 format |
| attendance.employee_id | string (UUID) | Yes | Employee ID | RFC 4122 UUID v4 format |
| attendance.company_id | string (UUID) | Yes | Company ID | RFC 4122 UUID v4 format |
| attendance.attendance_date | string (date) | Yes | Local calendar date | ISO 8601 date format (YYYY-MM-DD) |
| attendance.check_in_time | string (datetime) | No | Server timestamp of check-in | ISO 8601 format, UTC timezone (Z suffix), nullable |
| attendance.check_out_time | string (datetime) | No | Server timestamp of check-out | ISO 8601 format, UTC timezone (Z suffix), nullable |
| attendance.status | string (ENUM) | Yes | Attendance lifecycle state | Enum: "NOT_STARTED", "CHECKED_IN", "CHECKED_OUT" |
| attendance.worked_time | string | No | Derived duration (e.g., "9h 29m") | Read-only, nullable if not checked out |
| attendance.is_auto_check_out | boolean | Yes | Flag indicating if check-out was automatic | Boolean |
| attendance.created_at | string (datetime) | Yes | Creation timestamp | ISO 8601 format, UTC timezone (Z suffix) |
| attendance.updated_at | string (datetime) | Yes | Last update timestamp | ISO 8601 format, UTC timezone (Z suffix) |
| employee | object | Yes | Employee information | - |
| employee.id | string (UUID) | Yes | Employee ID | RFC 4122 UUID v4 format |
| employee.first_name | string | Yes | Employee first name | Max 255 characters |
| employee.last_name | string | Yes | Employee last name | Max 255 characters |
| logs | array | Yes | Array of attendance log entries | - |
| logs[].id | string (UUID) | Yes | Attendance log entry ID | RFC 4122 UUID v4 format |
| logs[].action_type | string (ENUM) | Yes | Attendance action type | Enum: "CHECK_IN", "CHECK_OUT", "AUTO_CHECK_OUT" |
| logs[].action_time | string (datetime) | Yes | Server timestamp of action | ISO 8601 format, UTC timezone (Z suffix) |
| logs[].location | string | No | Location information | Free text, max 500 characters, nullable |
| logs[].ip_address | string | No | Client IP address | IPv4 or IPv6 format, nullable |
| logs[].device_info | string | No | Device information | Free text, max 255 characters, nullable |
| logs[].notes | string | No | System notes | Free text, max 1000 characters, nullable |
| logs[].is_auto_action | boolean | Yes | Flag indicating if action was automatic | Boolean |

**Note:** 
- `logs` array is returned in chronological order (oldest first)
- `AUTO_CHECK_OUT` action type is included in logs when check-out was automatic
- Date resolution respects employee's local timezone
- Only one Attendance record exists per employee per day

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 401 | `INVALID_TOKEN` | JWT token is invalid or missing required claims |
| 403 | `INSUFFICIENT_PERMISSIONS` | SuperAdmin attempting to access (explicitly excluded) |
| 403 | `INSUFFICIENT_PERMISSIONS` | Employee attempting to access (no access to company endpoints) |
| 403 | `INSUFFICIENT_PERMISSIONS` | Manager attempting to access employee outside their scope |
| 403 | `INSUFFICIENT_PERMISSIONS` | Deactivated employee attempting to access |
| 404 | `ATTENDANCE_NOT_FOUND` | Attendance record not found for specified employee and date |
| 404 | `EMPLOYEE_NOT_FOUND` | Employee not found or not in user's scope |
| 400 | `VALIDATION_FAILED` | Invalid path parameters (invalid UUID format, invalid date format) |
| 500 | `INTERNAL_ERROR` | Server error |

**Example Error Response (404):**
```json
{
  "error": {
    "code": "ATTENDANCE_NOT_FOUND",
    "details": [{"field": "attendance", "issue": "No attendance record found for employee and date."}]
  },
  "message": "Attendance record not found."
}
```

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159).
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- Returns 404 if attendance record doesn't exist for the specified employee and date.

---

## 5. Business Rules & Constraints

### 5.1 Attendance Rules

- **One per day:** Exactly one attendance record exists per employee per day
- **Status transitions:** Linear and irreversible (`NOT_STARTED` → `CHECKED_IN` → `CHECKED_OUT`)
- **Immutability:** Attendance records are immutable after `CHECKED_OUT` status
- **Mandatory check-out:** Check-out is mandatory (auto check-out at employee's local midnight if missed)
- **Timezone handling:** Attendance is calculated using employee's local timezone
- **Day reset:** Day resets at employee's local midnight

### 5.2 Check-In Rules

- Only one check-in per day per employee
- Check-in creates or updates attendance record to `CHECKED_IN` status
- If already checked in for today, returns existing attendance record (idempotent)
- Cannot check in if already checked out for today (returns 409 Conflict)

### 5.3 Check-Out Rules

- Only one check-out per day per employee
- Check-out requires prior check-in (cannot check out without checking in)
- Check-out updates attendance record to `CHECKED_OUT` status
- If already checked out for today, returns existing attendance record (idempotent)
- Attendance becomes immutable after `CHECKED_OUT` status
- `worked_time` is calculated as duration between `check_in_time` and `check_out_time`

### 5.4 Auto Check-Out Rules

- Auto check-out occurs at employee's local midnight if manual check-out is missed
- Auto check-out is system-initiated (background job, not API endpoint)
- Auto check-out sets `is_auto_check_out` flag to `true`
- Auto check-out creates AttendanceLog entry with action type `AUTO_CHECK_OUT`
- Auto check-out uses employee's configured timezone to determine local midnight

### 5.5 Access Control Rules

- **Employees:** Can view only their own attendance (today and history), can check-in/out for themselves only
- **Managers:** Can view attendance for all employees in their scope (via company endpoints), can check-in/out for themselves only
- **HR/CEO:** Full attendance visibility across the company (via company endpoints), can check-in/out for themselves only
- **SuperAdmin:** Cannot access or view attendance data (explicitly excluded from all endpoints)
- **Deactivated Employees:** Cannot view attendance history or perform check-in/check-out actions
- Historical attendance data remains stored even after employee deactivation

### 5.6 Live Counter Rules

- Single API endpoint (`GET /v1/attendance/today`) provides check-in time to the UI
- UI calculates live working-time counter by comparing check-in time (from API) with current client time
- Counter derives from server-stored check-in time retrieved via API
- Counter resumes correctly after page refresh or re-login (UI recalculates using API-provided check-in time)
- Counter stops permanently after check-out

---

## 6. Data Validation

### 6.1 Field Validation

**UUID Fields:**
- Format: RFC 4122 UUID v4 format
- Example: `550e8400-e29b-41d4-a716-446655440000`

**Date Fields:**
- Format: ISO 8601 date format (`YYYY-MM-DD`)
- Example: `2024-01-20`

**DateTime Fields:**
- Format: ISO 8601 format with UTC timezone (`YYYY-MM-DDTHH:mm:ssZ`)
- Example: `2024-01-20T10:30:00Z`
- All datetime fields MUST use UTC timezone (Z suffix required)

**Enum Fields:**
- `status`: `NOT_STARTED`, `CHECKED_IN`, `CHECKED_OUT` (case-sensitive)
- `action_type`: `CHECK_IN`, `CHECK_OUT`, `AUTO_CHECK_OUT` (case-sensitive)

**String Fields:**
- `location`: Max 500 characters, nullable
- `device_info`: Max 255 characters, nullable
- `notes`: Max 1000 characters, nullable
- `first_name`, `last_name`: Max 255 characters

**Timezone Fields:**
- `employee_timezone`: IANA timezone identifier (e.g., `Asia/Kolkata`, `America/New_York`)

### 6.2 Business-Level Validation

- **Uniqueness:** Exactly one attendance record per employee per day (enforced at database level)
- **State transitions:** Status transitions must follow linear path (`NOT_STARTED` → `CHECKED_IN` → `CHECKED_OUT`)
- **Dependencies:** Check-out requires prior check-in (cannot check out without checking in)
- **Date validation:** Attendance date must be valid calendar date (not future date for check-in/check-out)
- **Employee scope:** Manager can only access employees in their scope (enforced at application level)

---

## 7. Error Handling

### 7.1 Standard Error Response Format

All error responses follow this structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "details": [
      {
        "field": "field_name",
        "issue": "Error description"
      }
    ]
  },
  "message": "Human-friendly error message"
}
```

### 7.2 Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `UNAUTHENTICATED` | 401 | Missing or invalid authentication token |
| `TOKEN_EXPIRED` | 401 | JWT token has expired |
| `INVALID_TOKEN` | 401 | JWT token is invalid or missing required claims |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions (SuperAdmin excluded, Employee accessing company endpoint, Manager accessing employee outside scope, Deactivated employee) |
| `ATTENDANCE_NOT_FOUND` | 404 | Attendance record not found |
| `EMPLOYEE_NOT_FOUND` | 404 | Employee not found or not in user's scope |
| `VALIDATION_FAILED` | 400 | Request validation failed (invalid format, invalid enum, etc.) |
| `ALREADY_CHECKED_OUT` | 409 | Employee already checked out for today (cannot check in again) |
| `BUSINESS_RULE_FAILED` | 422 | Business rule violation (e.g., check-out without check-in, future date) |
| `INTERNAL_ERROR` | 500 | Server error |

---

## 8. Edge Cases & Error Scenarios

### 8.1 Check-In Edge Cases

- **Second check-in attempt on same day:** Returns existing attendance record (idempotent, 200 OK)
- **Check-in after check-out:** Returns 409 Conflict (`ALREADY_CHECKED_OUT`)
- **Check-in on future date:** Returns 422 Unprocessable Entity (`BUSINESS_RULE_FAILED`)

### 8.2 Check-Out Edge Cases

- **Check-out without prior check-in:** Returns 404 Not Found (`ATTENDANCE_NOT_FOUND`)
- **Second check-out attempt on same day:** Returns existing attendance record (idempotent, 200 OK)
- **Check-out on future date:** Returns 422 Unprocessable Entity (`BUSINESS_RULE_FAILED`)

### 8.3 Access Control Edge Cases

- **SuperAdmin attempting to access:** Returns 403 Forbidden (`INSUFFICIENT_PERMISSIONS`)
- **Deactivated employee attempting to access:** Returns 403 Forbidden (`INSUFFICIENT_PERMISSIONS`)
- **Employee attempting to access company endpoint:** Returns 403 Forbidden (`INSUFFICIENT_PERMISSIONS`)
- **Manager attempting to access employee outside scope:** Returns 403 Forbidden (`INSUFFICIENT_PERMISSIONS`)

### 8.4 Day Boundary Edge Cases

- **Day boundary crossing at employee local midnight:** Triggers auto check-out if missed (system-initiated, not API)
- **Timezone changes affecting auto check-out timing:** Uses employee's configured timezone
- **Page refresh or logout during active check-in:** UI fetches check-in time from API and recalculates counter

### 8.5 Concurrent Request Edge Cases

- **Concurrent check-in/check-out requests:** Database constraints prevent duplicate records (idempotent behavior)
- **Multiple browser tabs with same attendance session:** Each tab independently fetches check-in time from API and calculates counter

### 8.6 Data Edge Cases

- **Missing attendance record for today:** Returns 404 Not Found (`ATTENDANCE_NOT_FOUND`) for check-out, creates new record for check-in
- **Historical attendance after employee deactivation:** Data remains stored and visible to Manager/HR/CEO, but deactivated employee cannot access

---

## 9. Dependencies

### 9.1 Feature Dependencies

- **F-005 — Employee Management:** Provides employee identity, timezone, and activation status
- **F-002 — RBAC & Permission Engine:** Enforces role-based visibility and access, SuperAdmin exclusion, deactivated employee restrictions

### 9.2 Data Dependencies

- **Employee timezone:** Retrieved from Employee entity (F-005)
- **Employee activation status:** Used for access control (deactivated employees cannot access)
- **Role information:** Encoded in JWT token (F-002)
- **Organization scope:** Extracted from JWT token's `org_id` claim

---

## 10. Assumptions

1. Employee timezone is stored in Employee entity (F-005) and retrieved for attendance calculations
2. Auto check-out is implemented as a background job (system-initiated, not API endpoint)
3. Server stores all timestamps in UTC and converts using employee timezone for display
4. Live counter is calculated client-side using check-in time from API and current client time
5. Attendance data remains stored even if an employee is deactivated
6. SuperAdmin role is explicitly excluded from all attendance endpoints (enforced at API level)
7. Manager scope is determined by existing RBAC system (F-002)
8. JWT token includes required claims (`sub`, `role`, `org_id`, `exp`)

---

## 11. Open Questions

None identified at this stage. All requirements are clear from the domain model, feature brief, and UI data contract.

---

**Document Version:** 1.0  
**Last Updated:** 2024-01-20  
**Feature:** F-010 — Attendance Management

