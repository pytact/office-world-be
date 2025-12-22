# Project: officeWorld
# Feature: F-007 — Project Management

## Purpose
Provide a lightweight, company-scoped project structure that groups tasks into
initiatives without introducing membership, permissions, or hierarchy. Projects
exist purely as organizational containers, with visibility derived from task
assignment and lifecycle fully controlled by project status.

---

# Domain Model: F-007 — Project Management

## 1. Domain Glossary
| Term | Definition | Examples |
|------|------------|----------|
| Project | Company-scoped container for grouping tasks | Website Revamp |
| Project Status | Manual lifecycle state of a project | ACTIVE |
| Derived Visibility | Visibility based on task association | Employee sees project |
| Cascade Deletion | Deleting a project removes its tasks | Project removal |
| Frozen Project | Project where task changes are blocked | COMPLETED project |

---

## 2. Entities and Relationships

### 2.1 Entity List
| Entity | Description |
|--------|-------------|
| Project | Organizational container for tasks within a company |

---

### 2.2 Entity Details

#### Project
- **Description**:  
  Represents a company-scoped container used to organize tasks. Projects do not
  manage membership, permissions, or ownership. Access and visibility are derived
  entirely from task associations.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | Company | Owning company | Required |
  | Name | Project name | Company-unique |
  | Status | Project lifecycle state | Manually managed |
  | IsDeleted | Deletion marker | Cascade delete |

- **Status ENUM**:
```text
ACTIVE
INACTIVE
COMPLETED
Status Semantics:

ACTIVE: Project is editable; tasks can be added, moved, or removed

INACTIVE: Project is frozen; no task changes allowed

COMPLETED: Project is frozen and read-only; retained for reference

Relationships:

Project belongs to exactly one Company

Project can have zero or more Tasks

Tasks may exist without a Project

2.3 Relationship Overview (Text Diagram)
text
Copy code
Company 1..* Project
Project 0..* Task
Task 0..1 Project