================================================================================
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                    DATABASE DESIGN DOCUMENT                               ║
║                                                                            ║
║                    office world                                            ║
║                    F-001 — User & Role Management                          ║
║                                                                            ║
║                    PostgreSQL Database Specification                       ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
================================================================================

================================================================================
SECTION 2 — DOCUMENT CONTROL
================================================================================

| Field                    | Value                                    |
|--------------------------|------------------------------------------|
| Document Title           | Database Design Document — office world  |
| Feature                  | F-001 — User & Role Management           |
| Version                  | 1.0                                      |
| Date                     | 2024                                     |
| Database System          | PostgreSQL                               |
| Architecture             | Microsoft Azure Data Architecture        |
| Normalization Level      | Third Normal Form (3NF)                   |
| Document Status          | Draft                                     |
| Prepared By              | Enterprise Database Architect             |
| Reviewed By              | TBD                                       |
| Approved By              | TBD                                       |

================================================================================
SECTION 3 — INTRODUCTION
================================================================================

3.1 Purpose

This document provides the complete database design specification for the 
office world platform's User & Role Management feature (F-001). It defines 
the physical data model, table structures, relationships, constraints, 
indexes, and normalization approach for managing users, companies, roles, 
and role assignments within a multi-tenant SaaS environment.

3.2 Scope

This specification covers:
- User entity with invitation-based onboarding lifecycle
- Company entity as tenant boundary
- Role entity with fixed permission definitions
- UserRoleAssignment entity linking users, roles, and companies
- Employee entity (optional relationship with users)
- Complete audit trail and soft-delete support
- Multi-tenancy isolation through company boundaries

3.3 Document Structure

This document is organized into 10 sections:
1. Cover Page
2. Document Control
3. Introduction
4. System Overview
5. Non-Functional Requirements
6. Logical Data Model
7. Physical Data Model (detailed table definitions)
8. Normalization Verification
9. Index Strategy
10. Entity Relationship Diagram (ERD)

3.4 Database Technology

- Database System: PostgreSQL
- Architecture: Microsoft Azure Data Architecture
- Normalization: Third Normal Form (3NF)
- Naming Convention: snake_case (lowercase with underscores)

================================================================================
SECTION 4 — SYSTEM OVERVIEW
================================================================================

4.1 Business Purpose

office world is a multi-tenant SaaS platform enabling invitation-based user 
onboarding with strict role-based access control, company boundaries, and 
lifecycle management for users across tenant organizations.

4.2 Core Business Rules

- All users are onboarded via invitations (no self-registration)
- Each user has exactly one role within one company (except SuperAdmin)
- Each company can have at most one CEO at any given time
- SuperAdmin users are not tied to any company
- Invitations are always tied to a role (and company, except SuperAdmin)
- Deactivated users cannot log in but retain historical data
- Managers cannot view salary or personal information
- Role-based visibility rules are consistently enforced

4.3 Key Entities

1. **User**: Platform identity with invitation lifecycle, activation status, 
   and credential management
2. **Company**: Tenant organization boundary with unique name and slug
3. **Role**: Fixed, predefined role with immutable code and JSON permissions
4. **UserRoleAssignment**: Active association linking user, role, and company
5. **Employee**: Optional employee record linked to user (SuperAdmin excluded)

4.4 Multi-Tenancy Strategy

Multi-tenancy is implemented through company boundaries:
- Company is the tenant isolation boundary
- UserRoleAssignment.company_id provides tenant context
- SuperAdmin users have NULL company_id for platform-wide access
- Application-level filtering enforces tenant isolation

================================================================================
SECTION 5 — NON-FUNCTIONAL REQUIREMENTS
================================================================================

5.1 Performance Requirements

- Support for high-volume user queries with pagination
- Efficient filtering by company, role, and status
- Fast lookup by email (unique identifier)
- Optimized JOINs for user-role-company relationships

5.2 Scalability Requirements

- No specific partitioning or sharding requirements at this stage
- Design supports future horizontal scaling if needed
- Index strategy optimized for common query patterns

