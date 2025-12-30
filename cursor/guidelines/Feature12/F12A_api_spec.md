# API Specification: F-012 — Reports & Analytics (Part A: Core Reporting)

## 1. Overview

The Reports & Analytics API provides a read-only, role-aware reporting layer that aggregates data from operational domains (F-005 through F-011) to support decision-making, visibility, and oversight. This API enforces strict company scoping, role-based access control (RBAC), and supports consistent filtering across all report types.

**Key Characteristics:**
- **Read-only**: Reports are derived read models—no data mutation
- **Company-scoped**: All reports are isolated by company (no cross-company access)
- **Role-based**: Access and visibility strictly follow RBAC rules
- **On-demand**: Reports are generated on-demand (no scheduled delivery)
- **Near real-time**: Data reflects current system state with acceptable caching

**Report Types:**
- `ATTENDANCE` - Attendance reports (daily/monthly, employee-wise)
- `LEAVE` - Leave reports (applied/approved/rejected)
- `SALARY_SUMMARY` - Salary reports (company total only, aggregated)
- `EMPLOYEE` - Employee reports (headcount, department-wise)
- `TASK` - Task reports (status, progress, assignments)
- `PROJECT` - Project reports (status, progress, assignments)
- `AUDIT_SUMMARY` - Audit summary reports (counts and trends)

**Source Features:**
- F-005 — Employee Management
- F-006 — Salary & History Management
- F-007 — Project Management
- F-008 — Task Management & Assignment
- F-009 — Leave Management Workflow
- F-010 — Attendance Management
- F-011 — Audit Logging & Activity History

---

## 2. Global API Rules

### 2.1 Authentication

**JWT Token Structure:**
All API endpoints require JWT Bearer token authentication.

