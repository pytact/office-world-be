# API Specification: F-012 — Reports & Analytics (Part B: Export Functionality)

## 1. Overview

This document covers the export functionality for the Reports & Analytics feature. Export functionality allows authorized users to generate PDF snapshots of report views with applied filters. Exports are generated asynchronously and have a 24-hour time-to-live (TTL).

**Key Characteristics:**
- **Async generation**: PDF exports are generated asynchronously (not blocking)
- **Snapshot-based**: Exports reflect the filtered report view at the time of request
- **Immutable**: Export artifacts do not update when underlying data changes
- **TTL**: Export artifacts expire after 24 hours
- **Role-aware**: Exports respect the same role-based access and filter restrictions as report views

**Related Documentation:**
- Core reporting endpoints are documented in `F12A_api_spec.md`
- Export endpoints build upon report view functionality

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
- **SuperAdmin**: `org_id: null` - Has access to all organizations (but NO access to reports)
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
- `Content-Type`: `application/json` for JSON responses, `application/pdf` for PDF downloads

**Note:**
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- `X-Request-ID` header MUST be included in ALL responses for debugging and support.

### 2.4 Standard HTTP Status Codes

- `200 OK`: Successful GET operations (export status, download)
- `201 Created`: Successful POST operations (create export)
- `400 Bad Request`: Invalid request format (`INVALID_REQUEST` / `VALIDATION_FAILED`)
- `401 Unauthorized`: Missing or invalid authentication (`UNAUTHENTICATED`, `TOKEN_EXPIRED`, `INVALID_TOKEN`)
- `403 Forbidden`: Insufficient permissions (`INSUFFICIENT_PERMISSIONS`)
- `404 Not Found`: Resource not found (`EXPORT_NOT_FOUND`, `REPORT_TYPE_NOT_FOUND`)
- `410 Gone`: Resource expired (`EXPORT_EXPIRED`)
- `422 Unprocessable Entity`: Validation errors or business rule failures (`VALIDATION_ERROR`, `BUSINESS_RULE_FAILED`)
- `500 Internal Server Error`: Server errors (`INTERNAL_ERROR`, `ASYNC_OPERATION_FAILED`)

### 2.5 UTC Time Standard

**All datetime fields MUST use UTC timezone:**
- Format: ISO 8601 with `Z` suffix (e.g., `2024-01-20T10:30:00Z`)
- Examples: `created_at`, `expires_at`, `completed_at`
- Rationale: Prevents timezone confusion, standard practice for APIs and databases

---

## 3. Roles & Permissions

### 3.1 Role-Based Access for Exports

**Export Access Rules:**
- Exports follow the same role-based access rules as report views
- Users can only export reports they have access to view
- Export filters must respect the same role-based scope restrictions as report views

| Role | Can Export Reports | Scope |
|------|-------------------|-------|
| **CEO** | All report types | Company-scoped |
| **HR** | All report types | Company-scoped |
| **Manager** | ATTENDANCE, PROJECT, TASK | Company-scoped (within own company) |
| **Employee** | Own ATTENDANCE, LEAVE, TASK | Self-scoped (own data only) |
| **SuperAdmin** | No access | N/A (blocked) |

### 3.2 Export Ownership

- Exports are owned by the user who created them
- Users can only access their own exports (via export_id)
- Export access is validated on each request (status check, download)

---

## 4. Resources & Endpoints

### 4.1 Resource Overview

| Resource | Description | Lifecycle |
|----------|-------------|-----------|
| **Export** | PDF export request and artifact | Created on POST, processed asynchronously, expires after 24 hours |
| **ExportArtifact** | Generated PDF file | Generated after export processing completes, available for download until expiration |

**Export Status Values:**
- `PENDING`: Export request created, waiting to be processed
- `PROCESSING`: Export is being generated
- `COMPLETED`: Export is ready for download
- `FAILED`: Export generation failed
- `EXPIRED`: Export artifact has expired (24 hours TTL)

### 4.2 Endpoint Summary

| Method | Path | Purpose | Auth Required |
|--------|------|---------|---------------|
| POST | `/api/v1/reports/{report_type}/exports` | Create async PDF export | Yes |
| GET | `/api/v1/reports/{report_type}/exports/{export_id}` | Check export status (polling) | Yes |
| GET | `/api/v1/reports/{report_type}/exports/{export_id}/download` | Download PDF export | Yes |

