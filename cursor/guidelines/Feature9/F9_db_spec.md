# DATABASE DESIGN SPECIFICATION

================================================================================
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│                    DATABASE DESIGN SPECIFICATION                          │
│                                                                            │
│                    Project: officeWorld                                    │
│                    Feature: F-009 — Leave Management                      │
│                                                                            │
│                    Database: PostgreSQL                                    │
│                    Version: 1.0                                           │
│                    Date: 2024                                             │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
================================================================================

---

## SECTION 1 — COVER PAGE

┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│                    DATABASE DESIGN SPECIFICATION                          │
│                                                                            │
│                    Project: officeWorld                                    │
│                    Feature: F-009 — Leave Management                      │
│                                                                            │
│                    Database System: PostgreSQL                             │
│                    Document Version: 1.0                                   │
│                    Date: 2024                                              │
│                    Status: Draft                                           │
│                                                                            │
│                    Prepared By: Database Architect                         │
│                    Reviewed By:                                            │
│                    Approved By:                                            │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘

---

## SECTION 2 — DOCUMENT CONTROL

| Item | Details |
|------|---------|
| **Document Title** | Database Design Specification — Leave Management (F-009) |
| **Project Name** | officeWorld |
| **Feature** | F-009 — Leave Management |
| **Database System** | PostgreSQL |
| **Document Version** | 1.0 |
| **Date** | 2024 |
| **Status** | Draft |
| **Prepared By** | Database Architect |
| **Reviewed By** | - |
| **Approved By** | - |
| **Change History** | Version 1.0 — Initial draft |

---

## SECTION 3 — INTRODUCTION

### 3.1 Purpose
This document specifies the database design for the Leave Management feature (F-009) of the officeWorld system. It provides a complete physical data model, normalization analysis, indexing strategy, and entity relationship diagram for the leave request management functionality.

### 3.2 Scope
This specification covers:
- Physical database schema for `leave_requests` table
- Relationships to `companies` and `employees` tables (from F-005)
- Data types, constraints, and validation rules
- Indexing strategy for optimal query performance
- Normalization verification (3NF compliance)

### 3.3 Out of Scope
- Leave balance tracking and accrual
- Payroll or salary impact calculations
- Historical leave data archiving strategy
- Database replication and high availability configuration

### 3.4 Dependencies
- **F-005 — Employee Management**: `employees` table must exist
- **F-004 — Company Management**: `companies` table must exist
- **F-002 — RBAC & Permission Engine**: Role-based access control

### 3.5 Document Structure
1. Cover Page
2. Document Control
3. Introduction
4. System Overview
5. Non-Functional Requirements
6. Logical Data Model
7. Physical Data Model
8. Normalization
9. Index Strategy
10. Professional ASCII ER Diagram

---

## SECTION 4 — SYSTEM OVERVIEW

### 4.1 Business Purpose
The Leave Management system provides a deterministic, role-driven workflow for employees to request time off and for organizations to approve or reject those requests through a structured approval chain. It enforces strict validation rules, mandatory rejection reasons, role-based visibility, and integrates notifications for key leave events without handling balances or payroll.

### 4.2 Key Capabilities
- Leave request submission with date range and half-day support
- Role-based approval workflows (Employee → Manager → HR, Manager → HR, HR → CEO)
- Mandatory validation rules (overlaps, non-working days)
- Leave cancellation by applicant
- Role-based visibility of leave requests
- Email and in-app notifications for leave workflow events

### 4.3 Core Entities
- **leave_requests**: Main entity storing leave request data with dual status tracking (manager_status and hr_status)

### 4.4 Relationships
- `leave_requests` belongs to exactly one `company` (via `company_id`)
- `leave_requests` belongs to exactly one `employee` (applicant, via `employee_id`)
- `leave_requests` has exactly one manager approver (via `manager_approver_id` → `employees.id`)
- `leave_requests` has exactly one HR approver (via `hr_approver_id` → `employees.id`)
- CEO acts as final approver for HR leave (no separate CEO approver field, handled via role check)