**Token Format:**
```
Authorization: Bearer <jwt_token>
```

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
  "role": "hr",
  "org_id": "123e4567-e89b-12d3-a456-426614174000",
  "exp": 1735689600,
  "iat": 1735686000,
  "jti": "jwt_abc123xyz789"
}
```

**Role Encoding:**
- Roles MUST be encoded in JWT token (not database lookup during request)
- Role values: Use lowercase (e.g., `"ceo"`, `"hr"`, `"manager"`, `"employee"`, `"superadmin"`)
- SuperAdmin role: `org_id` MUST be `null` (indicates global access)
- Organization-scoped roles: `org_id` MUST contain organization UUID

**Token Validation:**
- Server MUST validate token signature, expiration, and required claims
- Missing or invalid token: Return `401 UNAUTHENTICATED`
- Missing required claims: Return `401 UNAUTHENTICATED` with error code `INVALID_TOKEN`
- Expired token: Return `401 UNAUTHENTICATED` with error code `TOKEN_EXPIRED`

**Multi-Tenancy from Token:**
- **SuperAdmin**: `org_id: null` - Has access to all organizations (but NO access to reports per BR-1203)
- **Organization-scoped users**: `org_id: "<uuid>"` - Access limited to specified organization
- Server MUST extract `org_id` from token for authorization checks

### 2.2 Base URL and Versioning

**Base URL:**
```
/api/v1
```

**Versioning:**
- All endpoints use `/api/v1` prefix
- Future versions will use `/api/v2`, etc.

### 2.3 Standard Response Format

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
- `ETag`: Resource version identifier (for GET responses of resources that support updates) - **Not applicable for reports (read-only)**
- `Last-Modified`: Timestamp of last modification - **Not applicable for reports (derived read models)**

**Note:**
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- `X-Request-ID` header MUST be included in ALL responses for debugging and support.

### 2.4 Standard HTTP Status Codes

- `200 OK`: Successful GET operations
- `400 Bad Request`: Invalid request format (`INVALID_REQUEST` / `VALIDATION_FAILED`)
- `401 Unauthorized`: Missing or invalid authentication (`UNAUTHENTICATED`, `TOKEN_EXPIRED`, `INVALID_TOKEN`)
- `403 Forbidden`: Insufficient permissions (`INSUFFICIENT_PERMISSIONS`)
- `404 Not Found`: Resource not found (`REPORT_TYPE_NOT_FOUND`, `REPORT_NOT_FOUND`)
- `422 Unprocessable Entity`: Validation errors or business rule failures (`VALIDATION_ERROR`, `BUSINESS_RULE_FAILED`)
- `500 Internal Server Error`: Server errors (`INTERNAL_ERROR`)

### 2.5 UTC Time Standard

**All datetime fields MUST use UTC timezone:**
- Format: ISO 8601 with `Z` suffix (e.g., `2024-01-20T10:30:00Z`)
- Examples: `created_at`, `updated_at`, `start_date`, `end_date`, `expires_at`
- Rationale: Prevents timezone confusion, standard practice for APIs and databases

---

## 3. Roles & Permissions

### 3.1 Role-Based Access Matrix

| Role | Accessible Reports | Scope |
|------|-------------------|-------|
| **CEO** | All report types | Company-scoped |
| **HR** | All report types | Company-scoped |
| **Manager** | ATTENDANCE, PROJECT, TASK (includes assignment data) | Company-scoped (within own company) |
| **Employee** | Own ATTENDANCE, LEAVE, TASK | Self-scoped (own data only) |
| **SuperAdmin** | No access | N/A (blocked by BR-1203) |

**Assignment Reports (Manager Scope):**
Assignment reports are not separate report types. They are included within TASK and PROJECT reports:
- Task assignments (visible in TASK report)
- Project ↔ task associations (visible in PROJECT report)
- Employee ↔ task mappings (visible in TASK report)

### 3.2 Company Scoping Rules

- **All reports are company-scoped**: Data is filtered by `org_id` from JWT token
- **No cross-company access**: Users cannot access reports from other companies
- **SuperAdmin exception**: SuperAdmin has `org_id: null` but is explicitly blocked from reports

### 3.3 Filter Scope Restrictions

**Employee:**
- Can apply filters only to own data
- `employee_id` filter is automatically restricted to authenticated user's ID
- Cannot filter by other employees, departments, or projects outside their scope

**Manager:**
- Can filter only within own company
- Can filter by employees in their company, departments, projects, tasks
- Cannot filter across companies

**HR / CEO:**
- Can filter across entire company
- Can filter by any employee, department, project, task within company
- Cannot filter across companies

**❌ No cross-company filtering for any role**

### 3.4 Salary Report Special Rules

**SALARY_SUMMARY Report:**
- Aggregation level: **Company total only**
- Explicit exclusions:
  - ❌ Per-employee salary
  - ❌ Department-wise totals
  - ❌ Role-wise totals
- Access: CEO and HR only (company-scoped)

---

## 4. Resources & Endpoints

### 4.1 Resource Overview

| Resource | Description | Lifecycle |
|----------|-------------|-----------|
| **ReportType** | Enumeration of available report types | Static (defined by system) |
| **Report** | Read-only aggregated view of domain data | Derived (generated on-demand) |
| **ReportView** | Role-specific projection of a report with filters applied | Derived (generated on-demand) |
| **ReportMetadata** | Metadata about a report type (title, description, filter options) | Static (defined by system) |
| **ReportData** | Aggregated data rows and totals for a report | Derived (generated on-demand) |

**Note:** Reports are **derived read models**, not persistent business entities with lifecycle or ownership.

### 4.2 Endpoint Summary

| Method | Path | Purpose | Auth Required |
|--------|------|---------|---------------|
| GET | `/api/v1/reports` | List accessible report types | Yes |
| GET | `/api/v1/reports/{report_type}` | Get report data with filters | Yes |

**Note:** Export endpoints are documented in `F12B_api_spec.md`.

### 4.3 Endpoint Details

#### 4.3.1 GET /api/v1/reports

- **Purpose:** List all report types accessible to the authenticated user's role
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** 
  - CEO: All report types
  - HR: All report types
  - Manager: ATTENDANCE, PROJECT, TASK only
  - Employee: ATTENDANCE, LEAVE, TASK only (self-scoped)
  - SuperAdmin: No access (empty list returned - filtered server-side)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers:**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- **Idempotency:** Yes (GET operation)

**Query Parameters**  
**Note:** Query parameters MUST be defined using a query schema class with `Depends()` pattern (Rule 9), NOT individual `Query()` parameters in the router endpoint.

**Query Schema Class (REQUIRED):**
```python
class ReportListQuery(BaseModel):
    """Query schema for listing accessible report types."""

    # No query parameters for this endpoint (returns all accessible reports)
    # Schema class still required for consistency

    model_config = ConfigDict(from_attributes=True)
