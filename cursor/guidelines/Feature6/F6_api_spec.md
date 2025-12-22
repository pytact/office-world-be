# API Specification: F-006 — Salary Management

## 1. Overview

This API specification defines the RESTful endpoints for the Salary Management feature (F-006) in the officeWorld system. The feature provides secure, auditable, and time-based salary management that defines employee compensation, maintains immutable salary history, manages bank details, executes salary payments, and delivers downloadable salary slips to employees, with strict role-based access control.

**Feature Dependencies:**
- F-005 — Employee Management (required for employee context)
- F-002 — RBAC & Permission Engine (required for authorization)
- F-003 — Notifications System (required for salary slip email delivery)
- F-011 — Audit Logging (required for audit trail)

**Out of Scope:**
- Employee self-service salary views (V1)
- Multiple bank accounts per employee
- Payroll tax calculations
- Salary analytics or reporting
- Hard deletion of salary or bank records

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
  "role": "hr",
  "org_id": "123e4567-e89b-12d3-a456-426614174000",
  "exp": 1735689600,
  "iat": 1735686000,
  "jti": "jwt_abc123xyz789"
}
```

**Role Values:**
- `"superadmin"` - Global access, `org_id` is `null`
- `"ceo"` - Full access to all salary data within organization
- `"hr"` - Manages salary configuration and payments within organization
- `"employee"` - No API access (receives salary slips via email only)
- `"manager"` - No access to salary data

**Token Validation:**
- Server MUST validate token signature, expiration, and required claims
- Missing or invalid token: Return `401 UNAUTHENTICATED`
- Expired token: Return `401 UNAUTHENTICATED` with error code `TOKEN_EXPIRED`
- Missing required claims: Return `401 UNAUTHENTICATED` with error code `INVALID_TOKEN`

### 2.2 Multi-Tenancy

- **SuperAdmin**: `org_id: null` - Has access to all organizations
- **Organization-scoped users** (CEO, HR): `org_id: "<uuid>"` - Access limited to specified organization
- Server MUST extract `org_id` from token for authorization checks
- All salary data is scoped to the organization from the token's `org_id` claim

### 2.3 Timezone Standard

**All datetime fields MUST use UTC timezone** (ISO 8601 format with `Z` suffix).

- Format: `YYYY-MM-DDTHH:mm:ssZ` (e.g., `2024-01-20T10:30:00Z`)
- All `created_at`, `updated_at`, `paid_on`, `effective_from`, `effective_to` fields are in UTC
- Date-only fields: `YYYY-MM-DD` format (e.g., `2024-01-20`)

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

| Role | Salary Overview | Create/Update SalaryDetails | Update BankInfo | Create SalaryPayment | List SalaryPayments | Download Salary Slip |
|------|----------------|----------------------------|-----------------|---------------------|-------------------|---------------------|
| **CEO** | ✅ Full access | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **HR** | ✅ Full access | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Employee** | ❌ Denied | ❌ Denied | ❌ Denied | ❌ Denied | ❌ Denied | ❌ Denied |
| **Manager** | ❌ Denied | ❌ Denied | ❌ Denied | ❌ Denied | ❌ Denied | ❌ Denied |
| **SuperAdmin** | ✅ Full access | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |

**Access Rules:**
- CEO and HR have full access to all salary data within their organization
- Employees and Managers are explicitly denied access to all salary endpoints
- SuperAdmin has global access across all organizations
- All salary-related actions are audit logged (F-011)

---

## 4. Resources & Endpoints

### 4.1 Resource Overview

**Primary Resources:**
- **SalaryDetails**: Time-bound salary configuration for an employee (only one active per employee)
- **BankInfo**: Employee bank account used for salary payments (one per employee, never deleted)
- **SalaryPayment**: Monthly executed salary record (immutable, append-only)
- **SalaryHistory**: Immutable audit log of salary configuration changes (read-only)

**Resource Relationships:**
- Employee 1:1 BankInfo
- Employee 1:* SalaryDetails
- Employee 1:* SalaryPayment
- SalaryDetails 1:* SalaryHistory

### 4.2 Endpoint Summary

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/v1/company/employees/{employee_id}/salary` | Get salary overview | CEO, HR |
| POST | `/v1/company/employees/{employee_id}/salary` | Create/Update SalaryDetails | CEO, HR |
| PATCH | `/v1/company/employees/{employee_id}/salary/bank-info` | Upsert BankInfo | CEO, HR |
| POST | `/v1/company/employees/{employee_id}/salary/payments` | Create SalaryPayment | CEO, HR |
| GET | `/v1/company/employees/{employee_id}/salary/payments` | List SalaryPayments | CEO, HR |
| GET | `/v1/company/employees/{employee_id}/salary/payments/{payment_id}/slip` | Download salary slip | CEO, HR |

