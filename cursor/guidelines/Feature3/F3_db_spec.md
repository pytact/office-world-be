================================================================================
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                    DATABASE DESIGN DOCUMENT                               ║
║                                                                            ║
║                    office world                                            ║
║                    F-003 — Notifications System                            ║
║                                                                            ║
║                    PostgreSQL Database Specification                       ║
║                    Microsoft Azure Data Architecture                       ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
================================================================================

================================================================================
SECTION 2 — DOCUMENT CONTROL
================================================================================

| Field                    | Value                                    |
|--------------------------|------------------------------------------|
| Document Title           | Database Design Document — office world  |
| Feature                  | F-003 — Notifications System             |
| Version                  | 1.0                                      |
| Date                     | 2024                                     |
| Database System          | PostgreSQL 15+                           |
| Architecture             | Microsoft Azure Data Architecture        |
| Normalization Level      | Third Normal Form (3NF)                   |
| Design Approach          | ERD-First Design                         |
| Document Status          | Draft                                     |
| Prepared By              | Enterprise Database Architect             |
| Reviewed By              | TBD                                       |
| Approved By              | TBD                                       |

================================================================================
SECTION 3 — INTRODUCTION
================================================================================

3.1 Purpose

This document provides the complete database design specification for the 
office world platform's Notifications System feature (F-003). It defines 
the physical data model, table structures, relationships, constraints, 
indexes, and normalization approach for managing notifications within a 
multi-tenant SaaS environment following Microsoft Azure Data Architecture 
principles and PostgreSQL 3NF normalization standards.

3.2 Scope

This specification covers:
- Notification entity with email-first and in-app delivery channels
- Company-scoped notification isolation (multi-tenant architecture)
- User-scoped notification visibility (row-level security)
- Polymorphic relationships to leaves and tasks
- Read/unread state management for in-app notifications
- Complete audit trail and soft-delete support
- Azure-compliant indexing and partitioning strategies

3.3 Document Structure

This document follows ERD-first design methodology and is organized into 10 sections:
1. Cover Page
2. Document Control
3. Introduction
4. System Overview
5. Non-Functional Requirements
6. Logical Data Model (with ERD)
7. Physical Data Model (detailed table definitions)
8. Normalization Verification (3NF compliance)
9. Index Strategy (Azure-optimized)
10. Entity Relationship Diagram (ERD - Detailed)

3.4 Database Technology

- Database System: PostgreSQL 15+
- Architecture: Microsoft Azure Data Architecture
- Normalization: Third Normal Form (3NF)
- Naming Convention: snake_case (lowercase with underscores)
- Design Methodology: ERD-First Design

================================================================================
SECTION 4 — SYSTEM OVERVIEW
================================================================================

4.1 Business Purpose

office world is a multi-tenant SaaS platform enabling invitation-based user 
onboarding with strict role-based access control, company boundaries, and 
lifecycle management for users across tenant organizations. The Notifications 
System provides a centralized, asynchronous mechanism to inform users about 
onboarding and workflow events through email-first delivery and limited 
in-app notifications.

4.2 Core Business Rules

- Notifications are created internally by the system via async workers (Celery)
- Email is the primary notification channel
- In-app notifications are limited to task and leave events only
- Invitation notifications are email-only and excluded from API responses
- All notifications are strictly company-scoped (multi-tenant isolation)
- Users can only view and manage their own notifications (row-level security)
- Read/unread state is only applicable to in-app notifications
- Notification delivery failures do not block core business workflows
- No automatic email retries are performed (failures are logged only)

4.3 Key Entities

1. **Notification**: Persisted notification record delivered to a user through 
   email and/or in-app channels. Supports read/unread state for in-app 
   notifications and polymorphic relationships to leaves and tasks.

4.4 Notification Types

The system supports the following notification event types (specific event types - Option B):
- `leave_request`: Manager receives when employee applies for leave
- `leave_approval`: Employee receives when leave is approved
- `leave_rejection`: Employee receives when leave is rejected
- `leave_manager_approval`: CEO/HR receives when manager approves leave (for final approval)
- `task_assignment`: Assigned user receives when task is assigned
- `task_permission_change`: Assigned user receives when task permission changes (Viewer ↔ Editor)
- `task_status_change`: Assigned user receives when task status changes
- `user_activation`: User receives when account is activated
- `user_deactivation`: User receives when account is deactivated

**Note:** Invitation notification types (`user_invitation`, `invitation_resend`) are 
email-only and excluded from API responses and in-app notification storage.

