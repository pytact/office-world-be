# API Specification: F-004 — Platform Company Management

## 1. Overview

The Platform Company Management feature (F-004) enables SuperAdmin to centrally provision, govern, and control the lifecycle of tenant companies. It also allows CEO and HR to update limited, non-governance company profile information without affecting access control, tenant isolation, or platform governance.

### 1.1 Feature Capabilities
- **Company Lifecycle Management**: SuperAdmin can create, activate, deactivate, and hard delete companies
- **Company Listing & Search**: SuperAdmin can list all companies with pagination, search, filtering, and sorting
- **Company Detail View**: SuperAdmin can view detailed company information with user counts
- **Company Profile Updates**: CEO and HR can update limited profile fields (description, address, website, logo_url, etc.)
- **Access Control**: Deactivated companies immediately block all associated user logins
- **Data Isolation**: Company defines tenant boundaries and ownership of all company-scoped data

### 1.2 Business Value
Provides centralized, secure, and auditable company management that protects data isolation and platform integrity. Enables controlled tenant onboarding, governance, and access control while allowing company-level admins to maintain basic profile information.

### 1.3 Technical Scope
- Company CRUD operations (SuperAdmin only)
- Company activation/deactivation via field updates
- Company listing with pagination, search, filtering, and sorting
- Company profile updates (CEO/HR only, limited fields)
- User count aggregation for company visibility
- Hard deletion with cascade to all company data (no dependency checks)
- Role-based access control and company-scoped data isolation

### 1.4 Out of Scope
- **User Management**: User creation, role assignment, and invitations are handled in F-001 (User & Role Management)
- **CEO Invitation**: CEO and other user invitations are handled via the existing user invitation endpoint in F-001
- **Self-service Company Signup**: All company creation is SuperAdmin-only
- **File Uploads**: Company logos are provided via `logo_url` string field (clients provide URL, no file upload endpoint)
- **Automated Notifications**: No automated notifications on company lifecycle changes
- **Soft Delete**: Only hard deletion is supported (irreversible)

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
  - UUID for company-scoped users (CEO, HR, Manager, Employee)
- `exp` (integer): Token expiration (Unix timestamp) - **REQUIRED**
- `iat` (integer): Token issued at (Unix timestamp) - **RECOMMENDED**
- `jti` (string): JWT ID for token revocation - **RECOMMENDED**

**Token Expiration:**
- Access tokens: 15 minutes to 1 hour
- Token refresh: Supported via separate endpoint (implementation TBD)

**Multi-tenancy:**
- SuperAdmin (`org_id: null`): Global platform access
- Company users (`org_id: "<uuid>"`): Limited to specified company

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
**Access Scope:** Global platform access, not tied to any company
**Capabilities:**
- Create, update, activate, deactivate, and delete companies
- View all companies across the platform
- Access company details with user counts
- Full company lifecycle management
- **Access denied to company-specific business data** (projects, tasks, attendance, leaves, salaries)

#### CEO (Company Admin)
**Access Scope:** Full company administration within own organization
**Capabilities:**
- View own company profile
- Update limited company profile fields (description, address, city, state, country, postal_code, website, logo_url)
- **Cannot update governance fields** (is_active, is_deleted, name, slug)
- **Cannot update profile when company is inactive** (is_active: false)

#### HR (Company Level)
**Access Scope:** Employee management and HR operations within own company
**Capabilities:**
- View own company profile
- Update limited company profile fields (description, address, city, state, country, postal_code, website, logo_url)
- **Cannot update governance fields** (is_active, is_deleted, name, slug)
- **Cannot update profile when company is inactive** (is_active: false)

### 3.2 Permission Matrix

| Endpoint | SuperAdmin | CEO | HR | Manager | Employee |
|----------|------------|-----|----|---------|----------|
| GET /api/v1/companies | ✅ | ❌ | ❌ | ❌ | ❌ |
| POST /api/v1/companies | ✅ | ❌ | ❌ | ❌ | ❌ |
| GET /api/v1/companies/{company_id} | ✅ | ❌ | ❌ | ❌ | ❌ |
| PATCH /api/v1/companies/{company_id} | ✅ | ❌ | ❌ | ❌ | ❌ |
| DELETE /api/v1/companies/{company_id} | ✅ | ❌ | ❌ | ❌ | ❌ |
| GET /api/v1/company/profile | ❌ | ✅ | ✅ | ❌ | ❌ |
| PATCH /api/v1/company/profile | ❌ | ✅* | ✅* | ❌ | ❌ |

*CEO and HR can only update profile when company is active (is_active: true). Updates are blocked when is_active: false.

### 3.3 Row-Level Security (RLS)
- **SuperAdmin**: Can access all companies (including soft-deleted via `is_deleted: true`)
- **CEO/HR**: Can only access their own company (determined from JWT `org_id` claim)
- **Company Scoping**: All company-scoped operations use `org_id` from JWT token for authorization

