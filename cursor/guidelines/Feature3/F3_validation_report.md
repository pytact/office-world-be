# Cross-Validation Report: F-003 Notifications System

## Validation Date: 2024

This report validates consistency across:
- F3_domain_model.md
- F3_api_spec.md
- F3_db_spec.md
- F3_ui_data_contract.md (reference)

---

## 1. FIELD MAPPING COMPARISON

### 1.1 Domain Model → API Spec → DB Spec Field Mapping

| Domain Model Field | API Spec Field | DB Spec Field | Status | Notes |
|-------------------|----------------|---------------|--------|-------|
| User | user_id | user_id | ✅ PASS | All match (snake_case) |
| Company | company_id | company_id | ✅ PASS | All match (snake_case) |
| Type | type | type | ⚠️ WARNING | Domain says "invite, leave, task" (categories), but API/DB use specific types (Option B) - This is correct per user decision |
| Title | title | title | ✅ PASS | All match |
| Message | message | message | ✅ PASS | All match |
| Channel | channel | channel | ✅ PASS | All match (values: "email", "in_app") |
| IsRead | is_read | is_read | ✅ PASS | All match (snake_case) |
| ReadAt | read_at | read_at | ✅ PASS | All match (snake_case) |
| Status | status | status | ✅ PASS | All match (values: "sent", "failed") |
| RelatedRecordId | related_record_id | related_record_id | ✅ PASS | All match (snake_case) |
| RelatedTable | related_table | related_table | ✅ PASS | All match (snake_case) |
| Data | data | data | ✅ PASS | All match |

### 1.2 Missing Fields Check

**Fields in API Spec but NOT in Domain Model:**
- `id` - ✅ OK (technical field, not business-level)
- `created_at` - ✅ OK (audit field)
- `updated_at` - ✅ OK (audit field)
- `user_id` - ✅ OK (explicit FK, domain model says "User" conceptually)
- `company_id` - ✅ OK (explicit FK, domain model says "Company" conceptually)

**Fields in DB Spec but NOT in API Spec:**
- `deleted_at` - ⚠️ ISSUE: Soft-delete field missing from API responses
- `created_by` - ⚠️ ISSUE: Audit field missing from API responses
- `updated_by` - ⚠️ ISSUE: Audit field missing from API responses
- `deleted_by` - ⚠️ ISSUE: Audit field missing from API responses

**Fields in UI Data Contract but NOT in API Spec:**
- None - ✅ All UI contract fields are in API spec

**Fields in API Spec but NOT in UI Data Contract:**
- `status` - ⚠️ WARNING: UI contract doesn't list status, but API returns it
- `data` - ⚠️ WARNING: UI contract doesn't list data, but API returns it
- `user_id` - ⚠️ WARNING: UI contract doesn't list user_id, but API returns it
- `company_id` - ⚠️ WARNING: UI contract doesn't list company_id, but API returns it
- `updated_at` - ⚠️ WARNING: UI contract doesn't list updated_at, but API returns it

**Analysis:**
- API spec includes more fields than UI contract requires (acceptable - API can return more)
- DB spec includes audit fields not in API responses (acceptable - these are internal)
- Missing `deleted_at` in API responses is acceptable (soft-deleted records are filtered out)

---

## 2. RELATIONSHIP VALIDATION

### 2.1 Domain Model Relationships

| Relationship | Domain Model | API Spec | DB Spec | Status |
|--------------|--------------|----------|---------|--------|
| Notification → User | *..1 (Required) | user_id (FK, required) | user_id (FK, NOT NULL) | ✅ PASS |
| Notification → Company | *..1 (Required) | company_id (FK, required) | company_id (FK, NOT NULL) | ✅ PASS |
| Notification → Leave/Task | *..1 (Optional, polymorphic) | related_record_id + related_table (optional) | related_record_id + related_table (nullable, logical FK) | ✅ PASS |

### 2.2 Foreign Key Constraints

| FK Field | Referenced Table | Domain Model | API Spec | DB Spec | Status |
|----------|-----------------|--------------|-----------|---------|--------|
| user_id | users.id | Required | Required | NOT NULL, FK | ✅ PASS |
| company_id | companies.id | Required | Required | NOT NULL, FK | ✅ PASS |
| related_record_id | leaves.id or tasks.id | Optional | Optional | NULL, logical (no FK) | ✅ PASS |
| created_by | users.id | N/A (audit) | Not in API | NULL, FK | ✅ PASS |
| updated_by | users.id | N/A (audit) | Not in API | NULL, FK | ✅ PASS |
| deleted_by | users.id | N/A (audit) | Not in API | NULL, FK | ✅ PASS |

**Analysis:**
- All relationships correctly mapped
- Polymorphic relationship correctly implemented as logical (no DB FK)
- Audit FKs correctly implemented

---

## 3. NAMING CONSISTENCY

### 3.1 Field Naming (snake_case)

