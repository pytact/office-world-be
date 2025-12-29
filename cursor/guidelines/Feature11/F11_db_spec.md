================================================================================
SECTION 1 — COVER PAGE
================================================================================

╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                    DATABASE DESIGN DOCUMENT                                  ║
║                                                                              ║
║                    F-011 — Audit Logging & Activity History                  ║
║                                                                              ║
║                    Project: officeWorld                                      ║
║                                                                              ║
║                    Database: PostgreSQL                                     ║
║                    Version: 1.0                                             ║
║                    Date: 2024                                                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

================================================================================
SECTION 2 — DOCUMENT CONTROL
================================================================================

| Field | Value |
|-------|-------|
| Document Title | Database Design Document — F-011 Audit Logging & Activity History |
| Project Name | officeWorld |
| Feature ID | F-011 |
| Feature Name | Audit Logging & Activity History |
| Database System | PostgreSQL |
| Document Version | 1.0 |
| Last Updated | 2024 |
| Author | Database Architect |
| Status | Draft |
| Related Documents | F11_domain_model.md, F11_api_spec.md, F11_ui_data_contract.md |

================================================================================
SECTION 3 — INTRODUCTION
================================================================================

### 3.1 Purpose

This document provides the complete database design specification for the Audit Logging & Activity History feature (F-011) of the officeWorld platform. The audit logging system provides a centralized, immutable, company-scoped record of critical system and user actions across all platform features, ensuring full traceability, compliance, and governance.

### 3.2 Scope

This database design covers:
- **audit_logs** table: Immutable, append-only records of system and user actions
- Relationships to **companies** and **users** tables (from other features)
- Indexing strategy optimized for high write throughput and efficient querying
- Data integrity constraints ensuring immutability and company scoping

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
10. ASCII ER Diagram

### 3.4 Key Design Principles

- **Immutability**: Audit logs are append-only and cannot be updated or deleted
- **Company Scoping**: All audit logs are strictly scoped to companies for multi-tenant isolation
- **High Write Throughput**: Optimized for asynchronous, non-blocking writes
- **Long-Term Storage**: Designed for permanent retention and compliance
- **Query Performance**: Indexed for efficient filtering by company, date, action, and table

================================================================================
SECTION 4 — SYSTEM OVERVIEW
================================================================================

### 4.1 Business Purpose

The Audit Logging & Activity History feature provides a comprehensive audit trail for:
- **Security and Compliance**: Full traceability of critical actions for regulatory compliance
- **Incident Investigation**: Ability to investigate and verify actions when incidents occur
- **Accountability and Governance**: Transparent record of who did what and when
- **Traceability**: Complete history of changes across all platform features

### 4.2 Core Functionality

- **Asynchronous Logging**: Audit logs are written asynchronously and never block business operations
- **Immutable Records**: Once created, audit logs cannot be edited or deleted
- **Company-Scoped**: All audit logs are filtered by company for multi-tenant isolation
- **Role-Based Visibility**: Different roles see different subsets of audit logs (CEO/HR see all, Manager sees only tasks/projects/task_assignments)
- **System Actions**: Supports logging of both user actions and system-generated actions (SYSTEM actor)

### 4.3 Key Entities

| Entity | Description | Table Name |
|--------|-------------|------------|
| AuditLog | Immutable record of a system or user action | audit_logs |

### 4.4 Relationships

| Relationship | Cardinality | Description |
|--------------|-------------|-------------|
| companies → audit_logs | 1 : M | One company has many audit logs (required) |
| users → audit_logs | 0..1 : M | A user can be actor in zero or more audit logs (optional, null for SYSTEM actions) |

### 4.5 Data Flow

1. **Audit Event Generation**: Significant domain actions across features trigger audit log creation
2. **Asynchronous Processing**: Audit logs are written asynchronously without blocking business operations
3. **Company Scoping**: All audit logs are automatically scoped to the company context
4. **Query Access**: Authorized roles query audit logs filtered by company and role-based visibility rules

================================================================================
SECTION 5 — NON-FUNCTIONAL REQUIREMENTS
================================================================================

### 5.1 Performance Requirements

- **High Write Throughput**: Support for high-volume asynchronous writes without impacting business operations
- **Minimal Latency**: Audit logging must not introduce noticeable latency to business transactions
- **Efficient Querying**: Fast filtering by company_id, created_at (date ranges), action_code, table_name, and actor_id
- **Pagination Support**: Efficient pagination for large result sets
- **Role-Based Filtering**: Optimized queries for Manager role filtering (table_name IN (tasks, projects, task_assignments))

