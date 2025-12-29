ui_data_contract.md
## 1. Feature Summary

The Audit Logging & Activity History feature provides a centralized, immutable, company-scoped record of critical system and user actions across all platform features. It supports governance, compliance, and traceability through read-only audit views with strict role-based visibility, while remaining asynchronous and non-blocking to business workflows.

## 2. Screens Covered
- SCR_AUDIT_LOG_LIST
- SCR_AUDIT_LOG_DETAIL

## 3. Data Requirements Per Screen
3.1 Screen ID
SCR_AUDIT_LOG_LIST
Route: /company/audit-logs

3.2 Reads (Server Data Required)
Reads:
- AuditLog:
    fields:
      - id
      - action_code
      - table_name
      - record_id
      - description
      - created_at
- Actor:
    fields:
      - id
      - user.first_name
      - user.last_name
      - role.code


Visibility rules enforced server-side:

CEO / HR: all audit logs for the company

Manager: only logs where table_name ∈ {tasks, projects, task_assignments}

Employee: no access

3.3 Writes (Actions / Mutations)
Writes:
- none


Audit logs are system-generated only.
UI never creates, edits, or deletes audit records.

3.4 Query Parameters
Query Parameters:
- start_date
- end_date
- action_code
- table_name
- page
- page_size
- sort_by
- sort_order

3.5 Derived or Aggregated Fields
Derived Fields:
- actor_display_name     // e.g. "Jane Doe (HR)" or "SYSTEM"

3.6 UI Data Constraints

Server-side pagination and filtering required

Audit logs must always be ordered by created_at (default descending)

Sensitive fields may be masked before returning to UI

Logs are immutable and permanently retained

SuperAdmin must never receive audit log data

3.1 Screen ID
SCR_AUDIT_LOG_DETAIL
Route: /company/audit-logs/:auditLogId

3.2 Reads (Server Data Required)
Reads:
- AuditLog:
    fields:
      - id
      - action_code
      - table_name
      - record_id
      - description
      - old_values
      - new_values
      - ip_address
      - user_agent
      - created_at
- Actor:
    fields:
      - id
      - user.first_name
      - user.last_name
      - role.code


old_values and new_values include only changed fields, not full snapshots.

3.3 Writes (Actions / Mutations)
Writes:
- none

3.4 Query Parameters
Query Parameters:
- auditLogId (path parameter)

3.5 Derived or Aggregated Fields
Derived Fields:
- has_value_changes (boolean)


True when old_values or new_values are non-empty.

3.6 UI Data Constraints

Read-only for all roles

Field-level masking may be applied for sensitive values (e.g. salary, bank info)

SYSTEM actor must be clearly distinguishable from user actors

Managers must be blocked if the log is outside allowed table scope

## 4. Proposed API Hints (Not Final API Spec)
Proposed API Hints:
- GET /api/v1/company/audit-logs
- GET /api/v1/company/audit-logs/{id}


Whether audit logs are fetched via dedicated endpoints or embedded in an admin
module response is left to the API Spec Builder.

## 5. Cross-Screen Data Dependencies
SCR_AUDIT_LOG_LIST and SCR_AUDIT_LOG_DETAIL both require:
- AuditLogSummary
  - action_code
  - table_name
  - record_id
  - created_at
  - actor

All features F-001 → F-010 act as:
- AuditLog producers (write-only, asynchronous)

## 6. Data Edge Cases

SYSTEM-generated audit logs with no user actor

Audit logs referencing deleted records

Manager attempting to access non-task/project logs

High-volume audit periods requiring pagination

Masked fields resulting in partial old/new values

Concurrent actions generating near-identical timestamps

Direct URL access to unauthorized audit log detail