### 4.3 Endpoint Details

**Note on Swagger Documentation (Rule 10):**
All endpoint router implementations MUST use centralized documentation classes. Create `SalaryApiDocs` class in `src/salary/documentations/salary_api_doc.py` (or appropriate module path) with `summary` and `description` for each endpoint operation. Use `summary=SalaryApiDocs.operation_name.summary` and `description=SalaryApiDocs.operation_name.description` in router decorators instead of hardcoded strings.

#### 4.3.1 GET /v1/company/employees/{employee_id}/salary

- **Purpose:** Retrieve complete salary overview for an employee, including current salary details, salary history, bank information, and payment summary
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, HR only (Employee and Manager access denied)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-None-Match: "20240120T103000Z"` (optional, for cache validation - returns 304 if unchanged)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
    - `ETag: "20240120T103000Z"` (REQUIRED - based on latest `updated_at` from any related resource)
    - `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (optional)
- **Idempotency:** Yes (GET is idempotent)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| employee_id | string (UUID) | Yes | Employee UUID (RFC 4122 UUID v4 format) |

**Query Parameters**

**Note:** Query parameters MUST be defined using a query schema class with `Depends()` pattern (Rule 9), NOT individual `Query()` parameters in the router endpoint.

**Query Schema Class (REQUIRED):**
```python
class SalaryOverviewQuery(BaseModel):
    """Query schema for salary overview endpoint."""

    include_history: bool = Field(True, description="Include salary history records")
    include_payments: bool = Field(True, description="Include recent payment summary")
    payment_limit: int = Field(10, ge=1, le=100, description="Number of recent payments to include (1-100)")

    model_config = ConfigDict(from_attributes=True)
```

**Router Endpoint Pattern (REQUIRED):**
```python
@router.get(
    "/salary",
    response_model=StandardResponse[SalaryOverviewResponse],
    summary=SalaryApiDocs.get_overview.summary,
    description=SalaryApiDocs.get_overview.description
)
async def get_salary_overview(
    employee_id: UUID,
    query: SalaryOverviewQuery = Depends(SalaryOverviewQuery),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_ceo_or_hr),
):
    """Get salary overview for an employee."""
    # Access via query.include_history, query.include_payments, query.payment_limit
```


**Query Parameters Table (for documentation only):**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| include_history | boolean | No | true | Include salary history records in response |
| include_payments | boolean | No | true | Include recent payment summary in response |
| payment_limit | integer | No | 10 | Number of recent payments to include (1-100) |

**Success Response (200 OK)**

```json
{
  "data": {
    "employee": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "first_name": "John",
      "last_name": "Doe",
      "is_active": true
    },
    "current_salary": {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "amount": "80000.00",
      "currency": "INR",
      "payment_frequency": "MONTHLY",
      "effective_from": "2024-01-01",
      "effective_to": "2024-12-31",
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T10:00:00Z"
    },
    "bank_info": {
      "bank_name": "HDFC",
      "branch": "Mumbai Main Branch",
      "account_number": "****1234",
      "ifsc_code": "HDFC****5678"
    },
    "salary_history": [
      {
        "id": "990e8400-e29b-41d4-a716-446655440004",
        "previous_amount": "75000.00",
        "new_amount": "80000.00",
        "effective_from": "2024-01-01",
        "changed_by": "Jane Smith",
        "created_at": "2024-01-01T10:00:00Z"
      }
    ],
    "recent_payments": [
      {
        "id": "770e8400-e29b-41d4-a716-446655440002",
        "amount": "80000.00",
        "month": 3,
        "year": 2024,
        "paid_on": "2024-03-05T10:00:00Z",
        "payment_method": "BANK_TRANSFER",
        "slip_url": "/v1/company/employees/550e8400-e29b-41d4-a716-446655440000/salary/payments/770e8400-e29b-41d4-a716-446655440002/slip"
      }
    ],
    "current_salary_amount": "80000.00",
    "current_salary_currency": "INR",
    "has_active_salary": true,
    "masked_account_number": "****1234"
  },
  "message": "Salary overview retrieved successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103000Z"` (REQUIRED - based on latest `updated_at` from any related resource)
- `Last-Modified: Wed, 20 Jan 2024 10:30:00 GMT` (optional)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- Sensitive bank fields (`account_number`, `ifsc_code`) are masked in all responses.
- If employee has no active salary, `current_salary`, `current_salary_amount`, and `current_salary_currency` will be `null`, and `has_active_salary` will be `false`.
- If employee has no bank info, `bank_info` will be `null` and `masked_account_number` will be `null`.
- Derived fields: `current_salary_amount` and `current_salary_currency` are derived from the active `current_salary` record. `masked_account_number` is derived from `bank_info.account_number` with masking applied.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | `INVALID_REQUEST` | Invalid employee_id format |
| 401 | `UNAUTHENTICATED` | Missing or invalid JWT token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 403 | `INSUFFICIENT_PERMISSIONS` | User is Employee or Manager (access denied) |
| 404 | `EMPLOYEE_NOT_FOUND` | Employee does not exist or not in user's organization |
| 304 | `NOT_MODIFIED` | Resource unchanged (If-None-Match header matches current ETag) |
| 500 | `INTERNAL_ERROR` | Server error |

