ui_data_contract.md
1. Feature Summary

The Leave Management feature provides a deterministic, role-driven workflow for employees to request time off and for organizations to approve or reject those requests through a structured approval chain. It enforces strict validation rules, mandatory rejection reasons, role-based visibility, and integrates notifications for key leave events without handling balances or payroll.

2. Screens Covered
- SCR_LEAVE_LIST
- SCR_LEAVE_CREATE
- SCR_LEAVE_DETAIL
- SCR_LEAVE_APPROVAL_QUEUE

3. Data Requirements Per Screen
3.1 Screen ID
SCR_LEAVE_LIST
Route: /company/leaves

3.2 Reads (Server Data Required)
Reads:
- LeaveRequest:
    fields:
      - id
      - leave_type
      - start_date
      - end_date
      - number_of_days
      - status
      - created_at
- Employee:
    fields:
      - id
      - user.first_name
      - user.last_name


Visibility rules:

Employee: own leave requests only

Manager: leave requests assigned to them for approval

HR / CEO: company-wide visibility

3.3 Writes (Actions / Mutations)
Writes:
- none

3.4 Query Parameters
Query Parameters:
- status
- start_date
- end_date
- employee_id          // HR / CEO only
- page
- page_size
- sort_by
- sort_order

3.5 Derived or Aggregated Fields
Derived Fields:
- leave_duration_label    // e.g. "3 days", "0.5 day"

3.6 UI Data Constraints

Server-side pagination, filtering, and sorting required

Role-based visibility must be enforced server-side

Soft-filtering must not leak unauthorized leave data

3.1 Screen ID
SCR_LEAVE_CREATE
Route: /company/leaves/create

3.2 Reads (Server Data Required)
Reads:
- none

3.3 Writes (Actions / Mutations)
Writes:
- create_leave_request

3.4 Query Parameters
Query Parameters:
- none

3.5 Derived or Aggregated Fields
Derived Fields:
- calculated_number_of_days


Derived from date range and day type.

3.6 UI Data Constraints

Overlapping leave requests must be blocked

Leave on weekends or holidays must be blocked

Leave requests cannot be edited after submission

Deactivated employees cannot submit leave requests

3.1 Screen ID
SCR_LEAVE_DETAIL
Route: /company/leaves/:leaveId

3.2 Reads (Server Data Required)
Reads:
- LeaveRequest:
    fields:
      - id
      - leave_type
      - start_date
      - end_date
      - day_type
      - number_of_days
      - reason
      - status
      - rejection_reason
      - created_at
      - manager_approved_at
      - hr_approved_at
- Employee:
    fields:
      - user.first_name
      - user.last_name

3.3 Writes (Actions / Mutations)
Writes:
- approve_leave
- reject_leave
- cancel_leave

3.4 Query Parameters
Query Parameters:
- leaveId (path parameter)

3.5 Derived or Aggregated Fields
Derived Fields:
- can_approve   (boolean)
- can_reject    (boolean)
- can_cancel    (boolean)


Derived from role, approval stage, and leave status.

3.6 UI Data Constraints

Rejection requires a mandatory reason

Cancel allowed only by applicant and only while pending

Approved, rejected, and cancelled leaves are terminal

Approvers must not approve their own leave

3.1 Screen ID
SCR_LEAVE_APPROVAL_QUEUE
Route: /company/leaves/approvals

3.2 Reads (Server Data Required)
Reads:
- LeaveRequest:
    fields:
      - id
      - leave_type
      - start_date
      - end_date
      - number_of_days
      - status
- Employee:
    fields:
      - user.first_name
      - user.last_name


Only leave requests awaiting the user’s approval are returned.

3.3 Writes (Actions / Mutations)
Writes:
- none

3.4 Query Parameters
Query Parameters:
- none

3.5 Derived or Aggregated Fields
Derived Fields:
- none

3.6 UI Data Constraints

Queue must include only actionable leave requests

Role-based approval routing enforced server-side

4. Proposed API Hints (Not Final API Spec)
Proposed API Hints:
- GET   /api/v1/company/leaves
- POST  /api/v1/company/leaves
- GET   /api/v1/company/leaves/{id}
- POST  /api/v1/company/leaves/{id}/approve
- POST  /api/v1/company/leaves/{id}/reject
- POST  /api/v1/company/leaves/{id}/cancel
- GET   /api/v1/company/leaves/approvals

5. Cross-Screen Data Dependencies
SCR_LEAVE_LIST, SCR_LEAVE_DETAIL, and SCR_LEAVE_APPROVAL_QUEUE all reuse:
- LeaveSummary
  - leave_type
  - start_date
  - end_date
  - number_of_days
  - status

F-003 (Notifications) triggered by:
- Leave submission
- Leave approval or rejection

6. Data Edge Cases

Overlapping leave submissions by same employee

Leave spanning weekends or holidays

Manager attempting to approve own leave

HR or CEO approving at incorrect stage

Deactivated employee accessing leave history

Cancel action attempted after approval or rejection

Direct URL access to unauthorized leave detail

Concurrent approvals causing race conditions