================================================================================
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                    DATABASE DESIGN SPECIFICATION                           ║
║                                                                            ║
║                         F-006 — Salary Management                          ║
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
║  Document Title:    Database Design Specification — F-006 Salary          ║
║                     Management                                             ║
╠════════════════════════════════════════════════════════════════════════════╣
║  Project Name:      office world                                           ║
║  Feature:           F-006 — Salary Management                              ║
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
║  Document ID:       F6-DB-SPEC-001                                         ║
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

This document defines the database design specification for the Salary Management 
feature (F-006) within the office world multi-tenant SaaS platform. The design 
follows Microsoft Azure Data Architecture principles, PostgreSQL 3NF normalization 
standards, and implements enterprise-grade patterns for multi-tenancy, audit 
logging, and data immutability.

### 3.2 Scope

This specification covers the database schema for:

- **Bank Information Management**: Employee bank account details for salary payments
- **Salary Configuration**: Time-based salary details with effective date ranges
- **Salary Payment Records**: Immutable monthly salary payment execution records
- **Salary History**: Immutable audit log of salary configuration changes

**Dependencies:**
- F-005 — Employee Management (employees table)
- F-002 — RBAC & Permission Engine (role-based access control)
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
- **Soft Delete**: All tables support soft deletion for audit compliance
- **Audit Trail**: Complete audit fields (created_at, updated_at, created_by, updated_by, deleted_at, deleted_by)
- **Data Immutability**: SalaryPayment and SalaryHistory are append-only
- **Referential Integrity**: Foreign key constraints with appropriate ON DELETE/ON UPDATE actions
- **Performance**: Comprehensive indexing strategy for foreign keys and audit fields

================================================================================
                        SECTION 4 — SYSTEM OVERVIEW
================================================================================

### 4.1 Business Purpose

The Salary Management system provides a secure, auditable, and time-based salary 
management solution that:

- Defines employee compensation with effective date ranges
- Maintains immutable salary history for compliance
- Manages bank account information for salary payments
- Executes monthly salary payments with automatic slip generation
- Enforces strict role-based access control (CEO and HR only)

### 4.2 System Architecture

**Multi-Tenant SaaS Platform:**
- Tenant boundary: Company (organization)
- Data isolation: Row-level security via company_id
- Access control: Role-based (SuperAdmin, CEO, HR, Manager, Employee)

**Key Entities:**
- **bank_info**: Employee bank account information (1:1 with employees)
- **salary_details**: Time-based salary configurations (1:M with employees)
- **salary_payments**: Monthly payment records (1:M with employees, immutable)
- **salary_history**: Audit log of salary changes (1:M with salary_details, immutable)

### 4.3 Data Flow

1. **Salary Configuration**: HR/CEO creates salary_details with effective dates
2. **Bank Information**: HR/CEO manages bank_info for employees
3. **Payment Execution**: HR/CEO creates salary_payments for specific month/year
4. **History Tracking**: System automatically creates salary_history on salary changes
5. **Audit Compliance**: All actions logged with created_by, updated_by, timestamps

### 4.4 Business Rules

| Rule ID | Description | Enforcement |
|---------|-------------|-------------|
| BR-601 | Salary amount represents monthly gross pay | Database constraint |
| BR-602 | Only one active SalaryDetails per employee | Application logic + unique constraint |
| BR-603 | Salary updates auto-close previous config | Application logic |
| BR-604 | Salary payments are immutable | Database constraint (no UPDATE/DELETE) |
| BR-605 | Only CEO and HR can create salary payments | Application-level authorization |
| BR-606 | Bank info updates affect future payments only | Application logic |
| BR-607 | Employees can view only their own salary data | Application-level authorization |
| BR-608 | Salary slip generated per salary payment | Application logic |

================================================================================
                        SECTION 5 — NON-FUNCTIONAL REQUIREMENTS
================================================================================

### 5.1 Performance Requirements

