# API Specification: F-005 — Employee Management

## 1. Overview

The Employee Management feature (F-005) provides a secure, company-bound employee system of record that maintains accurate personnel data, enforces strict role-based visibility, and preserves historical information while supporting downstream features such as salary, leave, and attendance management.

### 1.1 Feature Capabilities
- **Employee Lifecycle Management**: CEO and HR can create, update, activate, deactivate, and soft delete employees
- **Employee Listing & Search**: CEO, HR, and Manager can list employees with pagination, search, filtering, and sorting
- **Employee Detail View**: CEO, HR, and Manager can view detailed employee information with role-based field visibility
- **One-to-One User Linkage**: Enforces strict one-to-one relationship between User and Employee
- **Role-Based Access Control**: Different field visibility for CEO/HR (full), Manager (all fields), and Employee (no access)
- **Soft Delete**: Preserves historical data while removing from standard lists (not visible to anyone after soft delete)

### 1.2 Business Value
Provides a centralized, secure, and auditable employee management system that protects sensitive personnel data through field-level access controls. Enables accurate workforce records while supporting downstream HR workflows such as salary, leave, and attendance management.

### 1.3 Technical Scope
- Employee CRUD operations (CEO/HR only)
- Employee activation/deactivation via `is_active` field updates
- Employee listing with pagination, search, filtering, and sorting
- Role-based field-level visibility (CEO/HR full, Manager all fields, Employee no access)
- One-to-one User ↔ Employee constraint enforcement
- Soft deletion with complete data preservation
- ENUM-based controlled fields for consistency
- Company-scoped employee records

### 1.4 Out of Scope
- **SuperAdmin Access**: SuperAdmin is explicitly excluded from employee data
- **Hard Deletion**: Only soft deletion is supported (data preservation)
- **Salary Management**: Handled in F-006
- **Document Versioning**: Not supported
- **Bulk Import/Export**: Not supported
- **Self-Profile Endpoint**: Removed per design decision

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
  - `null` for SuperAdmin (global access, but excluded from employee endpoints)
  - UUID for company-scoped users (CEO, HR, Manager, Employee)
- `exp` (integer): Token expiration (Unix timestamp) - **REQUIRED**
- `iat` (integer): Token issued at (Unix timestamp) - **RECOMMENDED**
- `jti` (string): JWT ID for token revocation - **RECOMMENDED**

**Token Expiration:**
- Access tokens: 15 minutes to 1 hour
- Token refresh: Supported via separate endpoint (implementation TBD)

**Multi-tenancy:**
- SuperAdmin (`org_id: null`): **Explicitly excluded from employee endpoints** (returns 403)
- Company users (`org_id: "<uuid>"`): Limited to specified company's employees

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

#### CEO (Company Admin)
**Access Scope:** Full company administration within own organization
**Capabilities:**
- Create, update, activate, deactivate, and soft delete employees in own company
- View all employee fields (full access)
- List employees with full field visibility
- Access employee details with all fields

#### HR (Company Level)
**Access Scope:** Employee management and HR operations within own company
**Capabilities:**
- Create, update, activate, deactivate, and soft delete employees in own company
- View all employee fields (full access)
- List employees with full field visibility
- Access employee details with all fields

#### Manager (Company Level)
**Access Scope:** Employee visibility within own company
**Capabilities:**
- View all employee fields (full access to all fields)
- List employees with all fields visible
- Access employee details with all fields
- **Cannot create, update, or delete employees**
- **Cannot see CEO or HR employee records** (filtered out from lists)

#### Employee (Company Level)
**Access Scope:** No access to employee management endpoints
**Capabilities:**
- **No access to any employee endpoints** (returns 403)
- Cannot view employee lists
- Cannot access employee detail endpoints

#### SuperAdmin (Platform Level)
**Access Scope:** Explicitly excluded from employee data
**Capabilities:**
- **No access to any employee endpoints** (returns 403)
- Employee data is company-scoped and not accessible to SuperAdmin

### 3.2 Permission Matrix (F-005 Endpoints)

| Endpoint | SuperAdmin | CEO | HR | Manager | Employee |
|----------|------------|-----|----|---------|----------|
| GET /api/v1/company/employees | ❌ | ✅ | ✅ | ✅ (all fields) | ❌ |
| POST /api/v1/company/employees | ❌ | ✅ | ✅ | ❌ | ❌ |
| GET /api/v1/company/employees/{employee_id} | ❌ | ✅ | ✅ | ✅ (all fields) | ❌ |
| PATCH /api/v1/company/employees/{employee_id} | ❌ | ✅ | ✅ | ❌ | ❌ |
| DELETE /api/v1/employees/{employee_id} | ❌ | ✅ | ✅ | ❌ | ❌ |

**Notes:**
- Manager sees all fields but cannot see CEO or HR employee records in lists
- Employee role has no access to any employee endpoints
- SuperAdmin is explicitly excluded from all employee endpoints

### 3.3 Row-Level Security (RLS)
- **SuperAdmin**: Explicitly excluded (returns 403 for all employee endpoints)
- **CEO/HR**: Can only access employees in their own company (determined from JWT `org_id` claim)
- **Manager**: Can only access employees in their own company, excluding CEO and HR records
- **Employee**: No access to employee endpoints
- **Company Scoping**: All employee operations use `org_id` from JWT token for authorization

---

## 4. Resources & Endpoints

### 4.1 Resource Overview

