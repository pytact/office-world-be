ui_data_contract.md
1. Feature Summary

The Project Management feature provides lightweight, company-scoped project containers used to organize tasks into initiatives. Projects do not define membership or permissions; visibility and access are derived entirely from task assignment and enforced through project lifecycle status.

2. Screens Covered
- SCR_PROJECT_LIST
- SCR_PROJECT_CREATE
- SCR_PROJECT_DETAIL

3. Data Requirements Per Screen
3.1 Screen ID
SCR_PROJECT_LIST
Route: /company/projects

3.2 Reads (Server Data Required)
Reads:
- Project:
    fields:
      - id
      - name
      - status
- Aggregates:
    - task_count (derived)
- Visibility Rules:
    - task_derived_visibility


Returned projects must be filtered as follows:

CEO / Manager: all company projects

HR: all company projects (read-only)

Employee: only projects containing tasks assigned to the user

3.3 Writes (Actions / Mutations)
Writes:
- none

3.4 Query Parameters
Query Parameters:
- status
- search
- page
- page_size
- sort_by
- sort_order

3.5 Derived or Aggregated Fields
Derived Fields:
- project_status_label

3.6 UI Data Constraints

Server-side pagination, filtering, and sorting required

Visibility must be derived from task association, not explicit project membership

Employees must never receive projects without assigned tasks

INACTIVE and COMPLETED projects remain visible but restrict task interactions

3.1 Screen ID
SCR_PROJECT_CREATE
Route: /company/projects/create

3.2 Reads (Server Data Required)
Reads:
- none

3.3 Writes (Actions / Mutations)
Writes:
- create_project

3.4 Query Parameters
Query Parameters:
- none

3.5 Derived or Aggregated Fields
Derived Fields:
- none

3.6 UI Data Constraints

Only CEO and Manager can create projects

Project name must be unique within company

Initial project status must be provided

3.1 Screen ID
SCR_PROJECT_DETAIL
Route: /company/projects/:projectId

3.2 Reads (Server Data Required)
Reads:
- Project:
    fields:
      - id
      - name
      - status
- Aggregates:
    - task_count
- Task (summary only):
    fields:
      - id
      - title
      - status
      - assignee_id


Task data is read-only in this feature and exists only to support project context.
Task behavior and permissions are governed by F-008.

3.3 Writes (Actions / Mutations)
Writes:
- update_project
- change_project_status
- delete_project

3.4 Query Parameters
Query Parameters:
- projectId (path parameter)

3.5 Derived or Aggregated Fields
Derived Fields:
- is_project_frozen (boolean)


Derived from status ∈ {INACTIVE, COMPLETED}.

3.6 UI Data Constraints

Only CEO and Manager may update or delete projects

HR and Employees have read-only access

Frozen projects must block all task modifications

Deleting a project cascades deletion of associated tasks

4. Proposed API Hints (Not Final API Spec)
Proposed API Hints:
- GET    /api/v1/company/projects
- POST   /api/v1/company/projects
- GET    /api/v1/company/projects/{id}
- PATCH  /api/v1/company/projects/{id}
- PATCH  /api/v1/company/projects/{id}/status
- DELETE /api/v1/company/projects/{id}

5. Cross-Screen Data Dependencies
SCR_PROJECT_LIST and SCR_PROJECT_DETAIL both require:
- ProjectSummary
  - id
  - name
  - status
  - task_count

SCR_PROJECT_DETAIL integrates with:
- Task summaries (F-008)

6. Data Edge Cases

Projects with zero tasks (visible only to CEO / Manager / HR)

Employee assigned tasks removed from a project (project disappears from list)

Attempt to modify tasks under INACTIVE or COMPLETED project

Deleting a project with existing tasks (cascade behavior)

Manager attempting to access project from another company

Employee attempting to access project without task assignment