---

## SECTION 5 — NON-FUNCTIONAL REQUIREMENTS

### 5.1 Performance Requirements
- Query response time: < 100ms for single leave request retrieval
- List query response time: < 500ms for paginated leave requests (20 items per page)
- Support for concurrent approval operations with ETag-based concurrency control

### 5.2 Scalability Requirements
- Support for multiple companies (multi-tenancy via `company_id`)
- Expected volume: 100-1000 leave requests per company per year
- No partitioning or sharding required at this stage

### 5.3 Data Integrity Requirements
- Foreign key constraints to ensure referential integrity
- CHECK constraints for enum values (leave_type, day_type, manager_status, hr_status)
- NOT NULL constraints for required fields
- Unique constraint on overlapping leave prevention (application-level, not database-level)

### 5.4 Audit Requirements
- All audit fields required: `created_at`, `updated_at`, `created_by`, `updated_by`, `deleted_at`, `deleted_by`
- Soft delete support via `deleted_at` timestamp
- UTC timezone for all timestamp fields

### 5.5 Security Requirements
- Multi-tenancy isolation via `company_id` column
- Row-level security (RLS) may be implemented at application level
- Audit trail via `created_by`, `updated_by`, `deleted_by` fields

---

## SECTION 6 — LOGICAL DATA MODEL

### 6.1 Entity: LeaveRequest

**Description:**  
Represents a request for leave submitted by an employee. The request follows a role-based approval workflow and ends in a terminal state.

**Key Attributes:**
- Unique identifier (UUID)
- Employee reference (applicant)
- Company reference (multi-tenancy)
- Leave type (CASUAL, SICK, PAID, UNPAID)
- Date range (start_date, end_date)
- Day type (FULL_DAY, FIRST_HALF, SECOND_HALF)
- Calculated number of days
- Reason for leave
- Manager workflow status and approver details
- HR workflow status and approver details
- Audit fields (created_at, updated_at, created_by, updated_by, deleted_at, deleted_by)

**Business Rules:**
- Overlapping leave requests for the same employee are not allowed (application-level validation)
- Leave on weekends or holidays is not allowed (application-level validation)
- Rejection reasons are mandatory when status is REJECTED_MANAGER or REJECTED_HR
- Both manager_status and hr_status can be CANCELLED (by applicant)
- Number of days is calculated from date range and day_type

**Relationships:**
- Many leave_requests belong to one company (1:M)
- Many leave_requests belong to one employee (applicant) (1:M)
- Many leave_requests have one manager approver (1:M)
- Many leave_requests have one HR approver (1:M)

---

## SECTION 7 — PHYSICAL DATA MODEL

### 7.1 Table: leave_requests

