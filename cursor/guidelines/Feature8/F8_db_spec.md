================================================================================
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                    DATABASE DESIGN SPECIFICATION                           ║
║                                                                            ║
║                      F-008 — Task Management                              ║
║                                                                            ║
║                          office world Platform                             ║
║                                                                            ║
║                         PostgreSQL Database Design                         ║
║                                                                            ║
║                    Microsoft Azure Data Architecture                       ║
║                    PostgreSQL 3NF Normalization                           ║
║                                                                            ║
║                              Version 1.0                                  ║
║                         Date: 2024-01-20                                  ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
================================================================================

================================================================================
                        SECTION 1 — COVER PAGE
================================================================================

╔════════════════════════════════════════════════════════════════════════════╗
║  Document Title:    Database Design Specification — F-008 Task             ║
║                     Management                                              ║
╠════════════════════════════════════════════════════════════════════════════╣
║  Project Name:      office world                                            ║
║  Feature:           F-008 — Task Management                               ║
║  Database System:    PostgreSQL                                             ║
║  Architecture:       Microsoft Azure Data Architecture                     ║
║  Normalization:      3NF (Third Normal Form)                               ║
║  Version:            1.0                                                    ║
║  Date:               2024-01-20                                             ║
║  Status:             Draft                                                   ║
╚════════════════════════════════════════════════════════════════════════════╝

================================================================================
                        SECTION 2 — DOCUMENT CONTROL
================================================================================

╔════════════════════════════════════════════════════════════════════════════╗
║  Document Control Information                                              ║
╠════════════════════════════════════════════════════════════════════════════╣
║  Document ID:       F8-DB-SPEC-001                                         ║
║  Version:           1.0                                                     ║
║  Date:              2024-01-20                                             ║
║  Author:            Database Architecture Team                            ║
║  Reviewer:          TBD                                                    ║
║  Approver:          TBD                                                    ║
║  Status:            Draft                                                  ║
║  Classification:    Internal                                                ║
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

This document defines the database design specification for the Task Management & Assignment 
feature (F-008) within the office world multi-tenant SaaS platform. The design follows 
Microsoft Azure Data Architecture principles, PostgreSQL 3NF normalization standards, and 
implements enterprise-grade patterns for multi-tenancy, audit logging, and hard deletion.

### 3.2 Scope

This specification covers the database schema for:

- **Task Management**: Atomic units of work within a company with immutable ownership
- **Task Assignment**: Multi-assignee support with granular permissions (VIEWER, EDITOR)
- **Task Lifecycle**: Status-based lifecycle management (TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED)
- **Project Integration**: Optional task linkage to projects without inheriting project visibility
- **Hard Deletion**: Permanent task removal with cascade deletion of assignments

**Dependencies:**
- F-002 — RBAC & Permission Engine (role-based access control)
- F-003 — Notifications System (task event notifications)
- F-007 — Project Management (projects table for optional task linkage)
- Companies table (from core platform, tenant boundary)
- Employees table (from F-005, task owners and assignees)
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
10. Entity Relationship Diagram (ERD)

================================================================================
                        SECTION 4 — SYSTEM OVERVIEW
================================================================================

### 4.1 Business Context

The Task Management feature provides a focused, execution-oriented task system where work 
is created, owned, assigned, and completed with strict ownership rules, fine-grained 
assignment permissions, and clear visibility boundaries. Tasks are independent units of work 
that may optionally belong to projects, without inheriting project visibility.

### 4.2 Key Business Rules

**Task Ownership:**
- Each task has exactly one owner, set at creation (immutable)
- Task owner is automatically set to authenticated user (task creator)
- Task owner cannot be changed after creation
- Task owner has full control: edit, change status, manage assignments, delete

**Task Assignment:**
- Tasks support multiple assignees via TaskAssignment junction table
- Each assignment has a permission level: VIEWER or EDITOR
- VIEWER: Can view task only (read-only access)
- EDITOR: Can edit task name, description, and change task status
- Editors cannot: add/remove assignees, remove themselves, delete task
- UNIQUE constraint prevents duplicate assignments (same employee assigned twice to same task)

