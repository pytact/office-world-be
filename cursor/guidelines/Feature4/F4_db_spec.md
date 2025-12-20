================================================================================
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                    DATABASE DESIGN DOCUMENT                               ║
║                                                                            ║
║                    officeWorld                                             ║
║                    F-004 — Platform Company Management                     ║
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
| Feature                  | F-004 — Platform Company Management      |
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
officeWorld platform's Platform Company Management feature (F-004). It defines 
the physical data model, table structures, relationships, constraints, indexes, 
and normalization approach for managing tenant companies within a multi-tenant 
SaaS environment.

3.2 Scope

This specification covers:
- Company entity as tenant organization and data isolation boundary
- Company lifecycle management (creation, activation, deactivation, hard deletion)
- Company profile fields (editable by CEO/HR)
- Governance fields (SuperAdmin-only: is_active)
- Complete audit trail (created_at, updated_at, created_by, updated_by)
- Hard deletion support (irreversible removal of company and all associated data)
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

officeWorld is a controlled, multi-tenant SaaS platform where all tenant 
companies are provisioned and governed centrally. Company lifecycle management 
must be consistent, secure, and auditable to protect data isolation and platform 
integrity.

4.2 Core Business Rules

- Only SuperAdmin can create, activate, deactivate, or delete companies
- Company name and slug are immutable after creation
- Company name and slug must be globally unique (case-insensitive)
- Required fields at creation are name and slug
- Deactivated companies (is_active: false) block login for all associated users
- Hard deletion is irreversible and removes all company data
- CEO and HR can update limited profile fields (description, address, city, state, 
  country, postal_code, website, logo_url) when company is active
- CEO and HR cannot update governance fields (is_active, name, slug)
- Only one CEO is allowed per company (enforced at application level)

4.3 Key Entities

1. **Company**: Tenant organization owned and governed by the platform. Company 
   is a first-class aggregate that defines tenant boundaries, access control 
   scope, and ownership of all company-scoped data.

4.4 Relationships

- Company owns Users (via UserRoleAssignment)
- Company owns Employees
- Company owns all company-scoped records (leaves, tasks, salaries, notifications, 
  etc.)

================================================================================
SECTION 5 — NON-FUNCTIONAL REQUIREMENTS
================================================================================

5.1 Performance Requirements

- Support for high-volume company queries with pagination
- Efficient filtering by status (active/inactive), search by name/slug
- Fast lookup by slug (unique identifier)
- Optimized queries for company listing with user count aggregation

5.2 Scalability Requirements

- No specific partitioning or sharding requirements at this stage
- Design supports future horizontal scaling if needed
- Index strategy optimized for common query patterns

5.3 Data Integrity Requirements

- Referential integrity enforced through foreign key constraints
- Unique constraints on name and slug (case-insensitive)
- Check constraints for boolean fields
- Hard deletion removes all associated data (cascade handled at application level)
- Multi-tenant data isolation enforced via company_id foreign keys in related tables 
  (UserRoleAssignment, Employee, and all company-scoped domain records reference companies.id)

5.4 Audit Requirements

All tables include complete audit trail:
- created_at: Timestamp when record was created
- updated_at: Timestamp when record was last updated
- created_by: User ID who created the record (SuperAdmin)
- updated_by: User ID who last updated the record (SuperAdmin)

Note: Hard deletion is supported (no soft delete fields: deleted_at, deleted_by, 
is_deleted).

5.5 Security Requirements

- Company name and slug are immutable once set
- Governance fields (is_active) are SuperAdmin-only
- Hard deletion prevents data recovery
- Foreign key constraints prevent orphaned records

5.6 Availability Requirements

- Standard PostgreSQL high-availability configurations apply
- No special clustering requirements specified

================================================================================
SECTION 6 — LOGICAL DATA MODEL
================================================================================

6.1 Entity Relationships

The logical data model consists of one main entity for this feature:

1. **Company** (1) ←→ (*) **UserRoleAssignment**
   - Each company has many user role assignments
   - Company owns users through UserRoleAssignment