### 5.2 Scalability Requirements

- **No Partitioning**: No table partitioning required at this stage
- **Horizontal Scaling**: Design supports future horizontal scaling if needed
- **Index Strategy**: Comprehensive indexing for common query patterns
- **Long-Term Storage**: Designed for permanent retention (indefinite storage for compliance)

### 5.3 Data Integrity Requirements

- **Immutability**: Audit logs are append-only (no UPDATE or DELETE operations allowed)
- **Referential Integrity**: Foreign key constraints for company_id (RESTRICT) and actor_id (SET NULL)
- **Company Scoping**: All audit logs must belong to a company (company_id NOT NULL)
- **Generic Record References**: record_id is a generic UUID with no FK constraint (references may be deleted)
- **Data Validation**: action_code and table_name are free-text but should follow naming conventions

### 5.4 Audit Requirements

**Note**: The audit_logs table itself is an audit table, so it only includes:
- `created_at`: Timestamp when audit log was created (action timestamp)

**No additional audit fields** (no updated_at, created_by, updated_by, deleted_at, deleted_by) because:
- Audit logs are immutable (no updates)
- Audit logs are append-only (no deletes)
- The actor is already captured in `actor_id` field

### 5.5 Security Requirements

- **Company Isolation**: Strict company scoping ensures multi-tenant data isolation
- **Role-Based Access**: Database-level filtering supports role-based visibility rules
- **Sensitive Data**: old_values and new_values may contain sensitive information (masking at application layer)
- **Immutable History**: Immutability ensures audit trail cannot be tampered with

================================================================================
SECTION 6 — LOGICAL DATA MODEL
================================================================================

### 6.1 Entity Descriptions

#### AuditLog Entity

**Purpose**: Represents an immutable, append-only record capturing a meaningful action performed within the system.

**Key Characteristics**:
- Immutable: Once created, cannot be updated or deleted
- Append-only: New records only, no modifications
- Company-scoped: All records belong to a company
- Asynchronous: Written asynchronously without blocking business operations

**Business Fields**:
- `id`: Unique identifier (UUID)
- `actor_id`: User who performed the action (nullable for SYSTEM actions)
- `company_id`: Company that owns this audit log (required)
- `action_code`: Free-text action identifier (e.g., TASK_UPDATED, USER_INVITED)
- `table_name`: Affected entity/table name (reference only)
- `record_id`: Identifier of affected record (generic UUID, no FK constraint)
- `old_values`: Changed fields before action (JSONB, partial snapshot)
- `new_values`: Changed fields after action (JSONB, partial snapshot)
- `ip_address`: Source IP address (optional)
- `user_agent`: Client metadata (optional)
- `description`: Human-readable summary (optional)
- `created_at`: Action timestamp (immutable)

### 6.2 Key Relationships

**Company Relationship**:
- **Type**: One-to-Many (1 : M)
- **Cardinality**: One company has many audit logs
- **Required**: Yes (company_id is NOT NULL)
- **FK Constraint**: company_id → companies.id ON DELETE RESTRICT
- **Business Rule**: All audit logs must belong to a company (BR-1104)

**User (Actor) Relationship**:
- **Type**: Zero-or-One-to-Many (0..1 : M)
- **Cardinality**: A user can be actor in zero or more audit logs
- **Required**: No (actor_id is NULLABLE for SYSTEM actions)
- **FK Constraint**: actor_id → users.id ON DELETE SET NULL
- **Business Rule**: SYSTEM actions have null actor_id

### 6.3 Business Rules

| Rule ID | Description | Type | Enforcement |
|---------|-------------|------|-------------|
| BR-1101 | Audit logs are append-only and immutable | Constraint | Application + Database (no UPDATE/DELETE) |
| BR-1102 | Audit logging is asynchronous and non-blocking | Reliability | Application |
| BR-1103 | Only changed fields are stored in values | Optimization | Application |
| BR-1104 | Audit logs are strictly company-scoped | Security | Database (company_id NOT NULL, FK constraint) |
| BR-1105 | Managers have limited audit visibility | Visibility | Application (filtering by table_name) |

### 6.4 Data Isolation Strategy