- **Query Performance**: Salary overview queries must complete within 500ms
- **Scalability**: Support for 10,000+ employees per company
- **Concurrent Access**: Support 100+ concurrent users per company
- **Index Strategy**: All foreign keys and audit fields indexed

### 5.2 Security Requirements

- **Data Encryption**: Strong encryption for bank and salary data (application-level)
- **Access Control**: Row-level security via company_id (multi-tenancy)
- **Audit Compliance**: Complete audit trail for all data changes
- **Sensitive Data**: Bank account numbers and IFSC codes stored encrypted

### 5.3 Availability Requirements

- **Uptime**: 99.9% availability target
- **Backup**: Daily automated backups with 30-day retention
- **Disaster Recovery**: Point-in-time recovery capability

### 5.4 Compliance Requirements

- **Audit Trail**: Immutable audit logs for salary changes
- **Data Retention**: Salary data retained per company policy
- **Soft Delete**: All tables support soft deletion for compliance
- **Immutability**: SalaryPayment and SalaryHistory are append-only

### 5.5 Data Integrity Requirements

- **Referential Integrity**: Foreign key constraints with appropriate actions
- **Data Validation**: CHECK constraints for ENUM values
- **Uniqueness**: Unique constraints for business rules (one active salary per employee)
- **Immutability**: Application-level enforcement for immutable records

================================================================================
                        SECTION 6 — LOGICAL DATA MODEL
================================================================================

### 6.1 Entity Relationship Overview

The Salary Management feature consists of 4 primary entities:

1. **bank_info**: Employee bank account information
2. **salary_details**: Time-based salary configurations
3. **salary_payments**: Monthly payment execution records
4. **salary_history**: Audit log of salary configuration changes

**External Dependency:**
- **employees**: From F-005 (Employee Management), referenced via foreign keys

### 6.2 Entity Descriptions

#### 6.2.1 bank_info

Represents an employee's bank account used for salary payments. Only one active 
bank account exists per employee at any time. BankInfo is never hard-deleted 
(supports soft delete only).

**Key Attributes:**
- Employee reference (FK to employees)
- Bank name (ENUM: HDFC, ICICI, SBI, AXIS, KOTAK, PNB, BOB)
- Branch name
- Account number (sensitive, encrypted)
- IFSC code (sensitive, encrypted)

**Business Rules:**
- One bank account per employee (1:1 relationship)
- Updates affect future payments only
- Past salary payments remain unchanged

#### 6.2.2 salary_details

Defines the monthly gross salary configuration for an employee over a specific 
effective period. Only one active configuration is allowed per employee at any time.

**Key Attributes:**
- Employee reference (FK to employees)
- Amount (monthly gross salary)
- Currency (ENUM: INR, USD, EUR, GBP, AUD, CAD)
- Payment frequency (ENUM: MONTHLY, BI_WEEKLY, WEEKLY)
- Effective from date (inclusive)
- Effective to date (inclusive, nullable for active records)

**Business Rules:**
- Only one active SalaryDetails per employee (effective_to IS NULL)
- Updating salary auto-closes previous record (sets effective_to)
- Future salary payments use the latest active configuration

#### 6.2.3 salary_payments

Represents a completed salary payment for a specific employee, month, and year. 
Records are immutable and append-only (cannot be updated or deleted).

**Key Attributes:**
- Employee reference (FK to employees)
- Amount (derived from active SalaryDetails at payment time)
- Currency (derived from active SalaryDetails)
- Month (1-12)
- Year (YYYY)
- Paid on date (payment execution date)
- Payment method (ENUM: BANK_TRANSFER, UPI, CHEQUE, CASH)
- Slip URL (salary slip file location)

**Business Rules:**
- Only one payment per employee per month/year (unique constraint)
- Records are immutable (no UPDATE/DELETE operations)
- Amount derived from active SalaryDetails at payment time

#### 6.2.4 salary_history

Immutable audit record capturing changes to SalaryDetails over time. Created 
automatically when salary is updated.