2. **Company** (1) ←→ (*) **Employee**
   - Each company has many employees
   - Employees must belong to a company (required)

3. **Company** (1) ←→ (*) **DomainRecords**
   - Each company owns all company-scoped records (leaves, tasks, salaries, 
     notifications, etc.)

6.2 Key Business Rules

- Company.name is unique and immutable
- Company.slug is unique and immutable
- Company.is_active controls user access (SuperAdmin-only)
- Hard deletion removes company and all associated data
- Company defines tenant boundaries and data isolation
- Multi-tenant isolation: All company-scoped tables reference companies.id via company_id 
  foreign key, ensuring complete data isolation per tenant

6.3 Data Flow

- Company creation creates Company record with required fields (name, slug)
- Company defaults to active state (is_active: true) on creation
- Company activation/deactivation updates is_active field
- Hard deletion permanently removes company and all associated data
- Profile updates by CEO/HR modify non-governance fields only

================================================================================
SECTION 7 — PHYSICAL DATA MODEL
================================================================================

### 7.1 Table: companies

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique company identifier |
| name | VARCHAR(255) | No | No | No | - | NOT NULL, UNIQUE | Company name, immutable, case-insensitive unique |
| slug | VARCHAR(100) | No | No | No | - | NOT NULL, UNIQUE | URL-friendly company identifier, immutable, globally unique, lowercase alphanumeric with hyphens only |
| description | VARCHAR(1000) | No | No | Yes | NULL | - | Company description, editable by CEO/HR, max 1000 characters |
| address | VARCHAR(255) | No | No | Yes | NULL | - | Physical address, editable by CEO/HR, max 255 characters |
| city | VARCHAR(100) | No | No | Yes | NULL | - | City, editable by CEO/HR, max 100 characters |
| state | VARCHAR(100) | No | No | Yes | NULL | - | State, editable by CEO/HR, max 100 characters |
| country | VARCHAR(100) | No | No | Yes | NULL | - | Country, editable by CEO/HR, max 100 characters |
| postal_code | VARCHAR(20) | No | No | Yes | NULL | - | Postal/ZIP code, editable by CEO/HR, max 20 characters |
| website | VARCHAR(2048) | No | No | Yes | NULL | - | Company website URL, editable by CEO/HR, valid HTTPS URL, max 2048 characters |
| logo_url | VARCHAR(2048) | No | No | Yes | NULL | - | Company logo URL, editable by CEO/HR, valid HTTPS URL, max 2048 characters |
| is_active | BOOLEAN | No | No | No | true | NOT NULL | Company active state, SuperAdmin-only, defaults to true on creation |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated |
| created_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who created the record (SuperAdmin) |
| updated_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who last updated the record (SuperAdmin) |

**Foreign Key Constraints:**
- created_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- updated_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE

**Additional Constraints:**
- UNIQUE constraint on `name` (case-insensitive uniqueness for company names)
- UNIQUE constraint on `slug` (case-insensitive uniqueness for company slugs)
- CHECK constraint on `is_active` to ensure only boolean values (true/false)
- Business rule: `name` and `slug` are immutable after creation (enforced at application level)
- Business rule: `slug` must match pattern `^[a-z0-9]+(?:-[a-z0-9]+)*$` (enforced at application level)
- Business rule: `website` and `logo_url` must be valid HTTPS URLs (enforced at application level)

**Field Categories:**
- **Immutable Fields**: `name`, `slug` (cannot be changed after creation)
- **Governance Fields**: `is_active` (SuperAdmin-only)
- **Profile Fields**: `description`, `address`, `city`, `state`, `country`, `postal_code`, `website`, `logo_url` (editable by CEO/HR when company is active)

================================================================================
SECTION 8 — NORMALIZATION
================================================================================

### 8.1 Normalization Verification

All tables are verified against Third Normal Form (3NF) requirements:

#### 8.1.1 Table: companies

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
- All fields are atomic and directly related to the company entity
- No redundant data or calculated fields stored
- No transitive dependencies exist
- Design follows 3NF normalization principles