================================================================================
SECTION 5 — NON-FUNCTIONAL REQUIREMENTS
================================================================================

5.1 Performance Requirements (Azure-Optimized)

- Support high-volume notification creation via async workers (10,000+ notifications/day per company)
- Efficient querying for user-specific notifications with pagination (<100ms response time)
- Fast filtering by type, read status, and company scope (<50ms for filtered queries)
- Optimized unread count queries for badge display (<10ms response time)
- Support for Azure Database for PostgreSQL scaling (read replicas, connection pooling)

5.2 Scalability Requirements

- Support multi-tenant architecture with company-level data isolation
- Handle growing notification volume per company (millions of notifications)
- Efficient indexing for common query patterns (Azure query performance insights)
- Support for horizontal scaling via Azure Database sharding (if needed)

5.3 Data Integrity Requirements

- Enforce referential integrity for user and company relationships
- Ensure company-scoped data isolation (Azure Row-Level Security)
- Maintain audit trail for all notification operations
- Support soft-delete for data retention (compliance requirements)

5.4 Security Requirements (Azure Security Best Practices)

- Row-level security (RLS) for company-scoped access
- User-scoped visibility (users can only access their own notifications)
- Audit fields track all create/update/delete operations
- Azure Active Directory integration for authentication
- Encrypted data at rest and in transit

5.5 Availability Requirements

- Notification creation must not block core business workflows
- Async processing ensures non-blocking notification delivery
- Failed notifications are logged but do not prevent workflow completion
- Azure Database high availability (99.99% SLA)
- Automated backup and point-in-time recovery

================================================================================
SECTION 6 — LOGICAL DATA MODEL (ERD-FIRST DESIGN)
================================================================================

6.1 Entity Relationship Diagram (ERD) - Primary View

The following ERD shows the core relationships using Crow's Foot notation:

                        +------------------+
                        |     users        |
                        +------------------+
                        | id (PK)          |
                        +------------------+
                                 |
                                 | 1
                                 |
                                 | M
                                 |
                        +------------------+
                        |  notifications   |
                        +------------------+
                        | id (PK)          |
                        | user_id (FK)     |<---+
                        | company_id (FK)   |    |
                        +------------------+    |
                                 |              |
                                 |              |
                                 |              |
                    +------------+              |
                    |                           |
                    | 1                         |
                    |                           |
                    | M                         |
            +------------------+                |
            |    companies     |                |
            +------------------+                |
            | id (PK)          |                |
            +------------------+                |

6.2 Polymorphic Relationships (Conceptual)

The notifications table has optional polymorphic relationships to leaves and tasks
via the related_record_id and related_table fields:

    +------------------+                    +------------------+
    |    leaves        |                    |     tasks       |
    +------------------+                    +------------------+
    | id (PK)          |                    | id (PK)          |
    +------------------+                    +------------------+
            ^                                        ^
            |                                        |
            | *..1 (optional)                       | *..1 (optional)
            |                                        |
            | (when related_table = 'leaves')       | (when related_table = 'tasks')
            |                                        |
    +------------------+                    +------------------+
    |  notifications   |                    |  notifications   |
    +------------------+                    +------------------+
    | id (PK)          |                    | id (PK)          |
    | related_record_id|                    | related_record_id|
    | related_table    |                    | related_table    |
    +------------------+                    +------------------+

**Note:** The polymorphic relationship is implemented via:
- related_record_id (UUID, nullable): References leaves.id or tasks.id
- related_table (VARCHAR, nullable): Contains 'leaves' or 'tasks' to indicate target table
- This is a logical relationship enforced at the application layer, not a database foreign key constraint

6.3 Entity Descriptions

**Notification**
- Represents a persisted notification record delivered to a single user through 
  one or more channels (email and/or in-app)
- Belongs to exactly one User (recipient) - Foreign Key: user_id → users.id
- Scoped to exactly one Company (tenant boundary) - Foreign Key: company_id → companies.id
- May optionally reference a Leave or Task record (polymorphic relationship via related_record_id + related_table)
- Supports read/unread state for in-app notifications (is_read, read_at)
- Tracks delivery status (sent/failed) via status field

6.4 Key Relationships

| Relationship | Cardinality | Foreign Key | Constraint | Notes |
|--------------|-------------|------------|------------|-------|
| users → notifications | 1:M | notifications.user_id → users.id | ON DELETE RESTRICT | One user receives many notifications |
| companies → notifications | 1:M | notifications.company_id → companies.id | ON DELETE RESTRICT | One company has many notifications |
| leaves → notifications | 1:0..M | notifications.related_record_id (logical) | Application-enforced | Optional polymorphic relationship |
| tasks → notifications | 1:0..M | notifications.related_record_id (logical) | Application-enforced | Optional polymorphic relationship |