**Key Attributes:**
- SalaryDetails reference (FK to salary_details)
- Previous amount (before change)
- New amount (after change)
- Effective from date (when new salary becomes effective)
- Changed by (user who made the change)
- Created at (timestamp of change)

**Business Rules:**
- Records are immutable (no UPDATE/DELETE operations)
- Created automatically on salary updates
- Not created for first salary configuration (no previous amount)

### 6.3 Relationship Cardinality

| Relationship | Cardinality | Description |
|--------------|-------------|-------------|
| employees ↔ bank_info | 1:1 | One employee has exactly one bank account |
| employees ↔ salary_details | 1:M | One employee can have multiple salary configurations (historical) |
| employees ↔ salary_payments | 1:M | One employee can have multiple salary payments |
| salary_details ↔ salary_history | 1:M | One salary configuration can have multiple history records |

### 6.4 Multi-Tenancy Model

All salary-related data is scoped to the company (organization) through the 
employees table. The employees table (from F-005) contains company_id, which 
provides tenant isolation. Salary tables inherit tenant scope via employee_id 
foreign key relationships.

**Tenant Isolation Strategy:**
- Row-level security via company_id in employees table
- All salary queries filtered by company_id through employee relationships
- SuperAdmin can access all companies (application-level authorization)

================================================================================
                        SECTION 7 — PHYSICAL DATA MODEL
================================================================================

### 7.1 Table: bank_info

Stores employee bank account information used for salary payments. Only one 
active bank account per employee.

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique bank info identifier |
| employee_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES employees(id) ON DELETE RESTRICT ON UPDATE CASCADE | Foreign key to employees table, required |
| bank_name | VARCHAR(50) | No | No | No | - | NOT NULL, CHECK (bank_name IN ('HDFC', 'ICICI', 'SBI', 'AXIS', 'KOTAK', 'PNB', 'BOB')) | Bank identifier, ENUM-controlled, required |
| branch | VARCHAR(255) | No | No | No | - | NOT NULL, CHECK (LENGTH(branch) >= 1) | Bank branch name, min 1 character, max 255 characters, required |
| account_number | VARCHAR(20) | No | No | No | - | NOT NULL, CHECK (LENGTH(account_number) >= 8 AND LENGTH(account_number) <= 20 AND account_number ~ '^[A-Za-z0-9]+$') | Bank account number, min 8 characters, max 20 characters, alphanumeric only, sensitive data (encrypted at application level), required |
| ifsc_code | VARCHAR(11) | No | No | No | - | NOT NULL, CHECK (LENGTH(ifsc_code) = 11 AND ifsc_code ~ '^[A-Z]{4}0[A-Z0-9]{6}$') | Bank IFSC code, 11 characters, format: 4 uppercase letters + 0 + 6 alphanumeric (e.g., "HDFC0001234"), sensitive data (encrypted at application level), required |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created (UTC) |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated (UTC) |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted (UTC), NULL if active |
| created_by | UUID | No | No | Yes | NULL | - | User ID who created the record (CEO/HR) |
| updated_by | UUID | No | No | Yes | NULL | - | User ID who last updated the record (CEO/HR) |
| deleted_by | UUID | No | No | Yes | NULL | - | User ID who soft-deleted the record (CEO/HR) |

**Foreign Key Constraints:**
- `employee_id` REFERENCES `employees(id)` ON DELETE RESTRICT ON UPDATE CASCADE
  - **Rationale**: Cannot delete employee with bank info (preserve data integrity). Employee ID changes propagate.

**Additional Constraints:**
- UNIQUE constraint on `(employee_id)` WHERE `deleted_at IS NULL` (only one active bank info per employee)
- CHECK constraint on `bank_name` to ensure valid ENUM values
- CHECK constraint on `ifsc_code` to ensure 11-character format and valid IFSC pattern (4 uppercase letters + 0 + 6 alphanumeric)
- CHECK constraint on `account_number` to ensure min 8 characters, max 20 characters, and alphanumeric only
- CHECK constraint on `branch` to ensure min 1 character (NOT NULL already enforces non-empty, but explicit check for clarity)

