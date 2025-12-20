# Database Design Document: office_world

## 1. Cover Page

```
================================================================================
|                                                                              |
|                    DATABASE DESIGN DOCUMENT                                  |
|                                                                              |
| Project Name: office_world                                                   |
|                                                                              |
| Purpose: SaaS product for different companies to use                        |
|                                                                              |
| Version: 1.0                                                                |
| Date: 2024                                                                  |
|                                                                              |
| Author: Enterprise Database Architect                                        |
|                                                                              |
================================================================================
```

## 2. Document Control

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | 2024 | Enterprise Database Architect | Initial database design for F-000 Core Platform Foundation |

## 3. Introduction

This document provides the enterprise-grade database design for the office_world SaaS platform's Core Platform Foundation (F-000). The design follows Microsoft Azure Data Architecture guidelines, PostgreSQL 3NF normalization principles, and implements multi-tenant data isolation.

### 3.1 Scope
This database design covers the foundational entities required for user authentication, authorization, and multi-tenant isolation in a SaaS environment.

### 3.2 Objectives
- Provide secure user authentication and authorization
- Implement multi-tenant data isolation
- Support role-based access control (RBAC)
- Enable invitation-based user onboarding
- Maintain audit trails for compliance

## 4. System Overview

### 4.1 Business Context
office_world is a SaaS platform that provides company management capabilities to multiple tenant organizations. Each company operates in isolation while sharing the same application infrastructure.

### 4.2 Key Requirements
- Multi-tenant architecture with complete data isolation
- JWT-based authentication with role-based permissions
- Invitation-based user onboarding with time-bound tokens
- Soft-delete functionality for data retention
- Comprehensive audit logging

### 4.3 User Roles
- **SuperAdmin**: Global platform administrator (not tied to any company)
- **CEO**: Company executive with full organizational access
- **HR**: Human resources management within company
- **Manager**: Project and task management within company
- **Employee**: Individual user access within company

## 5. Non-Functional Requirements

### 5.1 Performance
- Support for 10,000+ concurrent users
- Sub-second query response times for authentication
- Efficient multi-tenant data filtering

### 5.2 Security
- Data encryption at rest and in transit
- Role-based access control (RBAC)
- Multi-tenant data isolation
- Audit logging for compliance

### 5.3 Scalability
- Horizontal scaling capability
- Partitioning strategy for large datasets
- Optimized indexing for query performance

### 5.4 Availability
- 99.9% uptime requirement
- Automated backup and recovery
- Redundant data storage

## 6. Logical Data Model

### 6.1 Entity Relationships
The core data model consists of four main entities:

- **Users**: Platform users who authenticate and access the system
- **Companies**: Tenant organizations that own users and data
- **Roles**: Predefined permission containers (SuperAdmin, CEO, HR, Manager, Employee)
- **User Role Assignments**: Junction table linking users to roles within company contexts

### 6.2 Key Relationships
- A Company can have many Users (via User Role Assignments)
- A User belongs to exactly one Company at a time (except SuperAdmin)
- A User has exactly one active Role assignment at any given time (one company at a time)
- A Role can be assigned to many Users within a Company

### 6.3 Data Isolation Strategy
Multi-tenancy is implemented through:
- `company_id` foreign keys in relevant tables
- Row-level filtering based on JWT `org_id` claims
- SuperAdmin users have `NULL` company_id for global access

## 7. Physical Data Model

### 7.1 Table: users

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique user identifier |
| email | VARCHAR(255) | No | No | No | - | UNIQUE, NOT NULL | User email address, RFC 5322 format |
| first_name | VARCHAR(50) | No | No | No | - | NOT NULL | User first name, alphanumeric and spaces |
| last_name | VARCHAR(50) | No | No | No | - | NOT NULL | User last name, alphanumeric and spaces |
| password | VARCHAR(255) | No | No | No | - | NOT NULL | Hashed password using bcrypt |
| is_active | BOOLEAN | No | No | No | true | NOT NULL | Account activation status |
| is_deleted | BOOLEAN | No | No | No | false | NOT NULL | Soft delete flag for data retention |
| invite_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when user was invited |
| activate_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when account was activated |
| expiry | TIMESTAMPTZ | No | No | Yes | NULL | - | Invitation token expiry timestamp |
| token | UUID | No | No | Yes | NULL | - | Current invitation/reset token |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted |
| created_by | UUID | No | No | Yes | NULL | - | User ID who created the record |
| updated_by | UUID | No | No | Yes | NULL | - | User ID who last updated the record |
| deleted_by | UUID | No | No | Yes | NULL | - | User ID who soft-deleted the record |

