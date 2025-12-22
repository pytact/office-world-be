Feature Brief: F-005 — Employee Management
1. Context & Problem

Background: officeWorld manages company users through strict roles and governance. To support HR operations, compliance, and downstream workflows (salary, leave, attendance), the platform requires a reliable employee system of record.

Current Pain / Problem: Without a centralized and controlled employee data model, organizations face inconsistent records, privacy risks, and weak lifecycle management tied to user access.

Why Now: Employee data is a prerequisite for salary management, leave workflows, attendance tracking, and reporting. This feature must be in place before dependent modules.

2. Goal / Outcome

Primary Goal: Provide a secure, company-bound employee management system with clear lifecycle and role-based visibility controls.

Secondary Goals:

Enforce one-to-one linkage between users and employees

Protect sensitive employee data through field-level access rules

Success Criteria (Business View):

Every company user (except SuperAdmin) has exactly one employee record

Employee data is accessible only to authorized roles

Deactivation and soft deletion preserve historical data without access leakage

3. In Scope

Employee creation, update, activation, deactivation, and soft deletion

One-to-one User ↔ Employee linkage

Company-bound employee records

Role-based field-level visibility

ENUM-based controlled fields for consistency

API-based dependent dropdowns for location fields

Viewing own employee profile (Employee role)

4. Out of Scope

SuperAdmin access to employee data

Hard deletion of employees

Salary management (handled in F-006)

Document versioning

Bulk import/export of employee data

5. Primary Actors
Actor	Description
CEO	Full access to employee data, including soft-deleted records
HR	Full access to employee data and lifecycle management
Manager	Limited read-only access to non-sensitive employee fields
Employee	Can view own employee profile only
SuperAdmin	Explicitly excluded from employee data
6. User Stories

As a CEO or HR, I want to manage employee records so that workforce data is accurate and up to date.

As a Manager, I want to view limited professional details of employees so that I can coordinate work without accessing sensitive data.

As an Employee, I want to view my own profile so that I can verify my information.

As the system, I want to preserve employee data when users are deactivated or soft-deleted.

7. Constraints & Assumptions
Constraints

Every user (CEO, HR, Manager, Employee) must have one employee record

SuperAdmin must not exist in the employee table

Employee records are always linked to exactly one company

Managers cannot view or edit personal data, salary data, or documents

Soft-deleted employees are hidden from normal lists

Assumptions

Employee creation requires an existing user

Reactivated employees regain access without data loss

Soft-deleted employees are visible only to CEO

Document files are stored securely

8. Dependencies

F-001 — User & Role Management

F-004 — Platform Company Management

9. Open Questions

None identified at this stage

10. Acceptance Criteria

 Each non-SuperAdmin user has exactly one employee record

 CEO and HR can create, edit, activate, deactivate, and soft-delete employees

 Managers can view employee lists with limited fields only and cannot see CEO or HR

 Employees can view only their own profile

 Deactivated employees cannot log in but retain all data

 Soft-deleted employees are hidden from standard lists but visible to CEO

 Field-level access rules are enforced for sensitive data

 Controlled ENUM values are enforced for employee fields

 Country, State, and City use API-based dependent dropdowns