**Business Rules:**
- Only one active bank_info per employee (enforced by unique constraint)
- BankInfo is never hard-deleted (soft delete only)
- Updates affect future payments only (application logic)

---

### 7.2 Table: salary_details

Stores time-based salary configurations for employees. Only one active 
configuration per employee at any time.

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique salary details identifier |
| employee_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES employees(id) ON DELETE RESTRICT ON UPDATE CASCADE | Foreign key to employees table, required |
| amount | NUMERIC(12,2) | No | No | No | - | NOT NULL, CHECK (amount > 0 AND amount <= 999999999.99) | Monthly gross salary amount, required, must be greater than 0 and less than or equal to 999999999.99 |
| currency | VARCHAR(10) | No | No | No | - | NOT NULL, CHECK (currency IN ('INR', 'USD', 'EUR', 'GBP', 'AUD', 'CAD')) | Salary currency, ENUM-controlled, required |
| payment_frequency | VARCHAR(20) | No | No | No | - | NOT NULL, CHECK (payment_frequency IN ('MONTHLY', 'BI_WEEKLY', 'WEEKLY')) | Payment cadence, ENUM-controlled, required |
| effective_from | DATE | No | No | No | - | NOT NULL, CHECK (effective_from >= CURRENT_DATE) | Start date of salary configuration (inclusive), must be today or future date, required |
| effective_to | DATE | No | No | Yes | NULL | - | End date of salary configuration (inclusive), NULL for active records, required for historical records |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created (UTC) |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated (UTC) |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted (UTC), NULL if active |
| created_by | UUID | No | No | Yes | NULL | - | User ID who created the record (CEO/HR) |
| updated_by | UUID | No | No | Yes | NULL | - | User ID who last updated the record (CEO/HR) |
| deleted_by | UUID | No | No | Yes | NULL | - | User ID who soft-deleted the record (CEO/HR) |

**Foreign Key Constraints:**
- `employee_id` REFERENCES `employees(id)` ON DELETE RESTRICT ON UPDATE CASCADE
  - **Rationale**: Cannot delete employee with salary details (preserve data integrity). Employee ID changes propagate.

**Additional Constraints:**
- UNIQUE constraint on `(employee_id, effective_from)` WHERE `deleted_at IS NULL` (prevent overlapping periods for same employee)
- CHECK constraint on `amount` to ensure positive value and max value (0 < amount <= 999999999.99)
- CHECK constraint on `currency` to ensure valid ENUM values
- CHECK constraint on `payment_frequency` to ensure valid ENUM values
- CHECK constraint: `effective_to IS NULL OR effective_to >= effective_from` (end date must be >= start date)
- CHECK constraint on `effective_from` to ensure date is today or future (effective_from >= CURRENT_DATE)

**Business Rules:**
- Only one active SalaryDetails per employee (effective_to IS NULL, enforced by application logic)
- No overlapping effective periods for same employee (enforced by unique constraint + application logic)
- Updating salary auto-closes previous record (application logic sets effective_to)

---

### 7.3 Table: salary_payments

