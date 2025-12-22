================================================================================
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                    DATABASE DESIGN SPECIFICATION                           ║
║                                                                            ║
║                      F-007 — Project Management                            ║
║                                                                            ║
║                          office world Platform                             ║
║                                                                            ║
║                         PostgreSQL Database Design                         ║
║                                                                            ║
║                    Microsoft Azure Data Architecture                       ║
║                    PostgreSQL 3NF Normalization                            ║
║                                                                            ║
║                              Version 1.0                                   ║
║                         Date: 2024-01-20                                   ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
================================================================================

================================================================================
                        SECTION 1 — COVER PAGE
================================================================================

╔════════════════════════════════════════════════════════════════════════════╗
║  Document Title:    Database Design Specification — F-007 Project          ║
║                     Management                                             ║
╠════════════════════════════════════════════════════════════════════════════╣
║  Project Name:      office world                                           ║
║  Feature:           F-007 — Project Management                             ║
║  Database System:   PostgreSQL                                              ║
║  Architecture:      Microsoft Azure Data Architecture                      ║
║  Normalization:     3NF (Third Normal Form)                                ║
║  Version:           1.0                                                     ║
║  Date:              2024-01-20                                             ║
║  Status:            Draft                                                   ║
╚════════════════════════════════════════════════════════════════════════════╝

================================================================================
                        SECTION 2 — DOCUMENT CONTROL
================================================================================

╔════════════════════════════════════════════════════════════════════════════╗
║  Document Control Information                                              ║
╠════════════════════════════════════════════════════════════════════════════╣
║  Document ID:       F7-DB-SPEC-001                                         ║
║  Version:           1.0                                                     ║
║  Date:              2024-01-20                                             ║
║  Author:            Database Architecture Team                             ║
║  Reviewer:          TBD                                                    ║
║  Approver:          TBD                                                    ║
║  Status:            Draft                                                  ║
║  Classification:   Internal                                                ║
╠════════════════════════════════════════════════════════════════════════════╣
║  Revision History                                                          ║
╠════════════════════════════════════════════════════════════════════════════╣
║  Version  Date        Author          Description                          ║
║  ───────  ──────────  ──────────────  ──────────────────────────────────── ║
║  1.0      2024-01-20  DB Team         Initial database design              ║
╚════════════════════════════════════════════════════════════════════════════╝

================================================================================
                        SECTION 3 — INTRODUCTION
================================================================================

### 3.1 Purpose

This document defines the database design specification for the Project Management 
feature (F-007) within the office world multi-tenant SaaS platform. The design 
follows Microsoft Azure Data Architecture principles, PostgreSQL 3NF normalization 
standards, and implements enterprise-grade patterns for multi-tenancy, audit logging, 
and soft deletion.

### 3.2 Scope

This specification covers the database schema for:

- **Project Management**: Lightweight, company-scoped project containers for organizing tasks
- **Project Lifecycle**: Status-based lifecycle management (ACTIVE, INACTIVE, COMPLETED)
- **Task Organization**: Projects group tasks into initiatives without explicit membership
- **Derived Visibility**: Project visibility derived from task associations

**Dependencies:**
- F-002 — RBAC & Permission Engine (role-based access control)
- F-008 — Task Management & Assignment (tasks table)
- Companies table (from core platform, tenant boundary)
- Multi-tenant architecture with company as tenant boundary

### 3.3 Document Structure

This document is organized into 10 sections:

1. Cover Page
2. Document Control
3. Introduction
4. System Overview
5. Non-Functional Requirements
6. Logical Data Model
7. Physical Data Model (complete table definitions)
8. Normalization Verification
9. Index Strategy
10. Professional ASCII ER Diagram

### 3.4 Design Principles

- **3NF Normalization**: All tables normalized to Third Normal Form
- **Multi-Tenancy**: Company-scoped data isolation via company_id
- **Soft Delete**: All tables support soft deletion for audit compliance (deleted_at)
- **Audit Trail**: Complete audit fields (created_at, updated_at, created_by, updated_by, deleted_at, deleted_by)
- **Referential Integrity**: Foreign key constraints with appropriate ON DELETE/ON UPDATE actions
- **Performance**: Comprehensive indexing strategy for foreign keys and audit fields
- **Data Integrity**: Company-unique project names (case-insensitive) enforced at database level

================================================================================
                        SECTION 4 — SYSTEM OVERVIEW
================================================================================

### 4.1 Business Purpose

The Project Management system provides lightweight, company-scoped project containers 
that:

