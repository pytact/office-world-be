1. Feature Summary

The User & Role Management feature enables invitation-based onboarding and lifecycle management of users within strict company and role boundaries. It allows SuperAdmin and authorized company admins (CEO, HR) to invite users, assign or change roles, manage activation status, and enforce role-based visibility rules across the platform.

2. Screens Covered
- SCR_USER_LIST_PLATFORM
- SCR_USER_LIST_COMPANY
- SCR_USER_DETAIL
- SCR_USER_INVITE

3. Data Requirements Per Screen
3.1 Screen ID
SCR_USER_LIST_PLATFORM
Route: /platform/users

3.2 Reads (Server Data Required)
Reads:
- User:
    fields:
      - email
      - first_name
      - last_name
      - is_active
      - is_deleted
      - invite_at
      - activate_at
- UserRoleAssignment:
    fields:
      - role.code
      - company.name
      - company.slug
- Company:
    fields:
      - name
      - slug

3.3 Writes (Actions / Mutations)
Writes:
- invite_user

3.4 Query Parameters
Query Parameters:
- search
- company_slug
- role_code
- status
- sort_by
- sort_order
- page
- page_size

3.5 Derived or Aggregated Fields
Derived Fields:
- invitation_status (pending | expired | activated)


Derived from invite_at, activate_at, and expiry.

3.6 UI Data Constraints

Server-side pagination, filtering, and sorting required

SuperAdmin visibility spans all companies

Sensitive fields (salary, personal data) must not be included

3.1 Screen ID
SCR_USER_LIST_COMPANY
Route: /company/users

3.2 Reads (Server Data Required)
Reads:
- User:
    fields:
      - email
      - first_name
      - last_name
      - is_active
      - invite_at
      - activate_at
- UserRoleAssignment:
    fields:
      - role.code

3.3 Writes (Actions / Mutations)
Writes:
- invite_user

3.4 Query Parameters
Query Parameters:
- search
- role_code
- status
- sort_by
- sort_order
- page
- page_size

3.5 Derived or Aggregated Fields
Derived Fields:
- invitation_status

3.6 UI Data Constraints

Company context inferred from authenticated user

Managers must receive restricted field sets (list-level visibility only)

Employees must not receive any data for this screen

3.1 Screen ID
SCR_USER_DETAIL
Route: /users/:userId

3.2 Reads (Server Data Required)
Reads:
- User:
    fields:
      - email
      - first_name
      - last_name
      - is_active
      - is_deleted
      - invite_at
      - activate_at
      - reinvite_count
      - last_reinvite_at
- UserRoleAssignment:
    fields:
      - role.code
      - company.name
      - company.slug

3.3 Writes (Actions / Mutations)
Writes:
- change_user_role
- deactivate_user
- reactivate_user
- resend_invitation

3.4 Query Parameters
Query Parameters:
- userId (path parameter)

3.5 Derived or Aggregated Fields
Derived Fields:
- invitation_status
- can_resend_invite (boolean)

3.6 UI Data Constraints

Role cardinality rules (e.g., single CEO per company) must be enforced server-side

Deactivated users remain readable but cannot authenticate

Re-invitation only allowed for inactive, non-activated users

3.1 Screen ID
SCR_USER_INVITE
Route: /users/invite

3.2 Reads (Server Data Required)
Reads:
- Role:
    fields:
      - name
      - code
- Company:
    fields:
      - name
      - slug


Company list required only for SuperAdmin context.

3.3 Writes (Actions / Mutations)
Writes:
- invite_user

3.4 Query Parameters
Query Parameters:
- none

3.5 Derived or Aggregated Fields
Derived Fields:
- none

3.6 UI Data Constraints

Invitation must always be tied to a role

Company selection hidden for non-SuperAdmin users

Duplicate invitations to the same email must be handled server-side

4. Proposed API Hints (Not Final API Spec)
Proposed API Hints:
- GET  /api/v1/platform/users
- GET  /api/v1/company/users
- GET  /api/v1/users/{id}
- POST /api/v1/users/invite
- PATCH /api/v1/users/{id}/role
- PATCH /api/v1/users/{id}/deactivate
- PATCH /api/v1/users/{id}/reactivate
- POST /api/v1/users/{id}/resend-invite

5. Cross-Screen Data Dependencies
SCR_USER_LIST_PLATFORM, SCR_USER_LIST_COMPANY, and SCR_USER_DETAIL all reuse:
- UserSummary
  - email
  - first_name
  - last_name
  - is_active
  - role.code

SCR_USER_INVITE and SCR_USER_DETAIL both require:
- Role reference data (code, name)

6. Data Edge Cases

Attempt to assign a second CEO within the same company

Inviting a user whose email already exists in active state

Resending invitation after multiple expiries

Deactivated user appearing in lists but blocked from login

Manager accessing list without sensitive fields

Employee attempting to access any user-management endpoint

SuperAdmin assigning or reassigning company context