#### Employee Resource
Represents a company-bound personnel record linked one-to-one with a User. Employee is the authoritative source of personal and professional data and drives access to HR-related workflows.

**Key Fields:**
- `employee_id` (UUID): Unique employee identifier
- `user_id` (UUID): Linked User ID (one-to-one, required, immutable)
- `company_id` (UUID): Owning company ID (required, immutable)
- `joining_date` (date): Employment start date (mandatory, immutable after creation)
- `employment_status` (string, ENUM): Current HR state (TRAINEE, PROBATION, CONFIRMED, NOTICE_PERIOD, ACTIVE, ON_HOLD, TERMINATED, RESIGNED)
- `job_title` (string, nullable): Professional title (editable by HR/CEO)
- `department` (string, ENUM, nullable): Functional department (FRONTEND, BACKEND, FULLSTACK, QA, HR, DEVOPS, UIUX, PRODUCT, MARKETING, DATA, SUPPORT)
- `employment_type` (string, ENUM, nullable): Nature of employment (FULL_TIME, PART_TIME, CONTRACT, FREELANCE, TEMPORARY)
- `employment_level` (string, ENUM, nullable): Seniority level (INTERN, JUNIOR, MID, SENIOR, LEAD, MANAGER)
- `work_email` (string, nullable): Official email (company-scoped, case-insensitive unique within company)
- `gender` (string, ENUM, nullable): Gender identity (MALE, FEMALE, OTHER)
- `marital_status` (string, ENUM, nullable): Marital status (SINGLE, MARRIED, DIVORCED, WIDOWED, SEPARATED)
- `blood_group` (string, ENUM, nullable): Blood group (A+, A-, B+, B-, AB+, AB-, O+, O-)
- `nationality` (string, nullable): Nationality (free text)
- `address` (string, nullable): Residential address (restricted visibility)
- `city` (string, nullable): City (API-based dropdown)
- `state` (string, nullable): State (dependent dropdown)
- `country` (string, nullable): Country (API-based dropdown)
- `document_type` (string, ENUM, nullable): Identity document type (AADHAAR, PAN, DL, VOTER_ID, PASSPORT)
- `document_number` (string, nullable): Identity document reference (restricted visibility)
- `separation_initiated_date` (date, nullable): Resignation submission or termination issue date (required if RESIGNED or TERMINATED)
- `separation_reason` (string, nullable): Reason for resignation or termination (mandatory if RESIGNED or TERMINATED)
- `last_working_day` (date, nullable): Final working day (valid for resignation & termination)
- `notice_period_days` (integer, nullable): Notice period duration (0 allowed for immediate termination)
- `is_active` (boolean): System access state (controls login, defaults to `true`)
- `is_deleted` (boolean): Soft delete flag (CEO-only visibility, defaults to `false`)
- `created_at` (datetime, UTC): Creation timestamp
- `updated_at` (datetime, UTC): Last update timestamp
- `created_by` (UUID, nullable): User ID who created the employee
- `updated_by` (UUID, nullable): User ID who last updated the employee

**Field Categories:**
- **Immutable Fields**: `user_id`, `company_id`, `joining_date` (cannot be changed after creation)
- **Lifecycle Fields**: `is_active`, `is_deleted` (CEO/HR only)
- **Professional Fields**: `job_title`, `department`, `employment_type`, `employment_level`, `work_email`, `employment_status`
- **Personal Fields**: `gender`, `marital_status`, `blood_group`, `nationality`, `address`, `city`, `state`, `country`, `document_type`, `document_number`
- **Separation Fields**: `separation_initiated_date`, `separation_reason`, `last_working_day`, `notice_period_days` (required when status is RESIGNED or TERMINATED)

**ENUM Definitions:**
- **EmploymentStatus**: TRAINEE, PROBATION, CONFIRMED, NOTICE_PERIOD, ACTIVE, ON_HOLD, TERMINATED, RESIGNED
- **EmploymentType**: FULL_TIME, PART_TIME, CONTRACT, FREELANCE, TEMPORARY
- **EmploymentLevel**: INTERN, JUNIOR, MID, SENIOR, LEAD, MANAGER
- **Department**: FRONTEND, BACKEND, FULLSTACK, QA, HR, DEVOPS, UIUX, PRODUCT, MARKETING, DATA, SUPPORT
- **Gender**: MALE, FEMALE, OTHER
- **MaritalStatus**: SINGLE, MARRIED, DIVORCED, WIDOWED, SEPARATED
- **BloodGroup**: A+, A-, B+, B-, AB+, AB-, O+, O-
- **DocumentType**: AADHAAR, PAN, DL, VOTER_ID, PASSPORT

**Relationships:**
- Exactly one Employee ↔ one User (one-to-one, required)
- Employee belongs to exactly one Company (required)
- Employee role mirrors User role (access control owned by F-001)

### 4.2 Endpoint Summary

| Method | Path | Purpose | Authentication |
|--------|------|---------|---------------|
| GET | `/api/v1/company/employees` | List employees with pagination, search, filtering, sorting | Required |
| POST | `/api/v1/company/employees` | Create new employee from existing User | Required |
| GET | `/api/v1/company/employees/{employee_id}` | Get employee details with role-based field visibility | Required |
| PATCH | `/api/v1/company/employees/{employee_id}` | Update employee fields (including is_active for deactivate/reactivate) | Required |
| DELETE | `/api/v1/employees/{employee_id}` | Soft delete employee | Required |

### 4.3 API Documentation Class (Rule 10)