- Organize tasks into initiatives without rigid membership or billing constructs
- Enable leadership to structure work by initiatives
- Preserve flexibility by keeping projects optional (tasks can exist without projects)
- Control project lifecycle through status management (ACTIVE, INACTIVE, COMPLETED)
- Derive visibility from task associations (no explicit project membership)

### 4.2 System Architecture

**Multi-Tenant SaaS Platform:**
- Tenant boundary: Company (organization)
- Data isolation: Row-level security via company_id
- Access control: Role-based (SuperAdmin, CEO, Manager, HR, Employee)

**Key Entities:**
- **projects**: Company-scoped project containers (1:M with companies, 1:M with tasks)
- **companies**: Tenant organizations (referenced, not defined in this feature)
- **tasks**: Work items that can be associated with projects (referenced from F-008)

### 4.3 Data Flow

1. **Project Creation**: CEO/Manager creates project within their company
2. **Task Association**: Tasks are assigned to projects (handled by F-008)
3. **Lifecycle Management**: Project status changes (ACTIVE → INACTIVE → COMPLETED)
4. **Visibility Derivation**: Employee visibility based on task assignments
5. **Soft Deletion**: Projects soft-deleted with cascade to associated tasks (application-level)

### 4.4 Business Rules

**Project Naming:**
- Project names must be unique within a company (case-insensitive)
- Minimum length: 1 character
- Maximum length: 255 characters

**Project Status:**
- **ACTIVE**: Project is editable; tasks can be added, moved, or removed
- **INACTIVE**: Project is frozen; no task changes allowed
- **COMPLETED**: Project is frozen and read-only; retained for reference
- Status transitions: No restrictions (can change to any status)

**Access Control:**
- **CEO/Manager**: Full access (create, read, update, delete all company projects)
- **HR**: Read-only access (view all company projects)
- **Employee**: Read-only access (view only projects with assigned tasks)

**Cascade Deletion:**
- Soft deletion of project cascades to associated tasks (application-level)
- Uses deleted_at timestamp for audit trail

**Company Scoping:**
- All projects are scoped to a company (company_id is required)
- Cross-company access is prevented by application-level authorization

================================================================================
                        SECTION 5 — NON-FUNCTIONAL REQUIREMENTS
================================================================================

### 5.1 Performance Requirements

- **Query Performance**: List projects with pagination, filtering, and sorting must complete within 200ms for up to 10,000 projects per company
- **Index Strategy**: Foreign keys and audit fields must be indexed for optimal query performance
- **Search Performance**: Project name search must support case-insensitive partial matching with GIN indexes

### 5.2 Scalability Requirements

- **Data Volume**: Support up to 1,000 projects per company
- **Concurrent Access**: Support up to 100 concurrent users per company
- **Growth**: Design must accommodate 10x growth in project count

### 5.3 Security Requirements

- **Multi-Tenancy**: Strict data isolation via company_id (row-level security)
- **Access Control**: Role-based access enforced at application level
- **Audit Trail**: Complete audit logging for all create, update, and delete operations
- **Soft Delete**: All deletions are soft deletes (deleted_at) for compliance

### 5.4 Data Integrity Requirements

- **Referential Integrity**: Foreign key constraints enforce company relationship
- **Uniqueness**: Company-unique project names enforced at database level (case-insensitive)
- **Status Validation**: Status enum values enforced via CHECK constraint
- **Null Constraints**: Required fields enforced via NOT NULL constraints

### 5.5 Availability Requirements

- **Uptime**: 99.9% availability target
- **Backup**: Daily automated backups with 30-day retention
- **Recovery**: Point-in-time recovery capability

### 5.6 Compliance Requirements

- **Audit Trail**: All changes tracked with created_by, updated_by, deleted_by
- **Soft Delete**: All deletions are soft deletes for audit compliance
- **Data Retention**: Deleted records retained indefinitely for audit purposes

================================================================================
                        SECTION 6 — LOGICAL DATA MODEL
================================================================================

### 6.1 Entity Overview

**projects**
- Represents a company-scoped container for organizing tasks
- No explicit membership or permissions
- Visibility derived from task associations
- Lifecycle controlled by status

### 6.2 Entity Relationships

**Company → Project (1:M)**
- One company can have many projects
- Project belongs to exactly one company
- Relationship: Required (company_id is NOT NULL)
- Foreign Key: projects.company_id → companies.id
- Action: ON DELETE RESTRICT (prevent orphan projects)
- Action: ON UPDATE CASCADE (propagate company ID changes)

