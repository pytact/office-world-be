ui_data_contract.md
1. Feature Summary

The Salary & History Management feature enables CEO and HR to securely manage employee compensation through time-based salary configurations, immutable salary history, bank information, and monthly salary payment records. It enforces strict RBAC, preserves auditability, and integrates with notifications for salary slip delivery without exposing salary data in employee-facing UI.

2. Screens Covered
- SCR_EMPLOYEE_SALARY_OVERVIEW
- SCR_SALARY_PAYMENT_CREATE

3. Data Requirements Per Screen
3.1 Screen ID
SCR_EMPLOYEE_SALARY_OVERVIEW
Route: /company/employees/:employeeId/salary

3.2 Reads (Server Data Required)
Reads:
- Employee:
    fields:
      - id
      - user.first_name
      - user.last_name
      - is_active

- SalaryDetails:
    fields:
      - id
      - amount
      - currency
      - payment_frequency
      - effective_from
      - effective_to

- SalaryHistory:
    fields:
      - previous_amount
      - new_amount
      - effective_from
      - changed_by
      - created_at

- BankInfo:
    fields:
      - bank_name
      - branch
      - account_number   // masked
      - ifsc_code        // masked

- SalaryPayment:
    fields:
      - id
      - amount
      - month
      - year
      - paid_on
      - payment_method
      - slip_url


Only CEO and HR may receive this dataset.
Employees and Managers must never receive salary or bank data.

3.3 Writes (Actions / Mutations)
Writes:
- create_salary_details
- update_salary_details
- update_bank_info


Updating salary creates a new SalaryDetails record and auto-closes the previous one.

3.4 Query Parameters
Query Parameters:
- employeeId (path parameter)

3.5 Derived or Aggregated Fields
Derived Fields:
- current_salary_amount
- current_salary_currency
- has_active_salary (boolean)
- masked_account_number

3.6 UI Data Constraints

Exactly one active SalaryDetails must exist at any time

Salary history records are immutable

Bank info updates affect future payments only

Sensitive bank fields must be masked in all UI responses

Deactivated employees remain readable for historical purposes

No employee-facing access under any circumstance

3.1 Screen ID
SCR_SALARY_PAYMENT_CREATE
Route: /company/employees/:employeeId/salary/payments/create

3.2 Reads (Server Data Required)
Reads:
- Employee:
    fields:
      - id
      - user.first_name
      - user.last_name
      - is_active

- SalaryDetails:
    fields:
      - amount
      - currency
      - payment_frequency
      - effective_from
      - effective_to


Used to compute the payable amount snapshot before confirmation.

3.3 Writes (Actions / Mutations)
Writes:
- create_salary_payment

3.4 Query Parameters
Query Parameters:
- employeeId (path parameter)

3.5 Derived or Aggregated Fields
Derived Fields:
- payable_amount
- payment_period_label   // e.g. "March 2025"

3.6 UI Data Constraints

Only one SalaryPayment per employee per month/year

SalaryPayment records are immutable

Salary slip must be generated and emailed on success

UI must not allow retroactive edits or deletions

4. Proposed API Hints (Not Final API Spec)
Proposed API Hints:
- GET   /api/v1/company/employees/{id}/salary
- POST  /api/v1/company/employees/{id}/salary
- PATCH /api/v1/company/employees/{id}/salary/bank-info
- POST  /api/v1/company/employees/{id}/salary/payments

5. Cross-Screen Data Dependencies
SCR_EMPLOYEE_DETAIL (F-005) links to:
- SCR_EMPLOYEE_SALARY_OVERVIEW

F-003 (Notifications System) triggered by:
- SalaryPayment creation → email salary slip

F-002 (RBAC) enforces:
- CEO / HR only access

6. Data Edge Cases

Employee without any salary configuration

Attempt to create overlapping SalaryDetails periods

Duplicate SalaryPayment for same month/year

Bank info updated after historical payments

Deactivated employee with existing salary history

SalaryDetails with future effective dates

Employee attempting to access salary routes (must be denied)

Manager attempting to access salary routes (must be denied)