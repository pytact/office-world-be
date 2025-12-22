================================================================================
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                    DATABASE DESIGN DOCUMENT                               ║
║                                                                            ║
║                    officeWorld                                             ║
║                    F-005 — Employee Management                              ║
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
| Document Title           | Database Design Document — officeWorld    |
| Feature                  | F-005 — Employee Management               |
| Version                  | 1.0                                      |
| Date                     | 2024                                     |
| Database System          | PostgreSQL                               |
| Architecture             | Microsoft Azure Data Architecture        |
| Normalization Level      | Third Normal Form (3NF)                  |
| Document Status          | Draft                                    |
| Prepared By              | Enterprise Database Architect            |
| Reviewed By              | TBD                                      |
| Approved By              | TBD                                      |

================================================================================
SECTION 3 — INTRODUCTION
================================================================================

3.1 Purpose

This document provides the complete database design specification for the 
officeWorld platform's Employee Management feature (F-005). It defines the 
physical data model, table structures, relationships, constraints, indexes, 
and normalization approach for managing company-bound employee records within 
a multi-tenant SaaS environment.

3.2 Scope

This specification covers:
- Employee entity as company-bound personnel record linked one-to-one with User
- Employee lifecycle management (creation, activation, deactivation, soft deletion)
- Professional and personal employee data fields
- Separation management (resignation, termination)
- Complete audit trail (created_at, updated_at, created_by, updated_by, deleted_at, deleted_by)
- Soft deletion support (logical removal while preserving historical data)
- Multi-tenancy isolation through company boundaries
- One-to-one User ↔ Employee constraint enforcement

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

officeWorld Employee Management provides a secure, company-bound employee system 
of record that maintains accurate personnel data, enforces strict role-based 
visibility, and preserves historical information while supporting downstream 
features such as salary, leave, and attendance management.

4.2 Core Business Rules

- Every non-SuperAdmin user must have exactly one employee record
- SuperAdmin must not exist in the employee table
- Employee records are always linked to exactly one company
- One-to-one User ↔ Employee relationship (enforced at database level)
- JoiningDate is mandatory and immutable after creation
- WorkEmail must be unique within company (case-insensitive)
- If employment_status is RESIGNED or TERMINATED, separation_initiated_date and 
  separation_reason are required
- Soft-deleted employees (is_deleted=true) are hidden from standard lists
- Deactivated employees (is_active=false) cannot log in but retain all data
- Managers cannot view or edit personal data, salary data, or documents (enforced 
  at application level)
- Soft-deleted employees are not visible to anyone (including CEO) after soft delete

4.3 Key Entities

1. **Employee**: Company-bound personnel record linked one-to-one with a User. 
   Employee is the authoritative source of personal and professional data and 
   drives access to HR-related workflows.

4.4 Relationships

- Employee belongs to exactly one Company (required, immutable)
- Employee is linked to exactly one User (required, one-to-one, immutable)
- Employee role mirrors User role (access control owned by F-001)

================================================================================
SECTION 5 — NON-FUNCTIONAL REQUIREMENTS
================================================================================

5.1 Performance Requirements

- Support for high-volume employee queries with pagination
- Efficient filtering by department, employment_status, search by name/email
- Fast lookup by user_id (one-to-one constraint)
- Optimized queries for employee listing with role-based filtering
- Efficient soft-delete filtering (exclude is_deleted=true records)
- Manager role filtering (excluding CEO/HR) should be efficient

5.2 Scalability Requirements

- No specific partitioning or sharding requirements at this stage
- Design supports future horizontal scaling if needed
- Index strategy optimized for common query patterns
- WorkEmail uniqueness constraint optimized for company-scoped lookups

5.3 Data Integrity Requirements

- Referential integrity enforced through foreign key constraints
- Unique constraint on user_id (one-to-one User ↔ Employee)
- Unique constraint on work_email within company (case-insensitive)
- Check constraints for all ENUM fields
- One-to-one User ↔ Employee constraint enforced at database level
- Soft deletion preserves historical data (no cascade deletion)

5.4 Audit Requirements