5.3 Data Integrity Requirements

- Referential integrity enforced through foreign key constraints
- Unique constraints on email, company name, company slug, role code
- Check constraints for status fields and enumerated values
- Soft-delete preserves historical data

5.4 Audit Requirements

All tables include complete audit trail:
- created_at: Timestamp when record was created
- updated_at: Timestamp when record was last updated
- deleted_at: Timestamp when record was soft-deleted (NULL if active)
- created_by: User ID who created the record
- updated_by: User ID who last updated the record
- deleted_by: User ID who soft-deleted the record

5.5 Security Requirements

- Email addresses are immutable once set
- Role codes are immutable
- Soft-delete prevents data loss
- Foreign key constraints prevent orphaned records

5.6 Availability Requirements

- Standard PostgreSQL high-availability configurations apply
- No special clustering requirements specified

================================================================================
SECTION 6 — LOGICAL DATA MODEL
================================================================================

6.1 Entity Relationships

The logical data model consists of five main entities:

1. **User** (1) ←→ (1) **UserRoleAssignment**
   - Each user has exactly one active role assignment

2. **Company** (1) ←→ (*) **UserRoleAssignment**
   - Each company has many user role assignments
   - company_id is NULL for SuperAdmin users

3. **Role** (1) ←→ (*) **UserRoleAssignment**
   - Each role can be assigned to many users

4. **User** (1) ←→ (0..1) **Employee**
   - Each user may have zero or one employee record
   - SuperAdmin users do not have employee records

6.2 Key Business Rules

- User.email is unique and immutable
- Company.name and Company.slug are unique
- Role.code is unique and immutable
- UserRoleAssignment enforces one active assignment per user
- UserRoleAssignment.company_id is nullable (for SuperAdmin)
- Employee.user_id is unique (one employee record per user)

6.3 Data Flow

- User invitation creates User record with invitation fields
- User activation sets activate_at timestamp
- Role assignment creates/updates UserRoleAssignment
- Company assignment via UserRoleAssignment.company_id
- Soft-delete sets deleted_at timestamp (preserves data)

================================================================================
SECTION 7 — PHYSICAL DATA MODEL
================================================================================

### 7.1 Table: users

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique user identifier |
| email | VARCHAR(255) | No | No | No | - | NOT NULL, UNIQUE | User email address, unique identifier, immutable |
| first_name | VARCHAR(100) | No | No | Yes | NULL | - | User first name, set at activation, nullable until activated |
| last_name | VARCHAR(100) | No | No | Yes | NULL | - | User last name, set at activation, nullable until activated |
| is_active | BOOLEAN | No | No | No | false | NOT NULL | Login eligibility flag, false blocks authentication |
| invite_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Initial invitation timestamp, set on first invite |
| activate_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Activation timestamp, null until user activates account |
| expiry | TIMESTAMPTZ | No | No | Yes | NULL | - | Invitation expiry timestamp, reset on re-invite |
| token | VARCHAR(255) | No | No | Yes | NULL | - | Credential token for invite and password reset |
| reinvite_count | INTEGER | No | No | No | 0 | NOT NULL | Number of re-invitations, incremented on resend |
| last_reinvite_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Last re-invite timestamp, nullable |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted (NULL if active) |
| created_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who created the record |
| updated_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who last updated the record |
| deleted_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who soft-deleted the record |

**Foreign Key Constraints:**
- created_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- updated_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- deleted_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE

**Additional Constraints:**
- UNIQUE constraint on `email` (enforced at database level)
- CHECK constraint: `reinvite_count >= 0` (non-negative count)
- Business rule: `email` is immutable (enforced at application level)

---

### 7.2 Table: companies

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique company identifier |
| name | VARCHAR(255) | No | No | No | - | NOT NULL, UNIQUE | Company name, unique identifier |
| slug | VARCHAR(255) | No | No | No | - | NOT NULL, UNIQUE | URL-friendly company identifier, unique |
| is_active | BOOLEAN | No | No | No | true | NOT NULL | Company availability flag, false blocks access |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted (NULL if active) |
| created_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who created the record |
| updated_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who last updated the record |
| deleted_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who soft-deleted the record |

