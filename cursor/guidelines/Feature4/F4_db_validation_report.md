# Database Validation Report: F-004 — Platform Company Management

**Feature:** F-004 — Platform Company Management  
**Validation Date:** 2025-01-20  
**Specification:** `F4_db_spec.md`  
**Status:** ❌ **FAILED** — Multiple Critical Issues Found

---

## Executive Summary

The Company model implementation has been validated against F4_db_spec.md. **Critical issues** were found that prevent compliance with the specification:

1. **CRITICAL:** Missing profile fields in database migration
2. **CRITICAL:** Soft delete fields present in migration (should be hard deletion)
3. **CRITICAL:** Missing foreign key constraints in migration
4. **CRITICAL:** Missing required indexes per Section 9
5. **CRITICAL:** Case-insensitive unique indexes incorrectly include soft delete WHERE clause
6. **WARNING:** Model vs Migration mismatch (model correct, migration incorrect)

---

## 1. Naming Consistency

### ✅ PASS — Table Naming
- **Specification:** `companies` (snake_case, plural)
- **Model:** `__tablename__ = "companies"` ✅
- **Migration:** `'companies'` ✅

### ✅ PASS — Column Naming
All column names match specification exactly:
- `id`, `name`, `slug`, `description`, `address`, `city`, `state`, `country`, `postal_code`, `website`, `logo_url`, `is_active`, `created_at`, `updated_at`, `created_by`, `updated_by` ✅

---

## 2. Missing Models

### ✅ PASS — All Models Present
- **Company model:** `src/companies/models.py` ✅
- **Related models:** UserRoleAssignment, User (referenced correctly) ✅

**Note:** Employee model relationship is documented but Employee model doesn't have `company_id` FK yet (separate feature).

---

## 3. Missing Fields

### ❌ CRITICAL — Profile Fields Missing in Migration

**Issue:** Initial migration (`001_initial_migration.py`) does NOT include profile fields required by F4_db_spec.md Section 7.1.

**Missing Fields in Migration:**
| Field | Type | Required | Status |
|-------|------|----------|--------|
| `description` | VARCHAR(1000) | Optional | ❌ Missing |
| `address` | VARCHAR(255) | Optional | ❌ Missing |
| `city` | VARCHAR(100) | Optional | ❌ Missing |
| `state` | VARCHAR(100) | Optional | ❌ Missing |
| `country` | VARCHAR(100) | Optional | ❌ Missing |
| `postal_code` | VARCHAR(20) | Optional | ❌ Missing |
| `website` | VARCHAR(2048) | Optional | ❌ Missing |
| `logo_url` | VARCHAR(2048) | Optional | ❌ Missing |

**Model Status:** ✅ All fields present in `src/companies/models.py`

**Impact:** Database schema doesn't match model. Application will fail with `UndefinedColumnError` when accessing profile fields.

**Required Action:** Create migration to add these 8 profile fields to `companies` table.

---

## 4. Broken Rules

### ❌ CRITICAL — Soft Delete Fields in Migration (Hard Deletion Required)

**Issue:** F4_db_spec.md Section 5.4 explicitly states: "Hard deletion is supported (no soft delete fields: deleted_at, deleted_by, is_deleted)."

**Current State:**
- **Migration (`001_initial_migration.py`):** Contains `deleted_at` and `deleted_by` columns ❌
- **Model (`src/companies/models.py`):** Correctly excludes soft delete fields ✅

**Specification Requirement:**
- Section 5.4: "Note: Hard deletion is supported (no soft delete fields: deleted_at, deleted_by, is_deleted)."
- Section 3.2: "Hard deletion support (irreversible removal of company and all associated data)"

**Impact:** Database schema violates specification. Soft delete fields should not exist for companies table.

**Required Action:** Create migration to remove `deleted_at` and `deleted_by` columns from `companies` table.

---

### ❌ CRITICAL — Missing Foreign Key Constraints in Migration

**Issue:** Migration doesn't define foreign key constraints for audit fields.

**Specification Requirement (Section 7.1):**
```
Foreign Key Constraints:
- created_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- updated_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
```

**Current State:**
- **Migration:** `created_by` and `updated_by` are UUID columns without FK constraints ❌
- **Model:** Correctly defines FK constraints ✅

**Impact:** Database doesn't enforce referential integrity. Orphaned records possible.

**Required Action:** Add foreign key constraints in migration (or update existing migration).

---

### ⚠️ WARNING — Case-Insensitive Unique Indexes Include Soft Delete WHERE Clause

**Issue:** Migration `004_add_f2_indexes_and_constraints.py` creates case-insensitive unique indexes with `WHERE deleted_at IS NULL`, but companies table should use hard deletion.