Stores monthly salary payment execution records. Records are immutable and 
append-only (cannot be updated or deleted).

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique salary payment identifier |
| employee_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES employees(id) ON DELETE RESTRICT ON UPDATE CASCADE | Foreign key to employees table, required |
| amount | NUMERIC(12,2) | No | No | No | - | NOT NULL, CHECK (amount > 0) | Paid amount, derived from active SalaryDetails at payment time, required |
| currency | VARCHAR(10) | No | No | No | - | NOT NULL, CHECK (currency IN ('INR', 'USD', 'EUR', 'GBP', 'AUD', 'CAD')) | Payment currency, derived from active SalaryDetails, ENUM-controlled, required |
| month | INTEGER | No | No | No | - | NOT NULL, CHECK (month >= 1 AND month <= 12) | Salary month (1-12), required |
| year | INTEGER | No | No | No | - | NOT NULL, CHECK (year >= 2000 AND year <= 9999) | Salary year (YYYY), required |
| paid_on | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Payment execution date (UTC), required |
| payment_method | VARCHAR(20) | No | No | No | - | NOT NULL, CHECK (payment_method IN ('BANK_TRANSFER', 'UPI', 'CHEQUE', 'CASH')) | Mode of payment, ENUM-controlled, required |
| slip_url | VARCHAR(500) | No | No | Yes | NULL | - | Salary slip file location/URL, optional (generated async) |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created (UTC) |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted (UTC), NULL if active (immutable records should not be soft-deleted, but field exists for consistency) |
| created_by | UUID | No | No | Yes | NULL | - | User ID who created the record (CEO/HR) |
| deleted_by | UUID | No | No | Yes | NULL | - | User ID who soft-deleted the record (should remain NULL for immutable records) |

**Foreign Key Constraints:**
- `employee_id` REFERENCES `employees(id)` ON DELETE RESTRICT ON UPDATE CASCADE
  - **Rationale**: Cannot delete employee with salary payments (preserve payment history). Employee ID changes propagate.

**Additional Constraints:**
- UNIQUE constraint on `(employee_id, month, year)` WHERE `deleted_at IS NULL` (only one payment per employee per month/year)
- CHECK constraint on `amount` to ensure positive value
- CHECK constraint on `currency` to ensure valid ENUM values
- CHECK constraint on `month` to ensure valid range (1-12)
- CHECK constraint on `year` to ensure valid range (2000-9999)
- CHECK constraint on `payment_method` to ensure valid ENUM values

**Business Rules:**
- Only one payment per employee per month/year (enforced by unique constraint)
- Records are immutable (no UPDATE operations, application-level enforcement)
- Records should not be soft-deleted (application-level enforcement, deleted_at should remain NULL)
- Amount and currency derived from active SalaryDetails at payment time

**Note:** This table does not include `updated_at` and `updated_by` fields because records are immutable (append-only).

---

### 7.4 Table: salary_history

Stores immutable audit log of salary configuration changes. Created automatically 
when SalaryDetails is updated.

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique salary history identifier |
| salary_details_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES salary_details(id) ON DELETE RESTRICT ON UPDATE RESTRICT | Foreign key to salary_details table, required |
| previous_amount | NUMERIC(12,2) | No | No | Yes | NULL | - | Previous salary amount (before change), NULL for first salary configuration |
| new_amount | NUMERIC(12,2) | No | No | No | - | NOT NULL, CHECK (new_amount > 0) | New salary amount (after change), required |
| effective_from | DATE | No | No | No | - | NOT NULL | Effective date of new salary configuration (inclusive), required |
| changed_by | UUID | No | No | Yes | NULL | - | User ID who made the salary change (CEO/HR) |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when salary change was recorded (UTC), required |

**Foreign Key Constraints:**
- `salary_details_id` REFERENCES `salary_details(id)` ON DELETE RESTRICT ON UPDATE RESTRICT
  - **Rationale**: Cannot delete salary_details with history (preserve audit trail). Salary details ID should not change (RESTRICT on UPDATE).

**Additional Constraints:**
- CHECK constraint on `new_amount` to ensure positive value

**Business Rules:**
- Records are immutable (no UPDATE/DELETE operations, application-level enforcement)
- Created automatically when SalaryDetails is updated (application logic)
- Not created for first salary configuration (previous_amount will be NULL)
- Records should never be soft-deleted (preserve audit trail)

**Note:** This table does not include `updated_at`, `updated_by`, `deleted_at`, or `deleted_by` fields because records are immutable (append-only audit log).

================================================================================
                        SECTION 8 — NORMALIZATION
================================================================================

### 8.1 Normalization Verification