================================================================================
SECTION 9 — INDEX STRATEGY
================================================================================

### 9.1 Primary Key Indexes

**Table: companies**
```sql
CREATE UNIQUE INDEX pk_companies ON companies(id);
```
- Automatically created by PostgreSQL PRIMARY KEY constraint
- Ensures unique identification of each company record

### 9.2 Foreign Key Indexes

**Table: companies**
```sql
CREATE INDEX idx_companies_created_by ON companies(created_by);
CREATE INDEX idx_companies_updated_by ON companies(updated_by);
```
- Improves JOIN performance for audit queries
- Enhances referential integrity check performance

### 9.3 Unique Constraint Indexes

**Table: companies**
```sql
CREATE UNIQUE INDEX uq_companies_name ON companies(LOWER(name));
CREATE UNIQUE INDEX uq_companies_slug ON companies(LOWER(slug));
```
- Ensures case-insensitive uniqueness for company name and slug
- Critical for preventing duplicate company identifiers

### 9.4 Audit Field Indexes

**Table: companies**
```sql
CREATE INDEX idx_companies_updated_at ON companies(updated_at);
```
- Essential for incremental sync and change tracking
- Supports ETag-based conditional requests
- Enables efficient queries for recently updated companies

### 9.5 Query Optimization Indexes

**Table: companies**
```sql
CREATE INDEX idx_companies_is_active ON companies(is_active);
CREATE INDEX idx_companies_created_at ON companies(created_at DESC);
```
- Optimizes filtering by active/inactive status
- Supports sorting by creation date (newest first)
- Improves pagination performance for company listings

### 9.6 Composite Indexes

**Table: companies**
```sql
CREATE INDEX idx_companies_status_created ON companies(is_active, created_at DESC);
```
- Optimizes common query pattern: filter by status and sort by creation date
- Supports paginated listings with status filtering

### 9.7 Text Search Indexes

**Table: companies**
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_companies_name_trgm ON companies USING gin(name gin_trgm_ops);
CREATE INDEX idx_companies_slug_trgm ON companies USING gin(slug gin_trgm_ops);
```
- Enables efficient case-insensitive partial text search on name and slug
- Supports search functionality in company listings
- Requires pg_trgm extension for trigram matching

### 9.8 Index Summary

| Table | Index Name | Columns | Type | Purpose |
|-------|------------|---------|------|---------|
| companies | pk_companies | id | UNIQUE | Primary key |
| companies | uq_companies_name | LOWER(name) | UNIQUE | Case-insensitive name uniqueness |
| companies | uq_companies_slug | LOWER(slug) | UNIQUE | Case-insensitive slug uniqueness |
| companies | idx_companies_created_by | created_by | INDEX | Foreign key performance |
| companies | idx_companies_updated_by | updated_by | INDEX | Foreign key performance |
| companies | idx_companies_updated_at | updated_at | INDEX | Audit and ETag support |
| companies | idx_companies_is_active | is_active | INDEX | Status filtering |
| companies | idx_companies_created_at | created_at DESC | INDEX | Creation date sorting |
| companies | idx_companies_status_created | is_active, created_at DESC | COMPOSITE | Status filter + date sort |
| companies | idx_companies_name_trgm | name | GIN (trigram) | Text search on name |
| companies | idx_companies_slug_trgm | slug | GIN (trigram) | Text search on slug |

### 9.9 Index Maintenance

- Monitor index usage with `pg_stat_user_indexes`
- Rebuild indexes periodically if fragmentation occurs
- Consider partial indexes for large datasets with specific query patterns
- Text search indexes (GIN) require more storage but provide fast search performance

================================================================================
SECTION 10 — ENTITY RELATIONSHIP DIAGRAM (ERD)
================================================================================

See separate ERD document: `ERD_F4_Platform_Company_Management.txt`

The ERD shows:
- Company as the main entity
- Relationships to UserRoleAssignment, Employee, and domain records
- Only Primary Key (id) and Foreign Key fields are shown
- Business fields and audit fields are excluded per ERD rules

================================================================================
END OF DOCUMENT
================================================================================

