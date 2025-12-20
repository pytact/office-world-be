# Project: officeWorld
# Feature: F-003 — Notifications System

## Purpose
Provide a centralized, asynchronous, and reliable notification system that
delivers email-first and limited in-app notifications for onboarding and
workflow events (leaves and tasks), without blocking core business processes,
while ensuring predictable delivery, auditability, and strict company scoping.

---

# Domain Model: F-003 — Notifications System

## 1. Domain Glossary
| Term | Definition | Examples |
|------|------------|----------|
| Notification | A persisted record representing a message delivered to a user | Leave approved notification |
| Notification Event | A business event that triggers notifications | Leave request submitted |
| Notification Channel | Medium used to notify users | Email, In-App |
| In-App Notification | Notification visible inside the application | Task update |
| Email Notification | Notification delivered via email | Invitation email |
| Recipient | User who receives a notification | Manager, HR |
| Notification Status | Delivery outcome of a notification | Sent, Failed |
| Rejection Reason | Mandatory explanation provided when an action is rejected | Leave rejected due to overlap |

---

## 2. Entities and Relationships

### 2.1 Entity List
| Entity | Description |
|--------|-------------|
| Notification | User-facing notification record |
| NotificationEvent | Conceptual trigger for notifications |
| NotificationRecipient | Logical mapping between notification and user |

> **Note:**  
> This feature introduces **Notification** as a first-class persisted entity.  
> NotificationEvent and NotificationRecipient are **conceptual constructs** used
> to explain behavior; they are not persisted as separate tables.

---

### 2.2 Entity Details

#### Notification
- **Description**:  
  Represents a notification delivered to a single user through one or more
  channels (email and/or in-app).

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | User | Recipient user | Required |
  | Company | Tenant scope | Required |
  | Type | Notification category | invite, leave, task |
  | Title | Short message title | Human-readable |
  | Message | Notification body | Rendered from template |
  | Channel | Email / In-App | Email-first |
  | IsRead | Read state | In-app only |
  | ReadAt | Read timestamp | In-app only |
  | Status | Delivery state | Sent / Failed |
  | RelatedRecordId | Related domain record | leave_id, task_id |
  | RelatedTable | Source table | leaves, tasks |
  | Data | Structured payload | Includes rejection reason |

- **Relationships**:
  - Belongs to exactly one User
  - Scoped to exactly one Company

---

### 2.3 Relationship Overview (Text Diagram)
```text
Notification *..1 User
Notification *..1 Company
Notification *..1 DomainRecord (Leave / Task)