**Current Indexes:**
```sql
-- Migration 004 (INCORRECT for hard deletion)
CREATE UNIQUE INDEX uq_companies_name_ci ON companies(LOWER(name)) 
WHERE deleted_at IS NULL;  -- ❌ Should not have WHERE clause

CREATE UNIQUE INDEX uq_companies_slug_ci ON companies(LOWER(slug)) 
WHERE deleted_at IS NULL;  -- ❌ Should not have WHERE clause
```

**Specification Requirement (Section 9.3):**
```sql
CREATE UNIQUE INDEX uq_companies_name ON companies(LOWER(name));
CREATE UNIQUE INDEX uq_companies_slug ON companies(LOWER(slug));
```

**Impact:** Indexes work but include unnecessary WHERE clause that references non-existent field (after removing deleted_at).

**Required Action:** Update indexes to remove WHERE clause (or recreate after removing deleted_at).

---

## 5. ERD Validation

### ✅ PASS — ERD Relationships Match Model

**ERD Requirements (ERD_F4_Platform_Company_Management.txt):**
1. Company 1..* UserRoleAssignment ✅
   - Model: `role_assignments: Mapped[list["UserRoleAssignment"]]` ✅
   - FK: `UserRoleAssignment.company_id → companies.id` ✅

2. Company 1..* Employee ✅
   - Documented in ERD (Employee model has company_id FK in other features)

3. Company 1..* DomainRecords ✅
   - Documented in ERD (leaves, tasks, notifications, etc.)

**Note:** ERD only shows PK/FK fields (per ERD rules), which matches model structure.

---

## 6. Constraints

### ❌ CRITICAL — Missing Foreign Key Constraints

**Issue:** Migration doesn't create FK constraints for `created_by` and `updated_by`.

**Required Constraints (Section 7.1):**
- `created_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE` ❌ Missing
- `updated_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE` ❌ Missing

**Model Status:** ✅ FK constraints correctly defined in model

**Impact:** Database doesn't enforce referential integrity.

---

### ✅ PASS — Check Constraint

**Specification:** CHECK constraint on `is_active` to ensure only boolean values.

**Migration:** ✅ `sa.CheckConstraint("is_active IN (true, false)", name='chk_companies_is_active')`

**Model:** ✅ Boolean type enforces boolean values

---

### ⚠️ WARNING — Unique Constraints

**Specification:** Case-insensitive unique constraints on `name` and `slug`.

**Current State:**
- **Migration 001:** Creates case-sensitive unique indexes (`ix_companies_name`, `ix_companies_slug`) ⚠️
- **Migration 004:** Creates case-insensitive unique indexes (`uq_companies_name_ci`, `uq_companies_slug_ci`) ✅
- **Model:** Uses `unique=True` (case-sensitive) ⚠️

**Issue:** Model defines case-sensitive uniqueness, but specification requires case-insensitive.

**Impact:** Application-level uniqueness check may conflict with database-level case-insensitive uniqueness.

**Recommendation:** Model `unique=True` is acceptable (SQLAlchemy constraint), but application must enforce case-insensitive uniqueness (per spec Section 4.2: "Company name and slug must be globally unique (case-insensitive)").

---

## 7. PK/FK Correctness

### ✅ PASS — Primary Key

**Specification:** `id` UUID, PRIMARY KEY, default `gen_random_uuid()`

**Model:**
```python
id: Mapped[UUID] = mapped_column(
    PostgresUUID(as_uuid=True),
    primary_key=True,
    default=uuid4,  # ✅ Correct
    index=True,
)
```

**Migration:**
```python
sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
sa.PrimaryKeyConstraint('id'),  # ✅ Correct
```

---

### ❌ CRITICAL — Foreign Keys Missing in Migration

**Specification (Section 7.1):**
- `created_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE`
- `updated_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE`

**Model:** ✅ Correctly defines FK constraints
```python
created_by: Mapped[UUID | None] = mapped_column(
    PostgresUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),  # ✅
    nullable=True,
    index=True,
)
```

**Migration:** ❌ Missing FK constraints
```python
sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),  # ❌ No FK
sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),  # ❌ No FK
```

**Impact:** Database doesn't enforce referential integrity for audit fields.

**Required Action:** Add FK constraints in migration.

---

### ✅ PASS — UserRoleAssignment Foreign Key

**Specification:** Company relationship via UserRoleAssignment.

**Migration:** ✅ Correctly defines FK
```python
sa.ForeignKeyConstraint(['company_id'], ['companies.id'], 
    ondelete='CASCADE', onupdate='CASCADE'),  # ✅ Correct
```

