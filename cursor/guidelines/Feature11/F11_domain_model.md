# Project: officeWorld
# Feature: F-011 — Audit Logging & Activity History

## Purpose
Provide a centralized, immutable, and company-scoped audit logging system that
records critical system and user actions across all features, ensuring full
traceability, compliance, and governance without impacting business workflows.

---

# Domain Model: F-011 — Audit Logging & Activity History

## 1. Domain Glossary
| Term | Definition | Examples |
|------|------------|----------|
| Audit Log | Immutable record of an action performed in the system | Task updated |
| Actor | User or system performing the action | HR user |
| Action Code | Free-text identifier describing the action | TASK_UPDATED |
| Target Entity | Domain object affected by the action | Task |
| Old Values | Previous values of changed fields | status=TODO |
| New Values | New values of changed fields | status=IN_PROGRESS |
| Company Scope | Boundary limiting audit visibility | Company A only |

---

## 2. Entities and Relationships

### 2.1 Entity List
| Entity | Description |
|--------|-------------|
| AuditLog | Immutable record of a system or user action |

---

### 2.2 Entity Details

#### AuditLog
- **Description**:  
  Represents an immutable, append-only record capturing a meaningful action
  performed within the system. Audit logs are written asynchronously and never
  block business operations.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | Actor | User or SYSTEM | Nullable for system actions |
  | Company | Related company | Mandatory |
  | ActionCode | Free-text action identifier | Feature-defined |
  | TableName | Affected entity/table | Reference only |
  | RecordId | Identifier of affected record | Reference only |
  | OldValues | Changed fields before action | Partial snapshot |
  | NewValues | Changed fields after action | Partial snapshot |
  | IPAddress | Source IP | Optional |
  | UserAgent | Client metadata | Optional |
  | Description | Human-readable summary | Optional |
  | CreatedAt | Action timestamp | Immutable |

- **ActionCode Semantics**:
  - Free-text, feature-owned identifiers
  - Examples:
```text
USER_INVITED
ROLE_ASSIGNED
TASK_CREATED
TASK_UPDATED
TASK_DELETED
LEAVE_APPROVED
SALARY_UPDATED
ATTENDANCE_CHECK_IN
SYSTEM_AUTO_CHECK_OUT
Value Storage Rule:

Only changed fields are stored in OldValues / NewValues

No full object snapshots

2.3 Relationship Overview (Text Diagram)
text
Copy code
Company 1..* AuditLog
User 0..* AuditLog (as Actor)
3. Audit Generation Rules
3.1 Audit Creation
Trigger: Significant domain action across any feature

Behavior:

AuditLog is created asynchronously

Failure to log does NOT fail the originating action

Examples of Audited Actions:

Create / update / delete operations

Status transitions

Approvals and rejections

Authentication events (login/logout)

System-driven actions (auto check-out)

3.2 Immutability & Retention
Audit logs:

Are append-only

Cannot be edited

Cannot be deleted

Are retained permanently

4. Visibility Rules
Role-Based Access
CEO:

Can view all audit logs within their company

HR:

Can view all audit logs within their company

Manager:

Can view audit logs where:

table_name is related to:

tasks

projects

task_assignments

Employee:

No access to audit logs

SuperAdmin:

Out of scope

5. Business Rules
Rule ID	Description	Type	Related Entities
BR-1101	Audit logs are append-only and immutable	Constraint	AuditLog
BR-1102	Audit logging is asynchronous and non-blocking	Reliability	AuditLog
BR-1103	Only changed fields are stored in values	Optimization	AuditLog
BR-1104	Audit logs are strictly company-scoped	Security	AuditLog
BR-1105	Managers have limited audit visibility	Visibility	AuditLog

6. Assumptions
Audit logs are for governance and diagnostics only

No UI-based editing or export is required initially

System actions use a virtual SYSTEM actor

Cross-company or global audit views are out of scope

Sensitive fields may be masked at presentation layer

7. Non-Functional Domain Considerations
High write throughput with minimal latency

Secure storage of potentially sensitive data

Consistent action code naming across features

Long-term storage strategy for compliance

Clear separation from business transaction logic