**Note:** All endpoint documentation MUST use the centralized `EmployeeApiDocs` class structure (Rule 10). Router endpoints MUST reference `summary` and `description` from this class, NOT hardcoded strings.

**Documentation Class Structure:**

```python
# src/employees/documentations/employee_api_doc.py
from typing import ClassVar

class EmployeeApiDocs:
    """API documentation for Employee endpoints"""
    
    list: ClassVar[dict] = {
        "summary": "Purpose of this API is to list employees with pagination, search, filtering, and sorting",
        "description": "Retrieves a paginated list of employees in the authenticated user's company. Supports filtering by department and employment_status, search by name/email, and sorting. Soft-deleted employees are excluded. CEO and HR see all employees with full fields. Manager sees all fields but cannot see CEO or HR employee records. Employee role has no access. Requires JWT authentication."
    }
    
    create: ClassVar[dict] = {
        "summary": "Purpose of this API is to create a new employee from existing User",
        "description": "Creates a new employee record linked to an existing User. Enforces one-to-one User ↔ Employee constraint. User must not already have an employee record. JoiningDate is mandatory and immutable after creation. ENUM fields must be validated. WorkEmail must be unique within company (case-insensitive). Separation fields are required when employment_status is RESIGNED or TERMINATED. Only CEO and HR can create employees."
    }
    
    get: ClassVar[dict] = {
        "summary": "Purpose of this API is to get employee details with role-based field visibility",
        "description": "Retrieves detailed employee information. CEO and HR see all fields. Manager sees all fields. Employee role has no access. Includes derived fields (can_edit, can_deactivate, can_soft_delete) based on role and employee state. Soft-deleted employees are not accessible. Requires If-None-Match header for cache validation (optional)."
    }
    
    update: ClassVar[dict] = {
        "summary": "Purpose of this API is to update employee fields including activation/deactivation",
        "description": "Updates employee fields. JoiningDate, user_id, and company_id are immutable. Setting is_active=false deactivates employee (blocks login). Setting is_active=true reactivates employee (restores login). Separation fields are required when employment_status changes to RESIGNED or TERMINATED. WorkEmail must be unique within company (case-insensitive). Only CEO and HR can update employees. Requires If-Match header for concurrency control."
    }
    
    delete: ClassVar[dict] = {
        "summary": "Purpose of this API is to soft delete an employee",
        "description": "Soft deletes an employee by setting is_deleted=true. After soft delete, employee is not visible to anyone (including CEO). Historical data is preserved. Only CEO and HR can soft delete employees. Requires If-Match header for concurrency control."
    }
```

**Router Endpoint Pattern (REQUIRED):**

```python
# src/employees/routers.py
from src.employees.documentations.employee_api_doc import EmployeeApiDocs

@router.get(
    "",
    response_model=StandardResponse[EmployeePaginatedResponse[EmployeeSummary]],
    summary=EmployeeApiDocs.list["summary"],
    description=EmployeeApiDocs.list["description"]
)
async def list_employees(...):
    """List employees with pagination, filtering, search, and sorting."""
    pass

@router.post(
    "",
    response_model=StandardResponse[EmployeeDetail],
    summary=EmployeeApiDocs.create["summary"],
    description=EmployeeApiDocs.create["description"]
)
async def create_employee(...):
    """Create a new employee from existing User."""
    pass
```

---

## 5. Endpoint Details

### 5.1 GET /api/v1/company/employees

- **Purpose:** List employees in authenticated user's company with pagination, search, filtering, and sorting
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, HR, Manager (Employee role returns 403, SuperAdmin returns 403)
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
class EmployeeListQuery(BaseModel):
    """Query schema for listing employees with pagination and filtering."""

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    search: Optional[str] = Field(None, description="Search by user name or email (case-insensitive partial match)")
    department: Optional[str] = Field(None, description="Filter by department (exact match): FRONTEND, BACKEND, FULLSTACK, QA, HR, DEVOPS, UIUX, PRODUCT, MARKETING, DATA, SUPPORT")
    employment_status: Optional[str] = Field(None, description="Filter by employment status (exact match): TRAINEE, PROBATION, CONFIRMED, NOTICE_PERIOD, ACTIVE, ON_HOLD, TERMINATED, RESIGNED")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, joining_date, job_title, department, employment_status")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)