### 4.3 Endpoint Details

#### 4.3.1 POST /api/v1/reports/{report_type}/exports

- **Purpose:** Create an asynchronous PDF export of a report view with applied filters
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** 
  - Same as report view access (see `F12A_api_spec.md` section 3.1)
  - CEO: All report types
  - HR: All report types
  - Manager: ATTENDANCE, PROJECT, TASK only
  - Employee: ATTENDANCE, LEAVE, TASK only (self-scoped)
  - SuperAdmin: No access (403 Forbidden)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `Content-Type: application/json` (REQUIRED)
  - **Response Headers:**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- **Idempotency:** No (each request creates a new export)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| report_type | string | Yes | Report type code | Enum: ATTENDANCE, LEAVE, SALARY_SUMMARY, EMPLOYEE, TASK, PROJECT, AUDIT_SUMMARY |

**Note:** All path parameters MUST use snake_case (e.g., `report_type`) - see Rule 2.

**Request Body**

**Schema Table:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| filters | object | No | Filter snapshot to apply to export | - |
| filters.start_date | string | No | Start date for date range filter | ISO 8601 format (YYYY-MM-DD), UTC timezone |
| filters.end_date | string | No | End date for date range filter | ISO 8601 format (YYYY-MM-DD), UTC timezone, must be >= start_date |
| filters.status | string | No | Filter by status | Enum values vary by report type |
| filters.employee_id | string | No | Filter by employee ID | RFC 4122 UUID v4 format, role-restricted |
| filters.department | string | No | Filter by department name | Exact match, case-sensitive |
| filters.project_id | string | No | Filter by project ID | RFC 4122 UUID v4 format |

**Request Body Example:**
```json
{
  "filters": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "status": "PRESENT",
    "department": "Engineering"
  }
}
```

**Empty Request Body:**
If no filters are provided, export uses default report view (no filters applied):
```json
{}
```

**Success Response (201 Created)**

```json
{
  "data": {
    "export_id": "e9c2f3a4-b5c6-4d7e-8f9a-0b1c2d3e4f5a",
    "report_type": "ATTENDANCE",
    "status": "PENDING",
    "created_at": "2024-01-20T10:30:00Z",
    "expires_at": "2024-01-21T10:30:00Z"
  },
  "message": "Export request created successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `Location: /api/v1/reports/attendance/exports/e9c2f3a4-b5c6-4d7e-8f9a-0b1c2d3e4f5a` (RECOMMENDED - for status checking)

**Response Schema:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| data | object | Yes | Export creation response | - |
| data.export_id | string | Yes | Unique export identifier | RFC 4122 UUID v4 format |
| data.report_type | string | Yes | Report type code | Enum: ATTENDANCE, LEAVE, SALARY_SUMMARY, EMPLOYEE, TASK, PROJECT, AUDIT_SUMMARY |
| data.status | string | Yes | Export status | Enum: PENDING, PROCESSING, COMPLETED, FAILED, EXPIRED |
| data.created_at | string | Yes | Export creation timestamp | ISO 8601 format (YYYY-MM-DDTHH:mm:ssZ), UTC timezone |
| data.expires_at | string | Yes | Export expiration timestamp | ISO 8601 format (YYYY-MM-DDTHH:mm:ssZ), UTC timezone (24 hours from creation) |
| message | string | Yes | Success message | - |

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | `INVALID_REQUEST` | Invalid request format or missing required path parameter |
| 400 | `VALIDATION_FAILED` | Request body validation failed (e.g., invalid date format, invalid UUID) |
| 401 | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 401 | `INVALID_TOKEN` | JWT token is invalid or malformed |
| 403 | `INSUFFICIENT_PERMISSIONS` | User role cannot export this report type |
| 404 | `REPORT_TYPE_NOT_FOUND` | Invalid report_type value |
| 422 | `VALIDATION_ERROR` | Filter validation failed (e.g., end_date < start_date, employee_id outside scope) |
| 422 | `BUSINESS_RULE_FAILED` | Business rule violation (e.g., employee trying to filter other employees' data) |
| 500 | `INTERNAL_ERROR` | Server error during export creation |

**Example Error (403 Forbidden - Insufficient Permissions):**
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "details": [{"field": "report_type", "issue": "Your role (employee) does not have access to export SALARY_SUMMARY reports"}]
  },
  "message": "You do not have permission to export this report type."
}
```