**Task Status Lifecycle:**
- Status values: TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED
- Owner and Editor can move task to any status at any time
- DONE and CANCELLED are terminal states (task becomes read-only)

**Project Integration:**
- Tasks can optionally belong to a project (project_id nullable)
- Task visibility is task-based, not project-based
- Tasks do not inherit project visibility or permissions

**Deletion Strategy:**
- Hard deletion only (no soft delete)
- When task is deleted, all task assignments are automatically deleted (CASCADE)
- Deleted tasks are permanently removed (is_deleted = true)
- Deleted tasks are excluded from all queries

**Multi-Tenancy:**
- Tasks are company-scoped (company_id required)
- All task operations are filtered by company context from JWT token
- Company deletion cascades to tasks and task assignments

### 4.3 Data Flow

- Task creation creates Task record with required fields (name, company_id, owner_id)
- Task owner is set to authenticated user (immutable)
- Initial task status must be TODO
- Task assignments are created via TaskAssignment records
- Task status changes update status field (owner or editor)
- Task deletion sets is_deleted = true and cascades to task assignments
- Company deletion cascades to all company tasks and assignments

================================================================================
                        SECTION 5 — NON-FUNCTIONAL REQUIREMENTS
================================================================================

### 5.1 Performance Requirements

- Support for high-volume task queries with pagination
- Efficient filtering by status, project_id, owner_id, company_id
- Fast search by task name (case-insensitive partial match)
- Optimized queries for role-based visibility (CEO/Manager see all, Employee sees own/assigned)
- Efficient filtering of deleted tasks (exclude is_deleted=true records)
- Fast lookup by task_id for detail views
- Efficient JOINs with employees, projects, and task_assignments tables

### 5.2 Scalability Requirements

- No specific partitioning or sharding requirements at this stage
- Design supports future horizontal scaling if needed
- Index strategy optimized for common query patterns
- Composite indexes for multi-column filtering and sorting

### 5.3 Data Integrity Requirements

- Referential integrity enforced through foreign key constraints
- UNIQUE constraint on (task_id, employee_id) prevents duplicate assignments
- Check constraints for all ENUM fields (status, permission)
- Immutable fields (owner_id) enforced at application level
- Hard deletion preserves referential integrity (CASCADE deletes assignments)
- Company scoping ensures data isolation per tenant

### 5.4 Audit Requirements

All tables include complete audit trail:
- created_at: Timestamp when record was created (TIMESTAMPTZ)
- updated_at: Timestamp when record was last updated (TIMESTAMPTZ)
- created_by: User ID who created the record (UUID, nullable)
- updated_by: User ID who last updated the record (UUID, nullable)

**Note:** Hard deletion is supported (no soft delete fields: deleted_at, deleted_by).
Hard deletion uses is_deleted BOOLEAN marker (true = deleted, false = active).

### 5.5 Security Requirements

- Task owner is immutable (cannot be changed after creation)
- Company scoping ensures data isolation per tenant
- Foreign key constraints prevent orphaned records
- Hard deletion permanently removes data (no recovery)
- Role-based access control handled by F-002 (RBAC & Permission Engine)

### 5.6 Availability Requirements

- Standard PostgreSQL high-availability configurations apply
- No special clustering requirements specified
- Cascade deletion ensures referential integrity during company/task deletion

================================================================================
                        SECTION 6 — LOGICAL DATA MODEL
================================================================================

### 6.1 Entity Relationships

The logical data model consists of two main entities for this feature:

1. **Task** (1) ←→ (1) **Company**
   - Each task belongs to exactly one company
   - One company has many tasks
   - Relationship: Required (company_id is NOT NULL)
   - Foreign Key: tasks.company_id → companies.id
   - Action: ON DELETE CASCADE (delete tasks when company deleted)
   - Action: ON UPDATE CASCADE (propagate company ID changes)

2. **Task** (1) ←→ (1) **Employee** (via owner_id)
   - Each task has exactly one owner (employee)
   - One employee can own many tasks
   - Relationship: Required (owner_id is NOT NULL)
   - Foreign Key: tasks.owner_id → employees.id
   - Action: ON DELETE CASCADE (delete tasks when employee deleted)
   - Action: ON UPDATE CASCADE (propagate employee ID changes)