---

## 4. Resources & Endpoints

### 4.1 Resource Overview

#### Company Resource
Represents a tenant organization within the platform. Company is a first-class aggregate that defines tenant boundaries, access control scope, and ownership of all company-scoped data.

**Key Fields:**
- `company_id` (UUID): Unique company identifier
- `name` (string): Company name (immutable, case-insensitive unique)
- `slug` (string): URL identifier (immutable, globally unique, lowercase alphanumeric-hyphens)
- `description` (string, nullable): Company description (editable by CEO/HR)
- `address` (string, nullable): Physical address (editable by CEO/HR)
- `city` (string, nullable): City (editable by CEO/HR)
- `state` (string, nullable): State (editable by CEO/HR)
- `country` (string, nullable): Country (editable by CEO/HR)
- `postal_code` (string, nullable): Postal/ZIP code (editable by CEO/HR)
- `website` (string, nullable): Company website URL (editable by CEO/HR)
- `logo_url` (string, nullable): Company logo URL (editable by CEO/HR, provided by client as string)
- `is_active` (boolean): Company active state (SuperAdmin-only, defaults to `true` on creation)
- `is_deleted` (boolean): Soft deletion marker (SuperAdmin-only, for visibility purposes)
- `user_count` (integer, derived): Number of users associated with the company (aggregate)
- `created_at` (datetime, UTC): Creation timestamp
- `updated_at` (datetime, UTC): Last update timestamp
- `created_by` (UUID, nullable): User ID who created the company
- `updated_by` (UUID, nullable): User ID who last updated the company

**Field Categories:**
- **Immutable Fields**: `name`, `slug` (cannot be changed after creation)
- **Governance Fields**: `is_active`, `is_deleted` (SuperAdmin-only)
- **Profile Fields**: `description`, `address`, `city`, `state`, `country`, `postal_code`, `website`, `logo_url` (editable by CEO/HR when company is active)

**Relationships:**
- Owns Users (via UserRoleAssignment)
- Owns Employees
- Owns all company-scoped records (leaves, tasks, salaries, notifications, etc.)

### 4.2 Endpoint Summary

| Method | Path | Purpose | Authentication |
|--------|------|---------|---------------|
| GET | `/api/v1/companies` | List all companies with pagination, search, filtering, sorting | Required |
| POST | `/api/v1/companies` | Create new company | Required |
| GET | `/api/v1/companies/{company_id}` | Get company details with user count | Required |
| PATCH | `/api/v1/companies/{company_id}` | Update company or activate/deactivate | Required |
| DELETE | `/api/v1/companies/{company_id}` | Hard delete company (irreversible) | Required |
| GET | `/api/v1/company/profile` | Get own company profile | Required |
| PATCH | `/api/v1/company/profile` | Update company profile fields | Required |

### 4.3 API Documentation Class (Rule 10)

**Note:** All endpoint documentation MUST use the centralized `CompanyApiDocs` class structure (Rule 10). Router endpoints MUST reference `summary` and `description` from this class, NOT hardcoded strings.

**Documentation Class Structure:**

```python
# src/companies/documentations/company_api_doc.py
from typing import ClassVar

class CompanyApiDocs:
    """API documentation for Company endpoints"""
    
    list: ClassVar[dict] = {
        "summary": "Purpose of this API is to list all companies with pagination, search, filtering, and sorting",
        "description": "Retrieves a paginated list of all companies across the platform. Supports search by company name or slug, filtering by status (active/inactive), and sorting by various fields. Only SuperAdmin can access this endpoint. Soft-deleted companies remain visible to SuperAdmin."
    }
    
    create: ClassVar[dict] = {
        "summary": "Purpose of this API is to create a new company",
        "description": "Creates a new company with required metadata (name and slug). Company defaults to active state (is_active: true) on creation. Name and slug must be globally unique. Only SuperAdmin can create companies."
    }
    
    get: ClassVar[dict] = {
        "summary": "Purpose of this API is to get company details with user count",
        "description": "Retrieves detailed company information including all profile fields, governance fields (is_active, is_deleted), user count aggregate, and audit fields. Only SuperAdmin can access this endpoint."
    }
    
    update: ClassVar[dict] = {
        "summary": "Purpose of this API is to update company information or activate/deactivate company",
        "description": "Updates company information including profile fields and governance fields. Can activate or deactivate company by setting is_active field. Name and slug are immutable and cannot be updated. Deactivation immediately blocks all associated user logins. Only SuperAdmin can update companies. Requires If-Match header for concurrency control."
    }
    
    delete: ClassVar[dict] = {
        "summary": "Purpose of this API is to hard delete a company",
        "description": "Permanently deletes a company and all associated data (users, employees, leaves, tasks, salaries, notifications, etc.). This operation is irreversible and proceeds even if company has active users. Only SuperAdmin can delete companies. Requires If-Match header for concurrency control."
    }
    
    get_profile: ClassVar[dict] = {
        "summary": "Purpose of this API is to get own company profile",
        "description": "Retrieves the authenticated user's company profile. Company is determined from JWT org_id claim. Response excludes governance fields (is_deleted, audit fields, user_count). Name and slug are read-only. Only CEO and HR can access this endpoint."
    }
    
    update_profile: ClassVar[dict] = {
        "summary": "Purpose of this API is to update company profile fields",
        "description": "Updates limited company profile fields (description, address, city, state, country, postal_code, website, logo_url). Governance fields (name, slug, is_active, is_deleted) cannot be updated. Updates are blocked when company is inactive (is_active: false). Only CEO and HR can update company profile. Requires If-Match header for concurrency control."
    }
```

