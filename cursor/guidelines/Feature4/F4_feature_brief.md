Feature Brief: F-004 — Platform Company Management
1. Context & Problem

Background: officeWorld is a controlled, multi-tenant SaaS where all tenant companies are provisioned and governed centrally. Company lifecycle management must be consistent, secure, and auditable to protect data isolation and platform integrity.

Current Pain / Problem: Without centralized company management, tenant onboarding, governance, and access control become fragmented, increasing operational risk and administrative overhead.

Why Now: Company provisioning and lifecycle control are prerequisites for user onboarding, RBAC enforcement, and all downstream company-scoped features.

2. Goal / Outcome

Primary Goal: Enable SuperAdmin-only management of tenant companies with clear lifecycle controls.

Secondary Goals:

Allow limited company profile updates by CEO/HR without affecting governance

Provide visibility into company status and scale for platform oversight

Success Criteria (Business View):

Companies can be created, activated, deactivated, and deleted reliably

Company deactivation immediately blocks user access while preserving data

SuperAdmin has full visibility across all companies

3. In Scope

Company creation with required metadata

Company update by SuperAdmin

Limited company profile updates by CEO/HR (non-governance fields)

Company activation and deactivation

Hard deletion of companies

CEO invitation and assignment by SuperAdmin

Company listing, search, and filtering for SuperAdmin

Visibility of company status and user counts

4. Out of Scope

Self-service company signup

Company lifecycle actions by non-SuperAdmin roles

Editing immutable identifiers (name, slug)

Automated notifications on company lifecycle changes

5. Primary Actors
Actor	Description
SuperAdmin	Global system user who manages all tenant companies
CEO	Company-level admin with limited company profile edit access
HR	Company-level admin with limited company profile edit access
6. User Stories

As a SuperAdmin, I want to create companies so that tenants can be onboarded.

As a SuperAdmin, I want to activate or deactivate companies so that access can be controlled.

As a SuperAdmin, I want to delete companies so that unused tenants can be removed.

As a CEO or HR, I want to update basic company profile details so that information stays current.

7. Constraints & Assumptions
Constraints

Only SuperAdmin can create, activate, deactivate, or delete companies

Required fields at creation are name and slug

name and slug are immutable after creation

Deactivated companies block login for all associated users

Only one CEO is allowed per company

Assumptions

Company slug is globally unique

Hard deletion is irreversible

Deactivated companies remain visible to SuperAdmin

Company data remains intact during deactivation

CEO/HR editable fields are limited to description, address, city, state, country, postal code, website, and logo URL

8. Dependencies

F-001 — User & Role Management

9. Open Questions

None identified at this stage

10. Acceptance Criteria

 SuperAdmin can create companies with required fields (name, slug)

 SuperAdmin can view a list of all companies with status and user counts

 SuperAdmin can search and filter companies by name and status

 SuperAdmin can activate and deactivate companies

 Deactivated companies prevent all associated users from logging in

 SuperAdmin can hard delete companies

 CEO and HR can update only allowed company profile fields

 Company name and slug cannot be edited after creation