**Project → Task (1:M)**
- One project can have many tasks
- Task may or may not belong to a project
- Relationship: Optional (project_id is NULLABLE in tasks table)
- Foreign Key: tasks.project_id → projects.id (defined in F-008)
- Action: ON DELETE RESTRICT (application handles soft-delete cascade)
- Action: ON UPDATE CASCADE (propagate project ID changes)

### 6.3 Entity Attributes

**projects**
- **id**: UUID primary key
- **company_id**: UUID foreign key to companies (required)
- **name**: VARCHAR(255) project name (required, company-unique, case-insensitive)
- **status**: VARCHAR(20) lifecycle state (required, enum: ACTIVE, INACTIVE, COMPLETED)
- **deleted_at**: TIMESTAMPTZ soft delete timestamp (nullable)
- **created_at**: TIMESTAMPTZ creation timestamp (required)
- **updated_at**: TIMESTAMPTZ last update timestamp (required)
- **created_by**: UUID user who created (nullable)
- **updated_by**: UUID user who last updated (nullable)
- **deleted_by**: UUID user who soft-deleted (nullable)

### 6.4 Business Constraints

**Uniqueness Constraints:**
- Project name must be unique within company (case-insensitive)
- Enforced via unique index: (company_id, LOWER(name)) WHERE deleted_at IS NULL

**Status Constraints:**
- Status must be one of: ACTIVE, INACTIVE, COMPLETED
- Enforced via CHECK constraint

**Referential Constraints:**
- company_id must reference existing company
- Enforced via FOREIGN KEY constraint

================================================================================
                        SECTION 7 — PHYSICAL DATA MODEL
================================================================================

### 7.1 Table: projects

**Description:**
Represents a company-scoped container used to organize tasks. Projects do not 
manage membership, permissions, or ownership. Access and visibility are derived 
entirely from task associations.

**Table Name:** `projects`

**Column Definitions:**

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique project identifier |
| company_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES companies(id) ON DELETE RESTRICT ON UPDATE CASCADE | Foreign key to companies table, required tenant boundary |
| name | VARCHAR(255) | No | No | No | - | NOT NULL | Project name, required, company-unique (case-insensitive) |
| status | VARCHAR(20) | No | No | No | 'ACTIVE' | NOT NULL, CHECK (status IN ('ACTIVE', 'INACTIVE', 'COMPLETED')) | Project lifecycle state, required, default ACTIVE |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Soft delete timestamp, NULL when active, set to current timestamp when deleted |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created (UTC) |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated (UTC) |
| created_by | UUID | No | No | Yes | NULL | - | User ID who created the record (CEO or Manager) |
| updated_by | UUID | No | No | Yes | NULL | - | User ID who last updated the record (CEO or Manager) |
| deleted_by | UUID | No | No | Yes | NULL | - | User ID who soft-deleted the record (CEO or Manager) |

**Foreign Key Constraints:**
- `fk_projects_company_id_companies`: 
  - `company_id` REFERENCES `companies(id)` 
  - ON DELETE RESTRICT (prevent deletion of company with active projects)
  - ON UPDATE CASCADE (propagate company ID changes)

**Additional Constraints:**
- **Unique Project Name per Company (Case-Insensitive):**
  - UNIQUE INDEX `uq_projects_company_name` ON `projects(company_id, LOWER(name))` 
  - WHERE `deleted_at IS NULL`
  - Ensures project names are unique within company (case-insensitive)
  - Only applies to non-deleted projects

- **Status Enum Check:**
  - CHECK constraint: `status IN ('ACTIVE', 'INACTIVE', 'COMPLETED')`
  - Enforces valid status values at database level

**Column Order:**
1. Primary Key (id)
2. Foreign Keys (company_id)
3. Business Fields (name, status)
4. Soft Delete Field (deleted_at)
5. Audit Fields (created_at, updated_at, created_by, updated_by, deleted_by)

**Table Creation SQL:**
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' 
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'COMPLETED')),
    deleted_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NULL,
    updated_by UUID NULL,
    deleted_by UUID NULL,
    
    CONSTRAINT fk_projects_company_id_companies 
        FOREIGN KEY (company_id) 
        REFERENCES companies(id) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE
);

-- Unique index for case-insensitive project name per company (active projects only)
CREATE UNIQUE INDEX uq_projects_company_name 
    ON projects(company_id, LOWER(name)) 
    WHERE deleted_at IS NULL;