**Example Error (422 Unprocessable Entity - Filter Validation):**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "details": [
      {"field": "filters.end_date", "issue": "End date must be greater than or equal to start date"},
      {"field": "filters.employee_id", "issue": "You can only filter by your own employee_id"}
    ]
  },
  "message": "Filter validation failed."
}
```

---

#### 4.3.2 GET /api/v1/reports/{report_type}/exports/{export_id}

- **Purpose:** Check export status (polling endpoint for async export processing)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** 
  - User must own the export (created by authenticated user)
  - OR user must have access to the report type (for admin/audit purposes)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers:**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- **Idempotency:** Yes (GET operation)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| report_type | string | Yes | Report type code | Enum: ATTENDANCE, LEAVE, SALARY_SUMMARY, EMPLOYEE, TASK, PROJECT, AUDIT_SUMMARY |
| export_id | string | Yes | Export identifier | RFC 4122 UUID v4 format |

**Note:** All path parameters MUST use snake_case (e.g., `report_type`, `export_id`) - see Rule 2.

**Query Parameters**  
None (status check only)

**Success Response (200 OK)**

**Status: PENDING or PROCESSING**
```json
{
  "data": {
    "export_id": "e9c2f3a4-b5c6-4d7e-8f9a-0b1c2d3e4f5a",
    "report_type": "ATTENDANCE",
    "status": "PROCESSING",
    "created_at": "2024-01-20T10:30:00Z",
    "expires_at": "2024-01-21T10:30:00Z",
    "file_url": null
  },
  "message": "Export is being processed"
}
```

**Status: COMPLETED**
```json
{
  "data": {
    "export_id": "e9c2f3a4-b5c6-4d7e-8f9a-0b1c2d3e4f5a",
    "report_type": "ATTENDANCE",
    "status": "COMPLETED",
    "created_at": "2024-01-20T10:30:00Z",
    "completed_at": "2024-01-20T10:32:15Z",
    "expires_at": "2024-01-21T10:30:00Z",
    "file_url": "/api/v1/reports/attendance/exports/e9c2f3a4-b5c6-4d7e-8f9a-0b1c2d3e4f5a/download",
    "file_size": 245678
  },
  "message": "Export completed successfully"
}
```

**Status: FAILED**
```json
{
  "data": {
    "export_id": "e9c2f3a4-b5c6-4d7e-8f9a-0b1c2d3e4f5a",
    "report_type": "ATTENDANCE",
    "status": "FAILED",
    "created_at": "2024-01-20T10:30:00Z",
    "failed_at": "2024-01-20T10:31:00Z",
    "expires_at": "2024-01-21T10:30:00Z",
    "error_message": "PDF generation failed: Insufficient data for report period"
  },
  "message": "Export generation failed"
}
```

**Status: EXPIRED**
```json
{
  "data": {
    "export_id": "e9c2f3a4-b5c6-4d7e-8f9a-0b1c2d3e4f5a",
    "report_type": "ATTENDANCE",
    "status": "EXPIRED",
    "created_at": "2024-01-20T10:30:00Z",
    "expires_at": "2024-01-21T10:30:00Z"
  },
  "message": "Export has expired"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Response Schema:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| data | object | Yes | Export status response | - |
| data.export_id | string | Yes | Unique export identifier | RFC 4122 UUID v4 format |
| data.report_type | string | Yes | Report type code | Enum: ATTENDANCE, LEAVE, SALARY_SUMMARY, EMPLOYEE, TASK, PROJECT, AUDIT_SUMMARY |
| data.status | string | Yes | Export status | Enum: PENDING, PROCESSING, COMPLETED, FAILED, EXPIRED |
| data.created_at | string | Yes | Export creation timestamp | ISO 8601 format (YYYY-MM-DDTHH:mm:ssZ), UTC timezone |
| data.completed_at | string | Conditional | Export completion timestamp | ISO 8601 format (YYYY-MM-DDTHH:mm:ssZ), UTC timezone (present if COMPLETED) |
| data.failed_at | string | Conditional | Export failure timestamp | ISO 8601 format (YYYY-MM-DDTHH:mm:ssZ), UTC timezone (present if FAILED) |
| data.expires_at | string | Yes | Export expiration timestamp | ISO 8601 format (YYYY-MM-DDTHH:mm:ssZ), UTC timezone (24 hours from creation) |
| data.file_url | string\|null | Conditional | Download URL for completed export | Full relative URL or null (present if COMPLETED) |
| data.file_size | integer | Conditional | PDF file size in bytes | Min: 0 (present if COMPLETED) |
| data.error_message | string | Conditional | Error message if export failed | Present if FAILED |
| message | string | Yes | Status message | - |

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | `INVALID_REQUEST` | Invalid request format or missing required path parameters |
| 400 | `VALIDATION_FAILED` | Invalid export_id format (not UUID) |
| 401 | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 401 | `INVALID_TOKEN` | JWT token is invalid or malformed |
| 403 | `INSUFFICIENT_PERMISSIONS` | User does not own this export and lacks access |
| 404 | `EXPORT_NOT_FOUND` | Export not found (invalid export_id or report_type mismatch) |
| 404 | `REPORT_TYPE_NOT_FOUND` | Invalid report_type value |
| 500 | `INTERNAL_ERROR` | Server error during status check |

**Example Error (404 Not Found - Export Not Found):**
```json
{
  "error": {
    "code": "EXPORT_NOT_FOUND",
    "details": [{"field": "export_id", "issue": "Export not found or does not belong to this report type"}]
  },
  "message": "Export not found."
}
```

**Example Error (403 Forbidden - Access Denied):**
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "details": [{"field": "export_id", "issue": "You do not have access to this export"}]
  },
  "message": "You do not have permission to access this export."
}
```

---

#### 4.3.3 GET /api/v1/reports/{report_type}/exports/{export_id}/download

- **Purpose:** Download generated PDF export
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** 
  - User must own the export (created by authenticated user)
  - OR user must have access to the report type (for admin/audit purposes)
  - Export must be in `COMPLETED` status
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers:**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
    - `Content-Type: application/pdf` (REQUIRED)
    - `Content-Disposition: attachment; filename="report_attendance_2024-01-20.pdf"` (RECOMMENDED)
    - `Content-Length: <file-size>` (REQUIRED)
- **Idempotency:** Yes (GET operation, same file returned)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| report_type | string | Yes | Report type code | Enum: ATTENDANCE, LEAVE, SALARY_SUMMARY, EMPLOYEE, TASK, PROJECT, AUDIT_SUMMARY |
| export_id | string | Yes | Export identifier | RFC 4122 UUID v4 format |

**Note:** All path parameters MUST use snake_case (e.g., `report_type`, `export_id`) - see Rule 2.

**Query Parameters**  
None (download only)

**Success Response (200 OK)**

**Response Body:** Raw binary PDF file data

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `Content-Type: application/pdf` (REQUIRED)
- `Content-Disposition: attachment; filename="report_attendance_2024-01-20.pdf"` (RECOMMENDED)
- `Content-Length: 245678` (REQUIRED - file size in bytes)

**Filename Format:**
- Pattern: `report_{report_type}_{date}.pdf`
- Example: `report_attendance_2024-01-20.pdf`
- Date format: `YYYY-MM-DD` (export creation date)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | `INVALID_REQUEST` | Invalid request format or missing required path parameters |
| 400 | `VALIDATION_FAILED` | Invalid export_id format (not UUID) |
| 401 | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 401 | `INVALID_TOKEN` | JWT token is invalid or malformed |
| 403 | `INSUFFICIENT_PERMISSIONS` | User does not own this export and lacks access |
| 404 | `EXPORT_NOT_FOUND` | Export not found (invalid export_id or report_type mismatch) |
| 404 | `REPORT_TYPE_NOT_FOUND` | Invalid report_type value |
| 410 | `EXPORT_EXPIRED` | Export has expired (24 hours TTL exceeded) |
| 422 | `BUSINESS_RULE_FAILED` | Export is not in COMPLETED status (still PENDING, PROCESSING, or FAILED) |
| 500 | `INTERNAL_ERROR` | Server error during download |

**Example Error (410 Gone - Export Expired):**
```json
{
  "error": {
    "code": "EXPORT_EXPIRED",
    "details": [{"field": "export_id", "issue": "Export has expired. Please create a new export."}]
  },
  "message": "Export has expired. Exports are available for 24 hours after creation."
}
```

**Example Error (422 Unprocessable Entity - Export Not Ready):**
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [{"field": "status", "issue": "Export is still processing. Status: PROCESSING"}]
  },
  "message": "Export is not ready for download. Please check export status."
}
```