All tables are verified against Third Normal Form (3NF) requirements.

#### 8.1.1 bank_info

**First Normal Form (1NF):**
- ✅ All columns contain atomic values (no arrays, no comma-separated lists)
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
- ✅ No transitive dependencies (all non-key columns depend directly on primary key)
- ✅ Bank name, branch, account number, IFSC code all depend directly on employee_id (via foreign key relationship)

**Normalization Status:** ✅ 3NF Compliant

---

#### 8.1.2 salary_details

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
- ✅ Amount, currency, payment_frequency, effective dates all depend directly on primary key
- ✅ Employee_id is a foreign key (properly normalized relationship)

**Normalization Status:** ✅ 3NF Compliant

---

#### 8.1.3 salary_payments

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
- ✅ Amount, currency, month, year, payment_method all depend directly on primary key
- ✅ Employee_id is a foreign key (properly normalized relationship)
- ✅ Amount and currency are stored (denormalized) for immutability and historical accuracy, but this is acceptable for audit/compliance requirements

**Normalization Status:** ✅ 3NF Compliant (acceptable denormalization for audit trail)

**Note:** Storing amount and currency in salary_payments (even though they could be derived from salary_details) is intentional denormalization for:
- Immutability: Payment amount must remain unchanged even if salary_details is updated
- Historical accuracy: Payment reflects salary at time of payment
- Audit compliance: Complete payment record without dependency on other tables

---

#### 8.1.4 salary_history

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
- ✅ All columns depend directly on primary key
- ✅ Salary_details_id is a foreign key (properly normalized relationship)

**Normalization Status:** ✅ 3NF Compliant

---

### 8.2 Acceptable Denormalization

**salary_payments.amount and salary_payments.currency:**
- **Reason**: Immutability and historical accuracy requirements
- **Rationale**: Payment amount must remain unchanged even if salary_details is updated. Payment reflects salary configuration at time of payment execution.
- **Alternative Considered**: Materialized view or computed column, but rejected due to immutability requirements.

**All tables include audit fields (created_at, updated_at, etc.):**
- **Reason**: Audit compliance and data governance requirements
- **Rationale**: Required for compliance, audit trails, and data governance. Standard practice for enterprise applications.

================================================================================
                        SECTION 9 — INDEX STRATEGY
================================================================================

### 9.1 Index Design Principles

- **Primary Keys**: Automatically indexed by PostgreSQL (unique index)
- **Foreign Keys**: Every foreign key column MUST have an index (critical for JOIN performance)
- **Audit Fields**: Every table with `updated_at` MUST have an index (essential for incremental sync and change tracking)
- **Unique Constraints**: Indexed automatically by PostgreSQL
- **Soft Delete**: Partial indexes for active records (WHERE deleted_at IS NULL)
- **Query Patterns**: Composite indexes for common query patterns

### 9.2 Index Specifications

#### 9.2.1 bank_info Indexes

```sql
-- Primary Key (automatic)
CREATE UNIQUE INDEX pk_bank_info ON bank_info(id);

-- Foreign Key Index (CRITICAL)
CREATE INDEX idx_bank_info_employee_id ON bank_info(employee_id);

-- Audit Field Index (CRITICAL)
CREATE INDEX idx_bank_info_updated_at ON bank_info(updated_at);

-- Soft Delete Index (for active records)
CREATE INDEX idx_bank_info_active ON bank_info(id) WHERE deleted_at IS NULL;

-- Unique Constraint Index (one active bank info per employee)
CREATE UNIQUE INDEX uq_bank_info_employee_active ON bank_info(employee_id) WHERE deleted_at IS NULL;
```

**Index Rationale:**
- `idx_bank_info_employee_id`: Critical for JOINs with employees table
- `idx_bank_info_updated_at`: Essential for incremental sync and change tracking
- `idx_bank_info_active`: Optimizes queries for active records only
- `uq_bank_info_employee_active`: Enforces business rule (one active bank info per employee)

---

