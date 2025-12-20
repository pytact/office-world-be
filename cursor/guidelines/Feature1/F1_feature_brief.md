Feature Brief: F-001 — User & Role Management
1. Context & Problem

Background: officeWorld is a controlled, multi-tenant SaaS where all users are onboarded via invitations and governed by strict role-based access. The platform requires centralized yet flexible user management aligned with company boundaries and global oversight.

Current Pain / Problem: Without a structured user and role management layer, onboarding, access control, and organizational governance become inconsistent and error-prone, especially across roles with different visibility and authority.

Why Now: All company operations depend on reliable user provisioning, role assignment, lifecycle control, and privacy enforcement immediately after the core foundation (F-000).

2. Goal / Outcome

Primary Goal: Enable secure, invitation-based user onboarding with strict role, company, and visibility rules.

Secondary Goals:

Allow controlled role changes post-activation

Enforce role-based data visibility and privacy

Success Criteria (Business View):

Users can only access the platform through valid invitations

Each user has exactly one role within one company

SuperAdmin has full platform-wide visibility and control

Managers are prevented from accessing salary and personal information

Role-based visibility rules are consistently enforced

3. In Scope

User invitation flows (company-scoped and platform-scoped)

Role assignment at invitation time

User activation and deactivation

Post-activation role and company changes

Enforcement of role cardinality rules (e.g., one CEO per company)

Role-based user visibility and data-access rules

SuperAdmin platform-wide user and company management

Company reassignment of users by SuperAdmin

4. Out of Scope

Self-service user registration

Role or permission customization

Multi-company membership for a single user

Hard deletion of users

Salary management logic (handled in F-006)

5. Primary Actors
Actor	Description
SuperAdmin	Global system user with full visibility and control across all companies and users
CEO	Company-level admin with authority over all users and data in own company
HR	Company-level admin managing users, roles, and sensitive employee data
Manager	Mid-level role with limited user visibility and no access to sensitive data
Employee	Standard user with no user-list visibility
6. User Stories

As a SuperAdmin, I want to invite users to any company and change their role or company so that I can manage the platform centrally.

As a CEO, I want to invite and manage users in my company so that I can control access.

As HR, I want to change user roles after activation so that organizational changes are reflected.

As a Manager, I want to see managers and employees for coordination, but not their salary or personal details.

As an Employee, I should not see user lists so that privacy is preserved.

7. Constraints & Assumptions
Constraints

A user belongs to exactly one company

A user has only one role at a time

Each company can have only one CEO

Invitations must be tied to a role (and company, except SuperAdmin)

Deactivated users cannot log in

SuperAdmin is not tied to any company

Managers cannot view salary information or personal information of any users

Assumptions

Deactivated users retain all historical data

Reactivated users do not need to reset passwords

Expired invitations can be resent manually

Role and permission definitions are fixed in V1

Manager user visibility is list-level only, excluding sensitive fields

8. Dependencies

F-000 — Core Platform Foundation

9. Open Questions

None identified at this stage

10. Acceptance Criteria

 SuperAdmin can view all companies and all users across the platform

 SuperAdmin can invite users and assign or change company and role

 CEO and HR can invite users to their own company only

 Invitations are always tied to a role (and company, except SuperAdmin)

 Users have only one role within one company

 Role changes are allowed by CEO, HR, or SuperAdmin

 Deactivated users cannot log in but retain historical data

 User visibility rules are enforced per role

 Managers cannot access salary data

 Managers cannot access personal information of users