**Router Endpoint Pattern (REQUIRED):**

```python
# src/companies/routers.py
from src.companies.documentations.company_api_doc import CompanyApiDocs

@router.get(
    "",
    response_model=StandardResponse[CompanyPaginatedResponse[CompanySummary]],
    summary=CompanyApiDocs.list["summary"],
    description=CompanyApiDocs.list["description"]
)
async def list_companies(...):
    """List companies with pagination, filtering, search, and sorting."""
    pass

@router.post(
    "",
    response_model=StandardResponse[CompanyDetail],
    summary=CompanyApiDocs.create["summary"],
    description=CompanyApiDocs.create["description"]
)
async def create_company(...):
    """Create a new company"""
    pass

# ... similar pattern for all endpoints
```

**Note:** 
- Documentation class MUST be created in `src/companies/documentations/company_api_doc.py` (or similar structure based on project conventions)
- All router endpoints MUST use `summary` and `description` from `CompanyApiDocs` class
- DO NOT use hardcoded strings in router decorators

---

## 4.4 Endpoint Details

#### 4.4.1 GET /api/v1/companies

- **Purpose:** List all companies across the platform with pagination, search, filtering, and sorting (SuperAdmin only)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin only
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-None-Match: "20240120T103000Z"` (optional, for cache validation - returns 304 if unchanged)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
- **Idempotency:** Yes (GET operation)

**Path Parameters**  
None

**Note:** All path parameters MUST use snake_case (e.g., `user_id`, `company_id`, `role_id`) - see Rule 2.

**Query Parameters**  
**Note:** Query parameters MUST be defined using a query schema class with `Depends()` pattern (Rule 9), NOT individual `Query()` parameters in the router endpoint.

**Query Schema Class (REQUIRED):**
```python
class CompanyListQuery(BaseModel):
    """Query schema for listing companies with pagination and filtering."""

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    search: Optional[str] = Field(None, description="Search by company name or slug (case-insensitive partial match)")
    status: Optional[str] = Field(None, description="Filter by status: active, inactive")
    sort_by: str = Field("created_at", description="Sort field: created_at, updated_at, name, slug, is_active")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)
```

**Router Endpoint Pattern (REQUIRED):**
```python
@router.get("", response_model=StandardResponse[CompanyPaginatedResponse[CompanySummary]])
async def list_companies(
    query: CompanyListQuery = Depends(CompanyListQuery),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_superadmin),
):
    """List companies with pagination, filtering, search, and sorting."""
    # Access via query.page, query.page_size, query.search, etc.
```

**Query Parameters Table (for documentation only):**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number (≥ 1) |
| page_size | integer | No | 20 | Page size (1-100) |
| search | string | No | null | Search by company name or slug (case-insensitive partial match) |
| status | string | No | null | Filter by status: active, inactive |
| sort_by | string | No | created_at | Sort field: created_at, updated_at, name, slug, is_active |
| sort_order | string | No | desc | Sort order: asc or desc |

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "items": [
      {
        "company_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Acme Corporation",
        "slug": "acme-corp",
        "is_active": true,
        "is_deleted": false,
        "user_count": 25,
        "created_at": "2024-01-20T10:00:00Z",
        "updated_at": "2024-01-20T15:30:00Z"
      },
      {
        "company_id": "660e8400-e29b-41d4-a716-446655440001",
        "name": "Tech Solutions Inc",
        "slug": "tech-solutions",
        "is_active": false,
        "is_deleted": false,
        "user_count": 12,
        "created_at": "2024-01-18T08:00:00Z",
        "updated_at": "2024-01-19T14:20:00Z"
      }
    ],
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8,
    "next_page": "/api/v1/companies?page=2&page_size=20&sort_by=created_at&sort_order=desc&status=active",
    "prev_page": null
  },
  "message": "Companies retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- `next_page` and `prev_page` include all query parameters (filters, sort, search) to preserve pagination state.
- Soft-deleted companies (is_deleted: true) remain visible to SuperAdmin.
- `user_count` represents the total number of users associated with the company.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User is not SuperAdmin |
| 400 Bad Request | `INVALID_REQUEST` | Invalid query parameter format or value |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during request processing |

Example error (403 Forbidden):
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "details": [{"field": "role", "issue": "Only SuperAdmin can access platform-wide company list."}]
  },
  "message": "You do not have permission to perform this action."
}
```

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate error.