**Foreign Key Constraints:**
- created_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- updated_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- deleted_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE

**Additional Constraints:**
- UNIQUE constraint on `name` (enforced at database level)
- UNIQUE constraint on `slug` (enforced at database level)
- Business rule: Only one CEO per company (enforced at application level via UserRoleAssignment)

---

### 7.3 Table: roles

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique role identifier |
| name | VARCHAR(100) | No | No | No | - | NOT NULL | Role display name (e.g., CEO, HR, Manager, Employee) |
| code | VARCHAR(50) | No | No | No | - | NOT NULL, UNIQUE | System identifier for role, immutable |
| permissions | JSONB | No | No | No | '{}' | NOT NULL | JSON permission map, fixed in V1 |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted (NULL if active) |
| created_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who created the record |
| updated_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who last updated the record |
| deleted_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who soft-deleted the record |

**Foreign Key Constraints:**
- created_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- updated_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- deleted_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE

**Additional Constraints:**
- UNIQUE constraint on `code` (enforced at database level)
- Business rule: `code` is immutable (enforced at application level)
- Business rule: Roles are seeded/fixed in V1 (no dynamic creation)

---

### 7.4 Table: user_role_assignments

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique assignment identifier |
| user_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES users(id) | Assigned user, required |
| role_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES roles(id) | Assigned role, required |
| company_id | UUID | No | Yes | Yes | NULL | REFERENCES companies(id) | Context company, NULL for SuperAdmin |
| is_active | BOOLEAN | No | No | No | true | NOT NULL | Assignment status, one active per user |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted (NULL if active) |
| created_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who created the record |
| updated_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who last updated the record |
| deleted_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who soft-deleted the record |

**Foreign Key Constraints:**
- user_id → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- role_id → roles(id) ON DELETE RESTRICT ON UPDATE CASCADE
- company_id → companies(id) ON DELETE RESTRICT ON UPDATE CASCADE
- created_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- updated_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- deleted_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE

**Additional Constraints:**
- UNIQUE constraint on `user_id` WHERE `is_active = true` AND `deleted_at IS NULL` (one active assignment per user, enforced via partial unique index)
- Business rule: Only one CEO per company (enforced at application level)
- Business rule: SuperAdmin users have NULL company_id

---

### 7.5 Table: employees

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique employee identifier |
| user_id | UUID | No | Yes | No | - | NOT NULL, UNIQUE, REFERENCES users(id) | Associated user, one employee record per user |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted (NULL if active) |
| created_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who created the record |
| updated_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who last updated the record |
| deleted_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who soft-deleted the record |

**Foreign Key Constraints:**
- user_id → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- created_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- updated_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- deleted_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE

**Additional Constraints:**
- UNIQUE constraint on `user_id` (one employee record per user)
- Business rule: SuperAdmin users do not have employee records (enforced at application level)

================================================================================
SECTION 8 — NORMALIZATION
================================================================================

### 8.1 Normalization Verification

All tables are verified against Third Normal Form (3NF) requirements:

#### 8.1.1 Table: users

**First Normal Form (1NF):**
- [✓] All columns contain atomic values (no arrays, no comma-separated lists)
- [✓] Each column contains only one type of data
- [✓] Each column has a unique name
- [✓] Order of rows/columns doesn't matter
- [✓] No repeating groups of columns

**Second Normal Form (2NF):**
- [✓] Table is in 1NF
- [✓] All non-key columns depend on the entire primary key (id)
- [✓] No partial dependencies (single-column primary key)

**Third Normal Form (3NF):**
- [✓] Table is in 2NF
- [✓] No transitive dependencies (non-key columns depend directly on primary key)
- [✓] All non-key columns depend directly on the primary key

