ui_data_contract.md
1. Feature Summary

The Employee Management feature provides a secure, company-bound system of record for personnel data. It enforces a strict one-to-one relationship between users and employees, applies role-based and field-level visibility controls, and preserves historical data while enabling downstream HR workflows such as salary, leave, and attendance.

2. Screens Covered
- SCR_EMPLOYEE_LIST
- SCR_EMPLOYEE_CREATE
- SCR_EMPLOYEE_DETAIL
- SCR_EMPLOYEE_SELF_PROFILE

3. Data Requirements Per Screen
3.1 Screen ID
SCR_EMPLOYEE_LIST
Route: /company/employees

3.2 Reads (Server Data Required)
Reads:
- Employee:
    fields:
      - id
      - user.email
      - user.first_name
      - user.last_name
      - job_title
      - department
      - employment_status
      - is_active
- Visibility Rules:
    - role_based_field_mask


Returned fields must be role-filtered:

CEO / HR: full professional fields

Manager: limited professional fields only

Employee: no access

3.3 Writes (Actions / Mutations)
Writes:
- none

3.4 Query Parameters
Query Parameters:
- search
- department
- employment_status
- page
- page_size
- sort_by
- sort_order

3.5 Derived or Aggregated Fields
Derived Fields:
- employment_status_label

3.6 UI Data Constraints

Server-side pagination, filtering, and sorting required

Soft-deleted employees excluded by default

Managers must not receive CEO or HR employee records

SuperAdmin must never receive employee data

3.1 Screen ID
SCR_EMPLOYEE_CREATE
Route: /company/employees/create

3.2 Reads (Server Data Required)
Reads:
- User:
    fields:
      - id
      - email
      - role.code


Only users without an existing Employee record are selectable.

3.3 Writes (Actions / Mutations)
Writes:
- create_employee

3.4 Query Parameters
Query Parameters:
- none

3.5 Derived or Aggregated Fields
Derived Fields:
- none

3.6 UI Data Constraints

Employee creation requires an existing User

JoiningDate is mandatory and immutable after creation

ENUM fields must be validated server-side

Sensitive fields must be accepted but visibility-restricted later

3.1 Screen ID
SCR_EMPLOYEE_DETAIL
Route: /company/employees/:employeeId

3.2 Reads (Server Data Required)
Reads:
- Employee:
    fields:
      - id
      - joining_date
      - employment_status
      - job_title
      - department
      - employment_type
      - employment_level
      - work_email
      - gender
      - marital_status
      - blood_group
      - nationality
      - address
      - city
      - state
      - country
      - document_type
      - document_number
      - separation_initiated_date
      - separation_reason
      - last_working_day
      - notice_period_days
      - is_active
      - is_deleted
- User:
    fields:
      - email
      - first_name
      - last_name


Returned fields must be filtered by role:

CEO / HR: full access

Manager: professional, non-sensitive subset only

Employee: no access (except own profile via SCR_EMPLOYEE_SELF_PROFILE)

3.3 Writes (Actions / Mutations)
Writes:
- update_employee
- deactivate_employee
- reactivate_employee
- soft_delete_employee

3.4 Query Parameters
Query Parameters:
- employeeId (path parameter)

3.5 Derived or Aggregated Fields
Derived Fields:
- can_edit_employee     (boolean)
- can_deactivate        (boolean)
- can_soft_delete       (boolean)


Derived from role and employee state.

3.6 UI Data Constraints

Deactivation must block login immediately

Soft-deleted employees remain readable only to CEO

Separation fields required when status is RESIGNED or TERMINATED

Field-level access rules enforced server-side

3.1 Screen ID
SCR_EMPLOYEE_SELF_PROFILE
Route: /me/profile

3.2 Reads (Server Data Required)
Reads:
- Employee:
    fields:
      - joining_date
      - employment_status
      - job_title
      - department
      - employment_type
      - employment_level
      - work_email
      - gender
      - marital_status
      - blood_group
      - nationality
      - address
      - city
      - state
      - country
- User:
    fields:
      - email
      - first_name
      - last_name

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

Read-only access

Must return only the authenticated user’s Employee record

No navigation to other employee entities

4. Proposed API Hints (Not Final API Spec)
Proposed API Hints:
- GET    /api/v1/company/employees
- POST   /api/v1/company/employees
- GET    /api/v1/company/employees/{id}
- PATCH  /api/v1/company/employees/{id}
- PATCH  /api/v1/company/employees/{id}/deactivate
- PATCH  /api/v1/company/employees/{id}/reactivate
- DELETE /api/v1/company/employees/{id}
- GET    /api/v1/me/employee-profile

5. Cross-Screen Data Dependencies
SCR_EMPLOYEE_LIST and SCR_EMPLOYEE_DETAIL both require:
- EmployeeSummary
  - user.name
  - job_title
  - department
  - employment_status

SCR_EMPLOYEE_SELF_PROFILE reuses:
- EmployeeDetail (self-only subset)

6. Data Edge Cases

User without Employee record (should not occur post-creation)

Employee deactivated while User remains active (login blocked)

Soft-deleted employee hidden from lists

Manager attempting to view CEO or HR records

Employee attempting to access list or detail routes

SuperAdmin attempting to access employee endpoints

ENUM value mismatches from outdated clients