---

#### 4.4.2 POST /api/v1/companies

- **Purpose:** Create a new company with required metadata (SuperAdmin only)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin only
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
- **Idempotency:** No (creates new resource)

**Path Parameters**  
None

**Query Parameters**  
None

**Request Body**

**Schema Table:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| name | string | Yes | Company name | Min 1 character, max 255 characters, case-insensitive unique across all companies |
| slug | string | Yes | Company URL identifier | Lowercase alphanumeric with hyphens only (e.g., `acme-corp`), min 3 characters, max 100 characters, case-insensitive unique globally, pattern: `^[a-z0-9]+(?:-[a-z0-9]+)*$` |
| description | string | No | Company description | Max 1000 characters |
| address | string | No | Physical address | Max 255 characters |
| city | string | No | City | Max 100 characters |
| state | string | No | State | Max 100 characters |
| country | string | No | Country | Max 100 characters |
| postal_code | string | No | Postal/ZIP code | Max 20 characters |
| website | string | No | Company website URL | Valid HTTPS URL, max 2048 characters |
| logo_url | string | No | Company logo URL | Valid HTTPS URL, max 2048 characters |

**Note:** 
- `name` and `slug` are immutable after creation.
- `is_active` defaults to `true` (active) on creation.
- `is_deleted` defaults to `false` on creation.
- All other fields are optional and can be set during creation or updated later.
- `logo_url` is a string field where clients provide the URL (no file upload endpoint).

**Request Example:**
```json
{
  "name": "Acme Corporation",
  "slug": "acme-corp",
  "description": "Leading technology solutions provider",
  "address": "123 Main Street",
  "city": "San Francisco",
  "state": "CA",
  "country": "USA",
  "postal_code": "94105",
  "website": "https://www.acme-corp.com",
  "logo_url": "https://cdn.example.com/logos/acme-corp.png"
}
```

**Success Response (201 Created)**

```json
{
  "data": {
    "company_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Acme Corporation",
    "slug": "acme-corp",
    "description": "Leading technology solutions provider",
    "address": "123 Main Street",
    "city": "San Francisco",
    "state": "CA",
    "country": "USA",
    "postal_code": "94105",
    "website": "https://www.acme-corp.com",
    "logo_url": "https://cdn.example.com/logos/acme-corp.png",
    "is_active": true,
    "is_deleted": false,
    "user_count": 0,
    "created_at": "2024-01-20T10:30:00Z",
    "updated_at": "2024-01-20T10:30:00Z",
    "created_by": "770e8400-e29b-41d4-a716-446655440002",
    "updated_by": "770e8400-e29b-41d4-a716-446655440002"
  },
  "message": "Company created successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103000Z"` (REQUIRED - resource version identifier based on `updated_at`)
- `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (RECOMMENDED)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User is not SuperAdmin |
| 400 Bad Request | `VALIDATION_FAILED` | Request body validation failed (missing required fields, invalid format) |
| 409 Conflict | `DUPLICATE_COMPANY_NAME` | Company name already exists (case-insensitive) |
| 409 Conflict | `DUPLICATE_COMPANY_SLUG` | Company slug already exists (case-insensitive) |
| 422 Unprocessable Entity | `VALIDATION_ERROR` | Field validation failed (slug format, name length, etc.) |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during request processing |

Example error (409 Conflict - Duplicate Name):
```json
{
  "error": {
    "code": "DUPLICATE_COMPANY_NAME",
    "details": [{"field": "name", "issue": "A company with this name already exists."}]
  },
  "message": "Company name must be unique."
}
```

Example error (409 Conflict - Duplicate Slug):
```json
{
  "error": {
    "code": "DUPLICATE_COMPANY_SLUG",
    "details": [{"field": "slug", "issue": "A company with this slug already exists."}]
  },
  "message": "Company slug must be unique."
}
```

Example error (422 Unprocessable Entity - Validation Error):
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "details": [
      {"field": "slug", "issue": "Slug must be lowercase alphanumeric with hyphens only (e.g., acme-corp)."},
      {"field": "name", "issue": "Name must be between 1 and 255 characters."}
    ]
  },
  "message": "Request validation failed."
}
```

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.

---

#### 4.4.3 GET /api/v1/companies/{company_id}

- **Purpose:** Get company details with user count and full profile information (SuperAdmin only)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin only
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
| company_id | string (UUID) | Yes | Company identifier (RFC 4122 UUID v4 format) |

**Note:** All path parameters MUST use snake_case (e.g., `company_id`, `user_id`, `role_id`) - see Rule 2.