6.5 Key Business Rules

- Notification.user_id is required (every notification must have a recipient)
- Notification.company_id is required (all notifications are company-scoped)
- Notification.type must be one of the defined event types (CHECK constraint)
- Notification.channel must be 'email' or 'in_app' (CHECK constraint)
- Notification.status must be 'sent' or 'failed' (CHECK constraint)
- Notification.is_read is only applicable when channel = 'in_app'
- Notification.read_at is only applicable when channel = 'in_app' and is_read = true
- Notification.related_record_id and related_table must both be NULL or both be NOT NULL
- Polymorphic relationships to leaves/tasks are enforced at application layer

6.6 Data Flow

- Business events trigger notification creation via async workers (Celery)
- Notifications are persisted to database for in-app visibility
- Email notifications are sent asynchronously (not stored if email-only)
- Users mark notifications as read/unread via API
- Soft-delete preserves notification history for audit purposes

================================================================================
SECTION 7 — PHYSICAL DATA MODEL
================================================================================

7.1 Primary Key and Foreign Key Summary

| Table | Primary Key | Foreign Keys | Referenced Tables |
|-------|-------------|--------------|-------------------|
| notifications | id (UUID) | user_id → users.id<br>company_id → companies.id<br>created_by → users.id<br>updated_by → users.id<br>deleted_by → users.id | users, companies |

**Foreign Key Actions:**
- All foreign keys use ON DELETE RESTRICT ON UPDATE CASCADE
- Prevents orphaned records and maintains referential integrity
- Cascade updates ensure ID changes propagate correctly

7.2 Complete Table Definition

### 7.2.1 Table: notifications

| Field | Type | PK | FK | Null | Default | Constraints | Description |
|-------|------|----|----|------|---------|-------------|-------------|
| id | UUID | Yes | No | No | gen_random_uuid() | PRIMARY KEY | Primary key, unique notification identifier |
| user_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES users(id) | Recipient user ID, foreign key to users table |
| company_id | UUID | No | Yes | No | - | NOT NULL, REFERENCES companies(id) | Company ID for tenant scoping, foreign key to companies table |
| type | VARCHAR(50) | No | No | No | - | NOT NULL, CHECK (type IN ('leave_request', 'leave_approval', 'leave_rejection', 'leave_manager_approval', 'task_assignment', 'task_permission_change', 'task_status_change', 'user_activation', 'user_deactivation')) | Notification event type, specific event type (Option B) |
| title | VARCHAR(255) | No | No | No | - | NOT NULL | Short message title, human-readable |
| message | TEXT | No | No | No | - | NOT NULL | Notification body content, rendered from template |
| channel | VARCHAR(20) | No | No | No | - | NOT NULL, CHECK (channel IN ('email', 'in_app')) | Delivery channel, email or in-app |
| related_record_id | UUID | No | No | Yes | NULL | - | Related domain record ID (leave_id or task_id), nullable for polymorphic relationship |
| related_table | VARCHAR(50) | No | No | Yes | NULL | CHECK (related_table IN ('leaves', 'tasks')) | Source table name for polymorphic relationship, must match related_record_id |
| data | JSONB | No | No | Yes | NULL | - | Structured payload containing type-specific data (rejection reason, approver name, etc.) |
| is_read | BOOLEAN | No | No | No | false | NOT NULL | Read state, only applicable for in-app notifications |
| read_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Read timestamp, only applicable when channel = 'in_app' and is_read = true |
| status | VARCHAR(20) | No | No | No | 'sent' | NOT NULL, CHECK (status IN ('sent', 'failed')) | Delivery state, sent or failed |
| created_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was created |
| updated_at | TIMESTAMPTZ | No | No | No | CURRENT_TIMESTAMP | NOT NULL | Timestamp when record was last updated |
| deleted_at | TIMESTAMPTZ | No | No | Yes | NULL | - | Timestamp when record was soft-deleted (NULL if active) |
| created_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who created the record (system user for async workers) |
| updated_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who last updated the record |
| deleted_by | UUID | No | Yes | Yes | NULL | REFERENCES users(id) | User ID who soft-deleted the record |