```

**Router Endpoint Pattern (REQUIRED):**
```python
@router.get("", response_model=StandardResponse[list[ReportTypeResponse]])
async def list_reports(
    query: ReportListQuery = Depends(ReportListQuery),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List accessible report types based on user role."""
    # Implementation
```

**Query Parameters Table (for documentation only):**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| None | - | - | - | No query parameters for this endpoint |

**Success Response (200 OK)**

```json
{
  "data": [
    {
      "code": "ATTENDANCE",
      "label": "Attendance Report",
      "description": "Daily and monthly attendance reports with employee-wise breakdown",
      "is_accessible": true
    },
    {
      "code": "LEAVE",
      "label": "Leave Report",
      "description": "Leave applications, approvals, and rejections",
      "is_accessible": true
    },
    {
      "code": "TASK",
      "label": "Task Report",
      "description": "Task status, progress, and assignments",
      "is_accessible": true
    }
  ],
  "available_report_count": 3,
  "message": "Report types retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Response Schema:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| data | array | Yes | Array of ReportType objects | - |
| data[].code | string | Yes | Report type code | Enum: ATTENDANCE, LEAVE, SALARY_SUMMARY, EMPLOYEE, TASK, PROJECT, AUDIT_SUMMARY |
| data[].label | string | Yes | Human-readable report name | Min 1 char, max 255 chars |
| data[].description | string | Yes | Report description | Min 1 char, max 1000 chars |
| data[].is_accessible | boolean | Yes | Whether user can access this report type | Always true (filtered server-side) |
| available_report_count | integer | Yes | Total count of accessible report types | Min: 0 (derived field) |
| message | string | Yes | Success message | - |

**Empty State (200 OK):**
If user has no accessible reports (e.g., SuperAdmin), return empty array:
```json
{
  "data": [],
  "available_report_count": 0,
  "message": "No accessible report types found"
}
```

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 401 | `INVALID_TOKEN` | JWT token is invalid or malformed |
| 500 | `INTERNAL_ERROR` | Server error during processing |

**Example Error (401 Unauthorized):**
```json
{
  "error": {
    "code": "UNAUTHENTICATED",
    "details": [{"field": "authorization", "issue": "Missing or invalid authentication token"}]
  },
  "message": "Authentication required to access reports."
}
```

---

#### 4.3.2 GET /api/v1/reports/{report_type}

- **Purpose:** Get report data with optional filters; includes filter options in metadata
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** 
  - CEO: All report types (company-scoped)
  - HR: All report types (company-scoped)
  - Manager: ATTENDANCE, PROJECT, TASK only (company-scoped)
  - Employee: ATTENDANCE, LEAVE, TASK only (self-scoped)
  - SuperAdmin: No access (403 Forbidden - blocked by BR-1203)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-None-Match: "etag-value"` (optional, for cache validation - returns 304 if unchanged)
  - **Response Headers:**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
    - `ETag`: Not applicable (reports are derived read models, regenerated on-demand)
    - `Last-Modified`: Not applicable (reports are derived read models)
- **Idempotency:** Yes (GET operation, but data may change between requests)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| report_type | string | Yes | Report type code | Enum: ATTENDANCE, LEAVE, SALARY_SUMMARY, EMPLOYEE, TASK, PROJECT, AUDIT_SUMMARY |

**Note:** All path parameters MUST use snake_case (e.g., `report_type`) - see Rule 2.

**Query Parameters**  
**Note:** Query parameters MUST be defined using a query schema class with `Depends()` pattern (Rule 9), NOT individual `Query()` parameters in the router endpoint.

**Query Schema Class (REQUIRED):**
```python
class ReportViewQuery(BaseModel):
    """Query schema for viewing report data with filters and pagination."""

    # Date range filters
    start_date: Optional[str] = Field(None, description="Start date (ISO 8601 format, UTC: YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (ISO 8601 format, UTC: YYYY-MM-DD)")
    
    # Status filter (varies by report type)
    status: Optional[str] = Field(None, description="Filter by status (varies by report type)")
    
    # Entity filters (role-restricted)
    employee_id: Optional[str] = Field(None, description="Filter by employee ID (UUID, role-restricted)")
    department: Optional[str] = Field(None, description="Filter by department name (exact match)")
    project_id: Optional[str] = Field(None, description="Filter by project ID (UUID)")
    
    # Pagination (only for list-style reports)
    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    
    # Sorting
    sort_by: str = Field("created_at", description="Sort field (varies by report type)")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)
```

**Router Endpoint Pattern (REQUIRED):**
```python
@router.get("/{report_type}", response_model=StandardResponse[ReportViewResponse])
async def get_report(
    report_type: str,
    query: ReportViewQuery = Depends(ReportViewQuery),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get report data with optional filters."""
    # Access via query.start_date, query.end_date, query.page, etc.
```

**Query Parameters Table (for documentation only):**

| Name | Type | Required | Default | Description | Validation |
|------|------|----------|---------|-------------|------------|
| start_date | string | No | null | Start date for date range filter | ISO 8601 format (YYYY-MM-DD), UTC timezone |
| end_date | string | No | null | End date for date range filter | ISO 8601 format (YYYY-MM-DD), UTC timezone, must be >= start_date |
| status | string | No | null | Filter by status | Enum values vary by report type (see Report Type Specifications) |
| employee_id | string | No | null | Filter by employee ID | RFC 4122 UUID v4 format, role-restricted (see Filter Scope Restrictions) |
| department | string | No | null | Filter by department name | Exact match, case-sensitive |
| project_id | string | No | null | Filter by project ID | RFC 4122 UUID v4 format |
| page | integer | No | 1 | Page number for pagination | Min: 1 |
| page_size | integer | No | 20 | Number of items per page | Min: 1, Max: 100 |
| sort_by | string | No | "created_at" | Field to sort by | Varies by report type (see Report Type Specifications) |
| sort_order | string | No | "desc" | Sort order | Enum: "asc", "desc" (case-sensitive) |

**Pagination Rules:**
- **List-style reports** (ATTENDANCE, LEAVE, TASK, PROJECT, EMPLOYEE, AUDIT_SUMMARY): Pagination supported
- **Aggregate reports** (SALARY_SUMMARY): No pagination (returns single aggregate object)
- For aggregate reports, `page` and `page_size` parameters are ignored

**Request Body**  
None (GET request)

**Success Response (200 OK)**

**For List-Style Reports (with pagination):**
```json
{
  "data": {
    "metadata": {
      "report_type": "ATTENDANCE",
      "title": "Attendance Report",
      "description": "Daily and monthly attendance reports with employee-wise breakdown",
      "source_features": ["F-010"],
      "filter_options": {
        "date_range": {
          "min_date": "2024-01-01",
          "max_date": "2024-12-31"
        },
        "status": ["PRESENT", "ABSENT", "LATE", "HALF_DAY"],
        "departments": ["Engineering", "Sales", "HR"],
        "employees": [
          {
            "employee_id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "John Doe"
          }
        ],
        "projects": [
          {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Project Alpha"
          }
        ]
      }
    },
    "rows": [
      {
        "employee_id": "550e8400-e29b-41d4-a716-446655440000",
        "employee_name": "John Doe",
        "date": "2024-01-20",
        "status": "PRESENT",
        "check_in_time": "2024-01-20T09:00:00Z",
        "check_out_time": "2024-01-20T18:00:00Z",
        "hours_worked": 8.5
      }
    ],
    "totals": {
      "total_employees": 150,
      "total_present": 145,
      "total_absent": 5,
      "total_hours": 1160.5
    },
    "pagination": {
      "items": [...],
      "total": 150,
      "page": 1,
      "page_size": 20,
      "total_pages": 8,
      "next_page": "/api/v1/reports/attendance?page=2&page_size=20&start_date=2024-01-01&end_date=2024-01-31",
      "prev_page": null
    },
    "row_count": 150,
    "has_export": true
  },
  "message": "Report data retrieved successfully"
}
```

**For Aggregate Reports (SALARY_SUMMARY, no pagination):**
```json
{
  "data": {
    "metadata": {
      "report_type": "SALARY_SUMMARY",
      "title": "Salary Summary Report",
      "description": "Company-wide salary totals (aggregated only)",
      "source_features": ["F-006"],
      "filter_options": {
        "date_range": {
          "min_date": "2024-01-01",
          "max_date": "2024-12-31"
        }
      }
    },
    "totals": {
      "company_total_salary": 5000000.00,
      "currency": "USD",
      "period": "2024-01",
      "employee_count": 150
    },
    "rows": null,
    "pagination": null,
    "row_count": null,
    "has_export": true
  },
  "message": "Report data retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Response Schema:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| data | object | Yes | Report view data | - |
| data.metadata | object | Yes | Report metadata | - |
| data.metadata.report_type | string | Yes | Report type code | Enum: ATTENDANCE, LEAVE, SALARY_SUMMARY, EMPLOYEE, TASK, PROJECT, AUDIT_SUMMARY |
| data.metadata.title | string | Yes | Report title | Min 1 char, max 255 chars |
| data.metadata.description | string | Yes | Report description | Min 1 char, max 1000 chars |
| data.metadata.source_features | array | Yes | Source feature codes | Array of strings (e.g., ["F-010"]) |
| data.metadata.filter_options | object | Yes | Available filter options | - |
| data.metadata.filter_options.date_range | object | No | Available date range | - |
| data.metadata.filter_options.date_range.min_date | string | No | Minimum available date | ISO 8601 format (YYYY-MM-DD) |
| data.metadata.filter_options.date_range.max_date | string | No | Maximum available date | ISO 8601 format (YYYY-MM-DD) |
| data.metadata.filter_options.status | array | No | Available status values | Array of strings (varies by report type) |
| data.metadata.filter_options.departments | array | No | Available departments | Array of strings |
| data.metadata.filter_options.employees | array | No | Available employees (role-restricted) | Array of objects with employee_id and name |
| data.metadata.filter_options.projects | array | No | Available projects | Array of objects with project_id and name |
| data.rows | array | Conditional | Report data rows | Required for list-style reports, null for aggregate reports |
| data.totals | object | Yes | Aggregated totals | - |
| data.pagination | object | Conditional | Pagination metadata | Required for list-style reports, null for aggregate reports |
| data.pagination.items | array | Conditional | Paginated items (same as rows) | - |
| data.pagination.total | integer | Conditional | Total number of items | Min: 0 |
| data.pagination.page | integer | Conditional | Current page number | Min: 1 |
| data.pagination.page_size | integer | Conditional | Items per page | Min: 1, Max: 100 |
| data.pagination.total_pages | integer | Conditional | Total number of pages | Min: 0 |
| data.pagination.next_page | string\|null | Conditional | URL for next page | Full relative URL or null |
| data.pagination.prev_page | string\|null | Conditional | URL for previous page | Full relative URL or null |
| data.row_count | integer\|null | Conditional | Total number of rows (before pagination) | Min: 0, null for aggregate reports (derived field) |
| data.has_export | boolean | Yes | Whether export functionality is available for this report | Always true (export endpoints available, see F12B_api_spec.md) |
| message | string | Yes | Success message | - |

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- For paginated responses, `next_page` and `prev_page` MUST include all query parameters (filters, sort, search) to preserve pagination state.
- `rows`, `pagination`, and `row_count` are `null` for SALARY_SUMMARY (aggregate report).
- `pagination.items` contains the same data as `rows` (convenience alias for paginated data).
- `row_count` represents total rows before pagination (useful for UI display of total records).
- `has_export` indicates export functionality is available (see `F12B_api_spec.md` for export endpoints).

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | `INVALID_REQUEST` | Invalid request format or missing required path parameter |
| 400 | `VALIDATION_FAILED` | Query parameter validation failed (e.g., invalid date format, invalid UUID) |
| 401 | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 401 | `INVALID_TOKEN` | JWT token is invalid or malformed |
| 403 | `INSUFFICIENT_PERMISSIONS` | User role cannot access this report type |
| 404 | `REPORT_TYPE_NOT_FOUND` | Invalid report_type value |
| 422 | `VALIDATION_ERROR` | Filter validation failed (e.g., end_date < start_date, employee_id outside scope) |
| 422 | `BUSINESS_RULE_FAILED` | Business rule violation (e.g., employee trying to filter other employees' data) |
| 500 | `INTERNAL_ERROR` | Server error during processing |

**Example Error (403 Forbidden - Insufficient Permissions):**
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "details": [{"field": "report_type", "issue": "Your role (employee) does not have access to SALARY_SUMMARY reports"}]
  },
  "message": "You do not have permission to access this report type."
}
```

**Example Error (422 Unprocessable Entity - Filter Validation):**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "details": [
      {"field": "end_date", "issue": "End date must be greater than or equal to start date"},
      {"field": "employee_id", "issue": "You can only filter by your own employee_id"}
    ]
  },
  "message": "Filter validation failed."
}
```

**Example Error (404 Not Found - Invalid Report Type):**
```json
{
  "error": {
    "code": "REPORT_TYPE_NOT_FOUND",
    "details": [{"field": "report_type", "issue": "Invalid report type: INVALID_TYPE"}]
  },
  "message": "Report type not found."
}
```

---

## 5. Report Type Specifications

### 5.1 ATTENDANCE Report

**Source Feature:** F-010 Attendance Management

**Access Roles:** CEO, HR, Manager, Employee (self-scoped)

**Pagination:** ✅ Yes

**Available Filters:**
- `start_date`, `end_date`: Date range (ISO 8601, UTC)
- `status`: Enum - `PRESENT`, `ABSENT`, `LATE`, `HALF_DAY`
- `employee_id`: UUID (role-restricted - employees can only filter own data)
- `department`: String (exact match)

**Sort Fields:** `date`, `employee_name`, `status`, `check_in_time`, `created_at`

**Response Structure:**
```json
{
  "rows": [
    {
      "employee_id": "550e8400-e29b-41d4-a716-446655440000",
      "employee_name": "John Doe",
      "date": "2024-01-20",
      "status": "PRESENT",
      "check_in_time": "2024-01-20T09:00:00Z",
      "check_out_time": "2024-01-20T18:00:00Z",
      "hours_worked": 8.5
    }
  ],
  "totals": {
    "total_employees": 150,
    "total_present": 145,
    "total_absent": 5,
    "total_late": 3,
    "total_hours": 1160.5
  }
}
```

### 5.2 LEAVE Report

**Source Feature:** F-009 Leave Management Workflow

**Access Roles:** CEO, HR, Employee (self-scoped)

**Pagination:** ✅ Yes

**Available Filters:**
- `start_date`, `end_date`: Date range (ISO 8601, UTC)
- `status`: Enum - `APPLIED`, `APPROVED`, `REJECTED`, `CANCELLED`
- `employee_id`: UUID (role-restricted - employees can only filter own data)

**Sort Fields:** `applied_date`, `start_date`, `end_date`, `status`, `employee_name`, `created_at`

**Response Structure:**
```json
{
  "rows": [
    {
      "leave_id": "123e4567-e89b-12d3-a456-426614174000",
      "employee_id": "550e8400-e29b-41d4-a716-446655440000",
      "employee_name": "John Doe",
      "leave_type": "ANNUAL",
      "start_date": "2024-02-01",
      "end_date": "2024-02-05",
      "days": 5,
      "status": "APPROVED",
      "applied_date": "2024-01-15T10:00:00Z"
    }
  ],
  "totals": {
    "total_applications": 45,
    "total_approved": 40,
    "total_rejected": 3,
    "total_pending": 2,
    "total_days": 180
  }
}
```

### 5.3 SALARY_SUMMARY Report

**Source Feature:** F-006 Salary & History Management

**Access Roles:** CEO, HR only

**Pagination:** ❌ No (single aggregate object)

**Available Filters:**
- `start_date`, `end_date`: Date range (ISO 8601, UTC) - for period selection

**Sort Fields:** N/A (aggregate report)

**Response Structure:**
```json
{
  "rows": null,
  "totals": {
    "company_total_salary": 5000000.00,
    "currency": "USD",
    "period": "2024-01",
    "employee_count": 150
  }
}
```

**Business Rules:**
- BR-1205: Salary reports are company-total only
- ❌ No per-employee salary
- ❌ No department-wise totals
- ❌ No role-wise totals

### 5.4 EMPLOYEE Report

**Source Feature:** F-005 Employee Management

**Access Roles:** CEO, HR

**Pagination:** ✅ Yes

**Available Filters:**
- `department`: String (exact match)
- `status`: Enum - `ACTIVE`, `INACTIVE`, `TERMINATED`

**Sort Fields:** `employee_name`, `department`, `hire_date`, `created_at`

**Response Structure:**
```json
{
  "rows": [
    {
      "employee_id": "550e8400-e29b-41d4-a716-446655440000",
      "employee_name": "John Doe",
      "email": "john.doe@example.com",
      "department": "Engineering",
      "role": "SOFTWARE_ENGINEER",
      "status": "ACTIVE",
      "hire_date": "2023-01-15"
    }
  ],
  "totals": {
    "total_employees": 150,
    "active_employees": 145,
    "inactive_employees": 3,
    "terminated_employees": 2,
    "departments": ["Engineering", "Sales", "HR", "Finance"]
  }
}
```

### 5.5 TASK Report

**Source Feature:** F-008 Task Management & Assignment

**Access Roles:** CEO, HR, Manager, Employee (self-scoped)

**Pagination:** ✅ Yes

**Available Filters:**
- `start_date`, `end_date`: Date range (ISO 8601, UTC) - for task dates
- `status`: Enum - `PENDING`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`
- `employee_id`: UUID (role-restricted - employees can only filter own tasks)
- `project_id`: UUID
- `department`: String (exact match)

**Sort Fields:** `task_name`, `status`, `due_date`, `priority`, `created_at`

**Response Structure:**
```json
{
  "rows": [
    {
      "task_id": "123e4567-e89b-12d3-a456-426614174000",
      "task_name": "Implement authentication",
      "project_id": "456e7890-e89b-12d3-a456-426614174001",
      "project_name": "Project Alpha",
      "assigned_to": "550e8400-e29b-41d4-a716-446655440000",
      "assigned_to_name": "John Doe",
      "status": "IN_PROGRESS",
      "priority": "HIGH",
      "due_date": "2024-02-15",
      "progress": 60
    }
  ],
  "totals": {
    "total_tasks": 200,
    "pending_tasks": 50,
    "in_progress_tasks": 80,
    "completed_tasks": 65,
    "cancelled_tasks": 5
  }
}
```

### 5.6 PROJECT Report

**Source Feature:** F-007 Project Management

**Access Roles:** CEO, HR, Manager

**Pagination:** ✅ Yes

**Available Filters:**
- `start_date`, `end_date`: Date range (ISO 8601, UTC) - for project dates
- `status`: Enum - `PLANNING`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `ON_HOLD`
- `department`: String (exact match)

**Sort Fields:** `project_name`, `status`, `start_date`, `end_date`, `created_at`

**Response Structure:**
```json
{
  "rows": [
    {
      "project_id": "456e7890-e89b-12d3-a456-426614174001",
      "project_name": "Project Alpha",
      "description": "Main project description",
      "status": "IN_PROGRESS",
      "start_date": "2024-01-01",
      "end_date": "2024-06-30",
      "progress": 45,
      "total_tasks": 50,
      "completed_tasks": 22,
      "department": "Engineering"
    }
  ],
  "totals": {
    "total_projects": 25,
    "planning_projects": 5,
    "in_progress_projects": 15,
    "completed_projects": 4,
    "cancelled_projects": 1
  }
}
```

### 5.7 AUDIT_SUMMARY Report

**Source Feature:** F-011 Audit Logging & Activity History

**Access Roles:** CEO, HR

**Pagination:** ✅ Yes

**Available Filters:**
- `start_date`, `end_date`: Date range (ISO 8601, UTC)
- `status`: Enum - `SUCCESS`, `FAILURE`, `ERROR` (if applicable)

**Sort Fields:** `timestamp`, `action`, `user_name`, `created_at`

**Response Structure:**
```json
{
  "rows": [
    {
      "timestamp": "2024-01-20T10:30:00Z",
      "action": "USER_LOGIN",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_name": "John Doe",
      "resource_type": "USER",
      "resource_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "SUCCESS",
      "ip_address": "192.168.1.1"
    }
  ],
  "totals": {
    "total_events": 5000,
    "success_events": 4800,
    "failure_events": 150,
    "error_events": 50,
    "unique_users": 150
  }
}
```

---

## 6. Business Rules

| Rule ID | Description | Type | Related Concepts |
|---------|-------------|------|------------------|
| BR-1201 | Reports are read-only | Constraint | Report |
| BR-1202 | Reports are company-scoped | Security | Report |
| BR-1203 | Role governs report visibility | Visibility | ReportView |
| BR-1204 | Employees can access only own data | Visibility | FilterSet |
| BR-1205 | Salary reports are company-total only | Constraint | SALARY_SUMMARY |
| BR-1206 | Export reflects filtered report snapshot | Behavior | ExportArtifact (see F12B_api_spec.md) |

**Filter Scope Enforcement:**
- **Employees**: 
  - `employee_id` filter automatically restricted to authenticated user's ID
  - If employee provides `employee_id` != their own ID, return 422 `BUSINESS_RULE_FAILED`
  - Cannot filter by other employees, departments, or projects outside their scope
- **Managers**: Can filter within company only (validated against `org_id` from token)
- **HR/CEO**: Can filter across entire company (validated against `org_id` from token)
- **Cross-company filtering**: Blocked for all roles (422 error if attempted)

**Salary Report Constraints:**
- SALARY_SUMMARY: Only company total, no breakdowns
- Access: CEO and HR only (403 if other roles attempt access)

---

## 7. Validation Rules

### 7.1 Report Type Validation

- **Format:** Enum - Must be one of: `ATTENDANCE`, `LEAVE`, `SALARY_SUMMARY`, `EMPLOYEE`, `TASK`, `PROJECT`, `AUDIT_SUMMARY`
- **Case sensitivity:** Case-insensitive (normalize to uppercase)
- **Error:** 404 `REPORT_TYPE_NOT_FOUND` if invalid

### 7.2 Date Range Validation

- **Format:** ISO 8601 format (YYYY-MM-DD), UTC timezone
- **Range:** `end_date` must be >= `start_date`
- **Error:** 422 `VALIDATION_ERROR` if invalid format or range violation

### 7.3 UUID Validation

- **Format:** RFC 4122 UUID v4 format
- **Fields:** `employee_id`, `project_id`
- **Error:** 400 `VALIDATION_FAILED` if invalid UUID format

### 7.4 Status Enum Validation

- **Format:** Enum values vary by report type (see Report Type Specifications)
- **Case sensitivity:** Case-sensitive
- **Error:** 422 `VALIDATION_ERROR` if invalid status for report type

### 7.5 Pagination Validation

- **page:** Integer, min: 1
- **page_size:** Integer, min: 1, max: 100
- **Error:** 400 `VALIDATION_FAILED` if out of range

### 7.6 Sort Order Validation

- **sort_order:** Enum - `asc` or `desc` (case-sensitive)
- **Error:** 400 `VALIDATION_FAILED` if invalid value

### 7.7 Role-Based Filter Validation

- **employee_id filter:** 
  - Employees: Must match authenticated user's ID (422 if other)
  - Managers/HR/CEO: Must belong to same company (422 if cross-company)
- **Error:** 422 `BUSINESS_RULE_FAILED` if filter exceeds role scope

---

## 8. Assumptions

- Reports are generated on-demand (no caching beyond acceptable performance optimization)
- Data is near real-time with acceptable caching
- Filter options are included in report metadata response (Option A)
- Large datasets support server-side aggregation and pagination
- Export functionality is documented in `F12B_api_spec.md`
- F-011 (Audit Logging) records report view access automatically
- UI-level masking may apply to sensitive fields (not API concern)

---

## 9. Open Questions

None identified at this stage.

---

**Note:** Export endpoints (create export, check status, download) are documented in `F12B_api_spec.md`.

