# Project: officeWorld
# Feature: F-004 — Platform Company Management

## Purpose
Provide a centralized, secure, and auditable company management capability where
SuperAdmin governs the full company lifecycle, while CEO and HR are allowed to
maintain limited company profile information without impacting tenant governance,
access control, or data isolation.

---

# Domain Model: F-004 — Platform Company Management

## 1. Domain Glossary
| Term | Definition | Examples |
|------|------------|----------|
| Company | Tenant organization and data isolation boundary | Acme Corp |
| Company Lifecycle | State transitions of a company | Active → Deactivated |
| Company Profile | Non-governance company information | Address, logo |
| Governance Fields | Fields controlling access and lifecycle | is_active, is_del |
| Hard Deletion | Irreversible removal of a company and all its data | Tenant purge |
| SuperAdmin | Global system user managing all companies | Platform admin |

---

## 2. Entities and Relationships

### 2.1 Entity List
| Entity | Description |
|--------|-------------|
| Company | Tenant organization owned and governed by the platform |

---

### 2.2 Entity Details

#### Company
- **Description**:  
  Represents a tenant organization within the platform.  
  Company is a first-class aggregate that defines tenant boundaries, access
  control scope, and ownership of all company-scoped data.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | Name | Company name | Immutable |
  | Slug | Unique company identifier | Immutable, globally unique |
  | Description | Company description | Editable by CEO/HR |
  | Address | Physical address | Editable by CEO/HR |
  | City | City | Editable by CEO/HR |
  | State | State | Editable by CEO/HR |
  | Country | Country | Editable by CEO/HR |
  | PostalCode | Postal/ZIP code | Editable by CEO/HR |
  | Website | Company website | Editable by CEO/HR |
  | LogoUrl | Company logo | Editable by CEO/HR |
  | IsActive | Company active state | SuperAdmin-only |
  | IsDeleted | Soft deletion marker | SuperAdmin-only |

- **Relationships**:
  - Owns Users (via UserRoleAssignment)
  - Owns Employees
  - Owns all company-scoped records (leaves, tasks, salaries, notifications, etc.)

---

### 2.3 Relationship Overview (Text Diagram)
```text
Company 1..* User
Company 1..* Employee
Company 1..* DomainRecords (Leaves, Tasks, Salaries, Notifications, etc.)