**Foreign Key Constraints:**
- user_id → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- company_id → companies(id) ON DELETE RESTRICT ON UPDATE CASCADE
- created_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- updated_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE
- deleted_by → users(id) ON DELETE RESTRICT ON UPDATE CASCADE

**Additional Constraints:**
- CHECK constraint on `type` to ensure only valid notification event types (column-level, defined inline)
- CHECK constraint on `channel` to ensure only 'email' or 'in_app' values (column-level, defined inline)
- CHECK constraint on `status` to ensure only 'sent' or 'failed' values (column-level, defined inline)
- CHECK constraint on `related_table` to ensure only 'leaves' or 'tasks' values when not NULL (column-level, defined inline)
- **Table-level CHECK constraint:** `(related_record_id IS NULL AND related_table IS NULL) OR (related_record_id IS NOT NULL AND related_table IS NOT NULL)` - Ensures related_record_id and related_table are both NULL or both NOT NULL
- **Table-level CHECK constraint:** `read_at IS NULL OR (channel = 'in_app' AND is_read = true)` - Ensures read_at is only set when channel is 'in_app' and is_read is true
- Business rule: `is_read` is only applicable when `channel = 'in_app'` (enforced at application layer for data entry, CHECK constraint enforces read_at relationship)

**SQL for Table-Level Constraints:**
```sql
ALTER TABLE notifications
ADD CONSTRAINT chk_notifications_related_fields 
CHECK ((related_record_id IS NULL AND related_table IS NULL) 
       OR (related_record_id IS NOT NULL AND related_table IS NOT NULL));

ALTER TABLE notifications
ADD CONSTRAINT chk_notifications_read_at 
CHECK (read_at IS NULL OR (channel = 'in_app' AND is_read = true));
```

**Azure Data Architecture Notes:**
- Table uses UUID primary keys for distributed system compatibility
- JSONB field enables flexible schema evolution without migrations
- TIMESTAMPTZ ensures timezone-aware timestamps for global deployments
- Soft-delete pattern supports compliance and audit requirements
- Foreign key constraints ensure data integrity across distributed systems

**Design Decisions:**
- The polymorphic relationship to leaves/tasks is implemented via `related_record_id` and `related_table` fields
- No database foreign key constraint exists for `related_record_id` (logical relationship enforced at application layer)
- The `data` field uses JSONB for efficient storage and querying of structured payload
- Soft-delete is implemented via `deleted_at` timestamp (NULL = active, NOT NULL = deleted)

================================================================================
SECTION 8 — NORMALIZATION VERIFICATION (3NF COMPLIANCE)
================================================================================

### 8.1 Table: notifications

**First Normal Form (1NF):**
- [x] All columns contain atomic values (no arrays, no comma-separated lists)
- [x] Each column contains only one type of data
- [x] Each column has a unique name
- [x] Order of rows/columns doesn't matter
- [x] No repeating groups of columns

**Second Normal Form (2NF):**
- [x] Table is in 1NF
- [x] All non-key columns depend on the entire primary key (id)
- [x] No partial dependencies (single-column primary key, no composite key)