3. **Task** (1) ←→ (M) **TaskAssignment**
   - One task has many task assignments
   - Task assignment belongs to exactly one task
   - Relationship: Required (task_id is NOT NULL)
   - Foreign Key: task_assignments.task_id → tasks.id
   - Action: ON DELETE CASCADE (delete assignments when task deleted)
   - Action: ON UPDATE CASCADE (propagate task ID changes)

4. **Employee** (M) ←→ (M) **Task** (via TaskAssignment)
   - Many employees can be assigned to many tasks
   - Junction table: task_assignments
   - Relationship: Required (employee_id is NOT NULL)
   - Foreign Key: task_assignments.employee_id → employees.id
   - Action: ON DELETE CASCADE (delete assignments when employee deleted)
   - Action: ON UPDATE CASCADE (propagate employee ID changes)

5. **Task** (M) ←→ (0..1) **Project**
   - Many tasks can optionally belong to one project
   - Project can have many tasks
   - Relationship: Optional (project_id is NULLABLE)
   - Foreign Key: tasks.project_id → projects.id
   - Action: ON DELETE RESTRICT (prevent deletion of project with tasks)
   - Action: ON UPDATE CASCADE (propagate project ID changes)

### 6.2 Key Business Rules

**Uniqueness Constraints:**
- Task assignment must be unique per task-employee pair
- Enforced via UNIQUE constraint: (task_id, employee_id)

**Status Constraints:**
- Status must be one of: TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED
- Enforced via CHECK constraint

**Permission Constraints:**
- Permission must be one of: VIEWER, EDITOR
- Enforced via CHECK constraint

**Referential Constraints:**
- company_id must reference existing company
- owner_id must reference existing employee
- project_id must reference existing project (if provided)
- task_id must reference existing task
- employee_id must reference existing employee
- All enforced via FOREIGN KEY constraints

**Immutable Fields:**
- owner_id cannot be changed after creation (enforced at application level)

**Hard Deletion:**
- Tasks use hard deletion (is_deleted BOOLEAN marker)
- Deleted tasks (is_deleted = true) are excluded from queries
- Cascade deletion: deleting task deletes all assignments
- Cascade deletion: deleting company deletes all tasks and assignments
- Cascade deletion: deleting employee deletes all owned tasks and assignments

### 6.3 Entity Attributes

**tasks**
- **id**: UUID primary key
- **company_id**: UUID foreign key to companies (required)
- **owner_id**: UUID foreign key to employees (required, immutable)
- **name**: VARCHAR(255) task title (required, min 1, max 255 characters)
- **description**: VARCHAR(5000) task details (optional, max 5000 characters)
- **status**: VARCHAR(20) lifecycle state (required, enum: TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED)
- **project_id**: UUID foreign key to projects (optional, nullable)
- **is_deleted**: BOOLEAN hard delete marker (required, default false)
- **created_at**: TIMESTAMPTZ creation timestamp (required)
- **updated_at**: TIMESTAMPTZ last update timestamp (required)
- **created_by**: UUID user who created (nullable)
- **updated_by**: UUID user who last updated (nullable)

**task_assignments**
- **id**: UUID primary key
- **task_id**: UUID foreign key to tasks (required)
- **employee_id**: UUID foreign key to employees (required)
- **permission**: VARCHAR(20) assignment permission (required, enum: VIEWER, EDITOR)
- **created_at**: TIMESTAMPTZ creation timestamp (required)
- **updated_at**: TIMESTAMPTZ last update timestamp (required)
- **created_by**: UUID user who created (nullable)
- **updated_by**: UUID user who last updated (nullable)

================================================================================
                        SECTION 7 — PHYSICAL DATA MODEL
================================================================================

### 7.1 Table: tasks

**Description:**
Represents a single unit of work within a company. Tasks are company-scoped, have one 
immutable owner, may have multiple assignees, and optionally belong to a project. All 
permissions and visibility are task-based.

**Table Name:** `tasks`

