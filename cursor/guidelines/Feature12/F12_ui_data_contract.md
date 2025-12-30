ui_data_contract.md
1. Feature Summary

The Reports & Analytics feature provides a read-only, role-aware reporting layer that aggregates data from operational domains to support decision-making and oversight. It enforces strict company scoping and RBAC, supports consistent filtering, and allows PDF export of report snapshots without mutating any underlying data.

2. Screens Covered
- SCR_REPORTS_HOME
- SCR_REPORT_VIEW

3. Data Requirements Per Screen
3.1 Screen ID
SCR_REPORTS_HOME
Route: /reports

3.2 Reads (Server Data Required)
Reads:
- ReportType:
    fields:
      - code
      - label
      - description
- AccessRules:
    fields:
      - is_accessible (boolean)


Only report types accessible to the authenticated user’s role are returned.

3.3 Writes (Actions / Mutations)
Writes:
- none

3.4 Query Parameters
Query Parameters:
- none

3.5 Derived or Aggregated Fields
Derived Fields:
- available_report_count

3.6 UI Data Constraints

Report list must be filtered server-side by role

SuperAdmin must never receive report metadata

No navigation to reports outside allowed types

3.1 Screen ID
SCR_REPORT_VIEW
Route: /reports/:reportType

3.2 Reads (Server Data Required)
Reads:
- ReportMetadata:
    fields:
      - report_type
      - title
      - description
      - source_features[]

- ReportData:
    fields:
      - rows[]            // aggregated, tabular or chart-ready data
      - totals[]          // optional, report-specific aggregates

- FilterOptions:
    fields:
      - date_range
      - status
      - employee_id       // role-restricted
      - department
      - project_id


ReportData structure varies by report_type but is always read-only and aggregated.

3.3 Writes (Actions / Mutations)
Writes:
- request_report_export


Export does not mutate report data; it generates a snapshot artifact.

3.4 Query Parameters
Query Parameters:
- reportType (path parameter)
- start_date
- end_date
- status
- employee_id
- department
- project_id


Filter parameters must be validated against role-based scope rules.

3.5 Derived or Aggregated Fields
Derived Fields:
- row_count
- has_export (boolean)

3.6 UI Data Constraints

Reports are strictly company-scoped

Employees may only see their own data

Salary reports must expose company totals only

Report views must never allow navigation to edit underlying records

Large datasets must support server-side aggregation and pagination (if applicable)

4. Proposed API Hints (Not Final API Spec)
Proposed API Hints:
- GET  /api/v1/reports
- GET  /api/v1/reports/{reportType}
- POST /api/v1/reports/{reportType}/export


API Designer will finalize payload shapes and export handling (sync vs async).

5. Cross-Screen Data Dependencies
SCR_REPORT_VIEW aggregates data from:
- F-005 Employee Management
- F-006 Salary & History Management
- F-007 Project Management
- F-008 Task Management & Assignment
- F-009 Leave Management Workflow
- F-010 Attendance Management
- F-011 Audit Logging & Activity History

F-011 also records:
- Report view access
- Report export actions

6. Data Edge Cases

User has no accessible reports (empty state)

Filters exceed role-based scope (blocked server-side)

Salary report requested by unauthorized role

Export requested on very large dataset (async generation)

Export completes after underlying data changes (snapshot consistency)

Missing or sparse data for selected period

Concurrent export requests for same report and filters