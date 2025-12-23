ui_data_contract.md
1. Feature Summary

The Task Management & Assignment feature provides an execution-focused system for creating, owning, assigning, and completing tasks within a company. It enforces immutable ownership, granular assignee permissions (viewer/editor), optional project linkage, and strict visibility boundaries, while integrating notifications for task-related events.

2. Screens Covered
- SCR_TASK_LIST
- SCR_TASK_CREATE
- SCR_TASK_DETAIL

3. Data Requirements Per Screen
3.1 Screen ID
SCR_TASK_LIST
Route: /company/tasks

3.2 Reads (Server Data Required)
Reads:
- Task:
    fields:
      - id
      - name
      - status
      - project_id (nullable)
      - owner_id
- TaskAssignment:
    fields:
      - employee_id
      - permission
- Project (summary, optional):
    fields:
      - id
      - name


Returned tasks must be filtered by visibility rules:

CEO / Manager: all company tasks

HR: all company tasks (read-only)

Employee: tasks they own or are assigned to

3.3 Writes (Actions / Mutations)
Writes:
- none

3.4 Query Parameters
Query Parameters:
- status
- project_id
- search
- page
- page_size
- sort_by
- sort_order

3.5 Derived or Aggregated Fields
Derived Fields:
- is_owner (boolean)
- user_permission (OWNER | EDITOR | VIEWER)
- can_edit_task (boolean)
- can_change_status (boolean)


Derived from ownership and TaskAssignment.permission.

3.6 UI Data Constraints

Server-side pagination, filtering, and sorting required

Tasks in terminal states (DONE, CANCELLED) are read-only

Tasks linked to INACTIVE or COMPLETED projects must respect project-level restrictions

Employees must never receive tasks outside ownership or assignment

3.1 Screen ID
SCR_TASK_CREATE
Route: /company/tasks/create

3.2 Reads (Server Data Required)
Reads:
- Project (optional selector):
    fields:
      - id
      - name
      - status


Only ACTIVE projects are selectable.

3.3 Writes (Actions / Mutations)
Writes:
- create_task

3.4 Query Parameters
Query Parameters:
- none

3.5 Derived or Aggregated Fields
Derived Fields:
- none

3.6 UI Data Constraints

Task owner is implicitly set to authenticated user and is immutable

Project association is optional

Initial task status must be provided

HR can create tasks only if permitted by RBAC (read-only default)

3.1 Screen ID
SCR_TASK_DETAIL
Route: /company/tasks/:taskId

3.2 Reads (Server Data Required)
Reads:
- Task:
    fields:
      - id
      - name
      - description
      - status
      - project_id (nullable)
      - owner_id
- TaskAssignment:
    fields:
      - employee_id
      - permission
- Project (optional):
    fields:
      - id
      - name
      - status

3.3 Writes (Actions / Mutations)
Writes:
- update_task            // owner and editors
- change_task_status     // owner only
- update_task_assignments
- delete_task            // owner only

3.4 Query Parameters
Query Parameters:
- taskId (path parameter)

3.5 Derived or Aggregated Fields
Derived Fields:
- is_owner (boolean)
- user_permission (OWNER | EDITOR | VIEWER)
- can_edit_task (boolean)
- can_change_status (boolean)
- can_manage_assignments (boolean)
- is_task_read_only (boolean)


Derived from ownership, assignment permission, task status, and project status.

3.6 UI Data Constraints

Only the owner can change task status or delete the task

Editors may edit name and description only

Viewers have read-only access

Assignments and permission changes are owner-only

Deleted tasks are permanently removed and must not be returned

4. Proposed API Hints (Not Final API Spec)
Proposed API Hints:
- GET    /api/v1/company/tasks
- POST   /api/v1/company/tasks
- GET    /api/v1/company/tasks/{id}
- PATCH  /api/v1/company/tasks/{id}
- PATCH  /api/v1/company/tasks/{id}/status
- PATCH  /api/v1/company/tasks/{id}/assignments
- DELETE /api/v1/company/tasks/{id}

5. Cross-Screen Data Dependencies
SCR_TASK_LIST and SCR_TASK_DETAIL both require:
- TaskSummary
  - id
  - name
  - status
  - project_id

SCR_TASK_DETAIL integrates with:
- Project status (F-007) for task mutability
- Notifications (F-003) on creation, assignment, and status changes

6. Data Edge Cases

Viewer attempting to edit a task

Editor attempting to change task status or assignments

Task owner attempting to reassign ownership (not allowed)

Task without a project

Task linked to INACTIVE or COMPLETED project

Duplicate assignment of same employee

HR attempting to modify tasks (must be blocked)

Hard-deleted task accessed via direct URL