================================================================================
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                    DATABASE DESIGN SPECIFICATION                           ║
║                                                                            ║
║                      F-010 — Attendance Management                        ║
║                                                                            ║
║                          officeWorld Platform                              ║
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
║  Document Title:    Database Design Specification — F-010 Attendance      ║
║                     Management                                              ║
╠════════════════════════════════════════════════════════════════════════════╣
║  Project Name:      officeWorld                                            ║
║  Feature:           F-010 — Attendance Management                         ║
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
║  Document ID:       F10-DB-SPEC-001                                        ║
║  Version:           1.0                                                     ║
║  Date:              2024-01-20                                             ║
║  Author:            Enterprise Database Architect                          ║
║  Reviewer:          TBD                                                    ║
║  Approver:          TBD                                                    ║
║  Status:            Draft                                                  ║
║  Classification:    Internal                                               ║
╠════════════════════════════════════════════════════════════════════════════╣
║  Revision History                                                          ║
╠════════════════════════════════════════════════════════════════════════════╣
║  Version  Date        Author          Description                          ║
║  ───────  ──────────  ──────────────  ──────────────────────────────────── ║
║  1.0      2024-01-20  DB Architect    Initial database design              ║
╚════════════════════════════════════════════════════════════════════════════╝

================================================================================
                        SECTION 3 — INTRODUCTION
================================================================================

### 3.1 Purpose

This document defines the database design specification for the Attendance Management 
feature (F-010) within the officeWorld multi-tenant SaaS platform. The design follows 
Microsoft Azure Data Architecture principles, PostgreSQL 3NF normalization standards, 
and implements enterprise-grade patterns for multi-tenancy, audit logging, and soft deletion.

### 3.2 Scope

This specification covers the database schema for:

- **Attendance Tracking**: Daily presence records for employees with server-time–driven 
  check-in and check-out events
- **Attendance Logs**: Immutable, append-only event log for all attendance actions with 
  contextual metadata
- **Auto Check-Out**: System-initiated check-out at employee's local midnight if manual 
  check-out is missed
- **Multi-Tenancy**: Company-scoped attendance data with strict isolation
- **Soft Deletion**: Logical removal while preserving historical data for compliance

**Dependencies:**
- F-002 — RBAC & Permission Engine (role-based access control)
- F-005 — Employee Management (employee identity, timezone, activation status)
- Companies table (from core platform, tenant boundary)
- Employees table (from F-005, attendance owners)
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

### 3.4 Database Technology

- Database System: PostgreSQL
- Architecture: Microsoft Azure Data Architecture
- Normalization: Third Normal Form (3NF)
- Naming Convention: snake_case (lowercase with underscores)

================================================================================
                        SECTION 4 — SYSTEM OVERVIEW
================================================================================

### 4.1 Business Context

The Attendance Management feature provides a reliable, server-time–driven attendance 
tracking system that records employee presence per day using immutable check-in and 
check-out events. It ensures accurate worked-time calculation across refreshes and 
sessions, enforces strict role-based visibility (excluding SuperAdmin), automatically 
handles missed check-outs at midnight, and avoids approvals, edits, or payroll coupling.

### 4.2 Key Business Rules