**Model:** ✅ Correctly defines relationship
```python
role_assignments: Mapped[list["UserRoleAssignment"]] = relationship(
    "UserRoleAssignment",
    back_populates="company",
    cascade="all, delete-orphan",
)
```

---

## 8. Index Strategy Validation

### ❌ CRITICAL — Missing Required Indexes

**Specification (Section 9):** Requires 10 indexes for companies table.

**Index Status:**

| Index Name | Columns | Type | Status | Migration |
|------------|---------|------|--------|-----------|
| `pk_companies` | `id` | UNIQUE | ✅ Auto (PK) | 001 |
| `uq_companies_name` | `LOWER(name)` | UNIQUE | ⚠️ Partial (has WHERE) | 004 |
| `uq_companies_slug` | `LOWER(slug)` | UNIQUE | ⚠️ Partial (has WHERE) | 004 |
| `idx_companies_created_by` | `created_by` | INDEX | ❌ Missing | - |
| `idx_companies_updated_by` | `updated_by` | INDEX | ❌ Missing | - |
| `idx_companies_updated_at` | `updated_at` | INDEX | ✅ Present | 004 |
| `idx_companies_is_active` | `is_active` | INDEX | ⚠️ Partial (has WHERE) | 004 |
| `idx_companies_created_at` | `created_at DESC` | INDEX | ❌ Missing | - |
| `idx_companies_status_created` | `is_active, created_at DESC` | COMPOSITE | ❌ Missing | - |
| `idx_companies_name_trgm` | `name` | GIN (trigram) | ❌ Missing | - |
| `idx_companies_slug_trgm` | `slug` | GIN (trigram) | ❌ Missing | - |

**Missing Indexes:**
1. `idx_companies_created_by` — Foreign key performance
2. `idx_companies_updated_by` — Foreign key performance
3. `idx_companies_created_at` — Creation date sorting
4. `idx_companies_status_created` — Composite (status + date sort)
5. `idx_companies_name_trgm` — Text search (requires pg_trgm extension)
6. `idx_companies_slug_trgm` — Text search (requires pg_trgm extension)

**Incorrect Indexes:**
- `uq_companies_name_ci` and `uq_companies_slug_ci` include `WHERE deleted_at IS NULL` (should be removed for hard deletion)
- `idx_companies_active` is partial index with WHERE clause (should be simple index per spec)

**Impact:** 
- Missing FK indexes: Poor JOIN performance for audit queries
- Missing created_at index: Poor sorting performance
- Missing composite index: Poor pagination performance with status filtering
- Missing trigram indexes: Poor text search performance

---

## 9. Model vs Migration Consistency

### ❌ CRITICAL — Model Correct, Migration Incorrect

**Model (`src/companies/models.py`):** ✅ **CORRECT**
- All profile fields present ✅
- No soft delete fields ✅
- FK constraints defined ✅
- All field types match spec ✅

**Migration (`001_initial_migration.py`):** ❌ **INCORRECT**
- Missing 8 profile fields ❌
- Contains soft delete fields (`deleted_at`, `deleted_by`) ❌
- Missing FK constraints for audit fields ❌

**Impact:** Database schema doesn't match model. Application will fail at runtime.

---

## 10. Summary of Issues

### Critical Issues (Must Fix)

1. **Missing Profile Fields in Migration**
   - 8 fields missing: description, address, city, state, country, postal_code, website, logo_url
   - **Action:** Create migration to add these fields

2. **Soft Delete Fields in Migration**
   - `deleted_at` and `deleted_by` should not exist (hard deletion per spec)
   - **Action:** Create migration to remove these columns

3. **Missing Foreign Key Constraints**
   - `created_by` and `updated_by` lack FK constraints
   - **Action:** Add FK constraints in migration

4. **Missing Required Indexes**
   - 6 indexes missing: created_by, updated_by, created_at, status_created composite, name_trgm, slug_trgm
   - **Action:** Create migration to add missing indexes

5. **Incorrect Index Definitions**
   - Case-insensitive unique indexes include WHERE deleted_at IS NULL (should be removed)
   - **Action:** Update indexes to remove WHERE clause

### Warnings (Should Fix)

1. **Model unique=True vs Case-Insensitive Requirement**
   - Model uses case-sensitive unique, but spec requires case-insensitive
   - **Impact:** Application must enforce case-insensitive uniqueness
   - **Status:** Acceptable if enforced at application level

---

## 11. Required Actions

### Immediate Actions (Before Deployment)