All tables include complete audit trail:
- created_at: Timestamp when record was created
- updated_at: Timestamp when record was last updated
- created_by: User ID who created the record (FK to users.id)
- updated_by: User ID who last updated the record (FK to users.id)
- deleted_at: Timestamp when record was soft-deleted (NULL if active)
- deleted_by: User ID who soft-deleted the record (FK to users.id, NULL if active)

5.5 Security Requirements

- Immutable fields (user_id, company_id, joining_date) cannot be updated
- Soft deletion preserves data for compliance and historical tracking
- Foreign key constraints prevent orphaned records
- Company scoping ensures data isolation per tenant
- WorkEmail uniqueness prevents duplicate employee emails within company

5.6 Availability Requirements

- Standard PostgreSQL high-availability configurations apply
- No special clustering requirements specified

================================================================================
SECTION 6 — LOGICAL DATA MODEL
================================================================================

6.1 Entity Relationships

The logical data model consists of one main entity for this feature:

1. **Company** (1) ←→ (*) **Employee**
   - Each company has many employees
   - Employees must belong to a company (required)

2. **User** (1) ←→ (1) **Employee**
   - Each user has exactly one employee record
   - One-to-one relationship (enforced at database level)
   - SuperAdmin users do not have employee records

6.2 Key Business Rules

- Employee.user_id is unique (one-to-one constraint)
- Employee.company_id is required and immutable
- Employee.joining_date is mandatory and immutable
- Employee.work_email is unique within company (case-insensitive)
- Employee.employment_status controls separation field requirements
- Employee.is_active controls login access
- Employee.is_deleted controls visibility (soft delete)
- Soft-deleted employees are completely hidden from all endpoints

6.3 Data Flow

- Employee creation requires existing User and Company
- Employee defaults to active state (is_active: true) on creation
- Employee activation/deactivation updates is_active field
- Soft deletion sets is_deleted=true, deleted_at, deleted_by
- Separation fields are required when employment_status changes to RESIGNED/TERMINATED
- Profile updates by CEO/HR modify editable fields only

================================================================================
SECTION 7 — PHYSICAL DATA MODEL
================================================================================