**Query Parameters**  
None

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "company_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Acme Corporation",
    "slug": "acme-corp",
    "description": "Leading technology solutions provider",
    "address": "123 Main Street",
    "city": "San Francisco",
    "state": "CA",
    "country": "USA",
    "postal_code": "94105",
    "website": "https://www.acme-corp.com",
    "logo_url": "https://cdn.example.com/logos/acme-corp.png",
    "is_active": true,
    "is_deleted": false,
    "user_count": 25,
    "created_at": "2024-01-20T10:00:00Z",
    "updated_at": "2024-01-20T15:30:00Z",
    "created_by": "770e8400-e29b-41d4-a716-446655440002",
    "updated_by": "770e8400-e29b-41d4-a716-446655440002"
  },
  "message": "Company retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103000Z"` (REQUIRED - resource version identifier based on `updated_at`)
- `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (RECOMMENDED)

**Conditional GET (304 Not Modified):**
If the request includes `If-None-Match: "20240120T103000Z"` header and the resource ETag matches, return `304 Not Modified` with no response body.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User is not SuperAdmin |
| 404 Not Found | `COMPANY_NOT_FOUND` | Company with specified company_id does not exist |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during request processing |

Example error (404 Not Found):
```json
{
  "error": {
    "code": "COMPANY_NOT_FOUND",
    "details": [{"field": "company_id", "issue": "Company with ID 550e8400-e29b-41d4-a716-446655440000 does not exist."}]
  },
  "message": "Company not found."
}
```

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate error.

---

#### 4.4.4 PATCH /api/v1/companies/{company_id}