**Multi-Tenancy**:
- All audit logs are scoped to companies via `company_id` foreign key
- Row-level filtering based on JWT `org_id` claims in application layer
- Database enforces company_id NOT NULL constraint
- No cross-company data access (enforced at application layer)

================================================================================
SECTION 7 — PHYSICAL DATA MODEL
================================================================================

### 7.1 Table: audit_logs

**Purpose**: Immutable, append-only records of system and user actions for audit, compliance, and traceability.

**Key Characteristics**:
- Append-only: No UPDATE or DELETE operations allowed
- Immutable: All fields are immutable once created
- Company-scoped: All records belong to a company (company_id NOT NULL)
- High write throughput: Optimized for asynchronous writes

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique audit log identifier |
| company_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES companies(id) ON DELETE RESTRICT ON UPDATE CASCADE | Company identifier, mandatory for company scoping |
| actor_id | UUID | No | Yes | Yes | NULL | REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE | User ID who performed the action, null for SYSTEM actions |
| action_code | VARCHAR(100) | No | No | No | - | NOT NULL | Free-text action identifier (e.g., TASK_UPDATED, USER_INVITED, SYSTEM_AUTO_CHECK_OUT) |
| table_name | VARCHAR(100) | No | No | No | - | NOT NULL | Affected entity/table name (reference only, e.g., tasks, users, employees) |
| record_id | UUID | No | No | Yes | NULL | - | Identifier of affected record (generic UUID, no FK constraint, reference may be deleted) |
| old_values | JSONB | No | No | Yes | NULL | - | Changed fields before action (partial snapshot, only changed fields, JSON object format) |
| new_values | JSONB | No | No | Yes | NULL | - | Changed fields after action (partial snapshot, only changed fields, JSON object format) |
| ip_address | VARCHAR(45) | No | No | Yes | NULL | - | Source IP address (supports IPv4 and IPv6, max 45 chars) |
| user_agent | VARCHAR(500) | No | No | Yes | NULL | - | Client metadata (browser, device information, max 500 chars) |
| description | VARCHAR(1000) | No | No | Yes | NULL | - | Human-readable summary of the action (max 1000 chars) |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Action timestamp, immutable (UTC timezone) |

**Foreign Key Constraints:**
- `company_id` → `companies(id)` ON DELETE RESTRICT ON UPDATE CASCADE
  - **Rationale**: Prevent company deletion if audit logs exist (preserve audit history)
  - **Action**: RESTRICT prevents deletion, CASCADE propagates ID changes
  
- `actor_id` → `users(id)` ON DELETE SET NULL ON UPDATE CASCADE
  - **Rationale**: Allow user deletion while preserving audit log (set actor_id to NULL)
  - **Action**: SET NULL preserves audit log when user is deleted, CASCADE propagates ID changes

**Additional Constraints:**
- **Immutability**: Enforced at application level (no UPDATE or DELETE operations)
- **Value Storage**: old_values and new_values contain only changed fields (not full object snapshots)
- **Action Code Format**: Free-text, feature-defined identifiers (no enum constraint, application-level validation)
- **Table Name Format**: Free-text table names (no enum constraint, application-level validation)

**Notes:**
- `record_id` has NO foreign key constraint because it references various tables (tasks, users, employees, etc.) and records may be deleted
- `old_values` and `new_values` use JSONB for efficient querying and indexing (PostgreSQL JSONB type)
- `ip_address` supports both IPv4 (max 15 chars) and IPv6 (max 45 chars)
- `user_agent` length set to 500 chars to accommodate full browser/device strings
- `description` length set to 1000 chars for comprehensive action summaries
- All timestamps use TIMESTAMPTZ (UTC timezone-aware)

================================================================================
SECTION 8 — NORMALIZATION VERIFICATION
================================================================================

### 8.1 Table: audit_logs

#### First Normal Form (1NF) Verification

- [x] **All columns contain atomic values**: Yes
  - All columns contain single, atomic values
  - No arrays, no comma-separated lists
  - JSONB columns (old_values, new_values) store structured JSON objects (atomic at column level)

- [x] **Each column contains only one type of data**: Yes
  - UUID columns: id, company_id, actor_id, record_id
  - VARCHAR columns: action_code, table_name, ip_address, user_agent, description
  - JSONB columns: old_values, new_values
  - TIMESTAMPTZ column: created_at

- [x] **Each column has a unique name**: Yes
  - All column names are unique within the table