**Attendance Rules:**
- Exactly one attendance record exists per employee per day
- Only one check-in and one check-out per day per employee
- Check-out is mandatory (auto check-out at employee's local midnight if missed)
- Attendance records are immutable after CHECKED_OUT status
- Status transitions are linear and irreversible: NOT_STARTED → CHECKED_IN → CHECKED_OUT
- Attendance is calculated using employee's local timezone
- Day resets at employee's local midnight

**Attendance Log Rules:**
- Immutable, append-only log that records every attendance action
- All actions are immutable once logged
- AUTO_CHECK_OUT is system-generated at local midnight
- Includes contextual metadata: location, IP address, device info, notes

**Access Control Rules:**
- Employees: Can view only their own attendance (today and history)
- Managers: Can view attendance for all employees in their scope
- HR/CEO: Full attendance visibility across the company
- SuperAdmin: Cannot access or view attendance data (explicitly excluded)
- Deactivated Employees: Cannot view attendance history or perform check-in/check-out actions
- Historical attendance data remains stored even after employee deactivation

**Multi-Tenancy:**
- Attendance records are company-scoped (company_id required)
- All attendance operations are filtered by company context from JWT token
- Company deletion should preserve attendance history (RESTRICT or application-level handling)

### 4.3 Data Flow

- Attendance creation occurs when employee checks in for the day
- Check-in creates or updates attendance record to CHECKED_IN status
- Check-out updates attendance record to CHECKED_OUT status
- Auto check-out occurs at employee's local midnight if manual check-out is missed
- Each attendance action (check-in, check-out, auto check-out) creates an AttendanceLog entry
- Attendance records become immutable after CHECKED_OUT status
- Worked time is calculated as duration between check_in_time and check_out_time
- Soft deletion preserves historical data for compliance

### 4.4 Key Entities

1. **Attendance**: One-per-day attendance record for an employee, driven entirely by 
   server timestamps. Exactly one attendance record exists per employee per day.

2. **AttendanceLog**: Immutable, append-only event log for attendance actions with 
   contextual metadata for audit and traceability. Includes both manual and automatic actions.

================================================================================
                        SECTION 5 — NON-FUNCTIONAL REQUIREMENTS
================================================================================

### 5.1 Performance Requirements

- Support for high-volume attendance queries with pagination
- Efficient filtering by employee_id, company_id, attendance_date, status
- Fast lookup by employee_id and attendance_date (unique constraint)
- Optimized queries for role-based visibility (Employee sees own, Manager/HR/CEO see company)
- Efficient filtering of soft-deleted records (exclude is_deleted=true records)
- Fast lookup by attendance_id for detail views with logs
- Efficient JOINs with employees and companies tables
- Support for date range queries (start_date, end_date filtering)

### 5.2 Scalability Requirements

- No specific partitioning or sharding requirements at this stage
- Design supports future horizontal scaling if needed
- Index strategy optimized for common query patterns
- Composite indexes for multi-column filtering and sorting
- Support for high-volume daily attendance records (expected: 100-1000 employees per company)

### 5.3 Data Integrity Requirements

- Referential integrity enforced through foreign key constraints
- UNIQUE constraint on (employee_id, attendance_date) prevents duplicate attendance per day
- Check constraints for all ENUM fields (status, action_type)
- Immutable fields (attendance becomes immutable after CHECKED_OUT) enforced at application level
- Soft deletion preserves historical data (no cascade deletion)
- Company scoping ensures data isolation per tenant
- Exactly one attendance per employee per day (enforced at database level)

### 5.4 Audit Requirements

All tables include complete audit trail:
- created_at: Timestamp when record was created (TIMESTAMPTZ)
- updated_at: Timestamp when record was last updated (TIMESTAMPTZ)
- created_by: User ID who created the record (UUID, nullable, FK to users.id)
- updated_by: User ID who last updated the record (UUID, nullable, FK to users.id)
- deleted_at: Timestamp when record was soft-deleted (TIMESTAMPTZ, nullable)
- deleted_by: User ID who soft-deleted the record (UUID, nullable, FK to users.id)
- is_deleted: Soft delete flag (BOOLEAN, defaults to false)

**Note:** Soft deletion is supported. Soft-deleted records are preserved for compliance 
and historical tracking. AttendanceLog records are immutable and append-only, so 
updated_at and updated_by may remain unchanged after creation.

### 5.5 Security Requirements

- Company scoping ensures data isolation per tenant
- Foreign key constraints prevent orphaned records
- Soft deletion preserves data for compliance and historical tracking
- Role-based access control handled by F-002 (RBAC & Permission Engine)
- SuperAdmin explicitly excluded from all attendance endpoints (enforced at application level)
- Deactivated employees cannot access attendance features (enforced at application level)
- Historical attendance data remains stored even after employee deactivation

### 5.6 Availability Requirements

- Standard PostgreSQL high-availability configurations apply
- No special clustering requirements specified
- Soft deletion preserves data for compliance and audit purposes

================================================================================
                        SECTION 6 — LOGICAL DATA MODEL
================================================================================

### 6.1 Entity Relationships

The logical data model consists of two main entities for this feature:

1. **Company** (1) ←→ (*) **Attendance**
   - Each company has many attendance records
   - One attendance record belongs to exactly one company
   - Relationship: Required (company_id is NOT NULL)
   - Foreign Key: attendance.company_id → companies.id
   - Action: ON DELETE RESTRICT (preserve attendance history when company deleted)
   - Action: ON UPDATE CASCADE (propagate company ID changes)

2. **Employee** (1) ←→ (*) **Attendance**
   - Each employee has many attendance records (one per day)
   - One attendance record belongs to exactly one employee
   - Relationship: Required (employee_id is NOT NULL)
   - Foreign Key: attendance.employee_id → employees.id
   - Action: ON DELETE RESTRICT (preserve attendance history when employee deleted)
   - Action: ON UPDATE CASCADE (propagate employee ID changes)

3. **Attendance** (1) ←→ (*) **AttendanceLog**
   - One attendance record has many attendance log entries
   - One attendance log entry belongs to exactly one attendance record
   - Relationship: Required (attendance_id is NOT NULL)
   - Foreign Key: attendance_logs.attendance_id → attendance.id
   - Action: ON DELETE RESTRICT (preserve log history when attendance deleted)
   - Action: ON UPDATE CASCADE (propagate attendance ID changes)

4. **Employee** (1) ←→ (*) **AttendanceLog**
   - Each employee has many attendance log entries
   - One attendance log entry belongs to exactly one employee
   - Relationship: Required (employee_id is NOT NULL)
   - Foreign Key: attendance_logs.employee_id → employees.id
   - Action: ON DELETE RESTRICT (preserve log history when employee deleted)
   - Action: ON UPDATE CASCADE (propagate employee ID changes)

### 6.2 Key Business Rules

**Uniqueness Constraints:**
- Attendance record must be unique per employee per day
- Enforced via UNIQUE constraint: (employee_id, attendance_date)

**Status Constraints:**
- Status must be one of: NOT_STARTED, CHECKED_IN, CHECKED_OUT
- Enforced via CHECK constraint

**Action Type Constraints:**
- Action type must be one of: CHECK_IN, CHECK_OUT, AUTO_CHECK_OUT
- Enforced via CHECK constraint

**Referential Constraints:**
- company_id must reference existing company
- employee_id must reference existing employee
- attendance_id must reference existing attendance record
- All enforced via FOREIGN KEY constraints

**Immutable Fields:**
- Attendance records become immutable after CHECKED_OUT status (enforced at application level)
- AttendanceLog records are immutable once created (append-only)

**Soft Deletion:**
- Both tables support soft deletion (is_deleted BOOLEAN marker)
- Soft-deleted records (is_deleted = true) are excluded from standard queries
- Soft deletion preserves historical data for compliance

### 6.3 Entity Attributes

**Attendance Entity:**
- Primary Key: id (UUID)
- Foreign Keys: company_id, employee_id, created_by, updated_by, deleted_by
- Business Fields: attendance_date, check_in_time, check_out_time, status, worked_time, is_auto_check_out
- Audit Fields: created_at, updated_at, deleted_at, created_by, updated_by, deleted_by, is_deleted

**AttendanceLog Entity:**
- Primary Key: id (UUID)
- Foreign Keys: attendance_id, employee_id, created_by, updated_by, deleted_by
- Business Fields: action_type, action_time, location, ip_address, device_info, notes, is_auto_action
- Audit Fields: created_at, updated_at, deleted_at, created_by, updated_by, deleted_by, is_deleted

================================================================================
                        SECTION 7 — PHYSICAL DATA MODEL
================================================================================

### 7.1 Table: attendance

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique attendance identifier |
| employee_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES employees(id) | Attending employee ID (required, immutable) |
| company_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES companies(id) | Owning company ID (required, immutable) |
| attendance_date | DATE | No | No | No | - | NOT NULL | Local calendar date (derived from employee timezone, required) |
| check_in_time | TIMESTAMPTZ | No | No | Yes | NULL | - | Server timestamp of check-in (UTC, nullable if not checked in) |
| check_out_time | TIMESTAMPTZ | No | No | Yes | NULL | - | Server timestamp of check-out (UTC, auto-set at midnight if missed, nullable if not checked out) |
| status | VARCHAR(20) | No | No | No | 'NOT_STARTED' | NOT NULL, CHECK (status IN ('NOT_STARTED', 'CHECKED_IN', 'CHECKED_OUT')) | Attendance lifecycle state, ENUM-controlled |
| worked_time | VARCHAR(20) | No | No | Yes | NULL | - | Derived duration between check-in and check-out (e.g., "9h 29m"), read-only, nullable if not checked out |
| is_auto_check_out | BOOLEAN | No | No | No | false | NOT NULL | Flag indicating if check-out was automatic (defaults to false) |
| is_deleted | BOOLEAN | No | No | No | false | NOT NULL | Soft delete flag, defaults to false |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted (NULL if active) |
| created_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who created the record |
| updated_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who last updated the record |
| deleted_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who soft-deleted the record |

**Foreign Key Constraints:**
- employee_id → employees(id) ON DELETE RESTRICT ON UPDATE CASCADE
- company_id → companies(id) ON DELETE RESTRICT ON UPDATE CASCADE
- created_by → users(id) ON DELETE SET NULL ON UPDATE CASCADE
- updated_by → users(id) ON DELETE SET NULL ON UPDATE CASCADE
- deleted_by → users(id) ON DELETE SET NULL ON UPDATE CASCADE

**Additional Constraints:**
- UNIQUE constraint on `(employee_id, attendance_date)` WHERE is_deleted = false (enforces exactly one attendance per employee per day, excluding soft-deleted records)
- CHECK constraint on `status` to ensure valid ENUM values: NOT_STARTED, CHECKED_IN, CHECKED_OUT
- Business rule: `employee_id` and `company_id` are immutable after creation (enforced at application level)
- Business rule: Attendance records become immutable after CHECKED_OUT status (enforced at application level)
- Business rule: `attendance_date` must be valid calendar date (not future date for check-in/check-out, enforced at application level)
- Business rule: `check_out_time` must be after `check_in_time` if both are set (enforced at application level)
- Business rule: `worked_time` is calculated as duration between `check_in_time` and `check_out_time` (enforced at application level)

**Field Categories:**
- **Primary Key**: `id`
- **Foreign Keys**: `employee_id`, `company_id`, `created_by`, `updated_by`, `deleted_by`
- **Immutable Fields**: `employee_id`, `company_id` (cannot be changed after creation)
- **Business Fields**: `attendance_date`, `check_in_time`, `check_out_time`, `status`, `worked_time`, `is_auto_check_out`
- **Lifecycle Fields**: `is_deleted` (soft delete flag)
- **Audit Fields**: `created_at`, `updated_at`, `deleted_at`, `created_by`, `updated_by`, `deleted_by`

### 7.2 Table: attendance_logs

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique attendance log identifier |
| attendance_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES attendance(id) | Related attendance record ID (required) |
| employee_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES employees(id) | Acting employee ID (required) |
| action_type | VARCHAR(20) | No | No | No | - | NOT NULL, CHECK (action_type IN ('CHECK_IN', 'CHECK_OUT', 'AUTO_CHECK_OUT')) | Attendance action type, ENUM-controlled |
| action_time | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Server timestamp of action (UTC, required) |
| location | VARCHAR(500) | No | No | Yes | NULL | - | Optional location information (free text, max 500 characters, nullable) |
| ip_address | VARCHAR(45) | No | No | Yes | NULL | - | Client IP address (IPv4 or IPv6 format, max 45 characters, nullable) |
| device_info | VARCHAR(255) | No | No | Yes | NULL | - | Client device details (free text, max 255 characters, nullable) |
| notes | VARCHAR(1000) | No | No | Yes | NULL | - | System notes (free text, max 1000 characters, nullable) |
| is_auto_action | BOOLEAN | No | No | No | false | NOT NULL | Flag indicating if action was automatic (defaults to false) |
| is_deleted | BOOLEAN | No | No | No | false | NOT NULL | Soft delete flag, defaults to false |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated (may remain unchanged for immutable records) |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted (NULL if active) |
| created_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who created the record (system-generated actions may have NULL) |
| updated_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who last updated the record (may remain NULL for immutable records) |
| deleted_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who soft-deleted the record |

**Foreign Key Constraints:**
- attendance_id → attendance(id) ON DELETE RESTRICT ON UPDATE CASCADE
- employee_id → employees(id) ON DELETE RESTRICT ON UPDATE CASCADE
- created_by → users(id) ON DELETE SET NULL ON UPDATE CASCADE
- updated_by → users(id) ON DELETE SET NULL ON UPDATE CASCADE
- deleted_by → users(id) ON DELETE SET NULL ON UPDATE CASCADE

**Additional Constraints:**
- CHECK constraint on `action_type` to ensure valid ENUM values: CHECK_IN, CHECK_OUT, AUTO_CHECK_OUT
- Business rule: AttendanceLog records are immutable once created (append-only, enforced at application level)
- Business rule: `action_time` must be valid timestamp (enforced at application level)
- Business rule: `ip_address` must be valid IPv4 or IPv6 format if provided (enforced at application level)
- Business rule: `is_auto_action` must be true when `action_type` is AUTO_CHECK_OUT (enforced at application level)

**Field Categories:**
- **Primary Key**: `id`
- **Foreign Keys**: `attendance_id`, `employee_id`, `created_by`, `updated_by`, `deleted_by`
- **Business Fields**: `action_type`, `action_time`, `location`, `ip_address`, `device_info`, `notes`, `is_auto_action`
- **Lifecycle Fields**: `is_deleted` (soft delete flag)
- **Audit Fields**: `created_at`, `updated_at`, `deleted_at`, `created_by`, `updated_by`, `deleted_by`

================================================================================
                        SECTION 8 — NORMALIZATION
================================================================================

### 8.1 Normalization Verification

All tables are verified against Third Normal Form (3NF) requirements:

#### 8.1.1 Table: attendance

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

**Normalization Status: ✅ PASS (3NF Compliant)**

**Rationale:**
- All fields are atomic and directly related to the attendance entity
- No redundant data or calculated fields stored (worked_time is stored for performance but can be recalculated)
- No transitive dependencies exist
- Foreign key relationships properly reference other entities (Employee, Company)
- Design follows 3NF normalization principles

#### 8.1.2 Table: attendance_logs

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

**Normalization Status: ✅ PASS (3NF Compliant)**

**Rationale:**
- All fields are atomic and directly related to the attendance log entity
- No redundant data or calculated fields stored
- No transitive dependencies exist
- Foreign key relationships properly reference other entities (Attendance, Employee)
- Design follows 3NF normalization principles

================================================================================
                        SECTION 9 — INDEX STRATEGY
================================================================================

### 9.1 Primary Key Indexes

**Table: attendance**
```sql
CREATE UNIQUE INDEX pk_attendance ON attendance(id);
```
- Automatically created by PostgreSQL PRIMARY KEY constraint
- Ensures unique identification of each attendance record

**Table: attendance_logs**
```sql
CREATE UNIQUE INDEX pk_attendance_logs ON attendance_logs(id);
```
- Automatically created by PostgreSQL PRIMARY KEY constraint
- Ensures unique identification of each attendance log entry

### 9.2 Foreign Key Indexes

**CRITICAL:** Every foreign key column MUST have an index for JOIN performance:

**Table: attendance**
```sql
CREATE INDEX idx_attendance_employee_id ON attendance(employee_id);
CREATE INDEX idx_attendance_company_id ON attendance(company_id);
CREATE INDEX idx_attendance_created_by ON attendance(created_by);
CREATE INDEX idx_attendance_updated_by ON attendance(updated_by);
CREATE INDEX idx_attendance_deleted_by ON attendance(deleted_by);
```
- Improves JOIN performance for employee and company lookups
- Enhances referential integrity check performance
- Optimizes audit trail queries

**Table: attendance_logs**
```sql
CREATE INDEX idx_attendance_logs_attendance_id ON attendance_logs(attendance_id);
CREATE INDEX idx_attendance_logs_employee_id ON attendance_logs(employee_id);
CREATE INDEX idx_attendance_logs_created_by ON attendance_logs(created_by);
CREATE INDEX idx_attendance_logs_updated_by ON attendance_logs(updated_by);
CREATE INDEX idx_attendance_logs_deleted_by ON attendance_logs(deleted_by);
```
- Improves JOIN performance for attendance and employee lookups
- Enhances referential integrity check performance
- Optimizes audit trail queries

### 9.3 Unique Constraint Indexes

**Table: attendance**
```sql
CREATE UNIQUE INDEX uq_attendance_employee_date ON attendance(employee_id, attendance_date) WHERE is_deleted = false;
```
- Ensures exactly one attendance record per employee per day (excluding soft-deleted records)
- Partial index excludes soft-deleted records for better performance

### 9.4 Audit Field Indexes

**MANDATORY:** Every table with `updated_at` MUST have an index:

**Table: attendance**
```sql
CREATE INDEX idx_attendance_updated_at ON attendance(updated_at);
```
- Essential for incremental sync and change tracking
- Supports ETag-based conditional requests
- Enables efficient queries for recently updated attendance records

**Table: attendance_logs**
```sql
CREATE INDEX idx_attendance_logs_updated_at ON attendance_logs(updated_at);
```
- Essential for incremental sync and change tracking
- Supports ETag-based conditional requests
- Enables efficient queries for recently updated log entries

### 9.5 Query Optimization Indexes

**Table: attendance**
```sql
CREATE INDEX idx_attendance_is_deleted ON attendance(is_deleted);
CREATE INDEX idx_attendance_status ON attendance(status);
CREATE INDEX idx_attendance_attendance_date ON attendance(attendance_date DESC);
CREATE INDEX idx_attendance_check_in_time ON attendance(check_in_time);
CREATE INDEX idx_attendance_check_out_time ON attendance(check_out_time);
CREATE INDEX idx_attendance_is_auto_check_out ON attendance(is_auto_check_out);
CREATE INDEX idx_attendance_created_at ON attendance(created_at DESC);
```
- Optimizes filtering by soft-delete status
- Supports filtering by status (NOT_STARTED, CHECKED_IN, CHECKED_OUT)
- Supports sorting by attendance date (newest first)
- Optimizes queries filtering by check-in/check-out times
- Supports filtering by auto check-out flag
- Supports sorting by creation date (newest first)

**Table: attendance_logs**
```sql
CREATE INDEX idx_attendance_logs_is_deleted ON attendance_logs(is_deleted);
CREATE INDEX idx_attendance_logs_action_type ON attendance_logs(action_type);
CREATE INDEX idx_attendance_logs_action_time ON attendance_logs(action_time DESC);
CREATE INDEX idx_attendance_logs_is_auto_action ON attendance_logs(is_auto_action);
CREATE INDEX idx_attendance_logs_created_at ON attendance_logs(created_at DESC);
```
- Optimizes filtering by soft-delete status
- Supports filtering by action type (CHECK_IN, CHECK_OUT, AUTO_CHECK_OUT)
- Supports sorting by action time (newest first)
- Supports filtering by auto action flag
- Supports sorting by creation date (newest first)

### 9.6 Composite Indexes

**Table: attendance**
```sql
CREATE INDEX idx_attendance_company_active ON attendance(company_id, is_deleted) WHERE is_deleted = false;
CREATE INDEX idx_attendance_company_date ON attendance(company_id, attendance_date DESC) WHERE is_deleted = false;
CREATE INDEX idx_attendance_company_status ON attendance(company_id, status) WHERE is_deleted = false;
CREATE INDEX idx_attendance_employee_date ON attendance(employee_id, attendance_date DESC) WHERE is_deleted = false;
CREATE INDEX idx_attendance_employee_status ON attendance(employee_id, status) WHERE is_deleted = false;
CREATE INDEX idx_attendance_date_status ON attendance(attendance_date, status) WHERE is_deleted = false;
```
- Optimizes common query pattern: filter by company and exclude soft-deleted
- Supports company-scoped date range queries
- Supports company-scoped status filtering
- Supports employee-scoped date range queries
- Supports employee-scoped status filtering
- Supports date and status filtering together
- Partial indexes exclude soft-deleted records for better performance

**Table: attendance_logs**
```sql
CREATE INDEX idx_attendance_logs_attendance_active ON attendance_logs(attendance_id, is_deleted) WHERE is_deleted = false;
CREATE INDEX idx_attendance_logs_attendance_type ON attendance_logs(attendance_id, action_type) WHERE is_deleted = false;
CREATE INDEX idx_attendance_logs_attendance_time ON attendance_logs(attendance_id, action_time) WHERE is_deleted = false;
CREATE INDEX idx_attendance_logs_employee_active ON attendance_logs(employee_id, is_deleted) WHERE is_deleted = false;
CREATE INDEX idx_attendance_logs_employee_type ON attendance_logs(employee_id, action_type) WHERE is_deleted = false;
```
- Optimizes queries filtering by attendance and excluding soft-deleted
- Supports filtering logs by attendance and action type
- Supports sorting logs by attendance and action time
- Supports filtering logs by employee and excluding soft-deleted
- Supports filtering logs by employee and action type
- Partial indexes exclude soft-deleted records for better performance

### 9.7 Index Summary

**Total Indexes:**
- attendance: 18 indexes (1 PK, 5 FK, 1 unique, 1 audit, 6 query optimization, 4 composite)
- attendance_logs: 15 indexes (1 PK, 5 FK, 0 unique, 1 audit, 5 query optimization, 3 composite)

**Index Strategy Rationale:**
- Foreign key indexes are critical for JOIN performance
- Audit field indexes (updated_at) are mandatory for change tracking
- Composite indexes optimize common query patterns (company + date, employee + date, etc.)
- Partial indexes (WHERE is_deleted = false) improve performance by excluding soft-deleted records
- Date indexes support efficient date range queries and sorting

================================================================================
                        SECTION 10 — ENTITY RELATIONSHIP DIAGRAM (ERD)
================================================================================

See separate ERD file: `ERD_F10_Attendance_Management.txt`

The ERD shows only Primary Key (id) and Foreign Key fields per db_instruction.md rules.

**Relationship Summary:**
- Company 1..* Attendance (One Company has many Attendance records)
- Employee 1..* Attendance (One Employee has many Attendance records)
- Attendance 1..* AttendanceLog (One Attendance has many AttendanceLog entries)
- Employee 1..* AttendanceLog (One Employee has many AttendanceLog entries)

**Key Relationships:**
- attendance.company_id → companies.id (ON DELETE RESTRICT, ON UPDATE CASCADE)
- attendance.employee_id → employees.id (ON DELETE RESTRICT, ON UPDATE CASCADE)
- attendance_logs.attendance_id → attendance.id (ON DELETE RESTRICT, ON UPDATE CASCADE)
- attendance_logs.employee_id → employees.id (ON DELETE RESTRICT, ON UPDATE CASCADE)

================================================================================
                        END OF DOCUMENT
================================================================================

**Document Version:** 1.0  
**Last Updated:** 2024-01-20  
**Feature:** F-010 — Attendance Management  
**Status:** Draft