**Normalization Status:** ✓ COMPLIANT (3NF)

---

#### 8.1.2 Table: companies

**First Normal Form (1NF):**
- [✓] All columns contain atomic values
- [✓] Each column contains only one type of data
- [✓] Each column has a unique name
- [✓] Order of rows/columns doesn't matter
- [✓] No repeating groups of columns

**Second Normal Form (2NF):**
- [✓] Table is in 1NF
- [✓] All non-key columns depend on the entire primary key (id)
- [✓] No partial dependencies

**Third Normal Form (3NF):**
- [✓] Table is in 2NF
- [✓] No transitive dependencies
- [✓] All non-key columns depend directly on the primary key

**Normalization Status:** ✓ COMPLIANT (3NF)

---

#### 8.1.3 Table: roles

**First Normal Form (1NF):**
- [✓] All columns contain atomic values
- [✓] Each column contains only one type of data
- [✓] Each column has a unique name
- [✓] Order of rows/columns doesn't matter
- [✓] No repeating groups of columns

**Second Normal Form (2NF):**
- [✓] Table is in 1NF
- [✓] All non-key columns depend on the entire primary key (id)
- [✓] No partial dependencies

**Third Normal Form (3NF):**
- [✓] Table is in 2NF
- [✓] No transitive dependencies
- [✓] All non-key columns depend directly on the primary key

**Normalization Status:** ✓ COMPLIANT (3NF)

**Note:** `permissions` JSONB field stores structured data but is atomic at the column level, maintaining 1NF compliance.

---

#### 8.1.4 Table: user_role_assignments

**First Normal Form (1NF):**
- [✓] All columns contain atomic values
- [✓] Each column contains only one type of data
- [✓] Each column has a unique name
- [✓] Order of rows/columns doesn't matter
- [✓] No repeating groups of columns

**Second Normal Form (2NF):**
- [✓] Table is in 1NF
- [✓] All non-key columns depend on the entire primary key (id)
- [✓] No partial dependencies (single-column primary key)

**Third Normal Form (3NF):**
- [✓] Table is in 2NF
- [✓] No transitive dependencies
- [✓] All non-key columns depend directly on the primary key

**Normalization Status:** ✓ COMPLIANT (3NF)

**Note:** This junction table properly resolves the many-to-many relationship between users, roles, and companies, maintaining normalization.

---

#### 8.1.5 Table: employees

**First Normal Form (1NF):**
- [✓] All columns contain atomic values
- [✓] Each column contains only one type of data
- [✓] Each column has a unique name
- [✓] Order of rows/columns doesn't matter
- [✓] No repeating groups of columns

**Second Normal Form (2NF):**
- [✓] Table is in 1NF
- [✓] All non-key columns depend on the entire primary key (id)
- [✓] No partial dependencies

**Third Normal Form (3NF):**
- [✓] Table is in 2NF
- [✓] No transitive dependencies
- [✓] All non-key columns depend directly on the primary key

**Normalization Status:** ✓ COMPLIANT (3NF)

---

### 8.2 Denormalization Analysis

**No intentional denormalization** has been applied. All tables maintain strict 3NF compliance.

**Future Considerations:**
- If performance requires, consider materialized views for aggregated user statistics
- Audit/history tables (if needed) would intentionally denormalize for snapshot purposes

================================================================================
SECTION 9 — INDEX STRATEGY
================================================================================

### 9.1 Indexing Principles

- Every foreign key column has an index for JOIN performance
- Every table with `updated_at` has an index for incremental sync and change tracking
- Unique constraints use indexes automatically
- Composite indexes created for common query patterns
- Partial indexes for soft-delete filtering

### 9.2 Primary Key Indexes

All primary keys are automatically indexed by PostgreSQL. Explicit definitions:

```sql
CREATE UNIQUE INDEX pk_users ON users(id);
CREATE UNIQUE INDEX pk_companies ON companies(id);
CREATE UNIQUE INDEX pk_roles ON roles(id);
CREATE UNIQUE INDEX pk_user_role_assignments ON user_role_assignments(id);
CREATE UNIQUE INDEX pk_employees ON employees(id);
```

