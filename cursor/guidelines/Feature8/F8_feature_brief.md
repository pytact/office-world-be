Feature Brief: F-008 — Task Management & Assignment
1. Context & Problem

Background: officeWorld requires a robust task execution layer to support daily operational work across companies. Tasks are the primary unit of work and may optionally be grouped into projects.

Current Pain / Problem: Without a clear task ownership model and granular permissions, task collaboration can become confusing, insecure, and hard to govern.

Why Now: Task execution is core to employee productivity and underpins project management, notifications, and operational visibility.

2. Goal / Outcome

Primary Goal: Enable structured task creation, assignment, and execution with clear ownership and permission boundaries.

Secondary Goals:

Support multi-assignee collaboration with controlled permissions

Ensure task visibility aligns with organizational roles

Success Criteria (Business View):

Tasks can be created, assigned, updated, and completed reliably

Task ownership and permission rules are consistently enforced

Relevant users receive timely notifications for task events

3. In Scope

Task creation, editing, and deletion

Task ownership (creator as immutable owner)

Multi-user task assignment

Viewer and Editor permission model

Task status lifecycle management

Optional linkage of tasks to projects

Task visibility based on role and assignment

Email and in-app notifications for task events

4. Out of Scope

Project-level permissions

Task priority or due date management

Task comments by viewers

Bulk task operations

Soft deletion of tasks

5. Primary Actors
Actor	Description
CEO	Full control over all tasks
Manager	Full control over all tasks
HR	View-only access to tasks
Employee	Can create, view, and manage own tasks
6. User Stories

As a user, I want to create tasks so that work can be tracked and executed.

As a task owner, I want full control over my task so that I can manage its lifecycle.

As an assignee, I want appropriate access to tasks based on my permission level.

As a manager or CEO, I want visibility into tasks so that I can oversee work progress.

7. Constraints & Assumptions
Constraints

Each task has exactly one owner, set at creation

Task owner cannot be changed after creation

Task owner or Editor can change task status

Hard deletion of tasks is allowed

Viewer and Editor permissions are strictly enforced

Assumptions

Task owner defaults to the task creator

Employees can edit and delete tasks they own

HR has read-only access to all tasks

Notifications are sent for task creation, assignment changes, and permission changes

8. Dependencies

F-002 — RBAC & Permission Engine

F-003 — Notifications System

F-007 — Project Management

9. Open Questions

None identified at this stage

10. Acceptance Criteria

 CEO and Manager can create, edit, and delete tasks

 Employees can create, edit, and delete tasks they own

 HR can view tasks but cannot modify them

 Each task has an immutable owner set at creation

 Tasks support multiple assignees

 Viewer permissions allow view-only access

 Editor permissions allow editing, commenting, and status changes but not reassignment

 Task statuses include TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED

 Task owner or Editor can change task status

 Tasks can exist with or without a project

 Notifications are sent for task creation, assignment changes, and permission changes