**Column Definitions:**

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique task identifier |
| company_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES companies(id) ON DELETE CASCADE ON UPDATE CASCADE | Foreign key to companies table, required tenant boundary |
| owner_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES employees(id) ON DELETE CASCADE ON UPDATE CASCADE | Foreign key to employees table, task owner (immutable) |
| name | VARCHAR(255) | No | No | No | - | NOT NULL | Task title, required, min 1 character, max 255 characters |
| description | VARCHAR(5000) | No | No | Yes | NULL | - | Task details, optional, max 5000 characters |
| status | VARCHAR(20) | No | No | No | 'TODO' | NOT NULL, CHECK (status IN ('TODO', 'IN_PROGRESS', 'HALT', 'REVIEW', 'DONE', 'CANCELLED')) | Task lifecycle state, required, default TODO |
| project_id | UUID | No | Yes | Yes | NULL | REFERENCES projects(id) ON DELETE RESTRICT ON UPDATE CASCADE | Foreign key to projects table, optional project linkage |
| is_deleted | BOOLEAN | No | No | No | false | NOT NULL | Hard delete marker, true = deleted, false = active |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created (UTC) |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated (UTC) |
| created_by | UUID | No | No | Yes | NULL | - | User ID who created the record |
| updated_by | UUID | No | No | Yes | NULL | - | User ID who last updated the record |

**Foreign Key Constraints:**
- `fk_tasks_company_id_companies`: 
  - `company_id` REFERENCES `companies(id)` 
  - ON DELETE CASCADE (delete tasks when company deleted)
  - ON UPDATE CASCADE (propagate company ID changes)

- `fk_tasks_owner_id_employees`: 
  - `owner_id` REFERENCES `employees(id)` 
  - ON DELETE CASCADE (delete tasks when employee deleted)
  - ON UPDATE CASCADE (propagate employee ID changes)

- `fk_tasks_project_id_projects`: 
  - `project_id` REFERENCES `projects(id)` 
  - ON DELETE RESTRICT (prevent deletion of project with tasks)
  - ON UPDATE CASCADE (propagate project ID changes)

**Additional Constraints:**
- **Status Enum Check:**
  - CHECK constraint: `status IN ('TODO', 'IN_PROGRESS', 'HALT', 'REVIEW', 'DONE', 'CANCELLED')`
  - Enforces valid status values at database level

- **Business Rules (Application Level):**
  - `owner_id` is immutable (cannot be changed after creation)
  - Initial task status must be TODO
  - Owner or Editor can change task status
  - Tasks in terminal states (DONE, CANCELLED) are read-only
  - Deleted tasks (is_deleted = true) are excluded from queries

**Column Order:**
1. Primary Key (id)
2. Foreign Keys (company_id, owner_id, project_id)
3. Business Fields (name, description, status)
4. Hard Delete Field (is_deleted)
5. Audit Fields (created_at, updated_at, created_by, updated_by)

