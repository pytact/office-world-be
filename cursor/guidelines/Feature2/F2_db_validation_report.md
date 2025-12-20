# Database Structure Validation Report
## F-002 — RBAC & Permission Engine (F2_db_spec.md)

**Validation Date:** 2025-01-19  
**Specification:** F2_db_spec.md  
**Status:** ⚠️ **VALIDATION WITH ISSUES**

---

## EXECUTIVE SUMMARY

| Category | Status | Issues Found |
|----------|--------|--------------|
| **Naming Consistency** | ✅ PASS | 0 |
| **Missing Models** | ✅ PASS | 0 |
| **Missing Fields** | ⚠️ ISSUES | 1 (password field not in F2 spec) |
| **Broken Rules** | ⚠️ ISSUES | 2 (CHECK constraint missing, field length mismatch) |
| **ERD Relationships** | ✅ PASS | 0 |
| **Constraints** | ⚠️ ISSUES | 3 (CHECK constraint missing, partial unique index missing) |
| **PK/FK Correctness** | ✅ PASS | 0 |

**Overall Status:** ⚠️ **6 ISSUES FOUND** - See details below

---

## 1. NAMING CONSISTENCY

### 1.1 Table Names
| Spec | Model | Status |
|------|-------|--------|
| `roles` | `roles` | ✅ |
| `users` | `users` | ✅ |
| `user_role_assignments` | `user_role_assignments` | ✅ |
| `companies` | `companies` | ✅ |

**Result:** ✅ **PASS** - All table names match spec (snake_case)

### 1.2 Field Names
All field names match specification exactly (snake_case):
- ✅ `id`, `name`, `code`, `permissions`, `created_at`, `updated_at`, `deleted_at`, `created_by`, `updated_by`, `deleted_by`
- ✅ `email`, `first_name`, `last_name`, `is_active`, `invite_at`, `activate_at`, `expiry`, `token`, `reinvite_count`, `last_reinvite_at`
- ✅ `user_id`, `role_id`, `company_id`
- ✅ `slug`

**Result:** ✅ **PASS** - All field names match spec (snake_case)

---

## 2. MISSING MODELS

### 2.1 Required Models (F2_db_spec.md Section 7)
| Model | Spec Section | Model File | Status |
|-------|-------------|------------|--------|
| `Role` | 7.1 | `src/permissions/models.py` | ✅ |
| `User` | 7.2 | `src/users/models.py` | ✅ |
| `UserRoleAssignment` | 7.3 | `src/permissions/models.py` | ✅ |
| `Company` | 7.4 | `src/companies/models.py` | ✅ |

**Result:** ✅ **PASS** - All 4 required models exist

---

## 3. MISSING FIELDS

### 3.1 Table: roles (Section 7.1)

| Field | Spec Type | Spec Null | Spec Default | Model Type | Model Null | Model Default | Status |
|-------|-----------|-----------|---------------|------------|------------|---------------|--------|
| `id` | UUID | No | gen_random_uuid() | PostgresUUID | No | uuid4 | ✅ |
| `name` | VARCHAR(100) | No | - | String(100) | No | - | ✅ |
| `code` | VARCHAR(50) | No | - | String(50) | No | - | ✅ |
| `permissions` | JSONB | No | '{}' | JSONB | No | '{}' | ✅ |
| `created_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | DateTime(timezone=True) | No | func.now() | ✅ |
| `updated_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | DateTime(timezone=True) | No | func.now() | ✅ |
| `deleted_at` | TIMESTAMPTZ | Yes | NULL | DateTime(timezone=True) | Yes | - | ✅ |
| `created_by` | UUID | Yes | NULL | PostgresUUID | Yes | - | ✅ |
| `updated_by` | UUID | Yes | NULL | PostgresUUID | Yes | - | ✅ |
| `deleted_by` | UUID | Yes | NULL | PostgresUUID | Yes | - | ✅ |

**Result:** ✅ **PASS** - All fields match spec

### 3.2 Table: users (Section 7.2)

