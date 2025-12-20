1. Feature Summary
The Core Platform Foundation feature provides the authentication and onboarding backbone of the officeWorld platform. It enables secure login, invitation-based user activation, password reset flows, and SuperAdmin access, while enforcing multi-tenant isolation and role-based governance. All other platform features depend on this foundation.
2. Screens Covered
- SCR_AUTH_LOGIN
- SCR_AUTH_ACTIVATION
- SCR_AUTH_PASSWORD_RESET_REQUEST
- SCR_AUTH_PASSWORD_RESET
3. Data Requirements Per Screen
3.1 Screen ID
SCR_AUTH_LOGIN
Route: /login
3.2 Reads (Server Data Required)
Reads:
- User:
    fields:
      - email
      - is_active
      - is_deleted
- UserRoleAssignment:
    fields:
      - role.code
      - company.slug
      - company.is_active
Used only for authentication context resolution after credential validation.
3.3 Writes (Actions / Mutations)
Writes:
- authenticate_user
- logout_user
3.4 Query Parameters
Query Parameters:
- none
3.5 Derived or Aggregated Fields
Derived Fields:
- is_super_admin (derived from UserRoleAssignment.company == null)
3.6 UI Data Constraints
Authentication must fail if user.is_active = false or user.is_deleted = true
Company context must be resolved server-side
Role and permissions must be available immediately after login (no follow-up fetch)
3.1 Screen ID
SCR_AUTH_ACTIVATION
Route: /activate/:token
3.2 Reads (Server Data Required)
Reads:
- User:
    fields:
      - email
      - invite_at
      - activate_at
      - expiry
      - token
3.3 Writes (Actions / Mutations)
Writes:
- activate_user_account
3.4 Query Parameters
Query Parameters:
- token (path parameter)
3.5 Derived or Aggregated Fields
Derived Fields:
- invitation_status (valid | expired | already_activated)
Derived from invite_at, activate_at, and expiry.
3.6 UI Data Constraints
Token validation must be performed server-side
Activation is single-use; repeated submissions must be rejected
No company or role mutation occurs at this stage
3.1 Screen ID
SCR_AUTH_PASSWORD_RESET_REQUEST
Route: /password-reset
3.2 Reads (Server Data Required)
Reads:
- none
Email existence must not be disclosed to the UI.
3.3 Writes (Actions / Mutations)
Writes:
- request_password_reset
3.4 Query Parameters
Query Parameters:
- none
3.5 Derived or Aggregated Fields
Derived Fields:
- none
3.6 UI Data Constraints
Response must be generic regardless of email validity
Token generation and email dispatch handled fully server-side
3.1 Screen ID
SCR_AUTH_PASSWORD_RESET
Route: /password-reset/:token
3.2 Reads (Server Data Required)
Reads:
- User:
    fields:
      - token
      - expiry
3.3 Writes (Actions / Mutations)
Writes:
- reset_password
3.4 Query Parameters
Query Parameters:
- token (path parameter)
3.5 Derived or Aggregated Fields
Derived Fields:
- token_valid (boolean)
Derived from token existence and expiry.
3.6 UI Data Constraints
Token validity must be checked before password mutation
Token must be invalidated immediately after successful reset
4. Proposed API Hints (Not Final API Spec)
Proposed API Hints:
- POST /api/v1/auth/login
- POST /api/v1/auth/logout
- GET  /api/v1/auth/activation/{token}
- POST /api/v1/auth/activation/{token}
- POST /api/v1/auth/password-reset/request
- POST /api/v1/auth/password-reset/{token}
Endpoint structure is indicative only; schemas and auth mechanics are defined by the API Spec Builder.
5. Cross-Screen Data Dependencies
SCR_AUTH_ACTIVATION and SCR_AUTH_PASSWORD_RESET both require:
- CredentialToken (User.token)
- Token expiry evaluation
SCR_AUTH_LOGIN and downstream features share:
- AuthenticatedUserContext
  - User
  - Role
  - Company (nullable)
6. Data Edge Cases
Invalid login credentials (no user match or wrong password)
Deactivated or soft-deleted users attempting login
Expired invitation token during activation
Already-activated user revisiting activation link
Expired or reused password reset token
SuperAdmin user with no company context
Company marked inactive blocking user access







