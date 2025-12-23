# Project: officeWorld
# Feature: F-008 — Task Management

## Purpose
Provide a focused, execution-oriented task system where work is created, owned,
assigned, and completed with strict ownership rules, fine-grained assignment
permissions, and clear visibility boundaries. Tasks are independent units of work
that may optionally belong to projects, without inheriting project visibility.

---

# Domain Model: F-008 — Task Management

## 1. Domain Glossary
| Term | Definition | Examples |
|------|------------|----------|
| Task | Atomic unit of work | Fix login bug |
| Task Owner | User who creates and owns the task | Manager |
| Assignee | User assigned to a task | Developer |
| Assignment Permission | Level of access for assignee | Viewer / Editor |
| Task Status | Lifecycle state of a task | IN_PROGRESS |
| Hard Deletion | Permanent removal of task | Delete task |

---

## 2. Entities and Relationships

### 2.1 Entity List
| Entity | Description |
|--------|-------------|
| Task   | Atomic unit of work within a company |
| TaskAssignment | Association between task and employee |

---

### 2.2 Entity Details

#### Task
- **Description**:  
  Represents a single unit of work. Tasks are company-scoped, have one immutable
  owner, may have multiple assignees, and optionally belong to a project. All
  permissions and visibility are task-based.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |-----_-|-------------|-------|
  | Company | Owning company | Required |
  | Owner | Task creator | Immutable |
  | Name | Task title | Editable |
  | Description | Task details | Editable |
  | Status | Task lifecycle state | ENUM-controlled |
  | Project | Optional project | Nullable |
  | IsDeleted | Hard delete marker | Permanent |

- **Status ENUM**:
```text
TODO
IN_PROGRESS
HALT
REVIEW
DONE
CANCELLED
Status Semantics:

Owner can move task to any status at any time

DONE and CANCELLED are terminal states

TaskAssignment
Description:
Represents assignment of an employee to a task with a specific permission level.

Key Fields (business-level):

Field	Description	Notes
Task	Assigned task	Required
Employee	Assigned employee	Required
Permission	Assignment permission	ENUM-controlled

Permission ENUM:

text
Copy code
VIEWER
EDITOR
Permission Semantics:

VIEWER: Can view task only

EDITOR: Can edit task name and description

Editors ❌ cannot:

Add/remove assignees

Change task status

Remove themselves

2.3 Relationship Overview (Text Diagram)
text
Copy code
Company 1..* Task
Task 1..1 Owner (Employee)
Task 1..* TaskAssignment
Employee *..* Task (via TaskAssignment)
Task 0..1 Project