| Field | Spec Type | Spec Null | Spec Default | Model Type | Model Null | Model Default | Status |
|-------|-----------|-----------|---------------|------------|------------|---------------|--------|
| `id` | UUID | No | gen_random_uuid() | PostgresUUID | No | uuid4 | ✅ |
| `email` | VARCHAR(255) | No | - | String(255) | No | - | ✅ |
| `first_name` | VARCHAR(100) | Yes | NULL | String(100) | Yes | - | ✅ |
| `last_name` | VARCHAR(100) | Yes | NULL | String(100) | Yes | - | ✅ |
| `is_active` | BOOLEAN | No | false | Boolean | No | false | ✅ |
| `invite_at` | TIMESTAMPTZ | Yes | NULL | DateTime(timezone=True) | Yes | - | ✅ |
| `activate_at` | TIMESTAMPTZ | Yes | NULL | DateTime(timezone=True) | Yes | - | ✅ |
| `expiry` | TIMESTAMPTZ | Yes | NULL | DateTime(timezone=True) | Yes | - | ✅ |
| `token` | VARCHAR(255) | Yes | NULL | String(255) | Yes | - | ✅ |
| `reinvite_count` | INTEGER | No | 0 | Integer | No | 0 | ✅ |
| `last_reinvite_at` | TIMESTAMPTZ | Yes | NULL | DateTime(timezone=True) | Yes | - | ✅ |
| `created_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | DateTime(timezone=True) | No | func.now() | ✅ |
| `updated_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | DateTime(timezone=True) | No | func.now() | ✅ |
| `deleted_at` | TIMESTAMPTZ | Yes | NULL | DateTime(timezone=True) | Yes | - | ✅ |
| `created_by` | UUID | Yes | NULL | PostgresUUID | Yes | - | ✅ |
| `updated_by` | UUID | Yes | NULL | PostgresUUID | Yes | - | ✅ |
| `deleted_by` | UUID | Yes | NULL | PostgresUUID | Yes | - | ✅ |
| `password` | **NOT IN F2 SPEC** | - | - | String(255) | Yes | - | ⚠️ **EXTRA FIELD** |

**Result:** ⚠️ **ISSUE** - `password` field exists in model but NOT in F2_db_spec.md Section 7.2
- **Note:** This field may be from F1_db_spec.md (authentication feature)
- **Action:** Verify if this field should be excluded from F-002 validation or if it's acceptable

### 3.3 Table: user_role_assignments (Section 7.3)

| Field | Spec Type | Spec Null | Spec Default | Model Type | Model Null | Model Default | Status |
|-------|-----------|-----------|---------------|------------|------------|---------------|--------|
| `id` | UUID | No | gen_random_uuid() | PostgresUUID | No | uuid4 | ✅ |
| `user_id` | UUID | No | - | PostgresUUID | No | - | ✅ |
| `role_id` | UUID | No | - | PostgresUUID | No | - | ✅ |
| `company_id` | UUID | Yes | NULL | PostgresUUID | Yes | - | ✅ |
| `is_active` | BOOLEAN | No | true | Boolean | No | true | ✅ |
| `created_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | DateTime(timezone=True) | No | func.now() | ✅ |
| `updated_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | DateTime(timezone=True) | No | func.now() | ✅ |
| `deleted_at` | TIMESTAMPTZ | Yes | NULL | DateTime(timezone=True) | Yes | - | ✅ |
| `created_by` | UUID | Yes | NULL | PostgresUUID | Yes | - | ✅ |
| `updated_by` | UUID | Yes | NULL | PostgresUUID | Yes | - | ✅ |
| `deleted_by` | UUID | Yes | NULL | PostgresUUID | Yes | - | ✅ |

**Result:** ✅ **PASS** - All fields match spec

### 3.4 Table: companies (Section 7.4)

| Field | Spec Type | Spec Null | Spec Default | Model Type | Model Null | Model Default | Status |
|-------|-----------|-----------|---------------|------------|------------|---------------|--------|
| `id` | UUID | No | gen_random_uuid() | PostgresUUID | No | uuid4 | ✅ |
| `name` | VARCHAR(255) | No | - | String(255) | No | - | ✅ |
| `slug` | VARCHAR(255) | No | - | String(255) | No | - | ✅ |
| `is_active` | BOOLEAN | No | true | Boolean | No | true | ✅ |
| `created_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | DateTime(timezone=True) | No | func.now() | ✅ |
| `updated_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | DateTime(timezone=True) | No | func.now() | ✅ |
| `deleted_at` | TIMESTAMPTZ | Yes | NULL | DateTime(timezone=True) | Yes | - | ✅ |
| `created_by` | UUID | Yes | NULL | PostgresUUID | Yes | - | ✅ |
| `updated_by` | UUID | Yes | NULL | PostgresUUID | Yes | - | ✅ |
| `deleted_by` | UUID | Yes | NULL | PostgresUUID | Yes | - | ✅ |

