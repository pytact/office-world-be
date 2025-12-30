# Project: officeWorld
# Feature: F-012 — Reports & Analytics

## Purpose
Provide a read-only, role-aware reporting and analytics layer that aggregates
data from operational domains to support decision-making, visibility, and
oversight—without mutating any underlying domain data or introducing workflows.

---

# Domain Model: F-012 — Reports & Analytics

## 1. Domain Glossary
| Term | Definition | Examples |
|------|------------|----------|
| Report | Read-only aggregated view of domain data | Attendance report |
| Report Type | Category defining report content | LEAVE |
| Report View | Role-specific projection of a report | Manager task report |
| Filter Set | Constraints applied to a report | Date range |
| Export Artifact | Generated PDF snapshot of report | Attendance.pdf |

---

## 2. Domain Concepts and Relationships

### 2.1 Concept List
| Concept | Description |
|--------|-------------|
| Report | Read-only aggregation of data from one or more domains |
| ReportType | Enumeration defining available reports |
| ReportView | Role-specific access and projection |
| FilterSet | User-applied constraints |
| ExportArtifact | Generated, immutable report output |

> Note: Reports are **derived read models**, not persistent business entities
> with lifecycle or ownership.

---

### 2.2 ReportType Enumeration
```text
ATTENDANCE
LEAVE
SALARY_SUMMARY
EMPLOYEE
TASK
PROJECT
AUDIT_SUMMARY
2.3 Source Domain Mapping
Report Type	Source Features
ATTENDANCE	F-010 Attendance
LEAVE	F-009 Leave
SALARY_SUMMARY	F-006 Salary
EMPLOYEE	F-005 Employee
TASK	F-008 Task
PROJECT	F-007 Project
AUDIT_SUMMARY	F-011 Audit Logs

3. Access & Visibility Rules
Role-Based Access Matrix
Role	Accessible Reports
CEO	All report types (company-scoped)
HR	All report types (company-scoped)
Manager	ATTENDANCE, PROJECT, TASK, assignment reports
Employee	Own ATTENDANCE, LEAVE, TASK
SuperAdmin	No access

Assignment Reports (Manager Scope)
Assignment reports include:

Task assignments

Project ↔ task associations

Employee ↔ task mappings

4. Filter Semantics
Filter Rules
Employee:

Can apply filters only to own data

Manager:

Can filter only within own company

HR / CEO:

Can filter across entire company

❌ No cross-company filtering for any role

Filter Examples
Date range

Status

Project

Employee (restricted by role)

5. Salary Report Semantics
SALARY_SUMMARY
Aggregation level:

Company total only

Explicit exclusions:

❌ Per-employee salary

❌ Department-wise totals

❌ Role-wise totals

6. Export & Output
PDF Export
Generated per report view (after filters applied)

Export is a read-only snapshot

Export does not update when underlying data changes

PDF generation may be asynchronous

Export artifacts have no lifecycle beyond generation

7. Workflows / Use Cases
7.1 View Report
Actor: Authorized user

Trigger: Report selection

Primary Flow:

User selects report type

System validates role access

Data aggregated from source domains

ReportView rendered

7.2 Apply Filters
Actor: Authorized user

Pre-conditions:

Filter scope allowed by role

Post-conditions:

ReportView refreshed with filtered data

7.3 Export Report
Actor: Authorized user

Trigger: Export request

Primary Flow:

Current ReportView captured

PDF generated asynchronously

Post-conditions:

ExportArtifact available for download

8. Business Rules
Rule ID	Description	Type	Related Concepts
BR-1201	Reports are read-only	Constraint	Report
BR-1202	Reports are company-scoped	Security	Report
BR-1203	Role governs report visibility	Visibility	ReportView
BR-1204	Employees can access only own data	Visibility	FilterSet
BR-1205	Salary reports are company-total only	Constraint	SALARY_SUMMARY
BR-1206	Export reflects filtered report snapshot	Behavior	ExportArtifact

9. Assumptions
No scheduled or automated report delivery

No custom report builder

No data mutation from reports

No real-time/live-updating exports

UI-level masking may apply to sensitive fields

10. Non-Functional Domain Considerations
Performance optimization for large datasets

Strict enforcement of RBAC and company isolation

Consistent aggregation logic across reports

Audit logging for report access (handled by F-011)

Scalability for future report expansion