```

================================================================================
                        SECTION 8 — NORMALIZATION VERIFICATION
================================================================================

### 8.1 Table: projects

**First Normal Form (1NF) Verification:**
- [x] All columns contain atomic values (no arrays, no comma-separated lists)
- [x] Each column contains only one type of data
- [x] Each column has a unique name
- [x] Order of rows/columns doesn't matter
- [x] No repeating groups of columns

**Result:** Table is in 1NF ✓

**Second Normal Form (2NF) Verification:**
- [x] Table is in 1NF
- [x] All non-key columns depend on the entire primary key (id)
- [x] No partial dependencies (single-column primary key, no composite key)

**Result:** Table is in 2NF ✓

**Third Normal Form (3NF) Verification:**
- [x] Table is in 2NF
- [x] No transitive dependencies (non-key columns don't depend on other non-key columns)
- [x] All non-key columns depend directly on the primary key

**Analysis:**
- `company_id` depends directly on `id` (project belongs to company)
- `name` depends directly on `id` (project name)
- `status` depends directly on `id` (project status)
- `deleted_at` depends directly on `id` (soft delete marker)
- All audit fields depend directly on `id` (project lifecycle events)

**Result:** Table is in 3NF ✓

**Normalization Summary:**
- **Current Form:** 3NF (Third Normal Form)
- **Denormalization:** None required
- **Performance Considerations:** Unique index on (company_id, LOWER(name)) for efficient uniqueness checks

================================================================================
                        SECTION 9 — INDEX STRATEGY
================================================================================

### 9.1 Primary Key Index

**Index:** `pk_projects`
- **Type:** UNIQUE INDEX (automatically created by PRIMARY KEY constraint)
- **Columns:** `id`
- **Purpose:** Enforce primary key uniqueness and optimize primary key lookups
- **SQL:**
```sql
-- Automatically created by PRIMARY KEY constraint
-- No explicit CREATE INDEX needed
```

### 9.2 Foreign Key Indexes

**Index:** `idx_projects_company_id`
- **Type:** B-tree INDEX
- **Columns:** `company_id`
- **Purpose:** Optimize JOINs with companies table and foreign key constraint checks
- **SQL:**
```sql
CREATE INDEX idx_projects_company_id ON projects(company_id);
```

**Rationale:** Foreign key columns MUST be indexed for optimal JOIN performance and referential integrity checks. This is critical for multi-tenant queries filtering by company_id.

### 9.3 Audit Field Indexes

**Index:** `idx_projects_updated_at`
- **Type:** B-tree INDEX
- **Columns:** `updated_at`
- **Purpose:** Essential for incremental sync, change tracking, ETag generation, and audit queries
- **SQL:**
```sql
CREATE INDEX idx_projects_updated_at ON projects(updated_at);
```

**Rationale:** The `updated_at` field is used for:
- ETag generation (conditional requests)
- Incremental data synchronization
- Change tracking and audit queries
- Sorting by last modified date

### 9.4 Unique Constraint Indexes

**Index:** `uq_projects_company_name`
- **Type:** UNIQUE INDEX (partial)
- **Columns:** `company_id, LOWER(name)`
- **Where Clause:** `WHERE deleted_at IS NULL`
- **Purpose:** Enforce case-insensitive unique project names within company (active projects only)
- **SQL:**
```sql
CREATE UNIQUE INDEX uq_projects_company_name 
    ON projects(company_id, LOWER(name)) 
    WHERE deleted_at IS NULL;
```

**Rationale:** 
- Partial unique index ensures uniqueness only for active (non-deleted) projects
- Case-insensitive comparison using LOWER() function
- Allows multiple deleted projects with same name to exist
- Efficient for uniqueness checks during INSERT/UPDATE operations

### 9.5 Composite Indexes for Common Query Patterns

**Index:** `idx_projects_company_status_active`
- **Type:** B-tree INDEX (partial)
- **Columns:** `company_id, status`
- **Where Clause:** `WHERE deleted_at IS NULL`
- **Purpose:** Optimize queries filtering by company and status (active projects only)
- **SQL:**
```sql
CREATE INDEX idx_projects_company_status_active 
    ON projects(company_id, status) 
    WHERE deleted_at IS NULL;
```

**Rationale:** Common query pattern: List active projects for a company. Partial index reduces index size and improves query performance.

**Index:** `idx_projects_company_created_at`
- **Type:** B-tree INDEX (partial)
- **Columns:** `company_id, created_at DESC`
- **Where Clause:** `WHERE deleted_at IS NULL`
- **Purpose:** Optimize queries sorting projects by creation date within company
- **SQL:**
```sql
CREATE INDEX idx_projects_company_created_at 
    ON projects(company_id, created_at DESC) 
    WHERE deleted_at IS NULL;
