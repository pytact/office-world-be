# Domain Model: F-001 — User & Role Management

## 1. Domain Glossary
| Term | Definition | Examples |
|------|------------|----------|
| User | Platform identity managed through invitations, roles, and lifecycle rules | Employee user |
| Company | Tenant organization boundary | Tech Corp |
| Role | Predefined access role with fixed permissions | CEO, HR |
| UserRoleAssignment | Active association between a user, role, and company | Manager in Tech Corp |
| Invitation | Embedded onboarding state of a user | Pending invite |
| Re-invitation | Resending an invitation to an existing inactive user | Invite resend |
| SuperAdmin | Global user with platform-wide authority | Platform admin |
| User Visibility | Rules controlling which users are visible to whom | Manager view |

---

## 2. Entities and Relationships

### 2.1 Entity List
| Entity | Description |
|--------|-------------|
| User | Platform user subject to invitation, role, and lifecycle rules |
| Company | Tenant organization |
| Role | Fixed, seeded role definition |
| UserRoleAssignment | Links User, Role, and Company |

> **Note:** Invitation and re-invitation are **embedded domain concepts** within `User`, not standalone entities.

---

### 2.2 Entity Details

#### User
- **Description**:  
  Represents a platform identity whose onboarding, activation, role assignment, visibility, and lifecycle are governed by strict rules.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | Email | Unique identifier | Immutable |
  | FirstName / LastName | User name | Set at activation |
  | IsActive | Login eligibility | False blocks authentication |
  | IsDeleted | Soft delete | Retains historical data |
  | InviteAt | Initial invitation timestamp | Set on first invite |
  | ActivateAt | Activation timestamp | Null until activated |
  | Expiry | Invitation expiry | Reset on re-invite |
  | Token | Credential token | Used for invite & reset |
  | ReinviteCount | Number of re-invitations | Incremented on resend |
  | LastReinviteAt | Last re-invite timestamp | Nullable |

- **Embedded Domain Concepts**:
  - **Invitation**
    - Lifecycle: Created → Sent → Expired → Activated
    - Derived from `invite_at`, `expiry`, `activate_at`
  - **Re-invitation**
    - Reuses the same User record
    - Generates a new token and expiry
  - **Credential Token**
    - Stored in `token`
    - Purpose: Activation or Password Reset

- **Relationships**:
  - Has exactly one UserRoleAssignment
  - Belongs to exactly one Company (except SuperAdmin)
  - May have one Employee record (SuperAdmin excluded)

---

#### Company
- **Description**:  
  Tenant boundary that constrains user management and visibility.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | Name | Company name | Unique |
  | Slug | URL identifier | Unique |
  | IsActive | Company availability | Blocks access |

- **Relationships**:
  - Has many Users via UserRoleAssignment
  - Has at most **one CEO** at any given time

---

#### Role
- **Description**:  
  Fixed and predefined role defining authority, visibility, and access boundaries.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | Name | Role name | CEO, HR, Manager |
  | Code | System identifier | Immutable |
  | Permissions | JSON permission map | Fixed in V1 |

- **Relationships**:
  - Assigned to Users via UserRoleAssignment
  - Cardinality rules enforced (e.g., single CEO per company)

---

#### UserRoleAssignment
- **Description**:  
  Active association defining a user’s role within a company context.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | User | Assigned user | Required |
  | Role | Assigned role | Overwritten on change |
  | Company | Context company | NULL for SuperAdmin |
  | IsActive | Assignment status | One active per user |

- **Relationships**:
  - Links User ↔ Role ↔ Company

---

### 2.3 Relationship Overview (Text Diagram)
```text
Company 1..* UserRoleAssignment
User 1..1 UserRoleAssignment
Role 1..* UserRoleAssignment
User 0..1 Employee