#### 9.2.2 salary_details Indexes

```sql
-- Primary Key (automatic)
CREATE UNIQUE INDEX pk_salary_details ON salary_details(id);

-- Foreign Key Index (CRITICAL)
CREATE INDEX idx_salary_details_employee_id ON salary_details(employee_id);

-- Audit Field Index (CRITICAL)
CREATE INDEX idx_salary_details_updated_at ON salary_details(updated_at);

-- Soft Delete Index (for active records)
CREATE INDEX idx_salary_details_active ON salary_details(id) WHERE deleted_at IS NULL;

-- Composite Index (for finding active salary for employee)
CREATE INDEX idx_salary_details_employee_active ON salary_details(employee_id, effective_from DESC, effective_to) WHERE deleted_at IS NULL;

-- Unique Constraint Index (prevent overlapping periods)
CREATE UNIQUE INDEX uq_salary_details_employee_effective ON salary_details(employee_id, effective_from) WHERE deleted_at IS NULL;
```

**Index Rationale:**
- `idx_salary_details_employee_id`: Critical for JOINs with employees table
- `idx_salary_details_updated_at`: Essential for incremental sync and change tracking
- `idx_salary_details_active`: Optimizes queries for active records only
- `idx_salary_details_employee_active`: Optimizes queries for active salary by employee (common query pattern)
- `uq_salary_details_employee_effective`: Enforces business rule (no overlapping periods)

---

#### 9.2.3 salary_payments Indexes

```sql
-- Primary Key (automatic)
CREATE UNIQUE INDEX pk_salary_payments ON salary_payments(id);

-- Foreign Key Index (CRITICAL)
CREATE INDEX idx_salary_payments_employee_id ON salary_payments(employee_id);

-- Soft Delete Index (for active records)
CREATE INDEX idx_salary_payments_active ON salary_payments(id) WHERE deleted_at IS NULL;

-- Composite Index (for finding payments by employee and date range)
CREATE INDEX idx_salary_payments_employee_date ON salary_payments(employee_id, year DESC, month DESC) WHERE deleted_at IS NULL;

-- Unique Constraint Index (one payment per employee per month/year)
CREATE UNIQUE INDEX uq_salary_payments_employee_month_year ON salary_payments(employee_id, month, year) WHERE deleted_at IS NULL;
```

**Index Rationale:**
- `idx_salary_payments_employee_id`: Critical for JOINs with employees table
- `idx_salary_payments_active`: Optimizes queries for active records only
- `idx_salary_payments_employee_date`: Optimizes queries for payment history by employee (common query pattern)
- `uq_salary_payments_employee_month_year`: Enforces business rule (one payment per employee per month/year)

**Note:** This table does not have `updated_at` field (immutable records), so no `updated_at` index is needed.

---

#### 9.2.4 salary_history Indexes

```sql
-- Primary Key (automatic)
CREATE UNIQUE INDEX pk_salary_history ON salary_history(id);

-- Foreign Key Index (CRITICAL)
CREATE INDEX idx_salary_history_salary_details_id ON salary_history(salary_details_id);

-- Composite Index (for finding history by salary details, ordered by date)
CREATE INDEX idx_salary_history_salary_details_created ON salary_history(salary_details_id, created_at DESC);
```

**Index Rationale:**
- `idx_salary_history_salary_details_id`: Critical for JOINs with salary_details table
- `idx_salary_history_salary_details_created`: Optimizes queries for salary history ordered by creation date (common query pattern)

**Note:** This table does not have `updated_at` or `deleted_at` fields (immutable audit log), so no indexes for those fields are needed.

---

### 9.3 Index Maintenance

- **Index Monitoring**: Monitor index usage with `pg_stat_user_indexes`
- **Index Bloat**: Regular VACUUM and REINDEX operations
- **Query Performance**: Analyze query plans to identify missing indexes
- **Index Overhead**: Balance query performance with write performance

### 9.4 Index Summary