**Description:**  
Stores leave request data with dual status tracking for manager and HR approval workflows. Supports soft delete for auditability.

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique leave request identifier |
| company_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES companies(id) ON DELETE RESTRICT ON UPDATE CASCADE | Company owning this leave request (multi-tenancy) |
| employee_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES employees(id) ON DELETE RESTRICT ON UPDATE CASCADE | Employee who submitted the leave request (applicant) |
| manager_approver_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES employees(id) ON DELETE RESTRICT ON UPDATE CASCADE | Manager employee assigned to approve this leave request |
| hr_approver_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES employees(id) ON DELETE RESTRICT ON UPDATE CASCADE | HR employee assigned to approve this leave request |
| leave_type | VARCHAR(20) | No | No | No | - | NOT NULL, CHECK (leave_type IN ('CASUAL', 'SICK', 'PAID', 'UNPAID')) | Type of leave: CASUAL, SICK, PAID, UNPAID |
| start_date | DATE | No | No | No | - | NOT NULL | Leave start date (inclusive, ISO 8601 format) |
| end_date | DATE | No | No | No | - | NOT NULL, CHECK (end_date >= start_date) | Leave end date (inclusive, must be >= start_date) |
| day_type | VARCHAR(20) | No | No | No | - | NOT NULL, CHECK (day_type IN ('FULL_DAY', 'FIRST_HALF', 'SECOND_HALF')) | Day type: FULL_DAY, FIRST_HALF, SECOND_HALF |
| number_of_days | NUMERIC(5,2) | No | No | No | - | NOT NULL, CHECK (number_of_days >= 0) | Calculated duration in days (derived from date range and day_type, half-days = 0.5) |
| reason | TEXT | No | No | No | - | NOT NULL, CHECK (LENGTH(reason) >= 10 AND LENGTH(reason) <= 500) | Reason for leave (mandatory, min 10 chars, max 500 chars) |
| manager_status | VARCHAR(20) | No | No | No | 'PENDING_MANAGER' | NOT NULL, CHECK (manager_status IN ('PENDING_MANAGER', 'APPROVED_MANAGER', 'REJECTED_MANAGER', 'CANCELLED')) | Manager workflow status: PENDING_MANAGER, APPROVED_MANAGER, REJECTED_MANAGER, CANCELLED |
| manager_approved_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when manager approved the leave request (nullable, UTC) |
| manager_rejection_reason | TEXT | No | No | Yes | NULL | CHECK (manager_rejection_reason IS NULL OR (LENGTH(manager_rejection_reason) >= 10 AND LENGTH(manager_rejection_reason) <= 500)) | Reason for manager rejection (nullable, required if manager_status = REJECTED_MANAGER, min 10 chars, max 500 chars) |
| hr_status | VARCHAR(20) | No | No | No | 'PENDING_HR' | NOT NULL, CHECK (hr_status IN ('PENDING_HR', 'APPROVED_HR', 'REJECTED_HR', 'CANCELLED')) | HR workflow status: PENDING_HR, APPROVED_HR, REJECTED_HR, CANCELLED |
| hr_approved_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when HR approved the leave request (nullable, UTC) |
| hr_rejection_reason | TEXT | No | No | Yes | NULL | CHECK (hr_rejection_reason IS NULL OR (LENGTH(hr_rejection_reason) >= 10 AND LENGTH(hr_rejection_reason) <= 500)) | Reason for HR rejection (nullable, required if hr_status = REJECTED_HR, min 10 chars, max 500 chars) |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when leave request was created (immutable, UTC) |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when leave request was last updated (UTC, updated via trigger or application) |
| created_by | UUID | No | Yes | Yes | NULL | REFERENCES employees(id) ON DELETE SET NULL ON UPDATE CASCADE | User ID who created the leave request (nullable, FK to employees) |
| updated_by | UUID | No | Yes | Yes | NULL | REFERENCES employees(id) ON DELETE SET NULL ON UPDATE CASCADE | User ID who last updated the leave request (nullable, FK to employees) |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when leave request was soft-deleted (nullable, NULL if active) |
| deleted_by | UUID | No | Yes | Yes | NULL | REFERENCES employees(id) ON DELETE SET NULL ON UPDATE CASCADE | User ID who soft-deleted the leave request (nullable, FK to employees) |

**Foreign Key Constraints:**

1. `fk_leave_requests_company_id`
   - Column: `company_id`
   - References: `companies(id)`
   - ON DELETE: RESTRICT (prevent deletion of company with active leave requests)
   - ON UPDATE: CASCADE (propagate company ID changes)

2. `fk_leave_requests_employee_id`
   - Column: `employee_id`
   - References: `employees(id)`
   - ON DELETE: RESTRICT (prevent deletion of employee with leave requests)
   - ON UPDATE: CASCADE (propagate employee ID changes)

3. `fk_leave_requests_manager_approver_id`
   - Column: `manager_approver_id`
   - References: `employees(id)`
   - ON DELETE: RESTRICT (prevent deletion of manager with assigned leave requests)
   - ON UPDATE: CASCADE (propagate employee ID changes)