**Foreign Key Constraints:**
- None (this table defines user identities)

**Additional Constraints:**
- UNIQUE constraint on `email` (case-insensitive uniqueness for user logins)
- CHECK constraint on `is_active` IN (true, false)
- CHECK constraint on `is_deleted` IN (true, false)
- CHECK constraint on `invite_at` < `activate_at` WHEN activate_at IS NOT NULL
- CHECK constraint on `activate_at` < `expiry` WHEN expiry IS NOT NULL

### 7.2 Table: companies

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique company identifier |
| name | VARCHAR(255) | No | No | No | - | UNIQUE, NOT NULL | Company name, case-insensitive unique |
| slug | VARCHAR(100) | No | No | No | - | UNIQUE, NOT NULL | URL-friendly company identifier |
| is_active | BOOLEAN | No | No | No | true | NOT NULL | Company activation status |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted |
| created_by | UUID | No | No | Yes | NULL | - | User ID who created the record (SuperAdmin) |
| updated_by | UUID | No | No | Yes | NULL | - | User ID who last updated the record (SuperAdmin) |
| deleted_by | UUID | No | No | Yes | NULL | - | User ID who soft-deleted the record (SuperAdmin) |

**Foreign Key Constraints:**
- None (this table defines company identities)

**Additional Constraints:**
- UNIQUE constraint on `name` (case-insensitive uniqueness)
- UNIQUE constraint on `slug` (URL-friendly uniqueness)
- CHECK constraint on `is_active` IN (true, false)
- CHECK constraint on `slug` format (alphanumeric, hyphens, underscores only)

### 7.3 Table: roles

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique role identifier |
| name | VARCHAR(50) | No | No | No | - | UNIQUE, NOT NULL | Display name of the role |
| code | VARCHAR(20) | No | No | No | - | UNIQUE, NOT NULL | System code identifier for the role |
| permissions | JSONB | No | No | No | '{}' | NOT NULL | JSON object containing role permissions |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted |
| created_by | UUID | No | No | Yes | NULL | - | User ID who created the record (SuperAdmin) |
| updated_by | UUID | No | No | Yes | NULL | - | User ID who last updated the record (SuperAdmin) |
| deleted_by | UUID | No | No | Yes | NULL | - | User ID who soft-deleted the record (SuperAdmin) |

**Foreign Key Constraints:**
- None (this table defines role definitions)

**Additional Constraints:**
- UNIQUE constraint on `name` (display name uniqueness)
- UNIQUE constraint on `code` (system code uniqueness)
- CHECK constraint on `permissions` JSON structure
- Predefined role codes: 'superadmin', 'ceo', 'hr', 'manager', 'employee'

### 7.4 Table: user_role_assignments

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique assignment identifier |
| user_id | UUID | No | Yes | No | - | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE CASCADE, NOT NULL | Assigned user identifier |
| role_id | UUID | No | Yes | No | - | REFERENCES roles(id) ON DELETE RESTRICT ON UPDATE CASCADE, NOT NULL | Assigned role identifier |
| company_id | UUID | No | Yes | Yes | NULL | REFERENCES companies(id) ON DELETE CASCADE ON UPDATE CASCADE | Company context (NULL for SuperAdmin) |
| is_active | BOOLEAN | No | No | No | true | NOT NULL | Assignment activation status |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted |
| created_by | UUID | No | No | Yes | NULL | - | User ID who created the record |
| updated_by | UUID | No | No | Yes | NULL | - | User ID who last updated the record |
| deleted_by | UUID | No | No | Yes | NULL | - | User ID who soft-deleted the record |

**Foreign Key Constraints:**
- user_id REFERENCES users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- role_id REFERENCES roles(id) ON DELETE RESTRICT ON UPDATE CASCADE
- company_id REFERENCES companies(id) ON DELETE CASCADE ON UPDATE CASCADE

**Additional Constraints:**
- UNIQUE constraint on (user_id, company_id) for one active role per user per company (prevents duplicates in same company)
- UNIQUE constraint on (user_id) WHERE deleted_at IS NULL AND is_active = true (ensures one user in one company at a time)
- CHECK constraint on `is_active` IN (true, false)
- Business rule: SuperAdmin assignments must have company_id = NULL

## 8. Normalization

### 8.1 First Normal Form (1NF) Verification
- [x] All columns contain atomic values (no arrays, no comma-separated lists)
- [x] Each column contains only one type of data
- [x] Each column has a unique name
- [x] Order of rows/columns doesn't matter
- [x] No repeating groups of columns