| Domain Model | API Spec | DB Spec | Status |
|--------------|----------|---------|--------|
| User | user_id | user_id | ✅ PASS |
| Company | company_id | company_id | ✅ PASS |
| IsRead | is_read | is_read | ✅ PASS |
| ReadAt | read_at | read_at | ✅ PASS |
| RelatedRecordId | related_record_id | related_record_id | ✅ PASS |
| RelatedTable | related_table | related_table | ✅ PASS |

**Analysis:**
- ✅ All naming is consistent (snake_case)
- ✅ Domain model uses PascalCase conceptually, but implementation uses snake_case correctly

---

## 4. VALIDATION RULES COMPARISON

### 4.1 Type Field Validation

| Source | Type Values | Status |
|--------|-------------|--------|
| Domain Model | "invite, leave, task" (categories) | ⚠️ NOTE: Conceptual categories |
| API Spec | Specific event types (Option B): leave_request, leave_approval, leave_rejection, leave_manager_approval, task_assignment, task_permission_change, task_status_change, user_activation, user_deactivation | ✅ PASS (per user decision) |
| DB Spec | CHECK constraint with same specific event types | ✅ PASS (matches API spec) |

**Analysis:**
- ✅ API and DB spec match (Option B - specific event types)
- ⚠️ Domain model shows categories, but this is acceptable (conceptual vs implementation)

### 4.2 Channel Field Validation

| Source | Channel Values | Status |
|--------|----------------|--------|
| Domain Model | "Email / In-App" | ✅ PASS (human-readable) |
| API Spec | "email", "in_app" | ✅ PASS (API format) |
| DB Spec | CHECK (channel IN ('email', 'in_app')) | ✅ PASS (matches API spec) |

**Analysis:**
- ✅ All consistent (domain model is human-readable, API/DB use lowercase with underscore)

### 4.3 Status Field Validation

| Source | Status Values | Status |
|--------|---------------|--------|
| Domain Model | "Sent / Failed" | ✅ PASS (human-readable) |
| API Spec | "sent", "failed" | ✅ PASS (API format) |
| DB Spec | CHECK (status IN ('sent', 'failed')) | ✅ PASS (matches API spec) |

**Analysis:**
- ✅ All consistent (domain model is human-readable, API/DB use lowercase)

### 4.4 Related Table Validation

| Source | Related Table Values | Status |
|--------|---------------------|--------|
| Domain Model | "leaves, tasks" | ✅ PASS |
| API Spec | "leaves", "tasks" | ✅ PASS |
| DB Spec | CHECK (related_table IN ('leaves', 'tasks')) | ✅ PASS (matches API spec) |

**Analysis:**
- ✅ All consistent

---

## 5. MISSING VALIDATIONS

### 5.1 Business Rule Validations

**Domain Model Business Rules:**
- IsRead is "In-app only" ✅ Documented in all specs
- ReadAt is "In-app only" ✅ Documented in all specs
- RelatedRecordId and RelatedTable must both be NULL or both be NOT NULL ✅ Documented in DB spec and API spec

**Missing Validations:**
- ⚠️ **ISSUE**: No CHECK constraint in DB spec enforcing `related_record_id` and `related_table` both NULL or both NOT NULL
  - **Location**: DB Spec Section 7.2.1
  - **Current**: Documented as business rule (application-enforced)
  - **Recommendation**: Consider adding CHECK constraint: `CHECK ((related_record_id IS NULL AND related_table IS NULL) OR (related_record_id IS NOT NULL AND related_table IS NOT NULL))`

- ⚠️ **ISSUE**: No CHECK constraint in DB spec enforcing `read_at IS NULL OR (channel = 'in_app' AND is_read = true)`
  - **Location**: DB Spec Section 7.2.1
  - **Current**: Documented as business rule (application-enforced)
  - **Recommendation**: Consider adding CHECK constraint for data integrity

---

## 6. MODULE ACTIONS / OPERATIONS

### 6.1 API Operations vs Domain Model

| Operation | Domain Model | API Spec | Status |
|-----------|--------------|----------|--------|
| Create Notification | System-generated (async workers) | Not exposed via API | ✅ PASS (correct - system-generated only) |
| Read Notification | View notification | GET /api/v1/notifications, GET /api/v1/notifications/{id} | ✅ PASS |
| Mark as Read | Update IsRead | PATCH /api/v1/notifications/{id}/read, PATCH /api/v1/notifications/read (bulk) | ✅ PASS |
| Mark as Unread | Update IsRead | PATCH /api/v1/notifications/read (bulk with action="unread") | ✅ PASS |
| Get Unread Count | Count unread | GET /api/v1/notifications/count | ✅ PASS |
| Delete Notification | Soft delete | Not exposed via API | ✅ PASS (correct - soft-delete is internal) |

**Analysis:**
- ✅ All operations correctly aligned
- ✅ No unauthorized operations exposed

---

## 7. MULTI-TENANT CONSTRAINTS

### 7.1 Company Scoping