**Table Creation SQL:**
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL,
    owner_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(5000) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'TODO' 
        CHECK (status IN ('TODO', 'IN_PROGRESS', 'HALT', 'REVIEW', 'DONE', 'CANCELLED')),
    project_id UUID NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NULL,
    updated_by UUID NULL,
    
    CONSTRAINT fk_tasks_company_id_companies 
        FOREIGN KEY (company_id) 
        REFERENCES companies(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    
    CONSTRAINT fk_tasks_owner_id_employees 
        FOREIGN KEY (owner_id) 
        REFERENCES employees(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    
    CONSTRAINT fk_tasks_project_id_projects 
        FOREIGN KEY (project_id) 
        REFERENCES projects(id) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE
);
```

### 7.2 Table: task_assignments

**Description:**
Represents assignment of an employee to a task with a specific permission level. This 
junction table enables many-to-many relationship between employees and tasks, with 
granular permission control (VIEWER, EDITOR).

**Table Name:** `task_assignments`

**Column Definitions:**

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique task assignment identifier |
| task_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES tasks(id) ON DELETE CASCADE ON UPDATE CASCADE | Foreign key to tasks table, assigned task |
| employee_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES employees(id) ON DELETE CASCADE ON UPDATE CASCADE | Foreign key to employees table, assigned employee |
| permission | VARCHAR(20) | No | No | No | - | NOT NULL, CHECK (permission IN ('VIEWER', 'EDITOR')) | Assignment permission level, required |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created (UTC) |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated (UTC) |
| created_by | UUID | No | No | Yes | NULL | - | User ID who created the record |
| updated_by | UUID | No | No | Yes | NULL | - | User ID who last updated the record |

**Foreign Key Constraints:**
- `fk_task_assignments_task_id_tasks`: 
  - `task_id` REFERENCES `tasks(id)` 
  - ON DELETE CASCADE (delete assignments when task deleted)
  - ON UPDATE CASCADE (propagate task ID changes)

- `fk_task_assignments_employee_id_employees`: 
  - `employee_id` REFERENCES `employees(id)` 
  - ON DELETE CASCADE (delete assignments when employee deleted)
  - ON UPDATE CASCADE (propagate employee ID changes)

**Additional Constraints:**
- **Unique Task-Employee Assignment:**
  - UNIQUE constraint on `(task_id, employee_id)`
  - Prevents duplicate assignments (same employee assigned twice to same task)
  - Enforced via UNIQUE INDEX

- **Permission Enum Check:**
  - CHECK constraint: `permission IN ('VIEWER', 'EDITOR')`
  - Enforces valid permission values at database level

- **Business Rules (Application Level):**
  - Editors cannot remove themselves (only owner can remove editors)
  - Owner cannot remove themselves (must remain owner)
  - Permission changes trigger notifications (F-003)

**Column Order:**
1. Primary Key (id)
2. Foreign Keys (task_id, employee_id)
3. Business Fields (permission)
4. Audit Fields (created_at, updated_at, created_by, updated_by)

**Table Creation SQL:**
```sql
CREATE TABLE task_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL,
    employee_id UUID NOT NULL,
    permission VARCHAR(20) NOT NULL 
        CHECK (permission IN ('VIEWER', 'EDITOR')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NULL,
    updated_by UUID NULL,
    
    CONSTRAINT fk_task_assignments_task_id_tasks 
        FOREIGN KEY (task_id) 
        REFERENCES tasks(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    
    CONSTRAINT fk_task_assignments_employee_id_employees 
        FOREIGN KEY (employee_id) 
        REFERENCES employees(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    
    CONSTRAINT uq_task_assignments_task_employee 
        UNIQUE (task_id, employee_id)
);
```

================================================================================
                        SECTION 8 — NORMALIZATION VERIFICATION
================================================================================

### 8.1 Table: tasks

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
- `company_id` depends directly on `id` (task belongs to company)
- `owner_id` depends directly on `id` (task has owner)
- `name` depends directly on `id` (task name)
- `description` depends directly on `id` (task description)
- `status` depends directly on `id` (task status)
- `project_id` depends directly on `id` (task may belong to project)
- `is_deleted` depends directly on `id` (hard delete marker)
- All audit fields depend directly on `id` (task lifecycle events)

**Result:** Table is in 3NF ✓

**Normalization Summary:**
- **Current Form:** 3NF (Third Normal Form)
- **Denormalization:** None required
- **Performance Considerations:** Composite indexes for common query patterns

### 8.2 Table: task_assignments

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
- `task_id` depends directly on `id` (assignment belongs to task)
- `employee_id` depends directly on `id` (assignment belongs to employee)
- `permission` depends directly on `id` (assignment permission level)
- All audit fields depend directly on `id` (assignment lifecycle events)

**Result:** Table is in 3NF ✓

**Normalization Summary:**
- **Current Form:** 3NF (Third Normal Form)
- **Denormalization:** None required
- **Performance Considerations:** Unique index on (task_id, employee_id) for efficient uniqueness checks

================================================================================
                        SECTION 9 — INDEX STRATEGY
================================================================================

### 9.1 Primary Key Indexes

**Index:** `pk_tasks`
- **Type:** UNIQUE INDEX (automatically created by PRIMARY KEY constraint)
- **Columns:** `id`
- **Purpose:** Enforce primary key uniqueness and optimize primary key lookups
- **SQL:**
```sql
-- Automatically created by PRIMARY KEY constraint
-- No explicit CREATE INDEX needed
```

**Index:** `pk_task_assignments`
- **Type:** UNIQUE INDEX (automatically created by PRIMARY KEY constraint)
- **Columns:** `id`
- **Purpose:** Enforce primary key uniqueness and optimize primary key lookups
- **SQL:**
```sql
-- Automatically created by PRIMARY KEY constraint
-- No explicit CREATE INDEX needed
```

### 9.2 Foreign Key Indexes

**Index:** `idx_tasks_company_id`
- **Type:** B-tree INDEX
- **Columns:** `company_id`
- **Purpose:** Optimize JOINs with companies table and foreign key constraint checks
- **SQL:**
```sql
CREATE INDEX idx_tasks_company_id ON tasks(company_id);
```

**Rationale:** Foreign key columns MUST be indexed for optimal JOIN performance and referential integrity checks. This is critical for multi-tenant queries filtering by company_id.

**Index:** `idx_tasks_owner_id`
- **Type:** B-tree INDEX
- **Columns:** `owner_id`
- **Purpose:** Optimize JOINs with employees table and foreign key constraint checks
- **SQL:**
```sql
CREATE INDEX idx_tasks_owner_id ON tasks(owner_id);
```

**Rationale:** Foreign key columns MUST be indexed for optimal JOIN performance. Critical for queries filtering by task owner.

**Index:** `idx_tasks_project_id`
- **Type:** B-tree INDEX
- **Columns:** `project_id`
- **Purpose:** Optimize JOINs with projects table and foreign key constraint checks
- **SQL:**
```sql
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
```

**Rationale:** Foreign key columns MUST be indexed for optimal JOIN performance. Critical for queries filtering by project.

**Index:** `idx_task_assignments_task_id`
- **Type:** B-tree INDEX
- **Columns:** `task_id`
- **Purpose:** Optimize JOINs with tasks table and foreign key constraint checks
- **SQL:**
```sql
CREATE INDEX idx_task_assignments_task_id ON task_assignments(task_id);
```

**Rationale:** Foreign key columns MUST be indexed for optimal JOIN performance. Critical for queries retrieving task assignments.

**Index:** `idx_task_assignments_employee_id`
- **Type:** B-tree INDEX
- **Columns:** `employee_id`
- **Purpose:** Optimize JOINs with employees table and foreign key constraint checks
- **SQL:**
```sql
CREATE INDEX idx_task_assignments_employee_id ON task_assignments(employee_id);
```

**Rationale:** Foreign key columns MUST be indexed for optimal JOIN performance. Critical for queries filtering by assigned employee.

### 9.3 Audit Field Indexes

**Index:** `idx_tasks_updated_at`
- **Type:** B-tree INDEX
- **Columns:** `updated_at`
- **Purpose:** Essential for incremental sync, change tracking, and audit queries
- **SQL:**
```sql
CREATE INDEX idx_tasks_updated_at ON tasks(updated_at);
```

**Rationale:** Every table with `updated_at` MUST have an index. This is critical for:
- Incremental data synchronization
- Change tracking and audit queries
- Sorting by last modified date
- Efficient pagination with time-based cursors

**Index:** `idx_task_assignments_updated_at`
- **Type:** B-tree INDEX
- **Columns:** `updated_at`
- **Purpose:** Essential for incremental sync, change tracking, and audit queries
- **SQL:**
```sql
CREATE INDEX idx_task_assignments_updated_at ON task_assignments(updated_at);
```

**Rationale:** Every table with `updated_at` MUST have an index. This is critical for incremental synchronization and change tracking.

### 9.4 Composite Indexes

**Index:** `idx_tasks_company_status_deleted`
- **Type:** B-tree INDEX
- **Columns:** `company_id, status, is_deleted`
- **Purpose:** Optimize common query pattern: filter by company, status, and exclude deleted tasks
- **SQL:**
```sql
CREATE INDEX idx_tasks_company_status_deleted ON tasks(company_id, status, is_deleted);
```

**Rationale:** This composite index optimizes the most common query pattern:
- Filter by company (equality check)
- Filter by status (equality check)
- Exclude deleted tasks (equality check on is_deleted)

**Index:** `idx_tasks_company_owner_deleted`
- **Type:** B-tree INDEX
- **Columns:** `company_id, owner_id, is_deleted`
- **Purpose:** Optimize query pattern: filter by company and owner, exclude deleted tasks
- **SQL:**
```sql
CREATE INDEX idx_tasks_company_owner_deleted ON tasks(company_id, owner_id, is_deleted);
```

**Rationale:** This composite index optimizes queries for:
- Employee viewing their own tasks (filter by company and owner)
- Exclude deleted tasks

**Index:** `idx_tasks_company_project_deleted`
- **Type:** B-tree INDEX
- **Columns:** `company_id, project_id, is_deleted`
- **Purpose:** Optimize query pattern: filter by company and project, exclude deleted tasks
- **SQL:**
```sql
CREATE INDEX idx_tasks_company_project_deleted ON tasks(company_id, project_id, is_deleted) WHERE project_id IS NOT NULL;
```

**Rationale:** This partial index optimizes queries filtering by project (only indexes non-null project_id values).

**Index:** `idx_tasks_company_created_deleted`
- **Type:** B-tree INDEX
- **Columns:** `company_id, created_at DESC, is_deleted`
- **Purpose:** Optimize query pattern: filter by company, sort by creation date, exclude deleted tasks
- **SQL:**
```sql
CREATE INDEX idx_tasks_company_created_deleted ON tasks(company_id, created_at DESC, is_deleted);
```

**Rationale:** This composite index optimizes pagination queries sorted by creation date.

### 9.5 Unique Indexes

**Index:** `uq_task_assignments_task_employee`
- **Type:** UNIQUE INDEX
- **Columns:** `task_id, employee_id`
- **Purpose:** Enforce unique task-employee assignment (prevent duplicate assignments)
- **SQL:**
```sql
-- Created via UNIQUE constraint in table definition
-- No explicit CREATE INDEX needed (constraint creates index automatically)
```

**Rationale:** Prevents duplicate assignments (same employee assigned twice to same task).

### 9.6 Partial Indexes for Deleted Records

**Index:** `idx_tasks_active`
- **Type:** B-tree INDEX (Partial)
- **Columns:** `id`
- **Purpose:** Optimize queries for active tasks only (exclude deleted)
- **SQL:**
```sql
CREATE INDEX idx_tasks_active ON tasks(id) WHERE is_deleted = false;
```

**Rationale:** Partial index for active tasks only, improving query performance when filtering out deleted records.

**Index:** `idx_tasks_company_active`
- **Type:** B-tree INDEX (Partial)
- **Columns:** `company_id, status`
- **Purpose:** Optimize queries for active tasks by company and status
- **SQL:**
```sql
CREATE INDEX idx_tasks_company_active ON tasks(company_id, status) WHERE is_deleted = false;
```

**Rationale:** Partial index for active tasks only, optimizing common filtering patterns.

### 9.7 Index Summary

**Total Indexes:**
- Primary Key Indexes: 2 (automatic)
- Foreign Key Indexes: 5 (mandatory)
- Audit Field Indexes: 2 (mandatory)
- Composite Indexes: 4 (performance optimization)
- Unique Indexes: 1 (data integrity)
- Partial Indexes: 2 (performance optimization)

**Index Maintenance:**
- All indexes are automatically maintained by PostgreSQL
- Index usage should be monitored via `pg_stat_user_indexes`
- Consider periodic `VACUUM ANALYZE` for optimal performance

================================================================================
                        SECTION 10 — ENTITY RELATIONSHIP DIAGRAM
================================================================================

See separate file: `F8_ERD.txt`

The ERD shows:
- Companies (1) → Tasks (*)
- Tasks (1) → Employees (1) via owner_id
- Tasks (1) → TaskAssignments (*)
- Employees (*) → Tasks (*) via TaskAssignments
- Tasks (*) → Projects (0..1)
- Projects (1) → Companies (1)
- Employees (1) → Companies (1)

All relationships use appropriate cardinality notation (Crow's Foot) and show only PRIMARY KEY and FOREIGN KEY fields.

================================================================================
                              END OF DOCUMENT
================================================================================