**Third Normal Form (3NF):**
- [x] Table is in 2NF
- [x] No transitive dependencies (non-key columns don't depend on other non-key columns)
- [x] All non-key columns depend directly on the primary key

**Normalization Analysis:**
- The `notifications` table is fully normalized to 3NF
- All columns directly depend on the primary key (id)
- Foreign keys (user_id, company_id) reference other tables, maintaining referential integrity
- The `data` JSONB field stores structured payload but does not violate normalization (it's a single atomic JSONB value)
- No calculated or derived values are stored (read_at is set by application, not calculated)
- No redundant data duplication (user and company information is referenced, not duplicated)

**Acceptable Design Decisions:**
- JSONB `data` field: Acceptable denormalization for flexible type-specific payload storage. Alternative would be separate columns for each notification type, which would violate normalization or require many nullable columns.
- Polymorphic relationship: Logical relationship via `related_record_id` + `related_table` is acceptable. Database-level FK constraint would require separate tables or complex inheritance, which is not practical for this use case.

**Azure Data Architecture Compliance:**
- Normalized design reduces data redundancy and storage costs
- 3NF ensures data consistency across distributed systems
- Foreign key relationships maintain referential integrity in Azure Database for PostgreSQL

================================================================================
SECTION 9 — INDEX STRATEGY (AZURE-OPTIMIZED)
================================================================================

### 9.1 Primary Key Index

**Index:** pk_notifications
```sql
CREATE UNIQUE INDEX pk_notifications ON notifications(id);
```
- Automatically created by PostgreSQL PRIMARY KEY constraint
- Ensures unique identification of each notification
- Azure Database for PostgreSQL automatically maintains this index

### 9.2 Foreign Key Indexes (MANDATORY - Azure Best Practice)

**Index:** idx_notifications_user_id
```sql
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
```
- **Purpose:** Improves JOIN performance with users table and user-scoped queries
- **Usage:** All queries filtering by user_id (user's own notifications)
- **Azure Impact:** Reduces query execution time and improves connection pool efficiency

**Index:** idx_notifications_company_id
```sql
CREATE INDEX idx_notifications_company_id ON notifications(company_id);
```
- **Purpose:** Improves JOIN performance with companies table and company-scoped queries
- **Usage:** All queries filtering by company_id (company-scoped data isolation)
- **Azure Impact:** Essential for multi-tenant query performance

**Index:** idx_notifications_created_by
```sql
CREATE INDEX idx_notifications_created_by ON notifications(created_by);
```
- **Purpose:** Improves queries filtering by audit field created_by
- **Usage:** Audit queries and permission checks

**Index:** idx_notifications_updated_by
```sql
CREATE INDEX idx_notifications_updated_by ON notifications(updated_by);
```
- **Purpose:** Improves queries filtering by audit field updated_by
- **Usage:** Audit queries and permission checks

**Index:** idx_notifications_deleted_by
```sql
CREATE INDEX idx_notifications_deleted_by ON notifications(deleted_by);
```
- **Purpose:** Improves queries filtering by audit field deleted_by
- **Usage:** Audit queries and permission checks

### 9.3 Audit Field Indexes (MANDATORY - Azure Change Tracking)

**Index:** idx_notifications_updated_at
```sql
CREATE INDEX idx_notifications_updated_at ON notifications(updated_at);
```
- **Purpose:** Essential for incremental sync, change tracking, and audit queries
- **Usage:** Queries filtering by updated_at, change tracking, incremental data sync
- **Azure Impact:** Enables Azure Data Factory incremental loads and change data capture

**Index:** idx_notifications_created_at
```sql
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);
```
- **Purpose:** Improves queries sorting by creation time (most common pattern)
- **Usage:** List notifications sorted by created_at DESC (newest first)
- **Azure Impact:** Optimizes pagination queries for Azure API Management

### 9.4 Soft Delete Indexes (Azure Compliance)

**Index:** idx_notifications_active
```sql
CREATE INDEX idx_notifications_active ON notifications(id) WHERE deleted_at IS NULL;
```
- **Purpose:** Partial index for active (non-deleted) notifications only
- **Usage:** All queries that filter out soft-deleted records
- **Azure Impact:** Reduces index size and improves query performance

**Index:** idx_notifications_status_active
```sql
CREATE INDEX idx_notifications_status_active ON notifications(status) WHERE deleted_at IS NULL;
```
- **Purpose:** Partial index for status filtering on active notifications
- **Usage:** Queries filtering by status on active notifications only

### 9.5 Composite Indexes (Azure Query Optimization)

**Index:** idx_notifications_user_company_active
```sql
CREATE INDEX idx_notifications_user_company_active ON notifications(user_id, company_id) WHERE deleted_at IS NULL;
```
- **Purpose:** Optimizes user-scoped, company-scoped queries on active notifications
- **Usage:** Primary query pattern: user's own notifications within company scope
- **Azure Impact:** Most frequently used index for API queries

**Index:** idx_notifications_user_type_read_active
```sql
CREATE INDEX idx_notifications_user_type_read_active ON notifications(user_id, type, is_read) WHERE deleted_at IS NULL AND channel = 'in_app';
```
- **Purpose:** Optimizes filtering by user, type, and read status for in-app notifications
- **Usage:** List endpoint queries with type and is_read filters
- **Azure Impact:** Supports filtered API queries with optimal performance

**Index:** idx_notifications_user_read_created_active
```sql
CREATE INDEX idx_notifications_user_read_created_active ON notifications(user_id, is_read, created_at DESC) WHERE deleted_at IS NULL AND channel = 'in_app';
```
- **Purpose:** Optimizes unread count queries and sorted list queries
- **Usage:** Unread count endpoint, list endpoint with sorting by created_at
- **Azure Impact:** Critical for real-time notification badge updates

**Index:** idx_notifications_company_type_created_active
```sql
CREATE INDEX idx_notifications_company_type_created_active ON notifications(company_id, type, created_at DESC) WHERE deleted_at IS NULL;
```
- **Purpose:** Optimizes company-wide notification queries filtered by type
- **Usage:** Company-level notification analytics and reporting
- **Azure Impact:** Supports Azure Analytics and reporting queries

### 9.6 JSONB Index (Optional - Azure Advanced Features)

**Index:** idx_notifications_data_gin
```sql
CREATE INDEX idx_notifications_data_gin ON notifications USING gin(data);
```
- **Purpose:** Enables efficient querying of JSONB data field
- **Usage:** Queries filtering or searching within the data JSONB field
- **Note:** Only create if queries frequently search within data field
- **Azure Impact:** Leverages PostgreSQL advanced indexing for JSON queries

### 9.7 Index Summary Table

| Index Name | Columns | Type | Partial | Purpose | Azure Impact |
|------------|---------|------|---------|---------|--------------|
| pk_notifications | id | UNIQUE | No | Primary key | Automatic |
| idx_notifications_user_id | user_id | B-tree | No | FK index, user-scoped queries | High |
| idx_notifications_company_id | company_id | B-tree | No | FK index, company-scoped queries | High |
| idx_notifications_created_by | created_by | B-tree | No | FK index, audit queries | Medium |
| idx_notifications_updated_by | updated_by | B-tree | No | FK index, audit queries | Medium |
| idx_notifications_deleted_by | deleted_by | B-tree | No | FK index, audit queries | Medium |
| idx_notifications_updated_at | updated_at | B-tree | No | Change tracking, incremental sync | High |
| idx_notifications_created_at | created_at DESC | B-tree | No | Sorting by creation time | Medium |
| idx_notifications_active | id | B-tree | Yes (deleted_at IS NULL) | Active records only | Medium |
| idx_notifications_status_active | status | B-tree | Yes (deleted_at IS NULL) | Status filtering on active | Low |
| idx_notifications_user_company_active | user_id, company_id | B-tree | Yes (deleted_at IS NULL) | User + company scope | Critical |
| idx_notifications_user_type_read_active | user_id, type, is_read | B-tree | Yes (deleted_at IS NULL AND channel = 'in_app') | Filtering for in-app notifications | High |
| idx_notifications_user_read_created_active | user_id, is_read, created_at DESC | B-tree | Yes (deleted_at IS NULL AND channel = 'in_app') | Unread count and sorted lists | Critical |
| idx_notifications_company_type_created_active | company_id, type, created_at DESC | B-tree | Yes (deleted_at IS NULL) | Company-level analytics | Medium |
| idx_notifications_data_gin | data | GIN | No | JSONB queries (optional) | Low |

**Azure Index Maintenance:**
- Monitor index usage with Azure Query Performance Insights
- Use `pg_stat_user_indexes` for index usage analysis
- Consider dropping `idx_notifications_data_gin` if not frequently used
- Partial indexes reduce index size and improve write performance in Azure
- Composite indexes are ordered by equality checks first, then range queries, then sort columns
- Azure Database for PostgreSQL automatically maintains index statistics

================================================================================
SECTION 10 — ENTITY RELATIONSHIP DIAGRAM (ERD - DETAILED)
================================================================================

10.1 Complete ERD with All Relationships

The complete Entity Relationship Diagram for the Notifications System is provided 
in a separate file: `F3_ERD.txt`

The ERD shows:
- Primary key (id) and foreign key fields only
- Relationships between notifications, users, and companies
- Polymorphic relationships to leaves and tasks (conceptual)
- Crow's Foot notation for cardinality

10.2 ERD Summary

| Relationship | From Table | To Table | Cardinality | Foreign Key | Constraint |
|--------------|------------|----------|-------------|-------------|------------|
| User → Notification | users | notifications | 1:M | notifications.user_id → users.id | ON DELETE RESTRICT |
| Company → Notification | companies | notifications | 1:M | notifications.company_id → companies.id | ON DELETE RESTRICT |
| Leave → Notification | leaves | notifications | 1:0..M | notifications.related_record_id (logical) | Application-enforced |
| Task → Notification | tasks | notifications | 1:0..M | notifications.related_record_id (logical) | Application-enforced |

10.3 ERD File Reference

Refer to `F3_ERD.txt` for the complete ASCII ERD diagram with:
- Canvas-mode monospace alignment
- Crow's Foot notation
- Primary key and foreign key fields only
- Relationship cardinality indicators
- Polymorphic relationship documentation

================================================================================
END OF DOCUMENT
================================================================================