### 8.2 Second Normal Form (2NF) Verification
- [x] All tables are in 1NF
- [x] All non-key columns depend on the entire primary key (not just part of it)
- [x] No partial dependencies (relevant for composite keys)

### 8.3 Third Normal Form (3NF) Verification
- [x] All tables are in 2NF
- [x] No transitive dependencies (non-key columns don't depend on other non-key columns)
- [x] All non-key columns depend directly on the primary key

### 8.4 Acceptable Denormalization
- **Audit Fields**: Intentionally duplicated created_by, updated_by, deleted_by across tables for audit trail completeness
- **JSON Permissions**: Denormalized permissions storage in roles table for performance (frequent reads, infrequent updates)

## 9. Index Strategy

### 9.1 Primary Key Indexes
- `CREATE UNIQUE INDEX pk_users ON users(id)`
- `CREATE UNIQUE INDEX pk_companies ON companies(id)`
- `CREATE UNIQUE INDEX pk_roles ON roles(id)`
- `CREATE UNIQUE INDEX pk_user_role_assignments ON user_role_assignments(id)`

### 9.2 Foreign Key Indexes (MANDATORY)
- `CREATE INDEX idx_user_role_assignments_user_id ON user_role_assignments(user_id)`
- `CREATE INDEX idx_user_role_assignments_role_id ON user_role_assignments(role_id)`
- `CREATE INDEX idx_user_role_assignments_company_id ON user_role_assignments(company_id)`

### 9.3 Audit Field Indexes (MANDATORY)
- `CREATE INDEX idx_users_updated_at ON users(updated_at)`
- `CREATE INDEX idx_companies_updated_at ON companies(updated_at)`
- `CREATE INDEX idx_roles_updated_at ON roles(updated_at)`
- `CREATE INDEX idx_user_role_assignments_updated_at ON user_role_assignments(updated_at)`

### 9.4 Unique Constraint Indexes
- `CREATE UNIQUE INDEX uq_users_email ON users(email)`
- `CREATE UNIQUE INDEX uq_companies_name ON companies(name)`
- `CREATE UNIQUE INDEX uq_companies_slug ON companies(slug)`
- `CREATE UNIQUE INDEX uq_roles_name ON roles(name)`
- `CREATE UNIQUE INDEX uq_roles_code ON roles(code)`
- `CREATE UNIQUE INDEX uq_user_role_assignments_user_company ON user_role_assignments(user_id, company_id) WHERE deleted_at IS NULL`
- `CREATE UNIQUE INDEX uq_user_active_assignment ON user_role_assignments(user_id) WHERE deleted_at IS NULL AND is_active = true`

### 9.5 Query Optimization Indexes
- `CREATE INDEX idx_users_is_active_deleted ON users(is_active, is_deleted) WHERE deleted_at IS NULL`
- `CREATE INDEX idx_users_token ON users(token) WHERE token IS NOT NULL AND deleted_at IS NULL`
- `CREATE INDEX idx_companies_is_active ON companies(is_active) WHERE deleted_at IS NULL`
- `CREATE INDEX idx_user_role_assignments_active ON user_role_assignments(user_id, company_id, role_id) WHERE is_active = true AND deleted_at IS NULL`

### 9.6 Partial Indexes for Soft Deletes
- `CREATE INDEX idx_users_active ON users(id) WHERE deleted_at IS NULL`
- `CREATE INDEX idx_companies_active ON companies(id) WHERE deleted_at IS NULL`
- `CREATE INDEX idx_roles_active ON roles(id) WHERE deleted_at IS NULL`
- `CREATE INDEX idx_user_role_assignments_active ON user_role_assignments(id) WHERE deleted_at IS NULL`

### 9.7 Text Search Indexes
- `CREATE INDEX idx_users_email_trgm ON users USING gin(email gin_trgm_ops)` (for email search)
- `CREATE INDEX idx_companies_name_trgm ON companies USING gin(name gin_trgm_ops)` (for company search)

## 10. Professional ASCII ER Diagram

```
+--------------------+             +--------------------+              +------------------------+
|     companies      |   1     M   | user_role_assignments |   M     1    |        roles          |
+--------------------+             +------------------------+              +--------------------+
| id (PK)            |<----------->| id (PK)                |<------------>| id (PK)            |
|                    |             | company_id (FK)        |              |                    |
|                    |             | user_id (FK)           |              |                    |
|                    |             | role_id (FK)           |              |                    |
+--------------------+             +------------------------+              +--------------------+
                                            ^
                                            | 1
                                            |
                                            |
+--------------------+             +------------------------+
|       users        |             |                        |
+--------------------+             |                        |
| id (PK)            |             |                        |
|                    |             |                        |
+--------------------+             |                        |
```