4. `fk_leave_requests_hr_approver_id`
   - Column: `hr_approver_id`
   - References: `employees(id)`
   - ON DELETE: RESTRICT (prevent deletion of HR with assigned leave requests)
   - ON UPDATE: CASCADE (propagate employee ID changes)

5. `fk_leave_requests_created_by`
   - Column: `created_by`
   - References: `employees(id)`
   - ON DELETE: SET NULL (preserve audit trail if employee deleted)
   - ON UPDATE: CASCADE (propagate employee ID changes)

6. `fk_leave_requests_updated_by`
   - Column: `updated_by`
   - References: `employees(id)`
   - ON DELETE: SET NULL (preserve audit trail if employee deleted)
   - ON UPDATE: CASCADE (propagate employee ID changes)

7. `fk_leave_requests_deleted_by`
   - Column: `deleted_by`
   - References: `employees(id)`
   - ON DELETE: SET NULL (preserve audit trail if employee deleted)
   - ON UPDATE: CASCADE (propagate employee ID changes)

**Additional Constraints:**

1. **Business Rule Constraint — Rejection Reason Required:**
   - Application-level validation: If `manager_status = 'REJECTED_MANAGER'`, then `manager_rejection_reason` must not be NULL
   - Application-level validation: If `hr_status = 'REJECTED_HR'`, then `hr_rejection_reason` must not be NULL
   - Note: Database-level CHECK constraint validates format/length but not NULL requirement based on status (handled by application)

2. **Business Rule Constraint — Overlapping Leave Prevention:**
   - Application-level validation: No overlapping leave requests for the same employee
   - Cannot be enforced at database level due to complexity (requires date range overlap check)
   - Implemented via application logic with database query

3. **Business Rule Constraint — Non-Working Days:**
   - Application-level validation: Leave requests cannot include weekends or holidays
   - Implemented via application logic

4. **Default Values:**
   - `manager_status` defaults to `'PENDING_MANAGER'` on insert
   - `hr_status` defaults to `'PENDING_HR'` on insert

**Trigger for updated_at:**
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_leave_requests_updated_at
    BEFORE UPDATE ON leave_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

## SECTION 8 — NORMALIZATION

### 8.1 Normalization Verification for `leave_requests` Table

#### First Normal Form (1NF) ✓
- [x] All columns contain atomic values (no arrays, no comma-separated lists)
- [x] Each column contains only one type of data
- [x] Each column has a unique name
- [x] Order of rows/columns doesn't matter
- [x] No repeating groups of columns

**Verification:** All columns store atomic values. No multi-valued attributes or repeating groups.

#### Second Normal Form (2NF) ✓
- [x] Table is in 1NF
- [x] All non-key columns depend on the entire primary key (not just part of it)
- [x] No partial dependencies

**Verification:** Primary key is `id` (single column), so no composite key exists. All non-key columns depend on the entire primary key `id`.

