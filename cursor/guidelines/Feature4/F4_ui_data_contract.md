ui_data_contract.md
1. Feature Summary

The Platform Company Management feature enables SuperAdmin to centrally provision, govern, and control the lifecycle of tenant companies. It also allows CEO and HR to update limited, non-governance company profile information without affecting access control, tenant isolation, or platform governance.

2. Screens Covered
- SCR_COMPANY_LIST_PLATFORM
- SCR_COMPANY_CREATE
- SCR_COMPANY_DETAIL_PLATFORM
- SCR_COMPANY_PROFILE

3. Data Requirements Per Screen
3.1 Screen ID
SCR_COMPANY_LIST_PLATFORM
Route: /platform/companies

3.2 Reads (Server Data Required)
Reads:
- Company:
    fields:
      - id
      - name
      - slug
      - is_active
      - is_deleted
- Aggregates:
    - user_count (derived)


user_count represents the number of users associated with the company.

3.3 Writes (Actions / Mutations)
Writes:
- none

3.4 Query Parameters
Query Parameters:
- search
- status          // active | inactive
- sort_by
- sort_order
- page
- page_size

3.5 Derived or Aggregated Fields
Derived Fields:
- company_status_label   // Active / Inactive

3.6 UI Data Constraints

Server-side pagination, filtering, and sorting required

Soft-deleted companies must remain visible to SuperAdmin

Non-SuperAdmin users must never receive this dataset

3.1 Screen ID
SCR_COMPANY_CREATE
Route: /platform/companies/create

3.2 Reads (Server Data Required)
Reads:
- none

3.3 Writes (Actions / Mutations)
Writes:
- create_company

3.4 Query Parameters
Query Parameters:
- none

3.5 Derived or Aggregated Fields
Derived Fields:
- none

3.6 UI Data Constraints

Required fields: name, slug

name and slug must be globally unique

Default activation state determined server-side

3.1 Screen ID
SCR_COMPANY_DETAIL_PLATFORM
Route: /platform/companies/:companyId

3.2 Reads (Server Data Required)
Reads:
- Company:
    fields:
      - id
      - name
      - slug
      - description
      - address
      - city
      - state
      - country
      - postal_code
      - website
      - logo_url
      - is_active
      - is_deleted
- Aggregates:
    - user_count

3.3 Writes (Actions / Mutations)
Writes:
- activate_company
- deactivate_company
- delete_company

3.4 Query Parameters
Query Parameters:
- companyId (path parameter)

3.5 Derived or Aggregated Fields
Derived Fields:
- company_status_label
- can_activate   (boolean)
- can_deactivate (boolean)


Derived from is_active and user role (SuperAdmin).

3.6 UI Data Constraints

Lifecycle actions are SuperAdmin-only

Deactivation must immediately block all company-scoped access

Hard deletion is irreversible and must remove all company data

3.1 Screen ID
SCR_COMPANY_PROFILE
Route: /company/profile

3.2 Reads (Server Data Required)
Reads:
- Company:
    fields:
      - name
      - slug
      - description
      - address
      - city
      - state
      - country
      - postal_code
      - website
      - logo_url
      - is_active

3.3 Writes (Actions / Mutations)
Writes:
- update_company_profile

3.4 Query Parameters
Query Parameters:
- none

3.5 Derived or Aggregated Fields
Derived Fields:
- none

3.6 UI Data Constraints

Editable fields limited to non-governance fields only

name and slug must be read-only

Inactive companies may present read-only or blocked state

4. Proposed API Hints (Not Final API Spec)
Proposed API Hints:
- GET    /api/v1/platform/companies
- POST   /api/v1/platform/companies
- GET    /api/v1/platform/companies/{id}
- PATCH  /api/v1/platform/companies/{id}/activate
- PATCH  /api/v1/platform/companies/{id}/deactivate
- DELETE /api/v1/platform/companies/{id}
- GET    /api/v1/company/profile
- PATCH  /api/v1/company/profile

5. Cross-Screen Data Dependencies
SCR_COMPANY_LIST_PLATFORM and SCR_COMPANY_DETAIL_PLATFORM both require:
- CompanySummary
  - id
  - name
  - slug
  - is_active
  - user_count

SCR_COMPANY_PROFILE reuses:
- CompanyProfile (subset of Company)

6. Data Edge Cases

Company with zero users

Deactivated company with existing active users (access blocked)

Attempt to activate an already active company

Attempt to deactivate an already inactive company

Hard deletion of company with large data volume

CEO / HR attempting to edit governance fields

Non-SuperAdmin attempting to access platform company routes