**Example Error (404 Not Found - Export Not Found):**
```json
{
  "error": {
    "code": "EXPORT_NOT_FOUND",
    "details": [{"field": "export_id", "issue": "Export not found or does not belong to this report type"}]
  },
  "message": "Export not found."
}
```

---

## 5. Export Flow

### 5.1 Async Export Flow

**Step 1: Create Export**
```
POST /api/v1/reports/{report_type}/exports
Request Body: { "filters": {...} }

Response: 201 Created
{
  "data": {
    "export_id": "e9c2f3a4-...",
    "status": "PENDING",
    "expires_at": "2024-01-21T10:30:00Z"
  }
}
```

**Step 2: Poll Export Status**
```
GET /api/v1/reports/{report_type}/exports/{export_id}

Response: 200 OK
{
  "data": {
    "export_id": "e9c2f3a4-...",
    "status": "PROCESSING",  // or COMPLETED
    "file_url": null  // or download URL if COMPLETED
  }
}
```

**Step 3: Download Export (when COMPLETED)**
```
GET /api/v1/reports/{report_type}/exports/{export_id}/download

Response: 200 OK
Content-Type: application/pdf
[Binary PDF data]
```

### 5.2 Export Status Transitions

```
PENDING → PROCESSING → COMPLETED
                    ↓
                  FAILED
                  
COMPLETED → EXPIRED (after 24 hours)
```

