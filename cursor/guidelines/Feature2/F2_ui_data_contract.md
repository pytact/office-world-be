ui_data_contract.md
1. Feature Summary

The RBAC & Permission Engine provides a centralized authorization layer that determines whether users may view data, access screens, or perform actions across the platform. It evaluates predefined, company-scoped permissions with design-time role inheritance and exposes permission results to the UI to ensure consistent visibility and action gating.

2. Screens Covered

This feature introduces no dedicated screens.

RBAC data is consumed implicitly by all feature screens, including but not limited to:

User & Role Management (F-001)

Employee Management (F-005)

Salary Management (F-006)

Project & Task Management (F-007, F-008)

Leave, Attendance, KPIs

3. UI-Wide Data Requirements (Global)

Because F-002 is cross-cutting, data requirements are defined globally, not per screen.

3.1 Reads (Server Data Required)
3.1.1 Permission Set (Per Authenticated User)
Reads:
- PermissionSet:
    fields:
      - resource
      - allowed_actions[]


Represents the final evaluated permissions for the current user, after:

Role inheritance (resolved at seed time)

Company scope resolution

User activation checks

3.1.2 Contextual Flags
Reads:
- AuthContext:
    fields:
      - user_id
      - role.code
      - company.slug (nullable)
      - is_super_admin
      - is_user_active
      - is_company_active


Used to short-circuit or qualify permission evaluation.

3.2 Writes (Triggers Affecting Permissions)

RBAC has no direct user-triggered mutations, but reacts to mutations from other features.

Writes (Indirect Triggers):
- change_user_role        (F-001)
- deactivate_user         (F-001)
- reactivate_user         (F-001)
- reassign_user_company   (F-001)
- deactivate_company      (F-004)


These actions must trigger permission cache invalidation.

3.3 Query Parameters
Query Parameters:
- none


Permission data is always resolved in the context of the authenticated user.

3.4 Derived or Aggregated Fields
Derived Fields:
- can_<action>_<resource> (boolean)


Examples:

can_create_user

can_update_task

can_read_salary

can_approve_leave

Derived from PermissionSet.resource → allowed_actions.

3.5 UI Data Constraints

Permission evaluation must be server-authoritative

UI permission flags are advisory only

Permission data must be available:

At initial app load

Immediately after login

Immediately after any permission-affecting change

No UI may assume access based solely on role name

Data-level restrictions must be enforced even when screen access is allowed

4. Proposed API Hints (Not Final API Spec)
Proposed API Hints:
- GET /api/v1/auth/permissions
- GET /api/v1/auth/context


These endpoints are logical constructs only; the API Spec Builder will decide
whether permissions are embedded in auth responses or fetched separately.

5. Cross-Screen Data Dependencies
All feature screens depend on:
- PermissionSet
- AuthContext

F-001 (User & Role Management) changes must trigger:
- Permission cache invalidation
- PermissionSet recomputation

F-004 (Company Management) affects:
- Company-scoped permissions

6. Data Edge Cases

SuperAdmin permissions evaluated without company scope

Deactivated users receive an empty PermissionSet

Inactive companies invalidate all company-scoped permissions

Permission cache stale after role change (must be invalidated)

UI rendering before permissions are loaded (must default to deny)

Direct URL access to restricted screens

Partial data visibility (e.g., list allowed, fields restricted)