**Result:** ✅ **PASS** - All fields match spec

---

## 4. BROKEN RULES

### 4.1 CHECK Constraints

#### Table: roles
| Constraint | Spec (Section 7.1) | Model | Status |
|------------|---------------------|-------|--------|
| `code IN ('superadmin', 'ceo', 'hr', 'manager', 'employee')` | ✅ Required | ❌ **MISSING** | ⚠️ **ISSUE** |

**Issue:** Spec Section 7.1 line 284 states:
> CHECK (code IN ('superadmin', 'ceo', 'hr', 'manager', 'employee'))

**Current State:** Model has `unique=True` and `nullable=False` but NO CHECK constraint

**Action Required:** Add CHECK constraint to model or migration:
```python
__table_args__ = (
    CheckConstraint("code IN ('superadmin', 'ceo', 'hr', 'manager', 'employee')", name="chk_roles_code"),
)
```

#### Table: users
| Constraint | Spec (Section 7.2) | Model | Status |
|------------|---------------------|-------|--------|
| `reinvite_count >= 0` | ✅ Required | ✅ CheckConstraint | ✅ |

**Result:** ✅ **PASS** - CHECK constraint implemented

#### Table: user_role_assignments
| Constraint | Spec (Section 7.3) | Model | Status |
|------------|---------------------|-------|--------|
| None specified | - | - | ✅ |

**Result:** ✅ **PASS** - No CHECK constraints required

#### Table: companies
| Constraint | Spec (Section 7.4) | Model | Status |
|------------|---------------------|-------|--------|
| None specified | - | - | ✅ |

**Result:** ✅ **PASS** - No CHECK constraints required

### 4.2 Field Length Mismatches

#### Table: roles
| Field | Spec Length | Model Length | Status |
|-------|-------------|--------------|--------|
| `name` | VARCHAR(100) | String(100) | ✅ |
| `code` | VARCHAR(50) | String(50) | ✅ |

**Result:** ✅ **PASS** - All lengths match

#### Table: users
| Field | Spec Length | Model Length | Status |
|-------|-------------|--------------|--------|
| `email` | VARCHAR(255) | String(255) | ✅ |
| `first_name` | VARCHAR(100) | String(100) | ✅ |
| `last_name` | VARCHAR(100) | String(100) | ✅ |
| `token` | VARCHAR(255) | String(255) | ✅ |

**Result:** ✅ **PASS** - All lengths match

#### Table: companies
| Field | Spec Length | Model Length | Status |
|-------|-------------|--------------|--------|
| `name` | VARCHAR(255) | String(255) | ✅ |
| `slug` | VARCHAR(255) | String(255) | ✅ |

**Result:** ✅ **PASS** - All lengths match

---

## 5. ERD RELATIONSHIPS

### 5.1 Relationship 1: User ↔ UserRoleAssignment
- **Spec:** User (1) ←→ (1) UserRoleAssignment (one active per user)
- **Model:**
  - User.role_assignments: `Mapped[list["UserRoleAssignment"]]` (1-to-many) ✅
  - UserRoleAssignment.user: `Mapped["User"]` (many-to-1) ✅
- **Status:** ✅ **CORRECT**
- **Note:** Business rule enforced via partial unique index: `UNIQUE(user_id) WHERE is_active = true AND deleted_at IS NULL`

### 5.2 Relationship 2: Role ↔ UserRoleAssignment
- **Spec:** Role (1) ←→ (M) UserRoleAssignment
- **Model:**
  - Role.role_assignments: `Mapped[list["UserRoleAssignment"]]` (1-to-many) ✅
  - UserRoleAssignment.role: `Mapped["Role"]` (many-to-1) ✅
- **Status:** ✅ **CORRECT**

### 5.3 Relationship 3: Company ↔ UserRoleAssignment
- **Spec:** Company (1) ←→ (M) UserRoleAssignment
- **Model:**
  - Company.role_assignments: `Mapped[list["UserRoleAssignment"]]` (1-to-many) ✅
  - UserRoleAssignment.company: `Mapped["Company | None"]` (many-to-1, nullable) ✅
- **Status:** ✅ **CORRECT**

**Result:** ✅ **PASS** - All relationships match ERD specification (Section 10)