| Requirement | Domain Model | API Spec | DB Spec | Status |
|-------------|--------------|----------|---------|--------|
| Company is Required | ✅ Required | ✅ Required | ✅ NOT NULL, FK | ✅ PASS |
| Company Isolation | ✅ Documented | ✅ Documented (RLS) | ✅ Index on company_id | ✅ PASS |
| Company Filtering | ✅ Documented | ✅ Documented (JWT org_id) | ✅ Index on company_id | ✅ PASS |

**Analysis:**
- ✅ All multi-tenant constraints correctly implemented

### 7.2 User Scoping

| Requirement | Domain Model | API Spec | DB Spec | Status |
|-------------|--------------|----------|---------|--------|
| User is Required | ✅ Required | ✅ Required | ✅ NOT NULL, FK | ✅ PASS |
| User Isolation | ✅ Documented | ✅ Documented (RLS) | ✅ Index on user_id | ✅ PASS |
| User Filtering | ✅ Documented | ✅ Documented (JWT sub) | ✅ Index on user_id | ✅ PASS |

**Analysis:**
- ✅ All user-scoping constraints correctly implemented

---

## 8. CRITICAL ISSUES FOUND

### 8.1 Column Order Violation (DB Spec)

**Issue:** Column order in Section 7.2.1 does not follow db_instruction.md required order

**Current Order:**
1. id (PK) ✅
2. user_id, company_id (FKs) ✅
3. type, title, message, channel ✅
4. **is_read, read_at, status** ❌ (Status/Flag fields mixed with business fields)
5. related_record_id, related_table, data ✅
6. created_at, updated_at, deleted_at, created_by, updated_by, deleted_by ✅

**Required Order (per db_instruction.md):**
1. Primary Key (id) ✅
2. Foreign Keys (user_id, company_id) ✅
3. Business Fields (type, title, message, channel, related_record_id, related_table, data)
4. Status/Flag Fields (is_read, read_at, status)
5. Audit Fields (created_at, updated_at, deleted_at, created_by, updated_by, deleted_by) ✅

**Correction Needed:**
Move `is_read`, `read_at`, and `status` to come AFTER `data` and BEFORE audit fields.

---

## 9. SUMMARY OF VALIDATION RESULTS

### 9.1 Overall Status

| Validation Category | Status | Issues Found |
|-------------------|--------|--------------|
| Field Mapping | ✅ PASS | 0 critical, 0 minor |
| Relationships | ✅ PASS | 0 issues |
| Naming Consistency | ✅ PASS | 0 issues |
| Validation Rules | ⚠️ WARNING | 0 critical, 2 minor (missing CHECK constraints) |
| Module Actions | ✅ PASS | 0 issues |
| Multi-Tenant Constraints | ✅ PASS | 0 issues |
| Column Order | ❌ FAIL | 1 critical (column order violation) |

### 9.2 Critical Issues (Must Fix)

1. **Column Order Violation** (DB Spec Section 7.2.1)
   - Status/Flag fields (is_read, read_at, status) must come after all business fields
   - Impact: Violates db_instruction.md Rule 5 (Column Order)

### 9.3 Minor Issues / Recommendations

1. **Missing CHECK Constraint** (DB Spec)
   - Consider adding CHECK constraint for `related_record_id` and `related_table` both NULL or both NOT NULL
   - Impact: Data integrity (currently application-enforced)

2. **Missing CHECK Constraint** (DB Spec)
   - Consider adding CHECK constraint for `read_at IS NULL OR (channel = 'in_app' AND is_read = true)`
   - Impact: Data integrity (currently application-enforced)

3. **UI Data Contract Fields** (Informational)
   - UI contract doesn't list `status`, `data`, `user_id`, `company_id`, `updated_at`
   - Impact: None (API can return more fields than UI contract requires)

---

## 10. RECOMMENDATIONS

### 10.1 Must Fix (Critical)

1. **Fix Column Order in DB Spec Section 7.2.1**
   - Reorder columns to: id, user_id, company_id, type, title, message, channel, related_record_id, related_table, data, **is_read, read_at, status**, created_at, updated_at, deleted_at, created_by, updated_by, deleted_by

### 10.2 Should Consider (Minor)

1. **Add CHECK Constraint for Related Fields**
   ```sql
   CHECK ((related_record_id IS NULL AND related_table IS NULL) 
          OR (related_record_id IS NOT NULL AND related_table IS NOT NULL))
   ```

2. **Add CHECK Constraint for Read Fields**
   ```sql
   CHECK (read_at IS NULL OR (channel = 'in_app' AND is_read = true))
   ```

### 10.3 Informational (No Action Required)

1. Domain model uses conceptual categories ("invite, leave, task") while API/DB use specific event types - This is correct per user's Option B decision
2. UI data contract lists fewer fields than API returns - This is acceptable (API can return more)
3. DB spec includes audit fields not in API responses - This is acceptable (internal fields)

---

**End of Validation Report**

