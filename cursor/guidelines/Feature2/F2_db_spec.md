================================================================================
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                    DATABASE DESIGN DOCUMENT                               ║
║                                                                            ║
║                    office world                                            ║
║                    F-002 — RBAC & Permission Engine                        ║
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
| Feature                  | F-002 — RBAC & Permission Engine         |
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
office world platform's RBAC & Permission Engine feature (F-002). It defines 
the database structures, relationships, indexes, and constraints used for 
permission evaluation, caching, and authorization enforcement within a 
multi-tenant SaaS environment.

**Important Note:** F-002 introduces **no new persisted entities**. This 
specification documents how F-002 uses existing database tables (roles, users, 
user_role_assignments, companies) for permission evaluation and caching.

3.2 Scope

This specification covers:
- Permission storage structure in `roles.permissions` JSONB column
- Permission evaluation queries using existing tables
- Index strategy for permission evaluation performance
- Cache invalidation triggers based on database changes
- Company-scoped permission evaluation patterns
- Multi-tenancy isolation for permission checks

3.3 Document Structure

This document is organized into 10 sections:
1. Cover Page
2. Document Control
3. Introduction
4. System Overview
5. Non-Functional Requirements
6. Logical Data Model
7. Physical Data Model (tables used by F-002)
8. Normalization Verification
9. Index Strategy
10. Entity Relationship Diagram (ERD)

3.4 Database Technology

- Database System: PostgreSQL
- Architecture: Microsoft Azure Data Architecture
- Normalization: Third Normal Form (3NF)
- Naming Convention: snake_case (lowercase with underscores)
- JSON Storage: JSONB for permission data

================================================================================
SECTION 4 — SYSTEM OVERVIEW
================================================================================

4.1 Business Purpose

office world is a multi-tenant SaaS platform enabling invitation-based user 
onboarding with strict role-based access control, company boundaries, and 
lifecycle management for users across tenant organizations.

F-002 (RBAC & Permission Engine) provides a centralized, deterministic 
authorization layer that enforces role-based access control consistently 
across all platform features using predefined roles, company scoping, and 
permission caching.

4.2 Core Business Rules

- Permissions are predefined and fixed in V1 (no dynamic permission creation)
- All non-SuperAdmin permissions are company-scoped
- Role inheritance is resolved at seed time (not runtime)
- Permission evaluation includes company_id match for non-SuperAdmin users
- SuperAdmin permissions are evaluated without company scope
- Permission cache is user-specific (keyed by user_id)
- Cache invalidation is near-real-time on role, user, or company changes
- Backend authorization is the source of truth
- Frontend permission checks are advisory only

4.3 Key Entities

F-002 uses existing database entities:

1. **Role**: Predefined permission container with JSONB permissions column
   - Stores resource-action mappings as JSONB
   - Role inheritance resolved at seed time
   - Immutable role codes

2. **User**: Platform identity with activation status
   - Used for permission evaluation context
   - Activation status affects permission computation

3. **UserRoleAssignment**: Links users to roles within company contexts
   - Provides company scoping for permission evaluation
   - company_id is NULL for SuperAdmin
   - One active assignment per user

4. **Company**: Tenant boundary for permission scoping
   - Company activation status affects permission evaluation
   - Inactive companies invalidate company-scoped permissions

**Non-Persisted Entities (Computed/Cached):**

5. **PermissionSet**: Computed effective permissions for a user
   - Computed from: Role.permissions + Company context + User activation
   - Not stored in database (computed at runtime)

6. **PermissionCache**: Cached representation of PermissionSet
   - Stored in Redis (not database)
   - Keyed by user_id
   - Automatically invalidated on relevant changes

4.4 Permission Model

**Resource-Action Structure:**
- **Resource**: Domain object being protected (e.g., `tasks`, `salary`, `users`, `employees`)
- **Action**: Operation performed on a resource (e.g., `create`, `read`, `update`, `delete`, `approve`)
- **Permission Format**: `{resource}:{action}` (e.g., `tasks:create`, `salary:read`)

**Permission Storage:**
- Permissions stored as JSONB in `roles.permissions` column
- Structure: `{"resource_name": ["action1", "action2", ...]}`
- Example: `{"tasks": ["create", "read", "update", "delete"], "salary": ["read"]}`