**Example Error Response (403 Forbidden):**
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "details": [{"field": "access", "issue": "Employees and Managers cannot access salary data."}]
  },
  "message": "Access denied. Only CEO and HR can view salary information."
}
```

**Example Error Response (404 Not Found):**
```json
{
  "error": {
    "code": "EMPLOYEE_NOT_FOUND",
    "details": [{"field": "employee_id", "issue": "Employee not found or not accessible."}]
  },
  "message": "Employee not found."
}
```

---

#### 4.3.2 POST /v1/company/employees/{employee_id}/salary

- **Purpose:** Create new SalaryDetails or update existing salary (creates new record and auto-closes previous active record)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, HR only (Employee and Manager access denied)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-Match: "20240120T103000Z"` (REQUIRED when updating existing active SalaryDetails - ETag from GET salary overview response, based on current salary's `updated_at`. OPTIONAL when creating first salary for employee)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
    - `ETag: "20240120T103500Z"` (New ETag after creation, based on new `updated_at`)
- **Idempotency:** No (creates new record each time)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| employee_id | string (UUID) | Yes | Employee UUID (RFC 4122 UUID v4 format) |

**Request Body**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| amount | decimal | Yes | Monthly gross salary amount | Decimal, min > 0, max 999999999.99, 2 decimal places |
| currency | string | Yes | Salary currency | Enum: "INR", "USD", "EUR", "GBP", "AUD", "CAD" (case-sensitive) |
| payment_frequency | string | Yes | Payment cadence | Enum: "MONTHLY", "BI_WEEKLY", "WEEKLY" (case-sensitive) |
| effective_from | string (date) | Yes | Start date of salary configuration (inclusive) | ISO 8601 date format (YYYY-MM-DD), must be today or future date |
| effective_to | string (date) | Yes | End date of salary configuration (inclusive) | ISO 8601 date format (YYYY-MM-DD), must be >= effective_from (same date allowed) |

**Request Body Example:**
```json
{
  "amount": "80000.00",
  "currency": "INR",
  "payment_frequency": "MONTHLY",
  "effective_from": "2024-01-01",
  "effective_to": "2024-12-31"
}
```

**Business Rules:**
- Only one active SalaryDetails per employee (system auto-closes previous record)
- No overlapping effective periods (system validates)
- User provides both `effective_from` and `effective_to` for the new SalaryDetails record
- Creating new SalaryDetails automatically sets `effective_to` on the previous active record to `effective_from - 1 day` (to prevent overlap)
- System creates SalaryHistory entry automatically when updating existing salary
- If no previous SalaryDetails exists, this becomes the first record (no SalaryHistory entry created)

**Success Response (201 Created)**

```json
{
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "employee_id": "550e8400-e29b-41d4-a716-446655440000",
    "amount": "80000.00",
    "currency": "INR",
    "payment_frequency": "MONTHLY",
    "effective_from": "2024-01-01",
    "effective_to": "2024-12-31",
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:00:00Z",
    "created_by": "Jane Smith",
    "updated_by": "Jane Smith"
  },
  "message": "Salary details created successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103500Z"` (New ETag after creation, based on new `updated_at`)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | `VALIDATION_FAILED` | Invalid request body format or validation errors |
| 401 | `UNAUTHENTICATED` | Missing or invalid JWT token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 403 | `INSUFFICIENT_PERMISSIONS` | User is Employee or Manager (access denied) |
| 404 | `EMPLOYEE_NOT_FOUND` | Employee does not exist or not in user's organization |
| 409 | `OVERLAPPING_SALARY_PERIOD` | New effective period overlaps with existing SalaryDetails |
| 412 | `PRECONDITION_FAILED` | ETag mismatch (If-Match header doesn't match current resource version) |
| 428 | `PRECONDITION_REQUIRED` | If-Match header required but missing (when updating existing resource) |
| 422 | `BUSINESS_RULE_FAILED` | Business rule violation (e.g., effective_to < effective_from) |
| 500 | `INTERNAL_ERROR` | Server error |

**Example Error Response (400 Bad Request - Validation):**
```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "details": [
      {"field": "amount", "issue": "Amount must be greater than 0."},
      {"field": "currency", "issue": "Invalid currency. Must be one of: INR, USD, EUR, GBP, AUD, CAD."},
      {"field": "effective_to", "issue": "Effective to date must be greater than or equal to effective from date (inclusive dates allowed)."}
    ]
  },
  "message": "Request validation failed."
}
```

**Example Error Response (409 Conflict - Overlapping Period):**
```json
{
  "error": {
    "code": "OVERLAPPING_SALARY_PERIOD",
    "details": [{"field": "effective_from", "issue": "Salary period overlaps with existing SalaryDetails. Please adjust the effective dates."}]
  },
  "message": "Cannot create salary details with overlapping effective period."
}
```

**Example Error Response (412 Precondition Failed - ETag mismatch):**
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

#### 4.3.3 PATCH /v1/company/employees/{employee_id}/salary/bank-info

- **Purpose:** Create or update BankInfo for an employee (upsert pattern - creates if not exists, updates if exists)
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, HR only (Employee and Manager access denied)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
    - `If-Match: "20240120T103000Z"` (REQUIRED when updating existing BankInfo - ETag from GET salary overview response, based on bank_info's `updated_at`. OPTIONAL when creating new BankInfo for employee)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
    - `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)
- **Idempotency:** Yes (upsert is idempotent)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| employee_id | string (UUID) | Yes | Employee UUID (RFC 4122 UUID v4 format) |

**Request Body**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| bank_name | string | Yes | Bank identifier | Enum: "HDFC", "ICICI", "SBI", "AXIS", "KOTAK", "PNB", "BOB" (case-sensitive) |
| branch | string | Yes | Bank branch name | String, min 1 character, max 255 characters |
| account_number | string | Yes | Bank account number | String, min 8 characters, max 20 characters, alphanumeric only |
| ifsc_code | string | Yes | Bank IFSC code | String, 11 characters, format: 4 uppercase letters + 0 + 6 alphanumeric (e.g., "HDFC0001234") |

**Request Body Example:**
```json
{
  "bank_name": "HDFC",
  "branch": "Mumbai Main Branch",
  "account_number": "1234567890123456",
  "ifsc_code": "HDFC0001234"
}
```

**Business Rules:**
- Only one BankInfo per employee (upsert pattern)
- BankInfo is never deleted (soft delete or updates only)
- Updates affect future salary payments only
- Past salary payments remain unchanged

**Success Response (200 OK)**

```json
{
  "data": {
    "id": "880e8400-e29b-41d4-a716-446655440003",
    "employee_id": "550e8400-e29b-41d4-a716-446655440000",
    "bank_name": "HDFC",
    "branch": "Mumbai Main Branch",
    "account_number": "****3456",
    "ifsc_code": "HDFC****234",
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "created_by": "Jane Smith",
    "updated_by": "Jane Smith"
  },
  "message": "Bank information updated successfully"
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `ETag: "20240120T103500Z"` (New ETag after update, based on new `updated_at`)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- Sensitive fields (`account_number`, `ifsc_code`) are masked in response (show last 4 characters for account_number, first 4 characters for ifsc_code, mask rest with `*`).
- `created_by` field will be `null` if BankInfo was created before audit tracking was implemented, or will contain the creator's name if this is a new creation.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | `VALIDATION_FAILED` | Invalid request body format or validation errors |
| 401 | `UNAUTHENTICATED` | Missing or invalid JWT token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 403 | `INSUFFICIENT_PERMISSIONS` | User is Employee or Manager (access denied) |
| 404 | `EMPLOYEE_NOT_FOUND` | Employee does not exist or not in user's organization |
| 412 | `PRECONDITION_FAILED` | ETag mismatch (If-Match header doesn't match current resource) |
| 422 | `VALIDATION_ERROR` | Field validation failed (e.g., invalid IFSC format) |
| 500 | `INTERNAL_ERROR` | Server error |

**Example Error Response (400 Bad Request - Validation):**
```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "details": [
      {"field": "bank_name", "issue": "Invalid bank name. Must be one of: HDFC, ICICI, SBI, AXIS, KOTAK, PNB, BOB."},
      {"field": "ifsc_code", "issue": "Invalid IFSC code format. Must be 11 characters: 4 uppercase letters + 0 + 6 alphanumeric."},
      {"field": "account_number", "issue": "Account number must be 8-20 alphanumeric characters."}
    ]
  },
  "message": "Request validation failed."
}
```

**Example Error Response (412 Precondition Failed - ETag mismatch):**
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

#### 4.3.4 POST /v1/company/employees/{employee_id}/salary/payments

- **Purpose:** Create a monthly salary payment record for an employee
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, HR only (Employee and Manager access denied)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- **Idempotency:** No (creates new record each time, but duplicate month/year is rejected)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| employee_id | string (UUID) | Yes | Employee UUID (RFC 4122 UUID v4 format) |

**Request Body**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| month | integer | Yes | Salary month | Integer, min 1, max 12 |
| year | integer | Yes | Salary year | Integer, min 2000, max 9999, YYYY format |
| payment_method | string | Yes | Mode of payment | Enum: "BANK_TRANSFER", "UPI", "CHEQUE", "CASH" (case-sensitive) |
| paid_on | string (datetime) | Yes | Payment execution date | ISO 8601 datetime format (YYYY-MM-DDTHH:mm:ssZ), UTC timezone |

**Request Body Example:**
```json
{
  "month": 3,
  "year": 2024,
  "payment_method": "BANK_TRANSFER",
  "paid_on": "2024-03-05T10:00:00Z"
}
```

**Business Rules:**
- Only one SalaryPayment per employee per month/year (duplicate rejected with 409)
- Amount is automatically derived from active SalaryDetails for the payment month
- Cannot create payment without active SalaryDetails (422 error)
- SalaryPayment records are immutable (cannot be updated or deleted)
- System automatically generates salary slip (async operation)
- System automatically emails salary slip to employee via F-003 (Notifications System)
- Payment amount is calculated based on active SalaryDetails for the payment month/year

**Success Response (201 Created)**

```json
{
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "employee_id": "550e8400-e29b-41d4-a716-446655440000",
    "amount": "80000.00",
    "currency": "INR",
    "month": 3,
    "year": 2024,
    "paid_on": "2024-03-05T10:00:00Z",
    "payment_method": "BANK_TRANSFER",
    "slip_url": "/v1/company/employees/550e8400-e29b-41d4-a716-446655440000/salary/payments/770e8400-e29b-41d4-a716-446655440002/slip",
    "payable_amount": "80000.00",
    "payment_period_label": "March 2024",
    "created_at": "2024-03-05T10:00:00Z",
    "created_by": "Jane Smith"
  },
  "message": "Salary payment created successfully. Salary slip will be emailed to the employee."
}
```

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)

**Note:** 
- Field order shown is for readability only. JSON objects are unordered (RFC 7159). Do not require or emphasize field order.
- DO NOT include `success` field - HTTP status codes indicate success/failure.
- Salary slip generation and email delivery are async operations. If they fail, the payment record is still created, but an error may be logged.
- Derived fields: `payable_amount` is the amount paid (same as `amount`), derived from active SalaryDetails. `payment_period_label` is a human-readable label (e.g., "March 2024") derived from `month` and `year`.

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | `VALIDATION_FAILED` | Invalid request body format or validation errors |
| 401 | `UNAUTHENTICATED` | Missing or invalid JWT token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 403 | `INSUFFICIENT_PERMISSIONS` | User is Employee or Manager (access denied) |
| 404 | `EMPLOYEE_NOT_FOUND` | Employee does not exist or not in user's organization |
| 409 | `DUPLICATE_SALARY_PAYMENT` | Salary payment already exists for this employee, month, and year |
| 422 | `BUSINESS_RULE_FAILED` | Business rule violation (e.g., no active SalaryDetails for payment month) |
| 500 | `INTERNAL_ERROR` | Server error |
| 500 | `ASYNC_OPERATION_FAILED` | Salary slip generation or email delivery failed (payment still created) |

**Example Error Response (400 Bad Request - Validation):**
```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "details": [
      {"field": "month", "issue": "Month must be between 1 and 12."},
      {"field": "year", "issue": "Year must be between 2000 and 9999."},
      {"field": "payment_method", "issue": "Invalid payment method. Must be one of: BANK_TRANSFER, UPI, CHEQUE, CASH."}
    ]
  },
  "message": "Request validation failed."
}
```

**Example Error Response (409 Conflict - Duplicate Payment):**
```json
{
  "error": {
    "code": "DUPLICATE_SALARY_PAYMENT",
    "details": [{"field": "payment", "issue": "Salary payment already exists for employee, month 3, and year 2024."}]
  },
  "message": "Cannot create duplicate salary payment for the same month and year."
}
```

**Example Error Response (422 Unprocessable Entity - No Active Salary):**
```json
{
  "error": {
    "code": "BUSINESS_RULE_FAILED",
    "details": [{"field": "salary_details", "issue": "No active salary configuration found for the payment month. Please configure salary details first."}]
  },
  "message": "Cannot create salary payment without active salary configuration."
}
```

**Example Error Response (500 Internal Server Error - Async Operation Failed):**
```json
{
  "error": {
    "code": "ASYNC_OPERATION_FAILED",
    "details": [{"field": "salary_slip", "issue": "Salary slip generation or email delivery failed. Payment record was created, but slip generation needs to be retried."}]
  },
  "message": "Asynchronous operation failed. Payment was created, but salary slip generation failed."
}
```

---

#### 4.3.5 GET /v1/company/employees/{employee_id}/salary/payments

- **Purpose:** List all salary payments for an employee with pagination, filtering, and sorting
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, HR only (Employee and Manager access denied)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- **Idempotency:** Yes (GET is idempotent)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| employee_id | string (UUID) | Yes | Employee UUID (RFC 4122 UUID v4 format) |

**Query Parameters**

**Note:** Query parameters MUST be defined using a query schema class with `Depends()` pattern (Rule 9), NOT individual `Query()` parameters in the router endpoint.

**Query Schema Class (REQUIRED):**
```python
class SalaryPaymentListQuery(BaseModel):
    """Query schema for listing salary payments with pagination and filtering."""

    page: int = Field(1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(20, ge=1, le=100, description="Page size (1-100)")
    year: Optional[int] = Field(None, ge=2000, le=9999, description="Filter by year (YYYY format)")
    month: Optional[int] = Field(None, ge=1, le=12, description="Filter by month (1-12)")
    payment_method: Optional[str] = Field(None, description="Filter by payment method: BANK_TRANSFER, UPI, CHEQUE, CASH")
    sort_by: str = Field("paid_on", description="Sort field: paid_on, month, year, amount, created_at")
    sort_order: str = Field("desc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)
```

**Router Endpoint Pattern (REQUIRED):**
```python
@router.get(
    "/salary/payments",
    response_model=StandardResponse[SalaryPaymentPaginatedResponse],
    summary=SalaryApiDocs.list_payments.summary,
    description=SalaryApiDocs.list_payments.description
)
async def list_salary_payments(
    employee_id: UUID,
    query: SalaryPaymentListQuery = Depends(SalaryPaymentListQuery),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_ceo_or_hr),
):
    """List salary payments for an employee."""
    # Access via query.page, query.page_size, query.year, query.month, etc.
```


**Query Parameters Table (for documentation only):**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number (≥ 1) |
| page_size | integer | No | 20 | Page size (1-100) |
| year | integer | No | null | Filter by year (YYYY format, 2000-9999) |
| month | integer | No | null | Filter by month (1-12) |
| payment_method | string | No | null | Filter by payment method: BANK_TRANSFER, UPI, CHEQUE, CASH |
| sort_by | string | No | paid_on | Sort field: paid_on, month, year, amount, created_at |
| sort_order | string | No | desc | Sort order: asc or desc |

**Success Response (200 OK)**

```json
{
  "data": {
    "items": [
      {
        "id": "770e8400-e29b-41d4-a716-446655440002",
        "employee_id": "550e8400-e29b-41d4-a716-446655440000",
        "amount": "80000.00",
        "currency": "INR",
        "month": 3,
        "year": 2024,
        "paid_on": "2024-03-05T10:00:00Z",
        "payment_method": "BANK_TRANSFER",
        "slip_url": "/v1/company/employees/550e8400-e29b-41d4-a716-446655440000/salary/payments/770e8400-e29b-41d4-a716-446655440002/slip",
        "created_at": "2024-03-05T10:00:00Z",
        "created_by": "Jane Smith"
      }
    ],
    "total": 24,
    "page": 1,
    "page_size": 20,
    "total_pages": 2,
    "next_page": "/v1/company/employees/550e8400-e29b-41d4-a716-446655440000/salary/payments?page=2&page_size=20&sort_by=paid_on&sort_order=desc",
    "prev_page": null
  },
  "message": "Salary payments retrieved successfully"
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
| 400 | `INVALID_REQUEST` | Invalid employee_id format or query parameter validation errors |
| 401 | `UNAUTHENTICATED` | Missing or invalid JWT token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 403 | `INSUFFICIENT_PERMISSIONS` | User is Employee or Manager (access denied) |
| 404 | `EMPLOYEE_NOT_FOUND` | Employee does not exist or not in user's organization |
| 500 | `INTERNAL_ERROR` | Server error |

**Example Error Response (400 Bad Request - Invalid Query Parameter):**
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "details": [{"field": "page_size", "issue": "Page size must be between 1 and 100."}]
  },
  "message": "Invalid query parameter."
}
```

---

#### 4.3.6 GET /v1/company/employees/{employee_id}/salary/payments/{payment_id}/slip

- **Purpose:** Download salary slip PDF for a specific salary payment
- **Authentication:** Required (JWT Bearer token)
- **Authorization / Roles:** CEO, HR only (Employee and Manager access denied)
- **Headers:**
  - **Request Headers:**
    - `Authorization: Bearer <token>` (REQUIRED)
  - **Response Headers (REQUIRED):**
    - `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
    - `Content-Type: application/pdf` (REQUIRED)
    - `Content-Disposition: attachment; filename="salary_slip_2024_03.pdf"` (RECOMMENDED)
- **Idempotency:** Yes (GET is idempotent)

**Path Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| employee_id | string (UUID) | Yes | Employee UUID (RFC 4122 UUID v4 format) |
| payment_id | string (UUID) | Yes | SalaryPayment UUID (RFC 4122 UUID v4 format) |

**Success Response (200 OK)**

**Response Body:** Raw PDF file binary data

**Response Headers:**
- `X-Request-ID: req_abc123xyz789` (REQUIRED - for debugging and support)
- `Content-Type: application/pdf` (REQUIRED)
- `Content-Disposition: attachment; filename="salary_slip_2024_03.pdf"` (RECOMMENDED)
- `Content-Length: <file-size-in-bytes>` (automatically set by server)

**Note:** 
- Response body is raw PDF binary data, not JSON.
- File name format: `salary_slip_YYYY_MM.pdf` (e.g., `salary_slip_2024_03.pdf`).

**Error Responses**

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | `INVALID_REQUEST` | Invalid employee_id or payment_id format |
| 401 | `UNAUTHENTICATED` | Missing or invalid JWT token |
| 401 | `TOKEN_EXPIRED` | JWT token has expired |
| 403 | `INSUFFICIENT_PERMISSIONS` | User is Employee or Manager (access denied) |
| 404 | `EMPLOYEE_NOT_FOUND` | Employee does not exist or not in user's organization |
| 404 | `SALARY_PAYMENT_NOT_FOUND` | Salary payment does not exist or not associated with employee |
| 404 | `SALARY_SLIP_NOT_FOUND` | Salary slip file not found (slip not generated yet) |
| 500 | `INTERNAL_ERROR` | Server error |

**Example Error Response (404 Not Found - Slip Not Found):**
```json
{
  "error": {
    "code": "SALARY_SLIP_NOT_FOUND",
    "details": [{"field": "slip", "issue": "Salary slip not found. The slip may not have been generated yet."}]
  },
  "message": "Salary slip not found."
}
```

**Note:** Error responses for this endpoint return JSON (not PDF) when an error occurs.

---

## 5. Webhooks / Async Behavior

### 5.1 Salary Slip Generation

**Async Operation:** When a SalaryPayment is created via `POST /v1/company/employees/{employee_id}/salary/payments`, the system:

1. Creates the SalaryPayment record immediately (synchronous)
2. Triggers async salary slip generation (background job)
3. Triggers async email delivery via F-003 (Notifications System)

**Error Handling:**
- If salary slip generation fails, the payment record is still created
- Server returns `500 ASYNC_OPERATION_FAILED` if async operations fail (payment still created)
- Salary slip may not be immediately available for download after payment creation
- Clients should poll or wait before attempting to download the slip

**Email Delivery:**
- Salary slip is automatically emailed to the employee's registered email address
- Email delivery is handled by F-003 (Notifications System)
- Email includes download link to the salary slip
- Email delivery failures are logged but do not affect payment record creation

### 5.2 Audit Logging

**All salary-related actions generate audit logs** via F-011 (Audit Logging):

- Creating/updating SalaryDetails → Audit log entry
- Updating BankInfo → Audit log entry
- Creating SalaryPayment → Audit log entry
- SalaryHistory entries are automatically created when SalaryDetails change

---

## 6. Rate Limiting & Performance

### 6.1 Rate Limiting

- Standard rate limiting applies to all endpoints
- Salary payment creation may have stricter rate limits to prevent abuse
- File download endpoints may have bandwidth limits

### 6.2 Performance Considerations

- Salary overview endpoint aggregates data from multiple sources (may be slower)
- Pagination is required for salary payment lists to ensure performance
- Salary slip generation is async to avoid blocking payment creation
- ETag support enables efficient cache validation for GET requests

### 6.3 Caching

- GET endpoints support ETag-based caching (If-None-Match header)
- Clients should cache salary overview data and validate with ETag
- Salary slip files may be cached by CDN (if applicable)

---

## 7. Open Questions

None identified at this stage.

---

## 8. Assumptions

1. **Employee Management (F-005):** Employee records exist and are accessible before salary configuration
2. **RBAC (F-002):** Role-based access control is enforced at the API gateway/middleware level
3. **Notifications (F-003):** Email delivery service is available and configured for salary slip delivery
4. **Audit Logging (F-011):** Audit logging system is available and automatically logs all salary-related actions
5. **Salary Slip Generation:** External service/template is available for generating salary slip PDFs
6. **Multi-tenancy:** All salary data is scoped to the organization from the JWT token's `org_id` claim
7. **Data Immutability:** SalaryPayment and SalaryHistory records are never modified or deleted (append-only)
8. **BankInfo Updates:** Updates to BankInfo affect future salary payments only, past payments remain unchanged
9. **No Retroactive Recalculation:** System does not support retroactive salary recalculation
10. **Manual Payment Execution:** Salary payment execution is manual (not scheduled/automated)

---

## 9. ENUM Definitions

### 9.1 BankName Enum

| Value | Description |
|-------|-------------|
| HDFC | HDFC Bank |
| ICICI | ICICI Bank |
| SBI | State Bank of India |
| AXIS | Axis Bank |
| KOTAK | Kotak Mahindra Bank |
| PNB | Punjab National Bank |
| BOB | Bank of Baroda |

**Validation:** Case-sensitive, must match one of the values above.

### 9.2 Currency Enum

| Value | Symbol | Description |
|-------|--------|-------------|
| INR | ₹ | Indian Rupee |
| USD | $ | US Dollar |
| EUR | € | Euro |
| GBP | £ | British Pound |
| AUD | A$ | Australian Dollar |
| CAD | C$ | Canadian Dollar |

**Validation:** Case-sensitive, must match one of the values above.

### 9.3 PaymentFrequency Enum

| Value | Description |
|-------|-------------|
| MONTHLY | Monthly payment |
| BI_WEEKLY | Bi-weekly payment (every 2 weeks) |
| WEEKLY | Weekly payment |

**Validation:** Case-sensitive, must match one of the values above.

### 9.4 PaymentMethod Enum

| Value | Description |
|-------|-------------|
| BANK_TRANSFER | Bank transfer/NEFT/RTGS |
| UPI | Unified Payments Interface |
| CHEQUE | Cheque payment |
| CASH | Cash payment |

**Validation:** Case-sensitive, must match one of the values above.

---

## 10. Data Masking Rules

### 10.1 Bank Account Number Masking

- **Format:** Show last 4 characters, mask rest with `*`
- **Example:** `1234567890123456` → `****3456`
- **Applied in:** All API responses containing `account_number` field

### 10.2 IFSC Code Masking

- **Format:** Show first 4 characters (bank code), mask rest with `*`
- **Example:** `HDFC0001234` → `HDFC****234`
- **Applied in:** All API responses containing `ifsc_code` field

### 10.3 Masking Application

- Masking is applied in all GET responses
- Masking is applied in all POST/PATCH responses
- Unmasked data is only available internally (not exposed via API)
- Masking rules are consistent across all endpoints

---

## 11. Business Rules Summary

| Rule ID | Description | Enforcement |
|---------|-------------|--------------|
| BR-601 | Salary amount represents monthly gross pay | Validation |
| BR-602 | Only one active SalaryDetails per employee | Business logic |
| BR-603 | Salary updates auto-close previous config | Business logic |
| BR-604 | Salary payments are immutable | Constraint (no update/delete) |
| BR-605 | Only CEO and HR can create salary payments | Authorization |
| BR-606 | Bank info updates affect future payments only | Business logic |
| BR-607 | Employees can view only their own salary data | Authorization (not applicable in V1 - no employee API access) |
| BR-608 | Salary slip generated per salary payment | Async operation |

---

## 12. Error Code Reference

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Invalid request format or parameters |
| `VALIDATION_FAILED` | 400 | Request body validation failed |
| `UNAUTHENTICATED` | 401 | Missing or invalid JWT token |
| `TOKEN_EXPIRED` | 401 | JWT token has expired |
| `INVALID_TOKEN` | 401 | JWT token missing required claims |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions (Employee/Manager access denied) |
| `EMPLOYEE_NOT_FOUND` | 404 | Employee does not exist or not accessible |
| `SALARY_PAYMENT_NOT_FOUND` | 404 | Salary payment does not exist |
| `SALARY_SLIP_NOT_FOUND` | 404 | Salary slip file not found |
| `OVERLAPPING_SALARY_PERIOD` | 409 | New salary period overlaps with existing SalaryDetails |
| `DUPLICATE_SALARY_PAYMENT` | 409 | Salary payment already exists for employee, month, and year |
| `DUPLICATE_BANK_INFO` | 409 | Bank info conflict (should not occur due to upsert pattern, but documented for completeness) |
| `PRECONDITION_FAILED` | 412 | ETag mismatch (If-Match header doesn't match current resource version) |
| `PRECONDITION_REQUIRED` | 428 | If-Match header required but missing (when updating existing resource) |
| `BUSINESS_RULE_FAILED` | 422 | Business rule violation (e.g., no active salary for payment) |
| `VALIDATION_ERROR` | 422 | Field validation error |
| `INTERNAL_ERROR` | 500 | Server error |
| `ASYNC_OPERATION_FAILED` | 500 | Async operation failure (salary slip generation/email) |

---

**End of API Specification**