---

## 6. CONSTRAINTS

### 6.1 CHECK Constraints

#### Table: roles
- ⚠️ **MISSING:** `CHECK (code IN ('superadmin', 'ceo', 'hr', 'manager', 'employee'))`
  - **Spec:** Section 7.1 line 284
  - **Status:** ❌ **NOT IMPLEMENTED**
  - **Action:** Add CheckConstraint to model or migration

#### Table: users
- ✅ `reinvite_count >= 0` (implemented)

**Result:** ⚠️ **1 CHECK CONSTRAINT MISSING**

### 6.2 UNIQUE Constraints

#### Table: roles
- ✅ `code`: UNIQUE (enforced via `unique=True` in model)
- ⚠️ **NOTE:** Spec Section 9.8 mentions partial unique index: `WHERE deleted_at IS NULL`
  - **Status:** Should be created in migration (not model constraint)

#### Table: users
- ✅ `email`: UNIQUE (enforced via `unique=True` in model)
- ⚠️ **NOTE:** Spec Section 9.8 mentions partial unique index: `WHERE deleted_at IS NULL`
  - **Status:** Should be created in migration (not model constraint)

#### Table: companies
- ✅ `name`: UNIQUE (enforced via `unique=True` in model)
- ✅ `slug`: UNIQUE (enforced via `unique=True` in model)
- ⚠️ **NOTE:** Spec Section 9.8 requires case-insensitive unique indexes:
  - `CREATE UNIQUE INDEX uq_companies_name_ci ON companies(LOWER(name)) WHERE deleted_at IS NULL`
  - `CREATE UNIQUE INDEX uq_companies_slug_ci ON companies(LOWER(slug)) WHERE deleted_at IS NULL`
  - **Status:** Should be created in migration (not model constraint)

#### Table: user_role_assignments
- ⚠️ **MISSING:** Spec Section 7.3 line 392 requires:
  - `UNIQUE(user_id) WHERE is_active = true AND deleted_at IS NULL`
  - **Status:** Should be created in migration as partial unique index
  - **Note:** Model has comment indicating this should be in migration ✅

**Result:** ⚠️ **PARTIAL UNIQUE INDEXES NEED TO BE CREATED IN MIGRATION**

---

## 7. PK/FK CORRECTNESS

### 7.1 Primary Keys

| Table | Spec Type | Model Type | Status |
|-------|-----------|------------|--------|
| roles | UUID | `PostgresUUID(as_uuid=True)` | ✅ |
| users | UUID | `PostgresUUID(as_uuid=True)` | ✅ |
| user_role_assignments | UUID | `PostgresUUID(as_uuid=True)` | ✅ |
| companies | UUID | `PostgresUUID(as_uuid=True)` | ✅ |

**Result:** ✅ **PASS** - All primary keys correct

### 7.2 Foreign Keys

#### Table: roles (audit fields)
| FK | References | ON DELETE | ON UPDATE | Indexed | Status |
|----|------------|-----------|-----------|---------|--------|
| created_by | users(id) | RESTRICT | CASCADE | ✅ | ✅ |
| updated_by | users(id) | RESTRICT | CASCADE | ✅ | ✅ |
| deleted_by | users(id) | RESTRICT | CASCADE | ✅ | ✅ |

#### Table: users (self-referencing)
| FK | References | ON DELETE | ON UPDATE | Indexed | Status |
|----|------------|-----------|-----------|---------|--------|
| created_by | users(id) | RESTRICT | CASCADE | ✅ | ✅ |
| updated_by | users(id) | RESTRICT | CASCADE | ✅ | ✅ |
| deleted_by | users(id) | RESTRICT | CASCADE | ✅ | ✅ |

#### Table: user_role_assignments
| FK | References | ON DELETE | ON UPDATE | Indexed | Status |
|----|------------|-----------|-----------|---------|--------|
| user_id | users(id) | RESTRICT | CASCADE | ✅ | ✅ |
| role_id | roles(id) | RESTRICT | CASCADE | ✅ | ✅ |
| company_id | companies(id) | **CASCADE** | CASCADE | ✅ | ✅ |
| created_by | users(id) | RESTRICT | CASCADE | ✅ | ✅ |
| updated_by | users(id) | RESTRICT | CASCADE | ✅ | ✅ |
| deleted_by | users(id) | RESTRICT | CASCADE | ✅ | ✅ |