### 9.3 Foreign Key Indexes

**CRITICAL:** Every foreign key column MUST have an index for JOIN performance:

```sql
-- users table
CREATE INDEX idx_users_created_by ON users(created_by);
CREATE INDEX idx_users_updated_by ON users(updated_by);
CREATE INDEX idx_users_deleted_by ON users(deleted_by);

-- companies table
CREATE INDEX idx_companies_created_by ON companies(created_by);
CREATE INDEX idx_companies_updated_by ON companies(updated_by);
CREATE INDEX idx_companies_deleted_by ON companies(deleted_by);

-- roles table
CREATE INDEX idx_roles_created_by ON roles(created_by);
CREATE INDEX idx_roles_updated_by ON roles(updated_by);
CREATE INDEX idx_roles_deleted_by ON roles(deleted_by);

-- user_role_assignments table
CREATE INDEX idx_user_role_assignments_user_id ON user_role_assignments(user_id);
CREATE INDEX idx_user_role_assignments_role_id ON user_role_assignments(role_id);
CREATE INDEX idx_user_role_assignments_company_id ON user_role_assignments(company_id);
CREATE INDEX idx_user_role_assignments_created_by ON user_role_assignments(created_by);
CREATE INDEX idx_user_role_assignments_updated_by ON user_role_assignments(updated_by);
CREATE INDEX idx_user_role_assignments_deleted_by ON user_role_assignments(deleted_by);

-- employees table
CREATE INDEX idx_employees_user_id ON employees(user_id);
CREATE INDEX idx_employees_created_by ON employees(created_by);
CREATE INDEX idx_employees_updated_by ON employees(updated_by);
CREATE INDEX idx_employees_deleted_by ON employees(deleted_by);
```

### 9.4 Audit Field Indexes

**MANDATORY:** Every table with `updated_at` MUST have an index:

```sql
CREATE INDEX idx_users_updated_at ON users(updated_at);
CREATE INDEX idx_companies_updated_at ON companies(updated_at);
CREATE INDEX idx_roles_updated_at ON roles(updated_at);
CREATE INDEX idx_user_role_assignments_updated_at ON user_role_assignments(updated_at);
CREATE INDEX idx_employees_updated_at ON employees(updated_at);
```

### 9.5 Unique Constraint Indexes

Unique constraints automatically create indexes:

```sql
-- users table
CREATE UNIQUE INDEX uq_users_email ON users(email) WHERE deleted_at IS NULL;

-- companies table
CREATE UNIQUE INDEX uq_companies_name ON companies(name) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX uq_companies_slug ON companies(slug) WHERE deleted_at IS NULL;

-- roles table
CREATE UNIQUE INDEX uq_roles_code ON roles(code) WHERE deleted_at IS NULL;

-- user_role_assignments table
CREATE UNIQUE INDEX uq_user_role_assignments_user_active ON user_role_assignments(user_id) 
    WHERE is_active = true AND deleted_at IS NULL;

-- employees table
CREATE UNIQUE INDEX uq_employees_user_id ON employees(user_id) WHERE deleted_at IS NULL;
```

### 9.6 Composite Indexes

Composite indexes for common query patterns:

```sql
-- user_role_assignments: Filter by company and role
CREATE INDEX idx_user_role_assignments_company_role ON user_role_assignments(company_id, role_id) 
    WHERE deleted_at IS NULL;

-- user_role_assignments: Filter by company and active status
CREATE INDEX idx_user_role_assignments_company_active ON user_role_assignments(company_id, is_active) 
    WHERE deleted_at IS NULL;

-- users: Filter by active status and soft-delete
CREATE INDEX idx_users_active_not_deleted ON users(is_active) 
    WHERE deleted_at IS NULL;

-- users: Search by email (already unique, but useful for partial matches if needed)
-- Note: Full-text search on email would require pg_trgm extension
```