**Role Inheritance (Design-Time):**
- CEO permissions include Manager + Employee permissions
- HR permissions include Employee permissions
- Manager permissions include Employee permissions
- Inheritance resolved at seed time (not runtime)

================================================================================
SECTION 5 — NON-FUNCTIONAL REQUIREMENTS
================================================================================

5.1 Performance Requirements

- Permission evaluation queries must complete in < 200ms (including cache miss)
- Cached permission retrieval must complete in < 50ms
- Efficient JOINs for user-role-company relationships
- Fast lookup of role permissions by role_id
- Optimized JSONB queries on roles.permissions column

5.2 Scalability Requirements

- Permission cache stored in Redis (not database) for horizontal scaling
- Database indexes support high-volume permission evaluation queries
- No specific partitioning or sharding requirements at this stage
- Design supports future horizontal scaling if needed

5.3 Data Integrity Requirements

- Referential integrity enforced through foreign key constraints
- Unique constraints on role.code
- JSONB structure validation at application level
- Soft-delete preserves historical data for audit

5.4 Audit Requirements

All tables include complete audit trail:
- created_at: Timestamp when record was created
- updated_at: Timestamp when record was last updated
- deleted_at: Timestamp when record was soft-deleted (NULL if active)
- created_by: User ID who created the record
- updated_by: User ID who last updated the record
- deleted_by: User ID who soft-deleted the record

5.5 Security Requirements

- Role codes are immutable
- Permissions are predefined and fixed in V1
- Company scoping enforced for all non-SuperAdmin permissions
- Soft-delete prevents data loss
- Foreign key constraints prevent orphaned records

5.6 Cache Invalidation Requirements

Permission cache must be invalidated on:
- User role change (user_role_assignments.role_id update)
- User activation/deactivation (users.is_active update)
- User company reassignment (user_role_assignments.company_id update)
- Company deactivation (companies.is_active update)

5.7 Availability Requirements

- Standard PostgreSQL high-availability configurations apply
- Redis cache for permission data (separate from database)
- No special clustering requirements specified

================================================================================
SECTION 6 — LOGICAL DATA MODEL
================================================================================

6.1 Entity Relationships

F-002 uses existing database relationships for permission evaluation:

1. **User (1) ←→ (1) UserRoleAssignment**
   - Each user has exactly one active role assignment
   - Provides role and company context for permission evaluation

2. **Role (1) ←→ (M) UserRoleAssignment**
   - Each role can be assigned to many users
   - Role contains permissions as JSONB in roles.permissions column

3. **Company (1) ←→ (M) UserRoleAssignment**
   - Each company has many user role assignments
   - company_id is NULL for SuperAdmin (no company scope)
   - Company context enables permission scoping

6.2 Permission Evaluation Flow

1. **User Context Resolution:**
   - User → UserRoleAssignment (active assignment)
   - UserRoleAssignment → Role (permission container)
   - UserRoleAssignment → Company (scoping boundary)

2. **Permission Retrieval:**
   - Extract permissions from roles.permissions JSONB column
   - Apply company scoping (if not SuperAdmin)
   - Check user activation status
   - Check company activation status

3. **PermissionSet Computation:**
   - Combine role permissions with company context
   - Filter by user/company activation status
   - Return resource-action mapping

4. **Cache Storage:**
   - Store computed PermissionSet in Redis
   - Key: `permission:user:{user_id}`
   - TTL: Until invalidation (no time-based expiration)

6.3 Key Business Rules

- Permissions are stored as JSONB in roles.permissions (not separate table)
- Role inheritance is resolved at seed time (permissions pre-computed)
- Company scoping applied at evaluation time (not stored)
- Permission cache is user-specific (one cache entry per user)
- Cache invalidation triggered by database changes (via application logic)

================================================================================
SECTION 7 — PHYSICAL DATA MODEL
================================================================================

**Note:** F-002 introduces no new persisted entities. This section documents 
the existing tables that F-002 uses for permission evaluation, focusing on 
permission-related aspects.

### 7.1 Table: roles