### 7.1 Table: employees

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique employee identifier |
| user_id | UUID | No | Yes | No | - | NOT NULL, UNIQUE, REFERENCES users(id) | Linked User ID (one-to-one, required, immutable) |
| company_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES companies(id) | Owning company ID (required, immutable) |
| joining_date | DATE | No | No | No | - | NOT NULL | Employment start date (mandatory, immutable after creation) |
| employment_status | VARCHAR(20) | No | No | No | - | NOT NULL, CHECK (employment_status IN ('TRAINEE', 'PROBATION', 'CONFIRMED', 'NOTICE_PERIOD', 'ACTIVE', 'ON_HOLD', 'TERMINATED', 'RESIGNED')) | Current HR state, ENUM-controlled |
| job_title | VARCHAR(255) | No | No | Yes | NULL | - | Professional title, editable by HR/CEO, max 255 characters |
| department | VARCHAR(20) | No | No | Yes | NULL | CHECK (department IN ('FRONTEND', 'BACKEND', 'FULLSTACK', 'QA', 'HR', 'DEVOPS', 'UIUX', 'PRODUCT', 'MARKETING', 'DATA', 'SUPPORT')) | Functional department, ENUM-controlled |
| employment_type | VARCHAR(20) | No | No | Yes | NULL | CHECK (employment_type IN ('FULL_TIME', 'PART_TIME', 'CONTRACT', 'FREELANCE', 'TEMPORARY')) | Nature of employment, ENUM-controlled |
| employment_level | VARCHAR(20) | No | No | Yes | NULL | CHECK (employment_level IN ('INTERN', 'JUNIOR', 'MID', 'SENIOR', 'LEAD', 'MANAGER')) | Seniority level, ENUM-controlled |
| work_email | VARCHAR(254) | No | No | Yes | NULL | - | Official email, company-scoped, case-insensitive unique within company |
| gender | VARCHAR(10) | No | No | Yes | NULL | CHECK (gender IN ('MALE', 'FEMALE', 'OTHER')) | Gender identity, ENUM-controlled |
| marital_status | VARCHAR(20) | No | No | Yes | NULL | CHECK (marital_status IN ('SINGLE', 'MARRIED', 'DIVORCED', 'WIDOWED', 'SEPARATED')) | Marital status, ENUM-controlled |
| blood_group | VARCHAR(5) | No | No | Yes | NULL | CHECK (blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')) | Blood group, ENUM-controlled |
| nationality | VARCHAR(100) | No | No | Yes | NULL | - | Nationality, free text, max 100 characters |
| address | VARCHAR(500) | No | No | Yes | NULL | - | Residential address, restricted visibility, max 500 characters |
| city | VARCHAR(100) | No | No | Yes | NULL | - | City, API-based dropdown, max 100 characters |
| state | VARCHAR(100) | No | No | Yes | NULL | - | State, dependent dropdown, max 100 characters |
| country | VARCHAR(100) | No | No | Yes | NULL | - | Country, API-based dropdown, max 100 characters |
| document_type | VARCHAR(20) | No | No | Yes | NULL | CHECK (document_type IN ('AADHAAR', 'PAN', 'DL', 'VOTER_ID', 'PASSPORT')) | Identity document type, ENUM-controlled |
| document_number | VARCHAR(50) | No | No | Yes | NULL | - | Identity document reference, restricted visibility, max 50 characters |
| separation_initiated_date | DATE | No | No | Yes | NULL | - | Resignation submission or termination issue date, required if RESIGNED or TERMINATED |
| separation_reason | VARCHAR(500) | No | No | Yes | NULL | - | Reason for resignation or termination, mandatory if RESIGNED or TERMINATED, max 500 characters |
| last_working_day | DATE | No | No | Yes | NULL | - | Final working day, valid for resignation & termination |
| notice_period_days | INTEGER | No | No | Yes | NULL | CHECK (notice_period_days >= 0 AND notice_period_days <= 365) | Notice period duration, 0 allowed for immediate termination, min 0, max 365 |
| is_active | BOOLEAN | No | No | No | true | NOT NULL | System access state, controls login, defaults to true |
| is_deleted | BOOLEAN | No | No | No | false | NOT NULL | Soft delete flag, defaults to false |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted (NULL if active) |
| created_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who created the record |
| updated_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who last updated the record |
| deleted_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who soft-deleted the record |

**Foreign Key Constraints:**
- user_id → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- company_id → companies(id) ON DELETE RESTRICT ON UPDATE CASCADE
- created_by → users(id) ON DELETE SET NULL ON UPDATE CASCADE
- updated_by → users(id) ON DELETE SET NULL ON UPDATE CASCADE
- deleted_by → users(id) ON DELETE SET NULL ON UPDATE CASCADE

**Additional Constraints:**
- UNIQUE constraint on `user_id` (enforces one-to-one User ↔ Employee relationship)
- UNIQUE constraint on `(company_id, LOWER(work_email))` WHERE work_email IS NOT NULL (case-insensitive work_email uniqueness within company)
- CHECK constraint on `employment_status` to ensure valid ENUM values
- CHECK constraint on `department` to ensure valid ENUM values
- CHECK constraint on `employment_type` to ensure valid ENUM values
- CHECK constraint on `employment_level` to ensure valid ENUM values
- CHECK constraint on `gender` to ensure valid ENUM values
- CHECK constraint on `marital_status` to ensure valid ENUM values
- CHECK constraint on `blood_group` to ensure valid ENUM values
- CHECK constraint on `document_type` to ensure valid ENUM values
- CHECK constraint on `notice_period_days` to ensure range 0-365
- CHECK constraint on `is_active` to ensure only boolean values (true/false)
- CHECK constraint on `is_deleted` to ensure only boolean values (true/false)
- Business rule: `user_id`, `company_id`, and `joining_date` are immutable after creation (enforced at application level)
- Business rule: `separation_initiated_date` and `separation_reason` are required when `employment_status` is RESIGNED or TERMINATED (enforced at application level)
- Business rule: `work_email` must be valid RFC 5322 format (enforced at application level)
- Business rule: `joining_date` cannot be a future date (enforced at application level)

**Field Categories:**
- **Primary Key**: `id`
- **Foreign Keys**: `user_id`, `company_id`, `created_by`, `updated_by`, `deleted_by`
- **Immutable Fields**: `user_id`, `company_id`, `joining_date` (cannot be changed after creation)
- **Professional Fields**: `job_title`, `department`, `employment_type`, `employment_level`, `work_email`, `employment_status`
- **Personal Fields**: `gender`, `marital_status`, `blood_group`, `nationality`, `address`, `city`, `state`, `country`, `document_type`, `document_number`
- **Separation Fields**: `separation_initiated_date`, `separation_reason`, `last_working_day`, `notice_period_days` (required when status is RESIGNED or TERMINATED)
- **Lifecycle Fields**: `is_active`, `is_deleted` (CEO/HR only)
- **Audit Fields**: `created_at`, `updated_at`, `deleted_at`, `created_by`, `updated_by`, `deleted_by`

================================================================================
SECTION 8 — NORMALIZATION
================================================================================

### 8.1 Normalization Verification

All tables are verified against Third Normal Form (3NF) requirements:

#### 8.1.1 Table: employees

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
- All fields are atomic and directly related to the employee entity
- No redundant data or calculated fields stored
- No transitive dependencies exist
- Foreign key relationships properly reference other entities (User, Company)
- Design follows 3NF normalization principles

================================================================================
SECTION 9 — INDEX STRATEGY
================================================================================

### 9.1 Primary Key Indexes

**Table: employees**
```sql
CREATE UNIQUE INDEX pk_employees ON employees(id);
```
- Automatically created by PostgreSQL PRIMARY KEY constraint
- Ensures unique identification of each employee record

### 9.2 Foreign Key Indexes

**CRITICAL:** Every foreign key column MUST have an index for JOIN performance:

**Table: employees**
```sql
CREATE INDEX idx_employees_user_id ON employees(user_id);
CREATE INDEX idx_employees_company_id ON employees(company_id);
CREATE INDEX idx_employees_created_by ON employees(created_by);
CREATE INDEX idx_employees_updated_by ON employees(updated_by);
CREATE INDEX idx_employees_deleted_by ON employees(deleted_by);
```
- Improves JOIN performance for user and company lookups
- Enhances referential integrity check performance
- Optimizes audit trail queries

### 9.3 Unique Constraint Indexes

**Table: employees**
```sql
CREATE UNIQUE INDEX uq_employees_user_id ON employees(user_id);
CREATE UNIQUE INDEX uq_employees_company_work_email ON employees(company_id, LOWER(work_email)) WHERE work_email IS NOT NULL;
```
- Ensures one-to-one User ↔ Employee relationship
- Ensures case-insensitive work_email uniqueness within company
- Partial index excludes NULL work_email values

### 9.4 Audit Field Indexes

**MANDATORY:** Every table with `updated_at` MUST have an index:

**Table: employees**
```sql
CREATE INDEX idx_employees_updated_at ON employees(updated_at);
```
- Essential for incremental sync and change tracking
- Supports ETag-based conditional requests
- Enables efficient queries for recently updated employees

### 9.5 Query Optimization Indexes

**Table: employees**
```sql
CREATE INDEX idx_employees_is_deleted ON employees(is_deleted);
CREATE INDEX idx_employees_is_active ON employees(is_active);
CREATE INDEX idx_employees_employment_status ON employees(employment_status);
CREATE INDEX idx_employees_department ON employees(department);
CREATE INDEX idx_employees_created_at ON employees(created_at DESC);
```
- Optimizes filtering by soft-delete status
- Optimizes filtering by active/inactive status
- Supports filtering by employment status
- Supports filtering by department
- Supports sorting by creation date (newest first)

### 9.6 Composite Indexes

**Table: employees**
```sql
CREATE INDEX idx_employees_company_active ON employees(company_id, is_deleted) WHERE is_deleted = false;
CREATE INDEX idx_employees_company_status ON employees(company_id, employment_status) WHERE is_deleted = false;
CREATE INDEX idx_employees_company_department ON employees(company_id, department) WHERE is_deleted = false;
CREATE INDEX idx_employees_status_active ON employees(employment_status, is_active) WHERE is_deleted = false;
```
- Optimizes common query pattern: filter by company and exclude soft-deleted
- Supports company-scoped status filtering
- Supports company-scoped department filtering
- Supports status and active state filtering
- Partial indexes exclude soft-deleted records for better performance

### 9.7 Soft Delete Indexes

**Table: employees**
```sql
CREATE INDEX idx_employees_active ON employees(id) WHERE is_deleted = false;
CREATE INDEX idx_employees_company_active_list ON employees(company_id, created_at DESC) WHERE is_deleted = false;
```
- Partial index for active records only (excludes soft-deleted)
- Optimizes employee listing queries with company scoping
- Improves performance for standard employee queries

### 9.8 Text Search Indexes

**Table: employees**
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_employees_work_email_trgm ON employees USING gin(work_email gin_trgm_ops) WHERE work_email IS NOT NULL;
```
- Enables efficient case-insensitive partial text search on work_email
- Supports search functionality in employee listings
- Requires pg_trgm extension for trigram matching
- Partial index excludes NULL work_email values

### 9.9 Index Summary

| Table | Index Name | Columns | Type | Purpose |
|-------|------------|---------|------|---------|
| employees | pk_employees | id | UNIQUE | Primary key |
| employees | uq_employees_user_id | user_id | UNIQUE | One-to-one User constraint |
| employees | uq_employees_company_work_email | company_id, LOWER(work_email) | UNIQUE (partial) | Case-insensitive work_email uniqueness |
| employees | idx_employees_user_id | user_id | INDEX | Foreign key performance |
| employees | idx_employees_company_id | company_id | INDEX | Foreign key performance |
| employees | idx_employees_created_by | created_by | INDEX | Foreign key performance |
| employees | idx_employees_updated_by | updated_by | INDEX | Foreign key performance |
| employees | idx_employees_deleted_by | deleted_by | INDEX | Foreign key performance |
| employees | idx_employees_updated_at | updated_at | INDEX | Audit and ETag support |
| employees | idx_employees_is_deleted | is_deleted | INDEX | Soft-delete filtering |
| employees | idx_employees_is_active | is_active | INDEX | Active status filtering |
| employees | idx_employees_employment_status | employment_status | INDEX | Status filtering |
| employees | idx_employees_department | department | INDEX | Department filtering |
| employees | idx_employees_created_at | created_at DESC | INDEX | Creation date sorting |
| employees | idx_employees_company_active | company_id, is_deleted | COMPOSITE (partial) | Company + active filter |
| employees | idx_employees_company_status | company_id, employment_status | COMPOSITE (partial) | Company + status filter |
| employees | idx_employees_company_department | company_id, department | COMPOSITE (partial) | Company + department filter |
| employees | idx_employees_status_active | employment_status, is_active | COMPOSITE (partial) | Status + active filter |
| employees | idx_employees_active | id | PARTIAL | Active records only |
| employees | idx_employees_company_active_list | company_id, created_at DESC | COMPOSITE (partial) | Company listing optimization |
| employees | idx_employees_work_email_trgm | work_email | GIN (trigram) | Text search on work_email |

### 9.10 Index Maintenance

- Monitor index usage with `pg_stat_user_indexes`
- Rebuild indexes periodically if fragmentation occurs
- Partial indexes on `is_deleted = false` improve performance for active record queries
- Text search indexes (GIN) require more storage but provide fast search performance
- Composite indexes should be created based on actual query patterns observed in production

================================================================================
SECTION 10 — ENTITY RELATIONSHIP DIAGRAM (ERD)
================================================================================

See separate ERD document: `ERD_F5_Employee_Management.txt`

The ERD shows:
- Employee as the main entity
- Relationships to Company (1..*) and User (1..1)
- Only Primary Key (id) and Foreign Key fields are shown
- Business fields and audit fields are excluded per ERD rules

================================================================================
END OF DOCUMENT
================================================================================