**Status Descriptions:**
- `PENDING`: Export request created, queued for processing
- `PROCESSING`: Export is being generated (PDF creation in progress)
- `COMPLETED`: Export is ready for download
- `FAILED`: Export generation failed (error occurred)
- `EXPIRED`: Export artifact has expired (24 hours TTL exceeded)

### 5.3 Export Artifact Lifecycle

**Time-to-Live (TTL):**
- Exports expire **24 hours** after creation (`created_at` timestamp)
- After expiration, exports cannot be downloaded (410 Gone)
- Expired exports may be deleted by the system (no guaranteed retention)

**Snapshot Consistency:**
- Exports reflect the filtered report view at the time of request
- Exports do NOT update when underlying data changes
- Each export is an immutable snapshot

**Concurrent Exports:**
- Multiple export requests for the same report and filters are allowed
- Each request creates a new export with a unique `export_id`
- No deduplication or reuse of existing exports

---

## 6. Business Rules

| Rule ID | Description | Type | Related Concepts |
|---------|-------------|------|------------------|
| BR-1206 | Export reflects filtered report snapshot | Behavior | ExportArtifact (defined in F12A_api_spec.md, referenced here) |
| BR-1207 | Exports respect role-based access and filter restrictions | Security | Export |
| BR-1208 | Exports expire after 24 hours | Lifecycle | ExportArtifact |
| BR-1209 | Exports are immutable snapshots | Constraint | ExportArtifact |

**Export Access Rules:**
- Users can only export reports they have access to view
- Export filters must respect the same role-based scope restrictions as report views
- Employees can only export their own data (same as report view restrictions)
- Managers can export company-scoped reports (same as report view restrictions)
- HR/CEO can export all company reports (same as report view restrictions)

**Export Filter Validation:**
- Filters in export request are validated against the same rules as report view filters
- Invalid filters (e.g., employee_id outside scope) result in 422 error
- Empty filters object exports default report view (no filters)

**Export Status Rules:**
- Exports start in `PENDING` status
- Status transitions to `PROCESSING` when generation begins
- Status transitions to `COMPLETED` when PDF is ready
- Status transitions to `FAILED` if generation fails
- Status transitions to `EXPIRED` after 24 hours (or on access attempt)

**Download Rules:**
- Only `COMPLETED` exports can be downloaded
- `PENDING`, `PROCESSING`, or `FAILED` exports return 422 error
- `EXPIRED` exports return 410 Gone error
- Users can only download their own exports (or have admin access)