### 9.7 Soft Delete Indexes

Partial indexes for soft-delete filtering:

```sql
-- Active records only (all tables)
CREATE INDEX idx_users_active ON users(id) WHERE deleted_at IS NULL;
CREATE INDEX idx_companies_active ON companies(id) WHERE deleted_at IS NULL;
CREATE INDEX idx_roles_active ON roles(id) WHERE deleted_at IS NULL;
CREATE INDEX idx_user_role_assignments_active ON user_role_assignments(id) WHERE deleted_at IS NULL;
CREATE INDEX idx_employees_active ON employees(id) WHERE deleted_at IS NULL;

-- Status-based partial indexes
CREATE INDEX idx_companies_active_status ON companies(is_active) WHERE deleted_at IS NULL;
CREATE INDEX idx_user_role_assignments_active_status ON user_role_assignments(is_active) WHERE deleted_at IS NULL;
```

### 9.8 Text Search Indexes (Optional)

If full-text search is required on name fields, consider:

```sql
-- Requires: CREATE EXTENSION pg_trgm;
CREATE INDEX idx_users_email_trgm ON users USING gin(email gin_trgm_ops);
CREATE INDEX idx_companies_name_trgm ON companies USING gin(name gin_trgm_ops);
CREATE INDEX idx_users_first_name_trgm ON users USING gin(first_name gin_trgm_ops);
CREATE INDEX idx_users_last_name_trgm ON users USING gin(last_name gin_trgm_ops);
```

### 9.9 Index Summary

| Table | Primary Key | Foreign Keys | Unique | Composite | Soft Delete | Audit | Total |
|-------|-------------|--------------|--------|-----------|-------------|-------|-------|
| users | 1 | 3 | 1 | 1 | 1 | 1 | 8 |
| companies | 1 | 3 | 2 | 0 | 1 | 1 | 8 |
| roles | 1 | 3 | 1 | 0 | 1 | 1 | 7 |
| user_role_assignments | 1 | 6 | 1 | 2 | 1 | 1 | 13 |
| employees | 1 | 4 | 1 | 0 | 1 | 1 | 8 |

**Total Indexes:** 44 (excluding optional text search indexes)

================================================================================
SECTION 10 — ENTITY RELATIONSHIP DIAGRAM (ERD)
================================================================================

+----------------------+             +--------------------------+             +----------------------+
|        User          |   1    1    |   UserRoleAssignment     |   1    M    |        Role          |
+----------------------+             +--------------------------+             +----------------------+
| id (PK)              |<----------->| id (PK)                  |<----------->| id (PK)              |
+----------------------+             | user_id (FK)             |             +----------------------+
                                     | role_id (FK)             |
                                     | company_id (FK)          |
+----------------------+             +--------------------------+
|      Company         |   1    M    |
+----------------------+             |
| id (PK)              |<------------+
+----------------------+


+----------------------+             +--------------------------+
|        User          |   1   0..1  |       Employee           |
+----------------------+             +--------------------------+
| id (PK)              |<----------->| id (PK)                  |
+----------------------+             | user_id (FK)             |
                                     +--------------------------+


================================================================================
RELATIONSHIP CARDINALITY:
================================================================================

1. User 1..1 UserRoleAssignment
   - Each user has exactly one active role assignment

2. Company 1..* UserRoleAssignment
   - Each company has many user role assignments
   - company_id is NULL for SuperAdmin users

3. Role 1..* UserRoleAssignment
   - Each role can be assigned to many users

4. User 0..1 Employee
   - Each user may have zero or one employee record
   - SuperAdmin users do not have employee records

================================================================================
NOTES:
- UserRoleAssignment.company_id is nullable (NULL for SuperAdmin)
- UserRoleAssignment enforces one active assignment per user
- Employee relationship is optional (0..1)
- Only Primary Key (id) and Foreign Key fields are shown
- Business fields and audit fields are excluded per ERD rules
================================================================================

================================================================================
END OF DOCUMENT
================================================================================