- [x] **Order of rows/columns doesn't matter**: Yes
  - Row order determined by created_at (query ordering)
  - Column order is implementation detail

- [x] **No repeating groups of columns**: Yes
  - No repeating groups (e.g., no phone1, phone2, phone3)

**1NF Status**: ✅ **PASS** - Table is in First Normal Form

#### Second Normal Form (2NF) Verification

- [x] **Table is in 1NF**: Yes (verified above)

- [x] **All non-key columns depend on the entire primary key**: Yes
  - Primary key: `id` (single column, not composite)
  - All non-key columns (company_id, actor_id, action_code, table_name, record_id, old_values, new_values, ip_address, user_agent, description, created_at) depend on the entire primary key (id)
  - No partial dependencies (not applicable for single-column primary key)

**2NF Status**: ✅ **PASS** - Table is in Second Normal Form

#### Third Normal Form (3NF) Verification

- [x] **Table is in 2NF**: Yes (verified above)

- [x] **No transitive dependencies**: Yes
  - All non-key columns depend directly on the primary key (id)
  - No non-key column depends on another non-key column
  - Example: company_id depends on id (primary key), not on any other non-key column
  - Example: actor_id depends on id (primary key), not on company_id or any other non-key column

**3NF Status**: ✅ **PASS** - Table is in Third Normal Form

#### Normalization Summary

| Normal Form | Status | Notes |
|-------------|--------|-------|
| 1NF | ✅ PASS | All columns contain atomic values, no repeating groups |
| 2NF | ✅ PASS | All non-key columns depend on entire primary key |
| 3NF | ✅ PASS | No transitive dependencies, all columns depend directly on primary key |

**Overall Normalization Status**: ✅ **FULLY NORMALIZED (3NF)**

**Acceptable Denormalization**:
- None required - table is fully normalized
- JSONB columns (old_values, new_values) store structured data but are atomic at column level (acceptable for audit/snapshot tables)

================================================================================
SECTION 9 — INDEX STRATEGY
================================================================================

### 9.1 Primary Key Index

**Index**: `pk_audit_logs`
```sql
CREATE UNIQUE INDEX pk_audit_logs ON audit_logs(id);
```
**Purpose**: Automatically created by PostgreSQL for primary key
**Usage**: Primary key lookups, foreign key references

### 9.2 Foreign Key Indexes (MANDATORY)

**Index 1**: `idx_audit_logs_company_id`
```sql
CREATE INDEX idx_audit_logs_company_id ON audit_logs(company_id);
```
**Purpose**: 
- Improve JOIN performance with companies table
- Essential for company-scoped queries (all queries filter by company_id)
- Supports referential integrity checks
**Usage**: Company filtering, multi-tenant isolation queries

**Index 2**: `idx_audit_logs_actor_id`
```sql
CREATE INDEX idx_audit_logs_actor_id ON audit_logs(actor_id);
```
**Purpose**: 
- Improve JOIN performance with users table
- Support filtering by actor (who performed the action)
- Supports referential integrity checks
**Usage**: Actor filtering, user activity queries

### 9.3 Audit Field Index (MANDATORY)

**Index**: `idx_audit_logs_created_at`
```sql
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```
**Purpose**: 
- Essential for date range queries (start_date, end_date filtering)
- Supports sorting by created_at (default descending)
- Critical for incremental sync and change tracking
- Required for pagination with date-based filtering
**Usage**: Date range filtering, sorting, pagination

### 9.4 Composite Indexes for Common Query Patterns

**Index 1**: `idx_audit_logs_company_created`
```sql
CREATE INDEX idx_audit_logs_company_created ON audit_logs(company_id, created_at DESC);
```
**Purpose**: 
- Optimize most common query pattern: filter by company + sort by created_at
- Supports company-scoped queries with date ordering
- Covers queries: WHERE company_id = ? ORDER BY created_at DESC
**Usage**: List queries with company filtering and date sorting

**Index 2**: `idx_audit_logs_company_action`
```sql
CREATE INDEX idx_audit_logs_company_action ON audit_logs(company_id, action_code);
```
**Purpose**: 
- Optimize filtering by company + action_code
- Supports action-specific audit log queries
**Usage**: Filter by company and specific action type