```

**Router Endpoint Pattern (REQUIRED):**
```python
@router.get("", response_model=StandardResponse[EmployeePaginatedResponse[EmployeeSummary]])
async def list_employees(
    query: EmployeeListQuery = Depends(EmployeeListQuery),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List employees with pagination, filtering, search, and sorting."""
    # Access via query.page, query.page_size, query.search, etc.
```

**Query Parameters Table (for documentation only):**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number (≥ 1) |
| page_size | integer | No | 20 | Page size (1-100) |
| search | string | No | null | Search by user name or email (case-insensitive partial match) |
| department | string | No | null | Filter by department (exact match, ENUM values) |
| employment_status | string | No | null | Filter by employment status (exact match, ENUM values) |
| sort_by | string | No | created_at | Sort field: created_at, updated_at, joining_date, job_title, department, employment_status |
| sort_order | string | No | desc | Sort order: asc or desc |

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "items": [
      {
        "employee_id": "550e8400-e29b-41d4-a716-446655440000",
        "user": {
          "user_id": "660e8400-e29b-41d4-a716-446655440001",
          "email": "john.doe@example.com",
          "first_name": "John",
          "last_name": "Doe"
        },
        "job_title": "Software Engineer",
        "department": "BACKEND",
        "employment_status": "ACTIVE",
        "is_active": true,
        "joining_date": "2024-01-15",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-20T10:30:00Z"
      }
    ],
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8,
    "next_page": "/api/v1/company/employees?page=2&page_size=20&sort_by=created_at&sort_order=desc&department=BACKEND",
    "prev_page": null
  },
  "message": "Employees retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Business Rules:**
- Soft-deleted employees (`is_deleted=true`) are excluded from results for all roles
- Manager cannot see CEO or HR employee records (filtered out)
- CEO and HR see all employees in their company
- Manager sees all employees in their company except CEO and HR
- Employee role has no access (returns 403)
- SuperAdmin has no access (returns 403)
- Company scoping: Only employees from authenticated user's company (from JWT `org_id`)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 401 | INVALID_TOKEN | Malformed token or missing required claims |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks permission (Employee role or SuperAdmin) |
| 400 | VALIDATION_FAILED | Invalid query parameter format or value |
| 304 | Not Modified | GET request with If-None-Match - resource unchanged, ETag matches (no response body) |
| 500 | INTERNAL_ERROR | Server error during request processing |

---

### 5.2 POST /api/v1/company/employees

- **Purpose:** Create a new employee from an existing User
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, HR only (Manager, Employee, SuperAdmin return 403)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
    - `ETag: "20240120T103000Z"` (ETag for newly created employee, based on `updated_at`)
- **Idempotency:** No (creates new resource)

**Path Parameters**  
None

**Query Parameters**  
None

**Request Body**

**Schema Table:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| user_id | string (UUID) | Yes | User ID to link employee to | RFC 4122 UUID v4 format, must exist, must not already have employee record |
| joining_date | string (date) | Yes | Employment start date | ISO 8601 date format (YYYY-MM-DD), cannot be future date, immutable after creation |
| employment_status | string | Yes | Current HR state | Enum: TRAINEE, PROBATION, CONFIRMED, NOTICE_PERIOD, ACTIVE, ON_HOLD, TERMINATED, RESIGNED (case-sensitive) |
| job_title | string | No | Professional title | Max 255 characters, alphanumeric and spaces only |
| department | string | No | Functional department | Enum: FRONTEND, BACKEND, FULLSTACK, QA, HR, DEVOPS, UIUX, PRODUCT, MARKETING, DATA, SUPPORT (case-sensitive) |
| employment_type | string | No | Nature of employment | Enum: FULL_TIME, PART_TIME, CONTRACT, FREELANCE, TEMPORARY (case-sensitive) |
| employment_level | string | No | Seniority level | Enum: INTERN, JUNIOR, MID, SENIOR, LEAD, MANAGER (case-sensitive) |
| work_email | string | No | Official email | RFC 5322 format, max 254 characters, case-insensitive unique within company |
| gender | string | No | Gender identity | Enum: MALE, FEMALE, OTHER (case-sensitive) |
| marital_status | string | No | Marital status | Enum: SINGLE, MARRIED, DIVORCED, WIDOWED, SEPARATED (case-sensitive) |
| blood_group | string | No | Blood group | Enum: A+, A-, B+, B-, AB+, AB-, O+, O- (case-sensitive) |
| nationality | string | No | Nationality | Max 100 characters, free text |
| address | string | No | Residential address | Max 500 characters |
| city | string | No | City | Max 100 characters, API-based dropdown |
| state | string | No | State | Max 100 characters, dependent dropdown |
| country | string | No | Country | Max 100 characters, API-based dropdown |
| document_type | string | No | Identity document type | Enum: AADHAAR, PAN, DL, VOTER_ID, PASSPORT (case-sensitive) |
| document_number | string | No | Identity document reference | Max 50 characters, restricted visibility |
| separation_initiated_date | string (date) | No | Resignation/termination date | ISO 8601 date format (YYYY-MM-DD), required if employment_status is RESIGNED or TERMINATED |
| separation_reason | string | No | Reason for resignation/termination | Max 500 characters, required if employment_status is RESIGNED or TERMINATED |
| last_working_day | string (date) | No | Final working day | ISO 8601 date format (YYYY-MM-DD), valid for resignation & termination |
| notice_period_days | integer | No | Notice period duration | Integer, min 0, max 365, 0 allowed for immediate termination |
| is_active | boolean | No | System access state | Defaults to `true` |

**Example Request:**
```json
{
  "user_id": "660e8400-e29b-41d4-a716-446655440001",
  "joining_date": "2024-01-15",
  "employment_status": "PROBATION",
  "job_title": "Software Engineer",
  "department": "BACKEND",
  "employment_type": "FULL_TIME",
  "employment_level": "MID",
  "work_email": "john.doe@example.com",
  "gender": "MALE",
  "marital_status": "SINGLE",
  "blood_group": "O+",
  "nationality": "Indian",
  "address": "123 Main Street",
  "city": "Bangalore",
  "state": "Karnataka",
  "country": "India",
  "document_type": "PAN",
  "document_number": "ABCDE1234F",
  "is_active": true
}
```

**Success Response (201 Created)**

```json
{
  "data": {
    "employee_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "660e8400-e29b-41d4-a716-446655440001",
    "company_id": "770e8400-e29b-41d4-a716-446655440002",
    "joining_date": "2024-01-15",
    "employment_status": "PROBATION",
    "job_title": "Software Engineer",
    "department": "BACKEND",
    "employment_type": "FULL_TIME",
    "employment_level": "MID",
    "work_email": "john.doe@example.com",
    "gender": "MALE",
    "marital_status": "SINGLE",
    "blood_group": "O+",
    "nationality": "Indian",
    "address": "123 Main Street",
    "city": "Bangalore",
    "state": "Karnataka",
    "country": "India",
    "document_type": "PAN",
    "document_number": "ABCDE1234F",
    "separation_initiated_date": null,
    "separation_reason": null,
    "last_working_day": null,
    "notice_period_days": null,
    "is_active": true,
    "is_deleted": false,
    "user": {
      "user_id": "660e8400-e29b-41d4-a716-446655440001",
      "email": "john.doe@example.com",
      "first_name": "John",
      "last_name": "Doe"
    },
    "created_at": "2024-01-20T10:30:00Z",
    "updated_at": "2024-01-20T10:30:00Z",
    "created_by": "880e8400-e29b-41d4-a716-446655440003",
    "updated_by": "880e8400-e29b-41d4-a716-446655440003"
  },
  "message": "Employee created successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103000Z"` (ETag for newly created employee, based on `updated_at`)

**Business Rules:**
- User must exist and belong to the same company as authenticated user
- User must not already have an employee record (one-to-one constraint)
- JoiningDate is mandatory and immutable after creation
- JoiningDate cannot be a future date
- WorkEmail must be unique within company (case-insensitive)
- If employment_status is RESIGNED or TERMINATED, separation_initiated_date and separation_reason are required
- ENUM values must match exact case-sensitive values
- Company is automatically set from JWT `org_id` claim
- Created_by and updated_by are set to authenticated user ID

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 401 | INVALID_TOKEN | Malformed token or missing required claims |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks permission (Manager, Employee, SuperAdmin) |
| 404 | USER_NOT_FOUND | User with specified user_id does not exist |
| 400 | VALIDATION_FAILED | Invalid request format or field validation failed |
| 409 | DUPLICATE_EMPLOYEE | User already has an employee record (one-to-one constraint violation) |
| 409 | DUPLICATE_WORK_EMAIL | WorkEmail already exists in company (case-insensitive) |
| 422 | BUSINESS_RULE_FAILED | Business rule violation (e.g., separation fields missing when status is RESIGNED/TERMINATED, user belongs to different company) |
| 500 | INTERNAL_ERROR | Server error during request processing |

Example error (409 Conflict - Duplicate Employee):
```json
{
  "error": {
    "code": "DUPLICATE_EMPLOYEE",
    "details": [{"field": "user_id", "issue": "User already has an employee record. One-to-one constraint violation."}]
  },
  "message": "Employee creation failed: User already has an employee record."
}
```

Example error (422 Unprocessable Entity - Missing Separation Fields):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [{"field": "separation_initiated_date", "issue": "Separation fields (separation_initiated_date, separation_reason) are required when employment_status is RESIGNED or TERMINATED."}]
  },
  "message": "Business rule violation: Separation fields are required for RESIGNED or TERMINATED status."
}
```

---

### 5.3 GET /api/v1/company/employees/{employee_id}

- **Purpose:** Get employee details with role-based field visibility
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, HR, Manager (Employee role returns 403, SuperAdmin returns 403)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-None-Match: "20240120T103000Z"` (optional, for cache validation - returns 304 if unchanged)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
    - `ETag: "20240120T103000Z"` (Resource version identifier based on `updated_at`)
    - `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (RECOMMENDED)
- **Idempotency:** Yes (GET operation)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| employee_id | string (UUID) | Yes | Employee identifier (RFC 4122 UUID v4 format) |

**Note:** All path parameters MUST use snake_case (e.g., `employee_id`) - see Rule 2.

**Query Parameters**  
None

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "employee_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "660e8400-e29b-41d4-a716-446655440001",
    "company_id": "770e8400-e29b-41d4-a716-446655440002",
    "joining_date": "2024-01-15",
    "employment_status": "ACTIVE",
    "job_title": "Software Engineer",
    "department": "BACKEND",
    "employment_type": "FULL_TIME",
    "employment_level": "MID",
    "work_email": "john.doe@example.com",
    "gender": "MALE",
    "marital_status": "SINGLE",
    "blood_group": "O+",
    "nationality": "Indian",
    "address": "123 Main Street",
    "city": "Bangalore",
    "state": "Karnataka",
    "country": "India",
    "document_type": "PAN",
    "document_number": "ABCDE1234F",
    "separation_initiated_date": null,
    "separation_reason": null,
    "last_working_day": null,
    "notice_period_days": null,
    "is_active": true,
    "is_deleted": false,
    "user": {
      "user_id": "660e8400-e29b-41d4-a716-446655440001",
      "email": "john.doe@example.com",
      "first_name": "John",
      "last_name": "Doe"
    },
    "can_edit_employee": true,
    "can_deactivate": true,
    "can_soft_delete": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T10:30:00Z",
    "created_by": "880e8400-e29b-41d4-a716-446655440003",
    "updated_by": "880e8400-e29b-41d4-a716-446655440003"
  },
  "message": "Employee retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103000Z"` (REQUIRED for resources that support updates, based on `updated_at`)
- `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (RECOMMENDED)

**Derived Fields:**
- `can_edit_employee` (boolean): True if authenticated user can edit employee (CEO/HR only)
- `can_deactivate` (boolean): True if authenticated user can deactivate employee (CEO/HR only, cannot deactivate own employee)
- `can_soft_delete` (boolean): True if authenticated user can soft delete employee (CEO/HR only, cannot soft delete own employee)

**Business Rules:**
- Employee must exist and belong to authenticated user's company
- Soft-deleted employees are not accessible (returns 404)
- CEO and HR see all fields
- Manager sees all fields
- Employee role has no access (returns 403)
- SuperAdmin has no access (returns 403)
- Derived fields are calculated based on role and employee state

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 401 | INVALID_TOKEN | Malformed token or missing required claims |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks permission (Employee role or SuperAdmin) or employee belongs to different company |
| 404 | EMPLOYEE_NOT_FOUND | Employee with specified employee_id does not exist or is soft-deleted |
| 304 | Not Modified | GET request with If-None-Match - resource unchanged, ETag matches (no response body) |
| 500 | INTERNAL_ERROR | Server error during request processing |

---

### 5.4 PATCH /api/v1/company/employees/{employee_id}

- **Purpose:** Update employee fields including activation/deactivation via is_active field
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, HR only (Manager, Employee, SuperAdmin return 403)
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
| employee_id | string (UUID) | Yes | Employee identifier (RFC 4122 UUID v4 format) |

**Note:** All path parameters MUST use snake_case (e.g., `employee_id`) - see Rule 2.

**Query Parameters**  
None

**Request Body**

**Schema Table:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| employment_status | string | No | Current HR state | Enum: TRAINEE, PROBATION, CONFIRMED, NOTICE_PERIOD, ACTIVE, ON_HOLD, TERMINATED, RESIGNED (case-sensitive) |
| job_title | string | No | Professional title | Max 255 characters, alphanumeric and spaces only |
| department | string | No | Functional department | Enum: FRONTEND, BACKEND, FULLSTACK, QA, HR, DEVOPS, UIUX, PRODUCT, MARKETING, DATA, SUPPORT (case-sensitive) |
| employment_type | string | No | Nature of employment | Enum: FULL_TIME, PART_TIME, CONTRACT, FREELANCE, TEMPORARY (case-sensitive) |
| employment_level | string | No | Seniority level | Enum: INTERN, JUNIOR, MID, SENIOR, LEAD, MANAGER (case-sensitive) |
| work_email | string | No | Official email | RFC 5322 format, max 254 characters, case-insensitive unique within company |
| gender | string | No | Gender identity | Enum: MALE, FEMALE, OTHER (case-sensitive) |
| marital_status | string | No | Marital status | Enum: SINGLE, MARRIED, DIVORCED, WIDOWED, SEPARATED (case-sensitive) |
| blood_group | string | No | Blood group | Enum: A+, A-, B+, B-, AB+, AB-, O+, O- (case-sensitive) |
| nationality | string | No | Nationality | Max 100 characters, free text |
| address | string | No | Residential address | Max 500 characters |
| city | string | No | City | Max 100 characters, API-based dropdown |
| state | string | No | State | Max 100 characters, dependent dropdown |
| country | string | No | Country | Max 100 characters, API-based dropdown |
| document_type | string | No | Identity document type | Enum: AADHAAR, PAN, DL, VOTER_ID, PASSPORT (case-sensitive) |
| document_number | string | No | Identity document reference | Max 50 characters, restricted visibility |
| separation_initiated_date | string (date) | No | Resignation/termination date | ISO 8601 date format (YYYY-MM-DD), required if employment_status is RESIGNED or TERMINATED |
| separation_reason | string | No | Reason for resignation/termination | Max 500 characters, required if employment_status is RESIGNED or TERMINATED |
| last_working_day | string (date) | No | Final working day | ISO 8601 date format (YYYY-MM-DD), valid for resignation & termination |
| notice_period_days | integer | No | Notice period duration | Integer, min 0, max 365, 0 allowed for immediate termination |
| is_active | boolean | No | System access state | Setting to false deactivates employee (blocks login), setting to true reactivates employee (restores login) |

**Note:** Immutable fields (`user_id`, `company_id`, `joining_date`) cannot be updated and will be ignored if included in request.

**Example Request (Deactivate Employee):**
```json
{
  "is_active": false
}
```

**Example Request (Update Multiple Fields):**
```json
{
  "employment_status": "CONFIRMED",
  "job_title": "Senior Software Engineer",
  "employment_level": "SENIOR",
  "work_email": "john.doe@example.com"
}
```

**Example Request (Set Resignation Status):**
```json
{
  "employment_status": "RESIGNED",
  "separation_initiated_date": "2025-02-01",
  "separation_reason": "Better opportunity",
  "last_working_day": "2025-02-28",
  "notice_period_days": 30
}
```

**Success Response (200 OK)**

```json
{
  "data": {
    "employee_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "660e8400-e29b-41d4-a716-446655440001",
    "company_id": "770e8400-e29b-41d4-a716-446655440002",
    "joining_date": "2024-01-15",
    "employment_status": "CONFIRMED",
    "job_title": "Senior Software Engineer",
    "department": "BACKEND",
    "employment_type": "FULL_TIME",
    "employment_level": "SENIOR",
    "work_email": "john.doe@example.com",
    "gender": "MALE",
    "marital_status": "SINGLE",
    "blood_group": "O+",
    "nationality": "Indian",
    "address": "123 Main Street",
    "city": "Bangalore",
    "state": "Karnataka",
    "country": "India",
    "document_type": "PAN",
    "document_number": "ABCDE1234F",
    "separation_initiated_date": null,
    "separation_reason": null,
    "last_working_day": null,
    "notice_period_days": null,
    "is_active": true,
    "is_deleted": false,
    "user": {
      "user_id": "660e8400-e29b-41d4-a716-446655440001",
      "email": "john.doe@example.com",
      "first_name": "John",
      "last_name": "Doe"
    },
    "can_edit_employee": true,
    "can_deactivate": true,
    "can_soft_delete": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T10:35:00Z",
    "created_by": "880e8400-e29b-41d4-a716-446655440003",
    "updated_by": "880e8400-e29b-41d4-a716-446655440003"
  },
  "message": "Employee updated successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)

**Business Rules:**
- Employee must exist and belong to authenticated user's company
- Immutable fields (`user_id`, `company_id`, `joining_date`) cannot be updated
- Setting `is_active=false` deactivates employee and blocks login immediately
- Setting `is_active=true` reactivates employee and restores login access
- If `employment_status` changes to RESIGNED or TERMINATED, `separation_initiated_date` and `separation_reason` are required
- WorkEmail must be unique within company (case-insensitive)
- ENUM values must match exact case-sensitive values
- Updated_by is set to authenticated user ID
- Soft-deleted employees cannot be updated (returns 404)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 401 | INVALID_TOKEN | Malformed token or missing required claims |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks permission (Manager, Employee, SuperAdmin) or employee belongs to different company |
| 404 | EMPLOYEE_NOT_FOUND | Employee with specified employee_id does not exist or is soft-deleted |
| 400 | VALIDATION_FAILED | Invalid request format or field validation failed |
| 409 | DUPLICATE_WORK_EMAIL | WorkEmail already exists in company (case-insensitive, different employee) |
| 412 | PRECONDITION_FAILED | ETag mismatch (resource was modified since retrieval) |
| 422 | BUSINESS_RULE_FAILED | Business rule violation (e.g., separation fields missing when status is RESIGNED/TERMINATED, attempting to update immutable fields) |
| 428 | PRECONDITION_REQUIRED | If-Match header missing but required |
| 500 | INTERNAL_ERROR | Server error during request processing |

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

Example error (422 Unprocessable Entity - Missing Separation Fields):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [{"field": "separation_initiated_date", "issue": "Separation fields (separation_initiated_date, separation_reason) are required when employment_status is RESIGNED or TERMINATED."}]
  },
  "message": "Business rule violation: Separation fields are required for RESIGNED or TERMINATED status."
}
```

---

### 5.5 DELETE /api/v1/employees/{employee_id}

- **Purpose:** Soft delete an employee (set is_deleted=true)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, HR only (Manager, Employee, SuperAdmin return 403)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-Match: "20240120T103000Z"` (REQUIRED - ETag from GET response, based on `updated_at`, see Rule 8)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
- **Idempotency:** Yes (conditional on ETag, returns success if already soft-deleted)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| employee_id | string (UUID) | Yes | Employee identifier (RFC 4122 UUID v4 format) |

**Note:** All path parameters MUST use snake_case (e.g., `employee_id`) - see Rule 2.

**Note:** DELETE endpoint uses `/api/v1/employees/{employee_id}` path (no `/company` prefix) per design decision.

**Query Parameters**  
None

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {},
  "message": "Employee soft deleted successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Business Rules:**
- Employee must exist and belong to authenticated user's company
- Soft delete sets `is_deleted=true`
- After soft delete, employee is not visible to anyone (including CEO)
- Historical data is preserved (no data loss)
- Cannot soft delete own employee record (returns 422)
- If employee is already soft-deleted, operation is idempotent (returns success)
- Company scoping: Only employees from authenticated user's company can be soft-deleted

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 | UNAUTHENTICATED | Missing or invalid authentication token |
| 401 | TOKEN_EXPIRED | JWT token has expired |
| 401 | INVALID_TOKEN | Malformed token or missing required claims |
| 403 | INSUFFICIENT_PERMISSIONS | User lacks permission (Manager, Employee, SuperAdmin) or employee belongs to different company |
| 404 | EMPLOYEE_NOT_FOUND | Employee with specified employee_id does not exist or is already soft-deleted |
| 412 | PRECONDITION_FAILED | ETag mismatch (resource was modified since retrieval) |
| 422 | BUSINESS_RULE_FAILED | Business rule violation (e.g., cannot soft delete own employee record) |
| 428 | PRECONDITION_REQUIRED | If-Match header missing but required |
| 500 | INTERNAL_ERROR | Server error during request processing |

Example error (422 Unprocessable Entity - Cannot soft delete own employee):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [{"field": "employee_id", "issue": "You cannot soft delete your own employee record."}]
  },
  "message": "Business rule violation: Users cannot soft delete their own employee records."
}
```

---

## 6. Webhooks / Async Behavior

No webhooks or async behavior defined for this feature.

---

## 7. Rate Limiting & Performance

- **Rate Limiting**: 100 requests per minute per user (configurable)
- **Request Size Limit**: 1MB maximum payload size
- **Pagination**: Default page size is 20, maximum is 100 items per page
- **Caching**: GET endpoints support ETag-based cache validation (If-None-Match header)
- **Performance Considerations**:
  - Employee list queries should be optimized with proper database indexes on `company_id`, `is_deleted`, `department`, `employment_status`
  - Manager role filtering (excluding CEO/HR) should be efficient
  - Soft-deleted employees are excluded at database query level

---

## 8. Open Questions

None identified at this stage.

---

## 9. Assumptions

- Employee creation requires an existing User (handled by F-001)
- Company context is determined from JWT `org_id` claim (handled by F-004)
- User roles are managed by F-001 (User & Role Management)
- Reactivated employees regain access without data loss
- Soft-deleted employees are completely hidden from all endpoints (not visible to anyone)
- Document files (if any) are stored securely (implementation detail)
- Country, State, and City dropdowns use external API-based dependent dropdowns (implementation detail)
- WorkEmail uniqueness is enforced at database level (case-insensitive)
- One-to-one User ↔ Employee constraint is enforced at database level

---

## 10. Cross-Feature Dependencies

### 10.1 F-001 — User & Role Management
- **User Entity**: Employee is linked one-to-one with User
- **Role Management**: Employee role mirrors User role (access control owned by F-001)
- **User Invitation**: Employee creation requires existing User (invited via F-001)

### 10.2 F-004 — Platform Company Management
- **Company Entity**: Employee belongs to exactly one Company
- **Company Scoping**: All employee operations are scoped to authenticated user's company (from JWT `org_id` claim)
- **Company Lifecycle**: Employee access may be affected by company activation/deactivation

---

## 11. Request/Response Schema Definitions

### 11.1 EmployeeCreate (Request Schema)

```python
class EmployeeCreate(BaseModel):
    """Request schema for creating an employee."""
    
    user_id: UUID
    joining_date: date
    employment_status: str  # ENUM: TRAINEE, PROBATION, CONFIRMED, NOTICE_PERIOD, ACTIVE, ON_HOLD, TERMINATED, RESIGNED
    job_title: Optional[str] = None
    department: Optional[str] = None  # ENUM: FRONTEND, BACKEND, FULLSTACK, QA, HR, DEVOPS, UIUX, PRODUCT, MARKETING, DATA, SUPPORT
    employment_type: Optional[str] = None  # ENUM: FULL_TIME, PART_TIME, CONTRACT, FREELANCE, TEMPORARY
    employment_level: Optional[str] = None  # ENUM: INTERN, JUNIOR, MID, SENIOR, LEAD, MANAGER
    work_email: Optional[str] = None
    gender: Optional[str] = None  # ENUM: MALE, FEMALE, OTHER
    marital_status: Optional[str] = None  # ENUM: SINGLE, MARRIED, DIVORCED, WIDOWED, SEPARATED
    blood_group: Optional[str] = None  # ENUM: A+, A-, B+, B-, AB+, AB-, O+, O-
    nationality: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    document_type: Optional[str] = None  # ENUM: AADHAAR, PAN, DL, VOTER_ID, PASSPORT
    document_number: Optional[str] = None
    separation_initiated_date: Optional[date] = None
    separation_reason: Optional[str] = None
    last_working_day: Optional[date] = None
    notice_period_days: Optional[int] = None
    is_active: Optional[bool] = True
```

### 11.2 EmployeeUpdate (Request Schema)

```python
class EmployeeUpdate(BaseModel):
    """Request schema for updating an employee."""
    
    employment_status: Optional[str] = None  # ENUM
    job_title: Optional[str] = None
    department: Optional[str] = None  # ENUM
    employment_type: Optional[str] = None  # ENUM
    employment_level: Optional[str] = None  # ENUM
    work_email: Optional[str] = None
    gender: Optional[str] = None  # ENUM
    marital_status: Optional[str] = None  # ENUM
    blood_group: Optional[str] = None  # ENUM
    nationality: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    document_type: Optional[str] = None  # ENUM
    document_number: Optional[str] = None
    separation_initiated_date: Optional[date] = None
    separation_reason: Optional[str] = None
    last_working_day: Optional[date] = None
    notice_period_days: Optional[int] = None
    is_active: Optional[bool] = None
```

### 11.3 EmployeeSummary (List Response Schema)

```python
class EmployeeSummary(BaseModel):
    """Summary schema for employee list responses."""
    
    employee_id: UUID
    user: UserSummary  # Nested user object with user_id, email, first_name, last_name
    job_title: Optional[str]
    department: Optional[str]
    employment_status: str
    is_active: bool
    joining_date: date
    created_at: datetime
    updated_at: datetime
```

### 11.4 EmployeeDetail (Detail Response Schema)

```python
class EmployeeDetail(BaseModel):
    """Detail schema for employee detail responses."""
    
    employee_id: UUID
    user_id: UUID
    company_id: UUID
    joining_date: date
    employment_status: str
    job_title: Optional[str]
    department: Optional[str]
    employment_type: Optional[str]
    employment_level: Optional[str]
    work_email: Optional[str]
    gender: Optional[str]
    marital_status: Optional[str]
    blood_group: Optional[str]
    nationality: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    document_type: Optional[str]
    document_number: Optional[str]
    separation_initiated_date: Optional[date]
    separation_reason: Optional[str]
    last_working_day: Optional[date]
    notice_period_days: Optional[int]
    is_active: bool
    is_deleted: bool
    user: UserSummary  # Nested user object
    can_edit_employee: bool  # Derived field
    can_deactivate: bool  # Derived field
    can_soft_delete: bool  # Derived field
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID]
    updated_by: Optional[UUID]
```

### 11.5 EmployeePaginatedResponse (Pagination Wrapper)

```python
class EmployeePaginatedResponse(BaseModel):
    """Pagination wrapper for employee list responses."""
    
    items: List[EmployeeSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
    next_page: Optional[str]  # Full relative URL or null
    prev_page: Optional[str]  # Full relative URL or null
```

---

**End of API Specification**

