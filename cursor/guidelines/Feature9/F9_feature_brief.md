Feature Brief: F-009 — Leave Management Workflow
1. Context & Problem

Background: officeWorld manages employee time-off through structured workflows that vary by role. Leave approvals must be deterministic, auditable, and aligned with organizational hierarchy.

Current Pain / Problem: Ad-hoc or inconsistent leave handling leads to confusion, delays, and lack of transparency across employees, managers, HR, and leadership.

Why Now: Leave workflows are a core HR operation and depend on Employee Management, RBAC, and Notifications being in place to function correctly.

2. Goal / Outcome

Primary Goal: Provide a clear, role-driven leave approval workflow with mandatory validations and notifications.

Secondary Goals:

Ensure predictable approval paths based on applicant role

Prevent invalid or conflicting leave requests

Success Criteria (Business View):

Leave requests follow the correct approval chain

Rejections always include reasons

Invalid leave requests are blocked at submission

Stakeholders receive timely notifications

3. In Scope

Leave request submission with date range and half-day support

Role-based approval workflows (Employee, Manager, HR)

Mandatory rejection reasons

Validation rules (overlaps, non-working days)

Leave cancellation by applicant

Email and in-app notifications for leave events

Role-based visibility of leave requests

4. Out of Scope

Leave balance tracking and accrual

Editing leave requests after submission

Approval for leave cancellation

Notifications on leave cancellation

Payroll or salary impact calculations

5. Primary Actors
Actor	Description
Employee	Applies for leave and views own requests
Manager	Approves or rejects assigned employee leave
HR	Final approver for employee and manager leave
CEO	Final approver for HR leave
System	Validates rules and triggers notifications
6. User Stories

As an employee, I want to apply for leave so that I can take time off.

As a manager, I want to approve or reject leave requests assigned to me so that team availability is managed.

As HR, I want to review and decide on leave requests so that company policies are enforced.

As a CEO, I want to approve HR leave so that leadership coverage is maintained.

7. Constraints & Assumptions
Constraints

Supported leave types: CASUAL, SICK, PAID, UNPAID

Leave requests are date-range based with half-day support

Overlapping leave requests for the same employee are not allowed

Leave on weekends or holidays is not allowed

Leave requests cannot be edited after submission

Rejection reasons are mandatory

Assumptions

Leave balance is not tracked in V1

Applicant can cancel a pending leave without approval

Cancellation does not trigger notifications

Notifications are delivered via F-003

8. Dependencies

F-005 — Employee Management

F-002 — RBAC & Permission Engine

F-003 — Notifications System

9. Open Questions

None identified at this stage

10. Acceptance Criteria

 Employees can submit date-range leave requests with half-day support

 System blocks overlapping leave requests for the same employee

 System blocks leave requests on non-working days

 Employee leave follows Manager → HR approval flow

 Manager leave follows HR approval flow

 HR leave follows CEO approval flow

 Rejection requires a mandatory reason and ends the workflow

 Approved leave completes only after final approval

 Applicants can cancel pending leave without approval

 Visibility rules are enforced per role

 Email and in-app notifications are sent for leave workflow events