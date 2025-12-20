# Domain Model: F-000 — Core Platform Foundation

## 1. Domain Glossary
| Term | Definition | Examples |
|------|------------|----------|
| User | Platform identity that can authenticate into the system | SuperAdmin, Employee user |
| Company | Tenant organization and data isolation boundary | Tech Corp |
| Role | Predefined permission container | CEO, HR |
| Permission | Action rights stored as value objects within a Role | create employee |
| UserRoleAssignment | Association between User, Role, and Company | CEO of Tech Corp |
| Invitation | Embedded lifecycle state representing a pending user onboarding | Pending invite |
| Credential Token | Time-bound token used for activation or password reset | Invite link token |
| SuperAdmin | Global user not tied to any company | Platform admin |

---

## 2. Entities and Relationships

### 2.1 Entity List
| Entity | Description |
|--------|-------------|
| User | Authenticated platform identity |
| Company | Tenant organization |
| Role | Fixed, seeded role definition |
| UserRoleAssignment | Links User, Role, and Company |

> **Note:** Invitation, CredentialToken, and Permission are **domain concepts embedded within entities**, not standalone aggregates or tables.

---

### 2.2 Entity Details

#### User
- **Description**:  
  Represents a platform user who may authenticate, be activated via invitation, or be deactivated.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | Email | Unique login identifier | Required |
  | FirstName / LastName | User profile name | Set at activation |
  | Password | Authentication credential | Hashed |
  | IsActive | Authentication flag | False blocks login |
  | IsDeleted | Soft delete flag | Retains history |
  | InviteAt | Invitation timestamp | Null if not invited |
  | ActivateAt | Activation timestamp | Null until activated |
  | Expiry | Invitation expiry | 24 hours |
  | Token | Credential token | Used for invite & reset |

- **Embedded Concepts**:
  - **Invitation**
    - Derived from: `invite_at`, `expiry`, `activate_at`
    - Lifecycle: Created → Sent → Expired → Activated
  - **CredentialToken**
    - Stored in `token`
    - Purpose: Activation or Password Reset

- **Relationships**:
  - Has exactly one UserRoleAssignment
  - Belongs to zero or one Company (zero for SuperAdmin)
  - May have one Employee record (not for SuperAdmin)

---

#### Company
- **Description**:  
  Tenant boundary that owns users and business data.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | Name | Company name | Unique |
  | Slug | URL identifier | Unique |
  | IsActive | Company availability | Blocks access |

- **Relationships**:
  - Has many Users (via UserRoleAssignment)
  - Owns employees, projects, tasks, etc. (outside F-000)

---

#### Role
- **Description**:  
  Fixed and predefined role defining access permissions.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | Name | Role display name | CEO, HR |
  | Code | System identifier | Immutable |
  | Permissions | JSON permission map | Fixed in V1 |

- **Embedded Concepts**:
  - **Permission**
    - Stored as JSON value objects
    - Format: `{resource: [actions]}`

- **Relationships**:
  - Assigned to Users via UserRoleAssignment

---

#### UserRoleAssignment
- **Description**:  
  Association entity defining a user’s role within a company context.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | User | Assigned user | Required |
  | Role | Assigned role | Required |
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