| Table | Index Count | Foreign Key Indexes | Audit Indexes | Unique Indexes | Composite Indexes |
|-------|-------------|---------------------|---------------|----------------|-------------------|
| bank_info | 5 | 1 | 1 | 2 | 0 |
| salary_details | 6 | 1 | 1 | 2 | 1 |
| salary_payments | 4 | 1 | 0 | 2 | 1 |
| salary_history | 3 | 1 | 0 | 1 | 1 |
| **Total** | **18** | **4** | **2** | **7** | **3** |

**Key Indexes (CRITICAL):**
- ✅ All foreign key columns indexed (4 indexes)
- ✅ All `updated_at` columns indexed (2 indexes for tables with updated_at)
- ✅ All unique constraints indexed (7 indexes)
- ✅ Composite indexes for common query patterns (3 indexes)

================================================================================
                        SECTION 10 — PROFESSIONAL ASCII ER DIAGRAM
================================================================================

================================================================================
                    ASCII ER DIAGRAM - F-006 Salary Management
                    (Crow's Foot Notation - PK and FK Fields Only)
================================================================================

Note: Employee entity is from F-005 (Employee Management) and is included
      here to show relationships. Only PK and FK fields are shown per rules.

+----------------------+              +----------------------+
|      employees       |   1      1   |      bank_info       |
|   (F-005 Entity)     |<------------>|                      |
+----------------------+              +----------------------+
| id (PK)              |              | id (PK)              |
|                      |              | employee_id (FK)     |
+----------------------+              +----------------------+


+----------------------+              +----------------------+
|      employees       |   1      M   |   salary_details     |
|   (F-005 Entity)     |<------------>|                      |
+----------------------+              +----------------------+
| id (PK)              |              | id (PK)              |
|                      |              | employee_id (FK)     |
+----------------------+              +----------------------+


+----------------------+              +----------------------+
|      employees       |   1      M   |   salary_payments    |
|   (F-005 Entity)     |<------------>|                      |
+----------------------+              +----------------------+
| id (PK)              |              | id (PK)              |
|                      |              | employee_id (FK)     |
+----------------------+              +----------------------+


+----------------------+              +----------------------+
|   salary_details     |   1      M   |   salary_history     |
+----------------------+<------------>|                      |
| id (PK)              |              | id (PK)              |
| employee_id (FK)     |              | salary_details_id    |
+----------------------+              |        (FK)           |
                                      +----------------------+


================================================================================
                           RELATIONSHIP SUMMARY
================================================================================

1. employees (1) ────< (M) bank_info
   - One employee has exactly one bank account
   - One bank account belongs to exactly one employee

2. employees (1) ────< (M) salary_details
   - One employee can have multiple salary configurations (historical)
   - One salary configuration belongs to exactly one employee

3. employees (1) ────< (M) salary_payments
   - One employee can have multiple salary payments
   - One salary payment belongs to exactly one employee

4. salary_details (1) ────< (M) salary_history
   - One salary configuration can have multiple history records
   - One history record belongs to exactly one salary configuration

================================================================================
                              CARDINALITY NOTES
================================================================================

- employees ↔ bank_info: 1:1 (one-to-one, mandatory on both sides)
- employees ↔ salary_details: 1:M (one-to-many, employee required)
- employees ↔ salary_payments: 1:M (one-to-many, employee required)
- salary_details ↔ salary_history: 1:M (one-to-many, salary_details required)

================================================================================
                              FOREIGN KEY ACTIONS
================================================================================

- bank_info.employee_id → employees.id: ON DELETE RESTRICT, ON UPDATE CASCADE
- salary_details.employee_id → employees.id: ON DELETE RESTRICT, ON UPDATE CASCADE
- salary_payments.employee_id → employees.id: ON DELETE RESTRICT, ON UPDATE CASCADE
- salary_history.salary_details_id → salary_details.id: ON DELETE RESTRICT, ON UPDATE RESTRICT

================================================================================

**End of Database Design Specification**

