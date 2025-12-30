# Domain Flow Log — OfficeWorld

**Project Name:** OfficeWorld
**Prepared By:** Ravi
**Reviewed By:** Shahid


**Issue Date:** 2025-01-23

## Summary of Identified Issues

1. Incorrect order of domain files
2. Incomplete domain file content
3. Improper domain modeling (missing / unnecessary fields)
4. Missing base domain information
5. Missing explanation of real-world working & examples


## Issue 1 — Incorrect Order of Domain Files

### Observation

The current order of domain files does not reflect **implementation priority or dependency flow**.

### Details

* Core business domains (e.g., **Employee**, **Salary**) appear later in the sequence
* Secondary or supporting domains (e.g., **Notifications**) appear earlier
* Initial development phases are forced to reference undefined core concepts


## Issue 2 — Incomplete Domain File Content

### Observation

Several domain sections are **partially written or left unfinished**.

### Details

* Descriptions stop mid-way
* Business flows are incomplete
* Context is missing for actions and states


## Issue 3 — Improper Domain Modeling

### Observation

Some entities contain either **missing required fields** or **unnecessary fields**.

### Details

* Business-critical fields are absent in some entities
* Certain fields have no clear domain purpose
* Domain intent is unclear or inconsistent


## Issue 4 — Missing Base Domain Information

### Observation

Essential system-level information is missing from domain files.

### Problem

This information is repeatedly requested during reviews, causing unnecessary delays.

### Details
Every domain file **must begin** with the following section:

## Base Domain Information

1. **Project Name:** OfficeWorld

2. **Project Purpose:**
   Multi-tenant SaaS platform enabling invitation-based user onboarding with
   strict role-based access control, company boundaries, and lifecycle
   management for users across tenant organizations.

3. **Key Entities:**
   Feature F-002 introduces no new persisted entities.

4. **User Roles:**
   SuperAdmin, CEO, HR, Manager, Employee

5. **Multi-Tenancy:**
   Yes — Company is the tenant boundary.

6. **Soft Delete Policy:**
   Enabled for all applicable entities.

7. **Audit Requirements:**
   Required — audit logging must be added for relevant actions.

8. **Special Requirements:**
   None.

---

### Impact of Adding This Section

Including this section ensures:

* Zero repeated clarification
* Faster and smoother reviews
* Clear shared understanding across the team
* Better AI-assisted development accuracy

---

## Issue 5 — Missing Explanation of Real-World Working

### Observation

Domain files currently focus on **structure**, but not on **actual working behavior**.

### Problem

* Developers struggle to understand what exactly needs to be built
* Cursor and other AI tools lack behavioral context
* Implementation assumptions vary between developers

### Expected Correction

Each domain file **must explain how the feature works in practice**, including:

* Step-by-step flow of key actions
* Real-world usage examples
* State transitions
* Validation and failure scenarios


**Issue Date:** 2025-01-23
**Domain File:** F10_domain_model.md

## Issue 6 - Display a live working-time counter for the current day

### Problem

* No clear explanation of how live working time will be displayed (continuous API calls, webhook, etc.).

## Issue 7 - SuperAdmin access to attendance data. f10_File: feature_file.md

## Problem

* If SuperAdmin cannot access employees, how can they access attendance?


## Issue 8 - Only one check-in and one check-out per day and Check-out is mandatory

## Problem

* What if the user forgets to check out? How are we going to handel this case.

## Issue 9 - Deactivated employees may view history but cannot check in/out

## Problem

* Deactivated employees cannot log in, so how can they view history?

## Issue 10 - F10_ui_data_contract.md define: SuperAdmin must never receive attendance data and F10_feature_file.md defines:SuperAdmin access to attendance data

## Problem

* UI contract says SuperAdmin must never access attendance data, but feature file says they can.

## Issue 11 -F10_ui_data_contract.md: Read-only for all roles 

## Problem

* Conflicting statements: read-only for all roles vs attendance visible to roles.

**Issue Date:** 2025-12-29
**Domain File:** F10_domain_model.md

## Issue 6 - audit log should be introduce in initial phase.

### Problem

* If we introduce the audit log after completing all phases, it will require refactoring the entire codebase again to add audit log functionality. This would mean re-testing the complete project and re-checking for errors.

The better option is to implement the audit log functionality incrementally with each phase, so there is no need for full re-testing and extensive bug fixing later, and we avoid separately adding logging code to all phases at the end.