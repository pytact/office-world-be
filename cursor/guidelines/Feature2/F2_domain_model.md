# Project: officeWorld
# Feature: F-002 — RBAC & Permission Engine

## Purpose
Establish a centralized, deterministic Role-Based Access Control (RBAC) and
permission evaluation engine that enforces authorization consistently across
all platform features, tenants, and user roles, using predefined permissions,
strict company scoping, and high-performance caching.

---

# Domain Model: F-002 — RBAC & Permission Engine

## 1. Domain Glossary
| Term | Definition | Examples |
|------|------------|----------|
| RBAC | Role-Based Access Control system | Platform authorization |
| Role | Predefined permission container | CEO, HR |
| Permission | Allowed action on a resource | task:create |
| Resource | Domain object being protected | users, salary |
| Action | Operation performed on a resource | create, read |
| Permission Set | Final evaluated permissions for a user | Effective permissions |
| Permission Cache | Cached permission set for performance | Redis entry |
| Company Scope | Tenant boundary for permission checks | company_id match |

---

## 2. Entities and Relationships

### 2.1 Entity List
| Entity | Description |
|--------|-------------|
| Role | Fixed permission container |
| Permission | Value object representing resource-action access |
| PermissionSet | Computed effective permissions for a user |
| PermissionCache | Cached representation of PermissionSet |

> **Note:**  
> This feature introduces **no new persisted entities**.  
> Permissions are stored as JSON within the `roles` table and evaluated dynamically.

---

### 2.2 Entity Details

#### Role
- **Description**:  
  A predefined, immutable role with a fully expanded set of permissions.
  Role inheritance is resolved at **seed time**, not at runtime.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | Name | Role name | CEO, HR, Manager |
  | Code | System identifier | Immutable |
  | Permissions | Resource-action map | Stored as JSON |

- **Inheritance Resolution (Design-Time Rule)**:
  - CEO permissions include Manager + Employee permissions
  - HR permissions include Employee permissions
  - Manager permissions include Employee permissions
  - No runtime role traversal or hierarchy evaluation

---

#### Permission (Value Object)
- **Description**:  
  Represents an allowed action on a protected resource.

- **Structure**:
```text
Resource → [Actions]

Examples:
tasks → [create, read, update, delete]
salary → [read]

Relationship Overview (Text Diagram)
Role 1..* Permission
User 1..1 PermissionSet
PermissionSet 1..1 PermissionCache