```

**Rationale:** Common query pattern: List projects for a company sorted by creation date (newest first). Partial index excludes deleted projects.

### 9.6 Text Search Indexes

**Index:** `idx_projects_name_trgm`
- **Type:** GIN INDEX (trigram)
- **Columns:** `name`
- **Purpose:** Optimize case-insensitive partial text search on project names
- **SQL:**
```sql
-- Requires pg_trgm extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX idx_projects_name_trgm 
    ON projects USING gin(name gin_trgm_ops);
```

**Rationale:** 
- Enables efficient case-insensitive partial matching (LIKE '%search%')
- Required for search functionality in project list endpoint
- GIN index provides fast text search performance

### 9.7 Soft Delete Indexes

**Index:** `idx_projects_active`
- **Type:** B-tree INDEX (partial)
- **Columns:** `id`
- **Where Clause:** `WHERE deleted_at IS NULL`
- **Purpose:** Optimize queries filtering active (non-deleted) projects
- **SQL:**
```sql
CREATE INDEX idx_projects_active 
    ON projects(id) 
    WHERE deleted_at IS NULL;
```

**Rationale:** Most queries filter out deleted projects. Partial index improves performance for active project queries.

### 9.8 Index Summary

| Index Name | Type | Columns | Where Clause | Purpose |
|------------|------|---------|--------------|---------|
| pk_projects | UNIQUE | id | - | Primary key enforcement |
| idx_projects_company_id | B-tree | company_id | - | Foreign key optimization |
| idx_projects_updated_at | B-tree | updated_at | - | Audit/ETag queries |
| uq_projects_company_name | UNIQUE | company_id, LOWER(name) | deleted_at IS NULL | Case-insensitive uniqueness |
| idx_projects_company_status_active | B-tree | company_id, status | deleted_at IS NULL | Company + status filtering |
| idx_projects_company_created_at | B-tree | company_id, created_at DESC | deleted_at IS NULL | Company + date sorting |
| idx_projects_name_trgm | GIN | name | - | Text search optimization |
| idx_projects_active | B-tree | id | deleted_at IS NULL | Active projects filtering |

### 9.9 Index Maintenance

**Monitoring:**
- Monitor index usage with `pg_stat_user_indexes`
- Review index bloat with `pg_stat_user_tables`
- Analyze query plans to ensure indexes are being used

**Maintenance:**
- Regular VACUUM and ANALYZE operations
- REINDEX for heavily updated indexes
- Consider partitioning if table grows beyond 1M rows per company

================================================================================
                        SECTION 10 — PROFESSIONAL ASCII ER DIAGRAM
================================================================================

**Entity Relationship Diagram (ERD)**
**Feature: F-007 — Project Management**
**Project: office world**

**Relationship Cardinality:**
- Company 1..* Project (One Company has many Projects)
- Project 0..* Task (One Project has zero or more Tasks)
- Task 0..1 Project (Task may or may not belong to a Project)

================================================================================

                    +------------------+              +------------------+
                    |    Companies     |     1    *   |    Projects      |
                    +------------------+<------------->+------------------+
                    | id (PK)          |              | id (PK)          |
                    +------------------+              | company_id (FK)   |
                                                      +------------------+
                                                              |
                                                              | 1
                                                              |
                                                              |
                                                              | *
                                                      +------------------+
                                                      |      Tasks       |
                                                      +------------------+
                                                      | id (PK)          |
                                                      | project_id (FK)  |
                                                      +------------------+

================================================================================

**Notes:**
- Projects belong to exactly one Company (company_id is NOT NULL)
- Tasks may exist without a Project (project_id is NULLABLE in tasks table)
- Projects can have zero or more Tasks
- Cascade deletion: Deleting a Project soft-deletes associated Tasks (application-level)
- All tables include audit fields (created_at, updated_at, created_by, updated_by, deleted_at, deleted_by)
- Projects table includes soft-delete marker (deleted_at)

**Foreign Key Relationships:**
- `projects.company_id` → `companies.id` (ON DELETE RESTRICT, ON UPDATE CASCADE)
- `tasks.project_id` → `projects.id` (defined in F-008, ON DELETE RESTRICT, ON UPDATE CASCADE)

================================================================================

**End of Database Design Specification**