- **Purpose:** Update company information or activate/deactivate company (SuperAdmin only)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin only
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-Match: "20240120T103000Z"` (REQUIRED - ETag from GET response, based on `updated_at`, see Rule 8)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
- **Idempotency:** Yes (idempotent update)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| company_id | string (UUID) | Yes | Company identifier (RFC 4122 UUID v4 format) |

**Note:** All path parameters MUST use snake_case (e.g., `company_id`, `user_id`, `role_id`) - see Rule 2.

**Query Parameters**  
None

**Request Body**

**Schema Table:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| description | string | No | Company description | Max 1000 characters |
| address | string | No | Physical address | Max 255 characters |
| city | string | No | City | Max 100 characters |
| state | string | No | State | Max 100 characters |
| country | string | No | Country | Max 100 characters |
| postal_code | string | No | Postal/ZIP code | Max 20 characters |
| website | string | No | Company website URL | Valid HTTPS URL, max 2048 characters |
| logo_url | string | No | Company logo URL | Valid HTTPS URL, max 2048 characters |
| is_active | boolean | No | Company active state | Boolean (true/false) |

**Note:** 
- `name` and `slug` are immutable and cannot be updated.
- `is_deleted` cannot be updated via this endpoint (use DELETE endpoint for hard deletion).
- To activate/deactivate company, send `{"is_active": true}` or `{"is_active": false}`.
- Deactivation immediately blocks all associated user logins.
- All fields are optional - only include fields to update.
- `logo_url` is a string field where clients provide the URL (no file upload endpoint).

**Request Example (Update Profile Fields):**
```json
{
  "description": "Updated company description",
  "address": "456 New Street",
  "city": "New York",
  "state": "NY",
  "country": "USA",
  "postal_code": "10001",
  "website": "https://www.updated-website.com",
  "logo_url": "https://cdn.example.com/logos/updated-logo.png"
}
```

**Request Example (Activate Company):**
```json
{
  "is_active": true
}
```

**Request Example (Deactivate Company):**
```json
{
  "is_active": false
}
```

**Success Response (200 OK)**

```json
{
  "data": {
    "company_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Acme Corporation",
    "slug": "acme-corp",
    "description": "Updated company description",
    "address": "456 New Street",
    "city": "New York",
    "state": "NY",
    "country": "USA",
    "postal_code": "10001",
    "website": "https://www.updated-website.com",
    "logo_url": "https://cdn.example.com/logos/updated-logo.png",
    "is_active": true,
    "is_deleted": false,
    "user_count": 25,
    "created_at": "2024-01-20T10:00:00Z",
    "updated_at": "2024-01-20T16:45:00Z",
    "created_by": "770e8400-e29b-41d4-a716-446655440002",
    "updated_by": "770e8400-e29b-41d4-a716-446655440002"
  },
  "message": "Company updated successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T164500Z"` (New ETag after update, based on new `updated_at`)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User is not SuperAdmin |
| 404 Not Found | `COMPANY_NOT_FOUND` | Company with specified company_id does not exist |
| 412 Precondition Failed | `PRECONDITION_FAILED` | ETag mismatch (If-Match header provided but resource was modified) |
| 428 Precondition Required | `PRECONDITION_REQUIRED` | If-Match header missing (required for update operations) |
| 400 Bad Request | `VALIDATION_FAILED` | Request body validation failed (invalid format) |
| 422 Unprocessable Entity | `VALIDATION_ERROR` | Field validation failed (URL format, length, etc.) |
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

Example error (422 Unprocessable Entity - Validation Error):
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "details": [
      {"field": "website", "issue": "Website must be a valid HTTPS URL."},
      {"field": "logo_url", "issue": "Logo URL must be a valid HTTPS URL."}
    ]
  },
  "message": "Request validation failed."
}
```

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.

---

#### 4.4.5 DELETE /api/v1/companies/{company_id}

- **Purpose:** Hard delete a company and all associated data (irreversible, SuperAdmin only)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** SuperAdmin only
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-Match: "20240120T103000Z"` (REQUIRED - ETag from GET response, based on `updated_at`, see Rule 8)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
- **Idempotency:** Yes (idempotent delete - returns 204 if already deleted)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| company_id | string (UUID) | Yes | Company identifier (RFC 4122 UUID v4 format) |

**Note:** All path parameters MUST use snake_case (e.g., `company_id`, `user_id`, `role_id`) - see Rule 2.

**Query Parameters**  
None

**Request Body**  
None

**Success Response (204 No Content)**

No response body. HTTP status code 204 indicates successful deletion.

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Note:** 
- Hard deletion is irreversible and proceeds even if company has active users.
- All associated data (users, employees, leaves, tasks, salaries, notifications, etc.) is permanently deleted.
- No dependency checks are performed before deletion.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User is not SuperAdmin |
| 404 Not Found | `COMPANY_NOT_FOUND` | Company with specified company_id does not exist |
| 412 Precondition Failed | `PRECONDITION_FAILED` | ETag mismatch (If-Match header provided but resource was modified) |
| 428 Precondition Required | `PRECONDITION_REQUIRED` | If-Match header missing (required for delete operations) |
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

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate error.

---

#### 4.4.6 GET /api/v1/company/profile

- **Purpose:** Get own company profile (non-governance fields only, CEO/HR only)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, HR only (own company from JWT `org_id`)
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
None

**Query Parameters**  
None

**Request Body**  
None

**Success Response (200 OK)**

```json
{
  "data": {
    "name": "Acme Corporation",
    "slug": "acme-corp",
    "description": "Leading technology solutions provider",
    "address": "123 Main Street",
    "city": "San Francisco",
    "state": "CA",
    "country": "USA",
    "postal_code": "94105",
    "website": "https://www.acme-corp.com",
    "logo_url": "https://cdn.example.com/logos/acme-corp.png",
    "is_active": true
  },
  "message": "Company profile retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103000Z"` (REQUIRED - resource version identifier based on `updated_at`)
- `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (RECOMMENDED)

**Note:** 
- Response excludes governance fields (`is_deleted`, `created_at`, `updated_at`, `created_by`, `updated_by`, `user_count`).
- `name` and `slug` are read-only (included for display purposes only).
- Company is determined from JWT `org_id` claim.

**Conditional GET (304 Not Modified):**
If the request includes `If-None-Match: "20240120T103000Z"` header and the resource ETag matches, return `304 Not Modified` with no response body.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User is not CEO or HR, or org_id is null |
| 404 Not Found | `COMPANY_NOT_FOUND` | Company from JWT org_id does not exist |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during request processing |

Example error (403 Forbidden):
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "details": [{"field": "role", "issue": "Only CEO and HR can access company profile."}]
  },
  "message": "You do not have permission to perform this action."
}
```

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate error.

---

#### 4.4.7 PATCH /api/v1/company/profile

- **Purpose:** Update company profile fields (non-governance fields only, CEO/HR only)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, HR only (own company from JWT `org_id`, blocked if `is_active: false`)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-Match: "20240120T103000Z"` (REQUIRED - ETag from GET response, based on `updated_at`, see Rule 8)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - unique request identifier for debugging)
- **Idempotency:** Yes (idempotent update)

**Path Parameters**  
None

**Query Parameters**  
None

**Request Body**

**Schema Table:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| description | string | No | Company description | Max 1000 characters |
| address | string | No | Physical address | Max 255 characters |
| city | string | No | City | Max 100 characters |
| state | string | No | State | Max 100 characters |
| country | string | No | Country | Max 100 characters |
| postal_code | string | No | Postal/ZIP code | Max 20 characters |
| website | string | No | Company website URL | Valid HTTPS URL, max 2048 characters |
| logo_url | string | No | Company logo URL | Valid HTTPS URL, max 2048 characters |

**Note:** 
- `name` and `slug` are immutable and cannot be updated.
- `is_active` and `is_deleted` are governance fields and cannot be updated via this endpoint.
- Updates are blocked when company is inactive (`is_active: false`).
- All fields are optional - only include fields to update.
- `logo_url` is a string field where clients provide the URL (no file upload endpoint).
- Company is determined from JWT `org_id` claim.