**Index 3**: `idx_audit_logs_company_table`
```sql
CREATE INDEX idx_audit_logs_company_table ON audit_logs(company_id, table_name);
```
**Purpose**: 
- Optimize Manager role filtering (table_name IN (tasks, projects, task_assignments))
- Supports table-specific audit log queries within company
- Critical for role-based visibility (Manager sees only specific tables)
**Usage**: Manager role queries, table-specific filtering

**Index 4**: `idx_audit_logs_company_created_action`
```sql
CREATE INDEX idx_audit_logs_company_created_action ON audit_logs(company_id, created_at DESC, action_code);
```
**Purpose**: 
- Optimize complex queries: company + date range + action filter
- Supports paginated queries with multiple filters
**Usage**: Advanced filtering with date range and action code

**Index 5**: `idx_audit_logs_company_created_table`
```sql
CREATE INDEX idx_audit_logs_company_created_table ON audit_logs(company_id, created_at DESC, table_name);
```
**Purpose**: 
- Optimize Manager role queries with date sorting
- Supports table filtering with date-based pagination
**Usage**: Manager role queries with date range and table filtering

### 9.5 Index Summary

| Index Name | Columns | Type | Purpose | Priority |
|------------|---------|------|---------|----------|
| pk_audit_logs | id | UNIQUE | Primary key | Required |
| idx_audit_logs_company_id | company_id | B-Tree | FK index, company filtering | Required |
| idx_audit_logs_actor_id | actor_id | B-Tree | FK index, actor filtering | Required |
| idx_audit_logs_created_at | created_at | B-Tree | Date filtering, sorting | Required |
| idx_audit_logs_company_created | company_id, created_at DESC | B-Tree | Common query pattern | High |
| idx_audit_logs_company_action | company_id, action_code | B-Tree | Action filtering | Medium |
| idx_audit_logs_company_table | company_id, table_name | B-Tree | Manager role filtering | High |
| idx_audit_logs_company_created_action | company_id, created_at DESC, action_code | B-Tree | Complex filtering | Medium |
| idx_audit_logs_company_created_table | company_id, created_at DESC, table_name | B-Tree | Manager queries with date | High |

### 9.6 Index Maintenance Considerations

- **Write Performance**: Multiple indexes may impact write performance, but necessary for query optimization
- **Index Size**: Monitor index sizes as audit logs grow (long-term storage)
- **Index Usage**: Monitor index usage with `pg_stat_user_indexes` to identify unused indexes
- **Maintenance**: Regular VACUUM and ANALYZE operations recommended for high-write tables

### 9.7 Future Index Considerations

- **Partial Indexes**: Consider partial indexes for Manager role if table_name filtering becomes performance bottleneck
  ```sql
  CREATE INDEX idx_audit_logs_manager_tables ON audit_logs(company_id, created_at DESC) 
  WHERE table_name IN ('tasks', 'projects', 'task_assignments');
  ```
- **JSONB Indexes**: If querying within old_values/new_values becomes common, consider GIN indexes:
  ```sql
  CREATE INDEX idx_audit_logs_old_values_gin ON audit_logs USING gin(old_values);
  CREATE INDEX idx_audit_logs_new_values_gin ON audit_logs USING gin(new_values);
  ```

================================================================================
SECTION 10 — PROFESSIONAL ASCII ER DIAGRAM
================================================================================

+------------------+             +----------------------+             +------------------+
|    companies     |   1     M  |    audit_logs       |  0..1    M  |      users       |
+------------------+             +----------------------+             +------------------+
| id (PK)          |<----------->| id (PK)              |<----------->| id (PK)          |
|                  |             | company_id (FK)     |             |                  |
|                  |             | actor_id (FK)       |             |                  |
+------------------+             +----------------------+             +------------------+

Relationship Details:
- companies (1) → audit_logs (M): One company has many audit logs
  * FK: audit_logs.company_id → companies.id
  * Cardinality: 1 to Many (required - company_id is NOT NULL)
  
- users (0..1) → audit_logs (M): A user can be actor in zero or more audit logs
  * FK: audit_logs.actor_id → users.id
  * Cardinality: Zero or One to Many (optional - actor_id is NULLABLE for SYSTEM actions)

Notes:
- audit_logs.company_id: NOT NULL (mandatory - all audit logs belong to a company)
- audit_logs.actor_id: NULLABLE (null for SYSTEM-generated actions)
- audit_logs table is append-only and immutable (no updates or deletes)

================================================================================
END OF DOCUMENT
================================================================================