**Purpose:** Stores predefined roles with permission definitions as JSONB.

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique role identifier |
| name | VARCHAR(100) | No | No | No | - | NOT NULL | Role display name (e.g., CEO, HR, Manager, Employee) |
| code | VARCHAR(50) | No | No | No | - | NOT NULL, UNIQUE, CHECK (code IN ('superadmin', 'ceo', 'hr', 'manager', 'employee')) | System identifier for role, immutable, case-sensitive enum |
| permissions | JSONB | No | No | No | '{}' | NOT NULL | JSON permission map, resource-action structure |
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
- CHECK constraint: `code IN ('superadmin', 'ceo', 'hr', 'manager', 'employee')` (enforced at database level, case-sensitive)
- Business rule: `code` is immutable (enforced at application level)
- Business rule: `code` matching is case-sensitive (e.g., 'CEO' ≠ 'ceo')
- Business rule: Roles are seeded/fixed in V1 (no dynamic creation)
- Business rule: `permissions` JSONB structure validated at application level

**Permission JSONB Structure:**
```json
{
  "tasks": ["create", "read", "update", "delete"],
  "salary": ["read"],
  "users": ["create", "read", "update"],
  "employees": ["create", "read", "update", "delete"],
  "leaves": ["create", "read", "approve"],
  "attendance": ["create", "read", "update"]
}
```

**Permission Evaluation:**
- Permissions are retrieved via: `SELECT permissions FROM roles WHERE id = ?`
- JSONB queries support efficient permission lookups
- GIN index on permissions column enables fast JSONB queries

---

### 7.2 Table: users

**Purpose:** Platform user identity with activation status affecting permission evaluation.

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique user identifier |
| email | VARCHAR(255) | No | No | No | - | NOT NULL, UNIQUE | User email address, unique identifier |
| first_name | VARCHAR(100) | No | No | Yes | NULL | - | User first name |
| last_name | VARCHAR(100) | No | No | Yes | NULL | - | User last name |
| is_active | BOOLEAN | No | No | No | false | NOT NULL | Login eligibility flag, affects permission evaluation |
| invite_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Initial invitation timestamp |
| activate_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Activation timestamp |
| expiry | TIMESTAMPTZ | No | No | Yes | NULL | - | Invitation expiry timestamp |
| token | VARCHAR(255) | No | No | Yes | NULL | - | Credential token for invite and password reset |
| reinvite_count | INTEGER | No | No | No | 0 | NOT NULL | Number of re-invitations |
| last_reinvite_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Last re-invite timestamp |
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
- Business rule: `is_active = false` results in empty PermissionSet
- Business rule: Cache invalidation triggered on `is_active` updates

**Permission Evaluation Impact:**
- `is_active = false` → Returns empty PermissionSet `{}`
- User activation/deactivation triggers permission cache invalidation

---

### 7.3 Table: user_role_assignments

**Purpose:** Links users to roles within company contexts, providing permission evaluation context.

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
- company_id → companies(id) ON DELETE CASCADE ON UPDATE CASCADE
- created_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- updated_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- deleted_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE

**Additional Constraints:**
- UNIQUE constraint on `user_id` WHERE `is_active = true` AND `deleted_at IS NULL` (one active assignment per user, enforced via partial unique index)
- Business rule: SuperAdmin users have NULL company_id
- Business rule: Role change triggers permission cache invalidation
- Business rule: Company reassignment triggers permission cache invalidation

**Permission Evaluation Impact:**
- `role_id` → Links to roles.permissions JSONB column
- `company_id` → Provides company scoping (NULL for SuperAdmin)
- Updates to `role_id`, `company_id`, or `is_active` trigger cache invalidation

---

### 7.4 Table: companies

**Purpose:** Tenant boundary providing company context for permission scoping.

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique company identifier |
| name | VARCHAR(255) | No | No | No | - | NOT NULL, UNIQUE | Company name, unique identifier |
| slug | VARCHAR(255) | No | No | No | - | NOT NULL, UNIQUE | URL-friendly company identifier, unique |
| is_active | BOOLEAN | No | No | No | true | NOT NULL | Company availability flag, affects permission evaluation |
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
- UNIQUE constraint on `name` (enforced at database level, case-insensitive)
- UNIQUE constraint on `slug` (enforced at database level, case-insensitive)
- Case-insensitive uniqueness: Use `CREATE UNIQUE INDEX uq_companies_slug_ci ON companies(LOWER(slug))` for case-insensitive slug uniqueness
- Business rule: `is_active = false` invalidates all company-scoped permissions
- Business rule: Company deactivation triggers permission cache invalidation for all company users