#### Third Normal Form (3NF) ✓
- [x] Table is in 2NF
- [x] No transitive dependencies (non-key columns don't depend on other non-key columns)
- [x] All non-key columns depend directly on the primary key

**Verification:** 
- All columns directly depend on the primary key `id`
- No transitive dependencies exist (e.g., no column depends on `employee_id` that isn't already a foreign key)
- Foreign key columns (`company_id`, `employee_id`, `manager_approver_id`, `hr_approver_id`) are references to other tables, not transitive dependencies
- `number_of_days` is a calculated/derived field but stored for performance (acceptable denormalization, documented below)

#### Acceptable Denormalization

**1. `number_of_days` Field:**
- **Rationale:** Calculated from `start_date`, `end_date`, and `day_type`
- **Reason:** Performance optimization for queries that filter/sort by number of days
- **Alternative:** Could be computed via generated column or view, but stored for query performance
- **Trade-off:** Slight storage overhead vs. query performance gain

**2. Dual Status Fields (`manager_status` and `hr_status`):**
- **Rationale:** Both statuses are needed for workflow tracking
- **Reason:** Business requirement to track manager and HR approval stages independently
- **Alternative:** Could use a single status with workflow state machine, but dual status provides clearer audit trail
- **Trade-off:** Additional column vs. clearer business logic representation

**Normalization Conclusion:**  
The `leave_requests` table is in **Third Normal Form (3NF)**. All acceptable denormalizations are documented with clear performance or business logic reasoning.

---

## SECTION 9 — INDEX STRATEGY

### 9.1 Primary Key Index

**Index:** `pk_leave_requests`  
**Type:** UNIQUE INDEX (automatically created by PRIMARY KEY constraint)  
**Columns:** `id`  
**SQL:**
```sql
CREATE UNIQUE INDEX pk_leave_requests ON leave_requests(id);
```
**Note:** Automatically created by PostgreSQL when PRIMARY KEY constraint is defined.

### 9.2 Foreign Key Indexes (MANDATORY)

**Index 1:** `idx_leave_requests_company_id`  
**Type:** B-tree INDEX  
**Columns:** `company_id`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_company_id ON leave_requests(company_id);
```
**Purpose:** Improves JOIN performance with `companies` table and multi-tenancy filtering.

**Index 2:** `idx_leave_requests_employee_id`  
**Type:** B-tree INDEX  
**Columns:** `employee_id`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_employee_id ON leave_requests(employee_id);
```
**Purpose:** Improves JOIN performance with `employees` table and queries filtering by applicant.

**Index 3:** `idx_leave_requests_manager_approver_id`  
**Type:** B-tree INDEX  
**Columns:** `manager_approver_id`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_manager_approver_id ON leave_requests(manager_approver_id);
```
**Purpose:** Improves queries filtering by manager approver (approval queue queries).

**Index 4:** `idx_leave_requests_hr_approver_id`  
**Type:** B-tree INDEX  
**Columns:** `hr_approver_id`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_hr_approver_id ON leave_requests(hr_approver_id);
```
**Purpose:** Improves queries filtering by HR approver (approval queue queries).

**Index 5:** `idx_leave_requests_created_by`  
**Type:** B-tree INDEX  
**Columns:** `created_by`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_created_by ON leave_requests(created_by);
```
**Purpose:** Improves audit queries filtering by creator.

**Index 6:** `idx_leave_requests_updated_by`  
**Type:** B-tree INDEX  
**Columns:** `updated_by`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_updated_by ON leave_requests(updated_by);
```
**Purpose:** Improves audit queries filtering by last updater.

**Index 7:** `idx_leave_requests_deleted_by`  
**Type:** B-tree INDEX  
**Columns:** `deleted_by`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_deleted_by ON leave_requests(deleted_by);
```
**Purpose:** Improves audit queries filtering by deleter.

### 9.3 Audit Field Indexes (MANDATORY)

**Index 1:** `idx_leave_requests_updated_at`  
**Type:** B-tree INDEX  
**Columns:** `updated_at`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_updated_at ON leave_requests(updated_at);
```
**Purpose:** Essential for incremental sync, change tracking, ETag generation, and audit queries. **MANDATORY per db_instruction.md Rule 8.1.**

**Index 2:** `idx_leave_requests_created_at`  
**Type:** B-tree INDEX  
**Columns:** `created_at`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_created_at ON leave_requests(created_at);
```
**Purpose:** Improves queries sorting/filtering by creation date (common in list endpoints).

**Index 3:** `idx_leave_requests_deleted_at`  
**Type:** B-tree INDEX  
**Columns:** `deleted_at`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_deleted_at ON leave_requests(deleted_at);
```
**Purpose:** Improves soft-delete filtering (WHERE deleted_at IS NULL for active records).

### 9.4 Composite Indexes

**Index 1:** `idx_leave_requests_company_status_active`  
**Type:** B-tree INDEX  
**Columns:** `company_id`, `manager_status`, `hr_status`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_company_status_active 
ON leave_requests(company_id, manager_status, hr_status) 
WHERE deleted_at IS NULL;
```
**Purpose:** Optimizes list queries filtering by company and status (common query pattern). Partial index for active records only.

**Index 2:** `idx_leave_requests_employee_date_range`  
**Type:** B-tree INDEX  
**Columns:** `employee_id`, `start_date`, `end_date`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_employee_date_range 
ON leave_requests(employee_id, start_date, end_date) 
WHERE deleted_at IS NULL;
```
**Purpose:** Optimizes overlap detection queries (checking for overlapping leave requests for same employee). Partial index for active records only.

**Index 3:** `idx_leave_requests_approver_pending`  
**Type:** B-tree INDEX  
**Columns:** `manager_approver_id`, `manager_status`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_approver_pending 
ON leave_requests(manager_approver_id, manager_status) 
WHERE deleted_at IS NULL AND manager_status = 'PENDING_MANAGER';
```
**Purpose:** Optimizes manager approval queue queries (pending_for_me filter). Partial index for pending manager approvals only.

**Index 4:** `idx_leave_requests_hr_approver_pending`  
**Type:** B-tree INDEX  
**Columns:** `hr_approver_id`, `hr_status`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_hr_approver_pending 
ON leave_requests(hr_approver_id, hr_status) 
WHERE deleted_at IS NULL AND hr_status = 'PENDING_HR' AND manager_status = 'APPROVED_MANAGER';
```
**Purpose:** Optimizes HR approval queue queries (pending_for_me filter). Partial index for pending HR approvals only.

**Index 5:** `idx_leave_requests_company_created_at`  
**Type:** B-tree INDEX  
**Columns:** `company_id`, `created_at DESC`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_company_created_at 
ON leave_requests(company_id, created_at DESC) 
WHERE deleted_at IS NULL;
```
**Purpose:** Optimizes list queries with company filter and default sort by created_at DESC. Partial index for active records only.

### 9.5 Soft Delete Partial Indexes

**Index 1:** `idx_leave_requests_active`  
**Type:** B-tree INDEX (Partial)  
**Columns:** `id`  
**SQL:**
```sql
CREATE INDEX idx_leave_requests_active 
ON leave_requests(id) 
WHERE deleted_at IS NULL;
```
**Purpose:** Optimizes queries that only retrieve active (non-deleted) leave requests.

### 9.6 Index Summary

| Index Name | Type | Columns | Partial | Purpose |
|------------|------|---------|---------|---------|
| pk_leave_requests | UNIQUE | id | No | Primary key |
| idx_leave_requests_company_id | B-tree | company_id | No | FK index, multi-tenancy |
| idx_leave_requests_employee_id | B-tree | employee_id | No | FK index, applicant queries |
| idx_leave_requests_manager_approver_id | B-tree | manager_approver_id | No | FK index, manager queue |
| idx_leave_requests_hr_approver_id | B-tree | hr_approver_id | No | FK index, HR queue |
| idx_leave_requests_created_by | B-tree | created_by | No | FK index, audit |
| idx_leave_requests_updated_by | B-tree | updated_by | No | FK index, audit |
| idx_leave_requests_deleted_by | B-tree | deleted_by | No | FK index, audit |
| idx_leave_requests_updated_at | B-tree | updated_at | No | Audit, ETag, sync |
| idx_leave_requests_created_at | B-tree | created_at | No | Sort/filter by creation |
| idx_leave_requests_deleted_at | B-tree | deleted_at | No | Soft delete filtering |
| idx_leave_requests_company_status_active | B-tree | company_id, manager_status, hr_status | Yes | List queries |
| idx_leave_requests_employee_date_range | B-tree | employee_id, start_date, end_date | Yes | Overlap detection |
| idx_leave_requests_approver_pending | B-tree | manager_approver_id, manager_status | Yes | Manager queue |
| idx_leave_requests_hr_approver_pending | B-tree | hr_approver_id, hr_status | Yes | HR queue |
| idx_leave_requests_company_created_at | B-tree | company_id, created_at DESC | Yes | List with sort |
| idx_leave_requests_active | B-tree | id | Yes | Active records only |

**Total Indexes:** 17 (1 primary key + 16 additional indexes)

---

## SECTION 10 — PROFESSIONAL ASCII ER DIAGRAM

================================================================================
                    ENTITY RELATIONSHIP DIAGRAM (ERD)
                    Feature: F-009 — Leave Management
                    Crow's Foot Notation (ASCII)
================================================================================

+----------------------+
|      companies       |
+----------------------+
| id (PK)              |
+----------------------+
         |
         | 1
         |
         |
+---------------------------+
|      leave_requests       |
+---------------------------+
| id (PK)                   |
| company_id (FK)            |
| employee_id (FK)           |
| manager_approver_id (FK)   |
| hr_approver_id (FK)        |
+---------------------------+
         |                    |                    | M
         | M                  | M                  |
         |                    |                    |
         |                    |                    |
+----------------------+     |     +----------------------+
|      employees       |     |     |      employees       |
|   (Applicant)        |     |     |  (Manager Approver) |
+----------------------+     |     +----------------------+
| id (PK)              |     |     | id (PK)              |
+----------------------+     |     +----------------------+
                              |
                              |
                              |
                    +----------------------+
                    |      employees       |
                    |   (HR Approver)      |
                    +----------------------+
                    | id (PK)              |
                    +----------------------+

================================================================================
                              RELATIONSHIP SUMMARY
================================================================================

1. companies (1) ────────< (M) leave_requests
   Relationship: One company can have many leave requests
   Foreign Key: leave_requests.company_id → companies.id
   Cardinality: 1 : M

2. employees (1) ────────< (M) leave_requests [Applicant]
   Relationship: One employee can create many leave requests
   Foreign Key: leave_requests.employee_id → employees.id
   Cardinality: 1 : M

3. employees (1) ────────< (M) leave_requests [Manager Approver]
   Relationship: One manager employee can approve many leave requests
   Foreign Key: leave_requests.manager_approver_id → employees.id
   Cardinality: 1 : M

4. employees (1) ────────< (M) leave_requests [HR Approver]
   Relationship: One HR employee can approve many leave requests
   Foreign Key: leave_requests.hr_approver_id → employees.id
   Cardinality: 1 : M

================================================================================
                              NOTES
================================================================================

- CEO approval is handled through hr_status field when applicant role is HR
- No separate CEO approver field exists (CEO acts as final approver via role check)
- All approvers (Manager, HR, CEO) are employees with different roles
- Manager and HR approvers are explicitly stored as foreign keys
- CEO approval is implicit (when hr_status = PENDING_HR and applicant role = HR)
- The employees table appears multiple times in the diagram to show different
  relationship roles (applicant, manager approver, HR approver), but it is
  the same physical table with role-based relationships

================================================================================

---

## APPENDIX A — SQL CREATE TABLE STATEMENT

```sql
-- Create leave_requests table
CREATE TABLE leave_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL,
    employee_id UUID NOT NULL,
    manager_approver_id UUID NOT NULL,
    hr_approver_id UUID NOT NULL,
    leave_type VARCHAR(20) NOT NULL CHECK (leave_type IN ('CASUAL', 'SICK', 'PAID', 'UNPAID')),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL CHECK (end_date >= start_date),
    day_type VARCHAR(20) NOT NULL CHECK (day_type IN ('FULL_DAY', 'FIRST_HALF', 'SECOND_HALF')),
    number_of_days NUMERIC(5,2) NOT NULL CHECK (number_of_days >= 0),
    reason TEXT NOT NULL CHECK (LENGTH(reason) >= 10 AND LENGTH(reason) <= 500),
    manager_status VARCHAR(20) NOT NULL DEFAULT 'PENDING_MANAGER' CHECK (manager_status IN ('PENDING_MANAGER', 'APPROVED_MANAGER', 'REJECTED_MANAGER', 'CANCELLED')),
    manager_approved_at TIMESTAMPTZ,
    manager_rejection_reason TEXT CHECK (manager_rejection_reason IS NULL OR (LENGTH(manager_rejection_reason) >= 10 AND LENGTH(manager_rejection_reason) <= 500)),
    hr_status VARCHAR(20) NOT NULL DEFAULT 'PENDING_HR' CHECK (hr_status IN ('PENDING_HR', 'APPROVED_HR', 'REJECTED_HR', 'CANCELLED')),
    hr_approved_at TIMESTAMPTZ,
    hr_rejection_reason TEXT CHECK (hr_rejection_reason IS NULL OR (LENGTH(hr_rejection_reason) >= 10 AND LENGTH(hr_rejection_reason) <= 500)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    
    -- Foreign Key Constraints
    CONSTRAINT fk_leave_requests_company_id 
        FOREIGN KEY (company_id) REFERENCES companies(id) 
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_leave_requests_employee_id 
        FOREIGN KEY (employee_id) REFERENCES employees(id) 
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_leave_requests_manager_approver_id 
        FOREIGN KEY (manager_approver_id) REFERENCES employees(id) 
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_leave_requests_hr_approver_id 
        FOREIGN KEY (hr_approver_id) REFERENCES employees(id) 
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_leave_requests_created_by 
        FOREIGN KEY (created_by) REFERENCES employees(id) 
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_leave_requests_updated_by 
        FOREIGN KEY (updated_by) REFERENCES employees(id) 
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_leave_requests_deleted_by 
        FOREIGN KEY (deleted_by) REFERENCES employees(id) 
        ON DELETE SET NULL ON UPDATE CASCADE
);

-- Create indexes (see Section 9 for complete index strategy)
-- Primary key index is automatically created
CREATE INDEX idx_leave_requests_company_id ON leave_requests(company_id);
CREATE INDEX idx_leave_requests_employee_id ON leave_requests(employee_id);
CREATE INDEX idx_leave_requests_manager_approver_id ON leave_requests(manager_approver_id);
CREATE INDEX idx_leave_requests_hr_approver_id ON leave_requests(hr_approver_id);
CREATE INDEX idx_leave_requests_created_by ON leave_requests(created_by);
CREATE INDEX idx_leave_requests_updated_by ON leave_requests(updated_by);
CREATE INDEX idx_leave_requests_deleted_by ON leave_requests(deleted_by);
CREATE INDEX idx_leave_requests_updated_at ON leave_requests(updated_at);
CREATE INDEX idx_leave_requests_created_at ON leave_requests(created_at);
CREATE INDEX idx_leave_requests_deleted_at ON leave_requests(deleted_at);

-- Composite indexes
CREATE INDEX idx_leave_requests_company_status_active 
    ON leave_requests(company_id, manager_status, hr_status) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_leave_requests_employee_date_range 
    ON leave_requests(employee_id, start_date, end_date) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_leave_requests_approver_pending 
    ON leave_requests(manager_approver_id, manager_status) 
    WHERE deleted_at IS NULL AND manager_status = 'PENDING_MANAGER';
CREATE INDEX idx_leave_requests_hr_approver_pending 
    ON leave_requests(hr_approver_id, hr_status) 
    WHERE deleted_at IS NULL AND hr_status = 'PENDING_HR' AND manager_status = 'APPROVED_MANAGER';
CREATE INDEX idx_leave_requests_company_created_at 
    ON leave_requests(company_id, created_at DESC) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_leave_requests_active 
    ON leave_requests(id) 
    WHERE deleted_at IS NULL;

-- Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_leave_requests_updated_at
    BEFORE UPDATE ON leave_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

**END OF DOCUMENT**