**Request Example:**
```json
{
  "description": "Updated company description",
  "address": "456 New Street",
  "city": "New York",
  "state": "NY",
  "country": "USA",
  "postal_code": "10001",
  "website": "https://www.updated-website.com",
  "logo_url": "https://cdn.example.com/logos/updated-logo.png"
}
```

**Success Response (200 OK)**

```json
{
  "data": {
    "name": "Acme Corporation",
    "slug": "acme-corp",
    "description": "Updated company description",
    "address": "456 New Street",
    "city": "New York",
    "state": "NY",
    "country": "USA",
    "postal_code": "10001",
    "website": "https://www.updated-website.com",
    "logo_url": "https://cdn.example.com/logos/updated-logo.png",
    "is_active": true
  },
  "message": "Company profile updated successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T164500Z"` (New ETag after update, based on new `updated_at`)

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User is not CEO or HR, or org_id is null |
| 404 Not Found | `COMPANY_NOT_FOUND` | Company from JWT org_id does not exist |
| 412 Precondition Failed | `PRECONDITION_FAILED` | ETag mismatch (If-Match header provided but resource was modified) |
| 428 Precondition Required | `PRECONDITION_REQUIRED` | If-Match header missing (required for update operations) |
| 422 Unprocessable Entity | `BUSINESS_RULE_FAILED` | Company is inactive (is_active: false) - updates blocked |
| 422 Unprocessable Entity | `VALIDATION_ERROR` | Field validation failed (URL format, length, etc.) |
| 400 Bad Request | `VALIDATION_FAILED` | Request body validation failed (invalid format) |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during request processing |

Example error (422 Unprocessable Entity - Company Inactive):
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [{"field": "company", "issue": "Cannot update company profile. Company is inactive (is_active: false)."}]
  },
  "message": "Company profile updates are blocked when company is inactive."
}
```

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

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.

---

## 5. Business Rules & Validations

### 5.1 Immutable Fields
- **`name`**: Cannot be changed after company creation. Attempts to update return `422 VALIDATION_ERROR`.
- **`slug`**: Cannot be changed after company creation. Attempts to update return `422 VALIDATION_ERROR`.

### 5.2 Uniqueness Constraints
- **Company Name**: Case-insensitive unique across all companies. Duplicate names return `409 DUPLICATE_COMPANY_NAME`.
- **Company Slug**: Case-insensitive unique globally. Duplicate slugs return `409 DUPLICATE_COMPANY_SLUG`.

### 5.3 Activation/Deactivation Rules
- **Default State**: New companies default to `is_active: true` on creation.
- **Deactivation Effect**: When `is_active` is set to `false`, all associated users are immediately blocked from logging in.
- **Activation Effect**: When `is_active` is set to `true`, user login access is restored.
- **Profile Updates**: CEO/HR cannot update company profile when `is_active: false` (returns `422 BUSINESS_RULE_FAILED`).

### 5.4 Deletion Rules
- **Hard Deletion**: DELETE endpoint permanently removes company and all associated data (irreversible).
- **No Dependency Checks**: Deletion proceeds even if company has active users, employees, or other dependencies.
- **Cascade Deletion**: All company-scoped data (users, employees, leaves, tasks, salaries, notifications, etc.) is permanently deleted.

### 5.5 Field Validation Rules
- **Name**: Min 1 character, max 255 characters, case-insensitive unique.
- **Slug**: Lowercase alphanumeric with hyphens only, min 3 characters, max 100 characters, pattern: `^[a-z0-9]+(?:-[a-z0-9]+)*$`, case-insensitive unique.
- **Description**: Max 1000 characters.
- **Address**: Max 255 characters.
- **City**: Max 100 characters.
- **State**: Max 100 characters.
- **Country**: Max 100 characters.
- **Postal Code**: Max 20 characters.
- **Website**: Valid HTTPS URL, max 2048 characters.
- **Logo URL**: Valid HTTPS URL, max 2048 characters (string field, no file upload).

### 5.6 Access Control Rules
- **SuperAdmin**: Can access all companies (including soft-deleted via `is_deleted: true`).
- **CEO/HR**: Can only access their own company (determined from JWT `org_id` claim).
- **Profile Updates**: CEO/HR can only update profile fields when company is active (`is_active: true`).

---

## 6. ETags & Conditional Requests (Rule 8)

### 6.1 ETag Generation
- **ETag Format**: Based on `updated_at` timestamp (e.g., `"20240120T103000Z"`).
- **ETag Changes**: ETag changes whenever `updated_at` changes.
- **Weak ETags**: Use weak ETags (`W/"..."`) if resource representation can vary.

### 6.2 GET Requests (Cache Validation)
- **If-None-Match Header**: Optional header for cache validation.
- **304 Not Modified**: Return `304 Not Modified` (no response body) if ETag matches.
- **200 OK**: Return full resource data with new ETag if ETag doesn't match.

### 6.3 PATCH/PUT/DELETE Requests (Concurrency Control)
- **If-Match Header**: REQUIRED for all update/delete operations.
- **412 Precondition Failed**: Return if ETag doesn't match current resource version.
- **428 Precondition Required**: Return if If-Match header is missing.

### 6.4 ETag Headers in Responses
- **GET Responses**: MUST include `ETag` header (based on `updated_at`).
- **GET Responses**: SHOULD include `Last-Modified` header (from `updated_at`).
- **PATCH/PUT Responses**: MUST include new `ETag` header (based on new `updated_at`).

---

## 7. Error Handling

### 7.1 Standard Error Response Format

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

### 7.2 Standard Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 Bad Request | `VALIDATION_FAILED` | Request body validation failed (missing required fields, invalid format) |
| 400 Bad Request | `INVALID_REQUEST` | Invalid query parameter format or value |
| 401 Unauthorized | `UNAUTHENTICATED` | Missing or invalid authentication token |
| 401 Unauthorized | `TOKEN_EXPIRED` | JWT token has expired |
| 401 Unauthorized | `INVALID_TOKEN` | Malformed token or missing required claims |
| 403 Forbidden | `INSUFFICIENT_PERMISSIONS` | User lacks required permissions |
| 404 Not Found | `COMPANY_NOT_FOUND` | Company with specified ID does not exist |
| 409 Conflict | `DUPLICATE_COMPANY_NAME` | Company name already exists (case-insensitive) |
| 409 Conflict | `DUPLICATE_COMPANY_SLUG` | Company slug already exists (case-insensitive) |
| 412 Precondition Failed | `PRECONDITION_FAILED` | ETag mismatch (If-Match header provided but resource was modified) |
| 422 Unprocessable Entity | `VALIDATION_ERROR` | Field validation failed (slug format, name length, URL format, etc.) |
| 422 Unprocessable Entity | `BUSINESS_RULE_FAILED` | Business rule violation (e.g., company inactive, cannot update profile) |
| 428 Precondition Required | `PRECONDITION_REQUIRED` | If-Match header missing (required for update/delete operations) |
| 500 Internal Server Error | `INTERNAL_ERROR` | Server error during request processing |

### 7.3 Error Response Examples

**Example 1: Validation Error (422)**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "details": [
      {"field": "slug", "issue": "Slug must be lowercase alphanumeric with hyphens only (e.g., acme-corp)."},
      {"field": "website", "issue": "Website must be a valid HTTPS URL."}
    ]
  },
  "message": "Request validation failed."
}
```