**Note:** `company_id` FK has `ondelete="CASCADE"` (correct per spec Section 7.3 line 386)

#### Table: companies (audit fields)
| FK | References | ON DELETE | ON UPDATE | Indexed | Status |
|----|------------|-----------|-----------|---------|--------|
| created_by | users(id) | RESTRICT | CASCADE | ✅ | ✅ |
| updated_by | users(id) | RESTRICT | CASCADE | ✅ | ✅ |
| deleted_by | users(id) | RESTRICT | CASCADE | ✅ | ✅ |

**Result:** ✅ **PASS** - All foreign keys correct (types, constraints, indexes)

---

## 8. MISSING INDEXES (MIGRATION REQUIRED)

### 8.1 Audit Field Indexes (Section 9.3 - MANDATORY)
**Every table with `updated_at` MUST have an index:**

| Index | Spec | Migration | Status |
|-------|------|-----------|--------|
| `idx_roles_updated_at` | Section 9.3 | ❌ Missing | ⚠️ |
| `idx_users_updated_at` | Section 9.3 | ❌ Missing | ⚠️ |
| `idx_user_role_assignments_updated_at` | Section 9.3 | ❌ Missing | ⚠️ |
| `idx_companies_updated_at` | Section 9.3 | ❌ Missing | ⚠️ |

**Action Required:** Create indexes in migration:
```sql
CREATE INDEX idx_roles_updated_at ON roles(updated_at);
CREATE INDEX idx_users_updated_at ON users(updated_at);
CREATE INDEX idx_user_role_assignments_updated_at ON user_role_assignments(updated_at);
CREATE INDEX idx_companies_updated_at ON companies(updated_at);
```

### 8.2 Permission Evaluation Indexes (Section 9.4)

| Index | Spec | Migration | Status |
|-------|------|-----------|--------|
| `idx_user_role_assignments_active_user` | Section 9.4 | ❌ Missing | ⚠️ |
| `idx_roles_code` (partial) | Section 9.4 | ❌ Missing | ⚠️ |
| `idx_user_role_assignments_company_active` | Section 9.4 | ❌ Missing | ⚠️ |
| `idx_users_active` | Section 9.4 | ❌ Missing | ⚠️ |
| `idx_companies_active` | Section 9.4 | ❌ Missing | ⚠️ |

**Action Required:** Create indexes in migration per Section 9.4

### 8.3 JSONB GIN Index (Section 9.5)

| Index | Spec | Migration | Status |
|-------|------|-----------|--------|
| `idx_roles_permissions_gin` | Section 9.5 | ❌ Missing | ⚠️ |

**Action Required:** Create GIN index in migration:
```sql
CREATE INDEX idx_roles_permissions_gin ON roles USING gin(permissions);
```

### 8.4 Soft Delete Indexes (Section 9.6)

| Index | Spec | Migration | Status |
|-------|------|-----------|--------|
| `idx_roles_active` | Section 9.6 | ❌ Missing | ⚠️ |
| `idx_users_active_only` | Section 9.6 | ❌ Missing | ⚠️ |
| `idx_user_role_assignments_active` | Section 9.6 | ❌ Missing | ⚠️ |
| `idx_companies_active_only` | Section 9.6 | ❌ Missing | ⚠️ |

**Action Required:** Create partial indexes in migration per Section 9.6

### 8.5 Composite Indexes (Section 9.7)

| Index | Spec | Migration | Status |
|-------|------|-----------|--------|
| `idx_user_role_assignments_evaluation` | Section 9.7 | ❌ Missing | ⚠️ |
| `idx_user_role_assignments_company_users` | Section 9.7 | ❌ Missing | ⚠️ |
| `idx_user_role_assignments_role_users` | Section 9.7 | ❌ Missing | ⚠️ |

**Action Required:** Create composite indexes in migration per Section 9.7

### 8.6 Unique Constraints as Indexes (Section 9.8)

| Index | Spec | Migration | Status |
|-------|------|-----------|--------|
| `uq_companies_name_ci` | Section 9.8 | ❌ Missing | ⚠️ |
| `uq_companies_slug_ci` | Section 9.8 | ❌ Missing | ⚠️ |
| `uq_user_role_assignments_user_active` | Section 7.3 | ❌ Missing | ⚠️ |

**Action Required:** Create partial unique indexes in migration per Section 9.8

---