**Permission Evaluation Impact:**
- `is_active = false` → Returns empty PermissionSet `{}` for all company-scoped users
- Company deactivation triggers cache invalidation for all users in that company

================================================================================
SECTION 8 — NORMALIZATION
================================================================================

### 8.1 Normalization Verification

**Note:** F-002 uses existing normalized tables. This section verifies normalization 
for tables used by F-002.

#### 8.1.1 Table: roles

**First Normal Form (1NF):**
- ✅ All columns contain atomic values
- ✅ Each column contains only one type of data
- ✅ Each column has a unique name
- ✅ Order of rows/columns doesn't matter
- ✅ No repeating groups of columns
- ✅ JSONB permissions column stores structured data (acceptable for JSONB)

**Second Normal Form (2NF):**
- ✅ Table is in 1NF
- ✅ All non-key columns depend on the entire primary key (id)
- ✅ No partial dependencies (single-column primary key)

**Third Normal Form (3NF):**
- ✅ Table is in 2NF
- ✅ No transitive dependencies
- ✅ All non-key columns depend directly on the primary key
- ✅ JSONB permissions column is acceptable (structured data storage)

**Status: ✅ PASS** - Table is in 3NF

#### 8.1.2 Table: users

**First Normal Form (1NF):**
- ✅ All columns contain atomic values
- ✅ Each column contains only one type of data
- ✅ Each column has a unique name
- ✅ Order of rows/columns doesn't matter
- ✅ No repeating groups of columns

**Second Normal Form (2NF):**
- ✅ Table is in 1NF
- ✅ All non-key columns depend on the entire primary key (id)
- ✅ No partial dependencies (single-column primary key)

**Third Normal Form (3NF):**
- ✅ Table is in 2NF
- ✅ No transitive dependencies
- ✅ All non-key columns depend directly on the primary key

**Status: ✅ PASS** - Table is in 3NF

#### 8.1.3 Table: user_role_assignments

**First Normal Form (1NF):**
- ✅ All columns contain atomic values
- ✅ Each column contains only one type of data
- ✅ Each column has a unique name
- ✅ Order of rows/columns doesn't matter
- ✅ No repeating groups of columns

**Second Normal Form (2NF):**
- ✅ Table is in 1NF
- ✅ All non-key columns depend on the entire primary key (id)
- ✅ No partial dependencies (single-column primary key)

**Third Normal Form (3NF):**
- ✅ Table is in 2NF
- ✅ No transitive dependencies
- ✅ All non-key columns depend directly on the primary key

**Status: ✅ PASS** - Table is in 3NF

#### 8.1.4 Table: companies

**First Normal Form (1NF):**
- ✅ All columns contain atomic values
- ✅ Each column contains only one type of data
- ✅ Each column has a unique name
- ✅ Order of rows/columns doesn't matter
- ✅ No repeating groups of columns

**Second Normal Form (2NF):**
- ✅ Table is in 1NF
- ✅ All non-key columns depend on the entire primary key (id)
- ✅ No partial dependencies (single-column primary key)

**Third Normal Form (3NF):**
- ✅ Table is in 2NF
- ✅ No transitive dependencies
- ✅ All non-key columns depend directly on the primary key

**Status: ✅ PASS** - Table is in 3NF

### 8.2 Acceptable Denormalization

**JSONB Permissions Column:**
- **Rationale:** Storing permissions as JSONB in roles.permissions is acceptable 
  because:
  - Permissions are fixed and predefined in V1
  - No separate permission table needed (reduces JOIN complexity)
  - JSONB provides efficient querying and indexing
  - Role inheritance is resolved at seed time (not runtime)
  - Performance benefit: Single query retrieves all permissions for a role

**Status: ✅ ACCEPTABLE** - Documented denormalization with clear performance reasoning

================================================================================
SECTION 9 — INDEX STRATEGY
================================================================================

### 9.1 Primary Key Indexes

All primary keys are automatically indexed by PostgreSQL:

```sql
-- Automatically created by PostgreSQL
CREATE UNIQUE INDEX pk_roles ON roles(id);
CREATE UNIQUE INDEX pk_users ON users(id);
CREATE UNIQUE INDEX pk_user_role_assignments ON user_role_assignments(id);
CREATE UNIQUE INDEX pk_companies ON companies(id);
```