**Example 2: Business Rule Violation (422)**
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [{"field": "company", "issue": "Cannot update company profile. Company is inactive (is_active: false)."}]
  },
  "message": "Company profile updates are blocked when company is inactive."
}
```

**Example 3: Duplicate Resource (409)**
```json
{
  "error": {
    "code": "DUPLICATE_COMPANY_NAME",
    "details": [{"field": "name", "issue": "A company with this name already exists."}]
  },
  "message": "Company name must be unique."
}
```

**Example 4: ETag Mismatch (412)**
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

## 8. Webhooks / Async Behavior

**Not applicable for this feature.** All operations are synchronous.

---

## 9. Rate Limiting & Performance

### 9.1 Rate Limiting
- **Default Limit**: 100 requests per minute per user (configurable)
- **Rate Limit Headers**: Standard rate limit headers included in responses (implementation TBD)

### 9.2 Performance Considerations
- **Pagination**: All list endpoints use server-side pagination (default page_size: 20, max: 100)
- **Database Indexing**: Ensure indexes on `name`, `slug`, `is_active`, `is_deleted`, `created_at`, `updated_at`
- **User Count Aggregation**: `user_count` is calculated via database aggregation (not stored field)

---

## 10. Open Questions

None identified at this stage.

---

## 11. Assumptions

1. **Company Slug Uniqueness**: Company slug is globally unique (case-insensitive).
2. **Hard Deletion**: Hard deletion is irreversible and proceeds even if company has active users.
3. **Deactivated Companies Visibility**: Deactivated companies remain visible to SuperAdmin.
4. **Company Data Retention**: Company data remains intact during deactivation (only login access is blocked).
5. **Logo URL**: Company logos are provided via `logo_url` string field (clients provide URL, no file upload endpoint).
6. **User Invitation**: CEO and other user invitations are handled via existing user invitation endpoint in F-001 (User & Role Management).
7. **JWT Token Claims**: JWT token uses `org_id` claim (not `company_id`) for consistency with other API specs.
8. **UTC Timezone**: All datetime fields use UTC timezone (ISO 8601 format with Z suffix).

---

**API Specification Completed:** 2024-01-20  
**Version:** 1.0  
**Status:** Ready for Implementation