## 9. VALIDATION SUMMARY

### 9.1 Critical Issues (Must Fix)

1. ⚠️ **MISSING CHECK CONSTRAINT:** `roles.code` must have CHECK constraint:
   ```python
   CheckConstraint("code IN ('superadmin', 'ceo', 'hr', 'manager', 'employee')", name="chk_roles_code")
   ```

2. ⚠️ **MISSING PARTIAL UNIQUE INDEX:** `user_role_assignments.user_id` must have:
   ```sql
   CREATE UNIQUE INDEX uq_user_role_assignments_user_active 
   ON user_role_assignments(user_id) 
   WHERE is_active = true AND deleted_at IS NULL;
   ```

3. ⚠️ **MISSING MANDATORY INDEXES:** All `updated_at` columns need indexes (Section 9.3)

4. ⚠️ **MISSING JSONB GIN INDEX:** `roles.permissions` needs GIN index (Section 9.5)

### 9.2 Minor Issues / Notes

1. **Extra Field:** `users.password` exists in model but NOT in F2_db_spec.md
   - **Note:** This field may be from F1_db_spec.md (authentication feature)
   - **Action:** Verify if acceptable or if should be excluded from F-002 validation

2. **Partial Unique Indexes (Migration Required)**
   - ⚠️ **NOT A MODEL ISSUE** - Partial unique indexes with `WHERE deleted_at IS NULL` should be created in migration
   - **Tables affected:** roles (code), users (email), companies (name, slug - case-insensitive)

3. **Performance Indexes (Migration Required)**
   - ⚠️ **NOT A MODEL ISSUE** - Permission evaluation indexes (Section 9.4), soft delete indexes (Section 9.6), and composite indexes (Section 9.7) should be created in migration

---

## 10. VALIDATION CONCLUSION

### Overall Status: ⚠️ **VALIDATION WITH ISSUES**

**Summary:**
- ✅ All 4 models exist and are correctly structured
- ✅ All field names match specification exactly (snake_case)
- ✅ All primary keys use UUID correctly
- ✅ All foreign keys have proper constraints and indexes
- ✅ All relationships match ERD specification
- ⚠️ **1 CHECK constraint missing** (roles.code enum)
- ⚠️ **1 partial unique index missing** (user_role_assignments.user_id)
- ⚠️ **Multiple performance indexes missing** (migration required)
- ⚠️ **1 extra field** (users.password - may be from F1 spec)

**Recommendations:**
1. ⚠️ **URGENT:** Add CHECK constraint for `roles.code` enum
2. ⚠️ **URGENT:** Create partial unique index for `user_role_assignments.user_id`
3. ⚠️ **HIGH PRIORITY:** Create mandatory `updated_at` indexes (Section 9.3)
4. ⚠️ **HIGH PRIORITY:** Create JSONB GIN index for `roles.permissions` (Section 9.5)
5. ⚠️ **MEDIUM PRIORITY:** Create permission evaluation indexes (Section 9.4)
6. ⚠️ **MEDIUM PRIORITY:** Create soft delete indexes (Section 9.6)
7. ⚠️ **MEDIUM PRIORITY:** Create composite indexes (Section 9.7)
8. ⚠️ **MEDIUM PRIORITY:** Create case-insensitive unique indexes for companies (Section 9.8)
9. ℹ️ **INFO:** Verify `users.password` field (may be from F1 spec, acceptable if cross-feature)

---

## 11. COMPLIANCE CHECKLIST

- [x] All table names match spec (snake_case)
- [x] All field names match spec (snake_case)
- [x] All 4 models exist
- [x] All fields present (except password - may be from F1)
- [x] All primary keys use UUID
- [x] All timestamps use `server_default=func.now()`
- [x] All foreign keys use `ON DELETE RESTRICT ON UPDATE CASCADE` (except company_id CASCADE)
- [x] All foreign keys are indexed
- [x] All relationships match ERD
- [ ] **CHECK constraint for roles.code enum** ❌
- [ ] **Partial unique index for user_role_assignments.user_id** ❌
- [ ] **All updated_at indexes created** ❌
- [ ] **JSONB GIN index for roles.permissions** ❌
- [ ] **Permission evaluation indexes created** ❌
- [ ] **Soft delete indexes created** ❌
- [ ] **Composite indexes created** ❌
- [ ] **Case-insensitive unique indexes for companies** ❌

---

**End of Validation Report**