1. **Create Migration: Add Profile Fields**
   ```sql
   ALTER TABLE companies ADD COLUMN description VARCHAR(1000);
   ALTER TABLE companies ADD COLUMN address VARCHAR(255);
   ALTER TABLE companies ADD COLUMN city VARCHAR(100);
   ALTER TABLE companies ADD COLUMN state VARCHAR(100);
   ALTER TABLE companies ADD COLUMN country VARCHAR(100);
   ALTER TABLE companies ADD COLUMN postal_code VARCHAR(20);
   ALTER TABLE companies ADD COLUMN website VARCHAR(2048);
   ALTER TABLE companies ADD COLUMN logo_url VARCHAR(2048);
   ```

2. **Create Migration: Remove Soft Delete Fields**
   ```sql
   ALTER TABLE companies DROP COLUMN deleted_at;
   ALTER TABLE companies DROP COLUMN deleted_by;
   ```

3. **Create Migration: Add Foreign Key Constraints**
   ```sql
   ALTER TABLE companies 
     ADD CONSTRAINT fk_companies_created_by 
     FOREIGN KEY (created_by) REFERENCES users(id) 
     ON DELETE RESTRICT ON UPDATE CASCADE;
   
   ALTER TABLE companies 
     ADD CONSTRAINT fk_companies_updated_by 
     FOREIGN KEY (updated_by) REFERENCES users(id) 
     ON DELETE RESTRICT ON UPDATE CASCADE;
   ```

4. **Create Migration: Add Missing Indexes**
   ```sql
   CREATE INDEX idx_companies_created_by ON companies(created_by);
   CREATE INDEX idx_companies_updated_by ON companies(updated_by);
   CREATE INDEX idx_companies_created_at ON companies(created_at DESC);
   CREATE INDEX idx_companies_status_created ON companies(is_active, created_at DESC);
   ```

5. **Create Migration: Add Text Search Indexes**
   ```sql
   CREATE EXTENSION IF NOT EXISTS pg_trgm;
   CREATE INDEX idx_companies_name_trgm ON companies USING gin(name gin_trgm_ops);
   CREATE INDEX idx_companies_slug_trgm ON companies USING gin(slug gin_trgm_ops);
   ```

6. **Update Migration: Fix Case-Insensitive Unique Indexes**
   ```sql
   -- Drop existing indexes
   DROP INDEX IF EXISTS uq_companies_name_ci;
   DROP INDEX IF EXISTS uq_companies_slug_ci;
   
   -- Recreate without WHERE clause
   CREATE UNIQUE INDEX uq_companies_name ON companies(LOWER(name));
   CREATE UNIQUE INDEX uq_companies_slug ON companies(LOWER(slug));
   ```

---

## 12. Validation Checklist

| Category | Status | Notes |
|----------|--------|-------|
| **Naming Consistency** | ✅ PASS | All names match spec |
| **Missing Models** | ✅ PASS | Company model present |
| **Missing Fields (Model)** | ✅ PASS | All fields in model |
| **Missing Fields (Migration)** | ❌ FAIL | 8 profile fields missing |
| **Soft Delete Fields** | ❌ FAIL | deleted_at/deleted_by in migration |
| **Foreign Key Constraints** | ❌ FAIL | Missing FK for audit fields |
| **Primary Key** | ✅ PASS | Correct UUID PK |
| **Foreign Keys (Model)** | ✅ PASS | Correctly defined |
| **Foreign Keys (Migration)** | ❌ FAIL | Missing in migration |
| **ERD Relationships** | ✅ PASS | Matches specification |
| **Check Constraints** | ✅ PASS | is_active constraint present |
| **Unique Constraints** | ⚠️ WARNING | Case-insensitive required |
| **Indexes (Required)** | ❌ FAIL | 6 indexes missing |
| **Indexes (Incorrect)** | ❌ FAIL | WHERE clauses incorrect |
| **Model vs Migration** | ❌ FAIL | Significant mismatch |

---

## 13. Conclusion

**Overall Status:** ❌ **FAILED**

The Company model implementation is **correct** and matches F4_db_spec.md, but the **database migration is incomplete and incorrect**. The migration:

1. ❌ Missing 8 profile fields
2. ❌ Contains soft delete fields (should be hard deletion)
3. ❌ Missing foreign key constraints
4. ❌ Missing 6 required indexes
5. ⚠️ Has incorrect index definitions

**Recommendation:** Create comprehensive migration to:
1. Add missing profile fields
2. Remove soft delete fields
3. Add foreign key constraints
4. Add missing indexes
5. Fix incorrect index definitions

**Priority:** **CRITICAL** — Database schema must match specification before deployment.

---

**End of Validation Report**