### 9.2 Foreign Key Indexes (CRITICAL)

**Every foreign key column MUST have an index for JOIN performance:**

```sql
-- user_role_assignments foreign keys
CREATE INDEX idx_user_role_assignments_user_id ON user_role_assignments(user_id);
CREATE INDEX idx_user_role_assignments_role_id ON user_role_assignments(role_id);
CREATE INDEX idx_user_role_assignments_company_id ON user_role_assignments(company_id);

-- roles audit fields (if used in queries)
CREATE INDEX idx_roles_created_by ON roles(created_by);
CREATE INDEX idx_roles_updated_by ON roles(updated_by);

-- users audit fields (if used in queries)
CREATE INDEX idx_users_created_by ON users(created_by);
CREATE INDEX idx_users_updated_by ON users(updated_by);

-- user_role_assignments audit fields (if used in queries)
CREATE INDEX idx_user_role_assignments_created_by ON user_role_assignments(created_by);
CREATE INDEX idx_user_role_assignments_updated_by ON user_role_assignments(updated_by);

-- companies audit fields (if used in queries)
CREATE INDEX idx_companies_created_by ON companies(created_by);
CREATE INDEX idx_companies_updated_by ON companies(updated_by);
```

### 9.3 Audit Field Indexes (MANDATORY)

**Every table with updated_at MUST have an index:**

```sql
-- Essential for incremental sync, change tracking, and audit queries
CREATE INDEX idx_roles_updated_at ON roles(updated_at);
CREATE INDEX idx_users_updated_at ON users(updated_at);
CREATE INDEX idx_user_role_assignments_updated_at ON user_role_assignments(updated_at);
CREATE INDEX idx_companies_updated_at ON companies(updated_at);
```

### 9.4 Permission Evaluation Indexes

**Indexes optimized for permission evaluation queries:**

```sql
-- Active user role assignment lookup (most common permission query)
CREATE UNIQUE INDEX idx_user_role_assignments_active_user 
ON user_role_assignments(user_id) 
WHERE is_active = true AND deleted_at IS NULL;

-- Role permissions lookup
CREATE INDEX idx_roles_code ON roles(code) WHERE deleted_at IS NULL;

-- Company-scoped permission queries
CREATE INDEX idx_user_role_assignments_company_active 
ON user_role_assignments(company_id, is_active) 
WHERE deleted_at IS NULL AND company_id IS NOT NULL;

-- User activation status lookup
CREATE INDEX idx_users_active ON users(id, is_active) WHERE deleted_at IS NULL;

-- Company activation status lookup
CREATE INDEX idx_companies_active ON companies(id, is_active) WHERE deleted_at IS NULL;
```

### 9.5 JSONB Indexes (GIN)

**GIN index on permissions JSONB column for efficient permission queries:**

```sql
-- Enable pg_trgm extension for text search (if needed)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- GIN index on permissions JSONB column
CREATE INDEX idx_roles_permissions_gin ON roles USING gin(permissions);

-- Alternative: GIN index on specific JSONB paths (if querying specific resources)
-- CREATE INDEX idx_roles_permissions_tasks ON roles USING gin((permissions->'tasks'));
```

### 9.6 Soft Delete Indexes

**Partial indexes excluding soft-deleted records:**

```sql
-- Active roles only
CREATE INDEX idx_roles_active ON roles(id) WHERE deleted_at IS NULL;

-- Active users only
CREATE INDEX idx_users_active_only ON users(id) WHERE deleted_at IS NULL;

-- Active user role assignments only
CREATE INDEX idx_user_role_assignments_active ON user_role_assignments(id) 
WHERE deleted_at IS NULL;

-- Active companies only
CREATE INDEX idx_companies_active_only ON companies(id) WHERE deleted_at IS NULL;
```

### 9.7 Composite Indexes

**Composite indexes for common permission evaluation query patterns:**