---

## 7. Validation Rules

### 7.1 Report Type Validation

- **Format:** Enum - Must be one of: `ATTENDANCE`, `LEAVE`, `SALARY_SUMMARY`, `EMPLOYEE`, `TASK`, `PROJECT`, `AUDIT_SUMMARY`
- **Case sensitivity:** Case-insensitive (normalize to uppercase)
- **Error:** 404 `REPORT_TYPE_NOT_FOUND` if invalid

### 7.2 Export ID Validation

- **Format:** RFC 4122 UUID v4 format
- **Error:** 400 `VALIDATION_FAILED` if invalid UUID format
- **Error:** 404 `EXPORT_NOT_FOUND` if export does not exist or belongs to different report type

### 7.3 Filter Validation (Export Request)

- **Date range:** Same validation as report view filters (see `F12A_api_spec.md` section 7.2)
- **UUID fields:** Same validation as report view filters (see `F12A_api_spec.md` section 7.3)
- **Status enum:** Same validation as report view filters (see `F12A_api_spec.md` section 7.4)
- **Role-based scope:** Same validation as report view filters (see `F12A_api_spec.md` section 7.7)
- **Error:** 422 `VALIDATION_ERROR` or `BUSINESS_RULE_FAILED` if validation fails

### 7.4 Export Status Validation

- **Download requirement:** Export must be in `COMPLETED` status
- **Error:** 422 `BUSINESS_RULE_FAILED` if status is not `COMPLETED`
- **Error:** 410 `EXPORT_EXPIRED` if status is `EXPIRED`

---

## 8. Error Handling

### 8.1 Export-Specific Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `EXPORT_NOT_FOUND` | 404 | Export not found (invalid export_id or report_type mismatch) |
| `EXPORT_EXPIRED` | 410 | Export has expired (24 hours TTL exceeded) |
| `ASYNC_OPERATION_FAILED` | 500 | Async export generation failed (internal error) |

### 8.2 Common Error Scenarios

**Export Creation Fails:**
- Invalid report type → 404 `REPORT_TYPE_NOT_FOUND`
- Insufficient permissions → 403 `INSUFFICIENT_PERMISSIONS`
- Invalid filters → 422 `VALIDATION_ERROR` or `BUSINESS_RULE_FAILED`
- Server error → 500 `INTERNAL_ERROR`

**Export Status Check Fails:**
- Export not found → 404 `EXPORT_NOT_FOUND`
- Access denied → 403 `INSUFFICIENT_PERMISSIONS`
- Server error → 500 `INTERNAL_ERROR`

**Export Download Fails:**
- Export not found → 404 `EXPORT_NOT_FOUND`
- Export expired → 410 `EXPORT_EXPIRED`
- Export not ready → 422 `BUSINESS_RULE_FAILED` (status not COMPLETED)
- Access denied → 403 `INSUFFICIENT_PERMISSIONS`
- Server error → 500 `INTERNAL_ERROR`

---

## 9. Assumptions

- PDF generation is asynchronous (non-blocking)
- Export artifacts are stored temporarily (24 hours TTL)
- Export generation may take several seconds to minutes depending on report size
- Clients should poll export status at reasonable intervals (e.g., every 2-5 seconds)
- Export artifacts are immutable snapshots (do not update when underlying data changes)
- F-011 (Audit Logging) records export creation, status checks, and downloads automatically
- Export file naming follows pattern: `report_{report_type}_{date}.pdf`
- Export file size is included in status response when COMPLETED

---

## 10. Open Questions

None identified at this stage.

---

## 11. Integration Notes

**Related Endpoints:**
- Report view endpoint: `GET /api/v1/reports/{report_type}` (see `F12A_api_spec.md`)
- Export endpoints build upon report view functionality

**Audit Logging:**
- F-011 (Audit Logging) automatically records:
  - Export creation (`POST /exports`)
  - Export status checks (`GET /exports/{export_id}`)
  - Export downloads (`GET /exports/{export_id}/download`)

**Performance Considerations:**
- Large reports may take longer to generate
- Clients should implement exponential backoff for status polling
- Consider rate limiting for export creation to prevent abuse

---

**Note:** Core reporting endpoints (list reports, view reports) are documented in `F12A_api_spec.md`.