```sql
-- Permission evaluation query: Get user's role and company context
CREATE INDEX idx_user_role_assignments_evaluation 
ON user_role_assignments(user_id, role_id, company_id, is_active) 
WHERE deleted_at IS NULL AND is_active = true;

-- Cache invalidation query: Find all users for a company
CREATE INDEX idx_user_role_assignments_company_users 
ON user_role_assignments(company_id, user_id) 
WHERE deleted_at IS NULL AND is_active = true AND company_id IS NOT NULL;

-- Cache invalidation query: Find all users with a specific role
CREATE INDEX idx_user_role_assignments_role_users 
ON user_role_assignments(role_id, user_id) 
WHERE deleted_at IS NULL AND is_active = true;
```

### 9.8 Unique Constraints as Indexes

**Partial unique indexes for business rules:**

```sql
-- One active role assignment per user (already defined as constraint)
-- Automatically creates index: uq_user_role_assignments_user_active

-- Unique role code (already defined as constraint)
-- Automatically creates index: uq_roles_code

-- Unique user email (already defined as constraint)
-- Automatically creates index: uq_users_email

-- Unique company name (case-insensitive)
CREATE UNIQUE INDEX uq_companies_name_ci ON companies(LOWER(name)) WHERE deleted_at IS NULL;

-- Unique company slug (case-insensitive)
CREATE UNIQUE INDEX uq_companies_slug_ci ON companies(LOWER(slug)) WHERE deleted_at IS NULL;
```

### 9.9 Index Maintenance

**Monitor index usage:**
```sql
-- Check index usage statistics
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

**Index Recommendations:**
- Monitor `idx_roles_permissions_gin` usage for JSONB queries
- Monitor `idx_user_role_assignments_active_user` for permission evaluation
- Consider dropping unused indexes to reduce write overhead

================================================================================
SECTION 10 — ENTITY RELATIONSHIP DIAGRAM (ERD)
================================================================================

**Note:** F-002 introduces no new persisted entities. This ERD shows the 
existing relationships used by F-002 for permission evaluation.

+--------------------+             +--------------------------+             +--------------------+
|       users        |   1     1   |  user_role_assignments   |   M     1   |       roles        |
+--------------------+             +--------------------------+             +--------------------+
| id (PK)            |<----------->| id (PK)                  |<------------>| id (PK)            |
|                    |             | user_id (FK)             |              |                    |
|                    |             | role_id (FK)             |              |                    |
|                    |             | company_id (FK)          |              |                    |
+--------------------+             +--------------------------+             +--------------------+
                                            ^
                                            | M
                                            |
                                            | 1
                                            |
+--------------------+                      |
|     companies      |                      |
+--------------------+                      |
| id (PK)            |<---------------------+
|                    |
+--------------------+

================================================================================
RELATIONSHIP CARDINALITY:
================================================================================

1. User (1) ←→ (1) UserRoleAssignment
   - Each user has exactly one active role assignment at a time
   - Enforced by unique constraint: (user_id) WHERE is_active = true AND deleted_at IS NULL

2. Role (1) ←→ (M) UserRoleAssignment
   - Each role can be assigned to many users across different companies
   - Permissions stored as JSONB in roles.permissions column

3. Company (1) ←→ (M) UserRoleAssignment
   - Each company has many user role assignments
   - company_id is NULL for SuperAdmin users (global access)
   - Company scoping enables permission evaluation boundaries

================================================================================
PERMISSION EVALUATION FLOW:
================================================================================

1. User → UserRoleAssignment → Role
   - User's active assignment links to their role
   - Role contains permissions as JSONB (resource → actions mapping)

2. UserRoleAssignment.company_id
   - Provides company context for permission scoping
   - NULL for SuperAdmin (no company scope)
   - UUID for company-scoped users (permissions evaluated within company)

3. PermissionSet Computation (Runtime, Not Persisted)
   - Computed from: Role.permissions (JSONB) + Company context + User activation status
   - Cached in Redis (PermissionCache) keyed by user_id
   - Automatically invalidated on role/user/company changes

================================================================================
NOTES:
================================================================================

- Only Primary Key (id) and Foreign Key fields are shown per ERD rules
- Business fields (name, email, permissions JSONB, etc.) are excluded
- Audit fields (created_at, updated_at, etc.) are excluded
- PermissionSet and PermissionCache are NOT shown (computed/cached, not persisted)
- Permissions are stored as JSONB in roles.permissions column (not a separate table)
- Role inheritance is resolved at seed time (not runtime, not shown in ERD)

================================================================================

