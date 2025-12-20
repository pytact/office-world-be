# Database Tables with Sample Data

---

## Table: users

**Fields:** id, email, first_name, last_name, password, is_active, is_del, token, invite_by, invite_at, activate_at, expiry, created_at, updated_at, created_by, updated_by

**Sample Records:**
```
| id | email              | first_name | last_name | password | is_active | is_del | created_at           |
|----|--------------------|------------|-----------|----------|-----------|--------|----------------------|
| 1  | admin@example.com  | Admin      | User      | ***      | true      | false  | 2024-01-01 10:00:00 |
| 2  | john@company.com   | John       | Doe       | ***      | true      | false  | 2024-01-02 11:00:00 |
| 3  | jane@company.com   | Jane       | Smith     | ***      | true      | false  | 2024-01-03 12:00:00 |
```

---

## Table: companies

**Fields:** id, name, desc, slug, address, city, state, country, postalcode, website, logo_url, is_active, is_del, created_at, updated_at, created_by, updated_by

**Sample Records:**
```
| id | name         | desc              | slug        | city      | country | is_active | is_del |
|----|--------------|-------------------|-------------|-----------|---------|-----------|--------|
| 1  | Tech Corp    | Technology Company| tech-corp   | New York  | USA     | true      | false  |
| 2  | Design Studio| Design Agency     | design-studio| London   | UK      | true      | false  |
| 3  | Sales Inc    | Sales Company     | sales-inc   | Mumbai    | India   | true      | false  |
```

---

## Table: roles

**Fields:** id, name, code, permissions (JSON), description, is_active, is_del, created_at, updated_at, created_by, updated_by

**Sample Records:**
```
| id | name       | code       | permissions (JSON)                                                                                                                                    | is_active | is_del |
|----|------------|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|--------|
| 1  | SuperAdmin | SuperAdmin | {"companies":["create","read","update","delete"],"users":["create","read","update","delete"],"users_roles":["create","read","update","delete"],"roles":["read"],"kpis":["read"]} | true      | false  |
| 2  | CEO        | CEO        | {"employees":["create","read","update","delete"],"salary":["create","read","update","delete"],"salary_history":["read"],"projects":["create","read","update","delete"],"tasks":["create","read","update","delete"],"task_assignments":["create","read","update","delete"],"attendance":["read"],"leaves":["read","approve"],"holidays":["create","read","update","delete"],"users_roles":["create","read","update"],"kpis":["read"]} | true | false |
| 3  | HR         | HR         | {"employees":["create","read","update"],"salary":["create","read","update","delete"],"salary_history":["read"],"attendance":["read"],"leaves":["read","approve"],"holidays":["create","read","update","delete"],"users_roles":["create","read","update"]} | true | false |
| 4  | Manager    | Manager    | {"employees":["read"],"projects":["create","read","update","delete"],"tasks":["create","read","update","delete"],"task_assignments":["create","read","update","delete"],"attendance":["read"],"leaves":["read","approve"],"kpis":["read"]} | true | false |
| 5  | Employee   | Employee   | {"employees":["read","update"],"tasks":["read","update"],"task_assignments":["create","read"],"leaves":["create","read"],"attendance":["create","read"],"holidays":["read"],"salary":["read"]} | true | false |
```

**Full JSON Permissions by Role:**

**1. SuperAdmin (id: 1)**
```json
{
  "companies": ["create", "read", "update", "delete"],
  "users": ["create", "read", "update", "delete"],
  "users_roles": ["create", "read", "update", "delete"],
  "roles": ["read"],
  "kpis": ["read"]
}
```

**2. CEO (id: 2)**
```json
{
  "employees": ["create", "read", "update", "delete"],
  "salary": ["create", "read", "update", "delete"],
  "salary_history": ["read"],
  "projects": ["create", "read", "update", "delete"],
  "tasks": ["create", "read", "update", "delete"],
  "task_assignments": ["create", "read", "update", "delete"],
  "attendance": ["read"],
  "leaves": ["read", "approve"],
  "holidays": ["create", "read", "update", "delete"],
  "users_roles": ["create", "read", "update"],
  "kpis": ["read"]
}
```

**3. HR (id: 3)**
```json
{
  "employees": ["create", "read", "update"],
  "salary": ["create", "read", "update", "delete"],
  "salary_history": ["read"],
  "attendance": ["read"],
  "leaves": ["read", "approve"],
  "holidays": ["create", "read", "update", "delete"],
  "users_roles": ["create", "read", "update"]
}
```

**4. Manager (id: 4)**
```json
{
  "employees": ["read"],
  "projects": ["create", "read", "update", "delete"],
  "tasks": ["create", "read", "update", "delete"],
  "task_assignments": ["create", "read", "update", "delete"],
  "attendance": ["read"],
  "leaves": ["read", "approve"],
  "kpis": ["read"]
}
```

**5. Employee (id: 5)**
```json
{
  "employees": ["read", "update"],
  "tasks": ["read", "update"],
  "task_assignments": ["create", "read"],
  "leaves": ["create", "read"],
  "attendance": ["create", "read"],
  "holidays": ["read"],
  "salary": ["read"]
}
```

---

## Table: users_roles

**Fields:** id, user_id, role_id, company_id, is_active, is_del, assigned_by, assigned_at, created_at, updated_at, created_by, updated_by

**Sample Records:**
```
| id | user_id | role_id | company_id | is_active | is_del | created_at           |
|----|---------|---------|------------|-----------|--------|----------------------|
| 1  | 1       | 1       | NULL       | true      | false  | 2024-01-01 10:00:00 |
| 2  | 2       | 2       | 1          | true      | false  | 2024-01-02 11:00:00 |
| 3  | 3       | 3       | 1          | true      | false  | 2024-01-03 12:00:00 |
```

---

## Table: employees

**Fields:** id, user_id, company_id (NOT NULL), role_id, job_title, department, employment_type, employment_status, work_email, date_of_birth, gender, marital_status, blood_group, nationality, address, city, state, country, alternate_phone, document_type, document_number, documentfile, is_active, is_del, created_at, updated_at, created_by, updated_by

**Note:** Employees must belong to a company (company_id is required). SuperAdmin users do not have employee records.

**Sample Records:**
```
| id | user_id | company_id | role_id | job_title    | department | employment_type | work_email        | is_active | is_del |
|----|---------|-------------|---------|--------------|------------|------------------|-------------------|-----------|--------|
| 1  | 2       | 1           | 2       | CEO          | NULL       | full-time        | ceo@techcorp.com  | true      | false  |
| 2  | 3       | 1           | 3       | HR Manager   | NULL       | full-time        | hr@techcorp.com   | true      | false  |
| 3  | 4       | 1           | 5       | Developer    | backend    | full-time        | dev@techcorp.com  | true      | false  |
| 4  | 5       | 2           | 5       | Designer     | frontend   | full-time        | designer@design.com| true     | false  |
```

---

## Table: salary

**Fields:** id, employee_id, company_id, salary, currency, payment_frequency, salary_date, is_del, created_at, updated_at, created_by, updated_by

**Sample Records:**
```
| id | employee_id | company_id | salary   | currency | payment_frequency | salary_date | is_del |
|----|-------------|-------------|----------|----------|--------------------|----------------|--------|
| 1  | 1           | 1           | 150000.00 | USD      | monthly            | 2024-01-01     | false  |
| 2  | 2           | 1           | 80000.00  | USD      | monthly            | 2024-01-01     | false  |
| 3  | 3           | 1           | 60000.00  | USD      | monthly            | 2024-01-01     | false  |
```

---

## Table: salary_history

**Fields:** id, employee_id, company_id, previous_salary, new_salary, salary_date, changed_by, created_at

**Sample Records:**
```
| id | employee_id | company_id | previous_salary | new_salary | salary_date | changed_by | created_at           |
|----|-------------|-------------|-----------------|------------|-----------------|------------|----------------------|
| 1  | 3           | 1           | 55000.00        | 60000.00   | 2024-06-01      | 1          | 2024-05-15 10:00:00 |
| 2  | 2           | 1           | 75000.00        | 80000.00   | 2024-07-01      | 1          | 2024-06-20 11:00:00 |
```

---

## Table: holidays

**Fields:** id, company_id, name, holiday_date, holiday_type, is_active, is_del, created_at, updated_at, created_by, updated_by

**Sample Records:**
```
| id | company_id | name            | holiday_date | holiday_type     | is_active | is_del |
|----|------------|-----------------|--------------|------------------|-----------|--------|
| 1  | 1          | New Year        | 2024-01-01   | national         | true      | false  |
| 2  | 1          | Independence Day| 2024-07-04   | national         | true      | false  |
| 3  | 1          | Company Holiday | 2024-12-25   | company_specific | true      | false  |
```

---

## Table: leaves

**Fields:** id, employee_id, company_id, leave_type, start_date, end_date, number_of_days, reason, status, manager_approved_by, manager_approved_at, manager_status, final_approved_by, final_approved_at, rejection_reason, is_del, created_at, updated_at, created_by, updated_by

**Note:** Leave approval workflow is 2-level: Employee → Manager (first level) → HR/CEO (final level). Status: pending, manager_approved, manager_rejected, approved, rejected.

**Sample Records:**
```
| id | employee_id | company_id | leave_type | start_date | end_date   | number_of_days | status          | manager_approved_by | manager_status | final_approved_by | is_del |
|----|-------------|-------------|------------|------------|------------|-----------------|-----------------|---------------------|----------------|-------------------|--------|
| 1  | 3           | 1           | annual     | 2024-08-01 | 2024-08-05 | 5.0             | approved        | 4                   | approved        | 2                 | false  |
| 2  | 3           | 1           | sick       | 2024-09-10 | 2024-09-10 | 1.0             | manager_approved| 4                   | approved        | NULL              | false  |
| 3  | 2           | 1           | casual     | 2024-10-15 | 2024-10-15 | 1.0             | rejected        | 4                   | rejected        | NULL              | false  |
```

---

## Table: projects

**Fields:** id, company_id, name, status, is_active, is_del, created_at, updated_at, created_by, updated_by

**Sample Records:**
```
| id | company_id | name              | status  | is_active | is_del |
|----|------------|-------------------|---------|-----------|--------|
| 1  | 1          | E-commerce Platform| active | true      | false  |
| 2  | 1          | Mobile App        | active | true      | false  |
| 3  | 1          | Testing Project   | completed| true    | false  |
```

---

## Table: tasks

**Fields:** id, project_id (nullable), name, status, is_active, is_del, created_at, updated_at, created_by, updated_by

**Note:** Tasks can be created individually (project_id = NULL) or inside projects (project_id = project.id).

**Sample Records:**
```
| id | project_id | name                    | status  | is_active | is_del |
|----|------------|-------------------------|---------|-----------|--------|
| 1  | 1          | Setup Database          | completed| true     | false  |
| 2  | 1          | Implement API           | active  | true      | false  |
| 3  | 2          | Design UI Mockups       | active  | true      | false  |
| 4  | NULL       | Review Documentation    | active  | true      | false  |
| 5  | NULL       | Update Company Website  | pending | true      | false  |
```

---

## Table: task_assignments

**Fields:** id, task_id, employee_id, permission_type (Viewer/Editor), is_active, is_del, created_at, updated_at, created_by

**Note:** When assigning a task, the assigner must specify permission_type: Viewer (read-only) or Editor (can update/edit).

**Sample Records:**
```
| id | task_id | employee_id | permission_type | is_active | is_del |
|----|---------|-------------|-----------------|-----------|--------|
| 1  | 1       | 3           | Editor          | true      | false  |
| 2  | 2       | 3           | Editor          | true      | false  |
| 3  | 2       | 5           | Viewer          | true      | false  |
| 4  | 3       | 6           | Editor          | true      | false  |
```

---

## Table: attendance

**Fields:** id, employee_id, company_id, attendance_date, check_in_time, check_out_time, status, is_del, created_at, updated_at, created_by, updated_by

**Sample Records:**
```
| id | employee_id | company_id | attendance_date | check_in_time        | check_out_time       | status  | is_del |
|----|-------------|------------|------------------|----------------------|----------------------|---------|--------|
| 1  | 3           | 1          | 2024-10-01      | 2024-10-01 09:00:00  | 2024-10-01 18:00:00  | present | false  |
| 2  | 3           | 1          | 2024-10-02      | 2024-10-02 09:15:00  | 2024-10-02 17:45:00  | present | false  |
| 3  | 3           | 1          | 2024-10-03      | NULL                 | NULL                 | absent  | false  |
| 4  | 2           | 1          | 2024-10-01      | 2024-10-01 08:30:00  | 2024-10-01 17:30:00  | present | false  |
```

---

## Table: attendance_logs

**Fields:** id, attendance_id, employee_id, action_type, action_time, location, ip_address, device_info, notes, created_at

**Sample Records:**
```
| id | attendance_id | employee_id | action_type | action_time          | location      | ip_address  | created_at           |
|----|---------------|-------------|-------------|----------------------|---------------|--------------|----------------------|
| 1  | 1             | 3           | check_in    | 2024-10-01 09:00:00  | Office Building| 192.168.1.10 | 2024-10-01 09:00:00 |
| 2  | 1             | 3           | check_out   | 2024-10-01 18:00:00  | Office Building| 192.168.1.10 | 2024-10-01 18:00:00 |
| 3  | 2             | 3           | check_in    | 2024-10-02 09:15:00  | Office Building| 192.168.1.15 | 2024-10-02 09:15:00 |
```

---

## Table: audit_logs

**Fields:** id, user_id, company_id, table_name, record_id, action_type, old_values, new_values, ip_address, user_agent, description, created_at

**Sample Records:**
```
| id | user_id | company_id | table_name | record_id | action_type | ip_address  | created_at           |
|----|---------|------------|-------------|-----------|-------------|-------------|----------------------|
| 1  | 1       | NULL       | users       | 2         | create      | 192.168.1.1  | 2024-01-02 11:00:00 |
| 2  | 2       | 1          | employees  | 1         | update      | 192.168.1.5  | 2024-01-15 14:30:00 |
| 3  | 1       | NULL       | companies   | 1         | create      | 192.168.1.1  | 2024-01-01 10:00:00 |
| 4  | 3       | 1          | leaves      | 1         | create      | 192.168.1.20 | 2024-08-01 09:00:00 |
```

---

## Table: notifications

**Fields:** id, user_id, company_id, type, title, message, related_record_id, related_table, link, is_read, read_at, data, created_at

**Note:** Stores in-app notifications. Types: leave_approval, task_assignment. Email notifications are sent separately.

**Sample Records:**
```
| id | user_id | company_id | type          | title              | message                    | related_record_id | related_table | is_read | created_at           |
|----|---------|------------|---------------|--------------------|----------------------------|-------------------|--------------|---------|----------------------|
| 1  | 3       | 1          | leave_approval| Leave Approved     | Your leave has been approved| 1                 | leaves       | false   | 2024-08-01 10:00:00 |
| 2  | 3       | 1          | task_assignment| New Task Assigned | Task "Implement API" assigned| 2                | tasks        | false   | 2024-08-02 11:00:00 |
| 3  | 4       | 1          | leave_approval| Leave Rejected    | Your leave has been rejected| 3                 | leaves       | true    | 2024-08-03 12:00:00 |
```

---

## Relationship Summary

**Core Tables:**
- `users` → `users_roles` (user_id)
- `users` → `employees` (user_id)
- `users` → `audit_logs` (user_id)
- `roles` → `users_roles` (role_id)

**Role Related:**
- `roles` → `users_roles` (role_id) - stores permissions as JSON

**Company Related:**
- `companies` → `users_roles` (company_id)
- `companies` → `employees` (company_id) - **Employees must belong to a company (required)**
- `companies` → `holidays` (company_id)
- `companies` → `projects` (company_id)
- `companies` → `salary` (company_id)
- `companies` → `salary_history` (company_id)
- `companies` → `leaves` (company_id)
- `companies` → `attendance` (company_id)
- `companies` → `audit_logs` (company_id)

**Employee Related:**
- `employees` → `salary` (employee_id)
- `employees` → `salary_history` (employee_id)
- `employees` → `leaves` (employee_id)
- `employees` → `attendance` (employee_id)
- `employees` → `task_assignments` (employee_id)

**Project Related:**
- `projects` → `tasks` (project_id) - **project_id is optional, tasks can be created individually**
- `tasks` → `task_assignments` (task_id)

**Attendance Related:**
- `attendance` → `attendance_logs` (attendance_id)

**Notifications Related:**
- `users` → `notifications` (user_id)
- `companies` → `notifications` (company_id)

**Notes:**
- `users_roles.company_id` is NULL for SuperAdmin (platform-level role)
- `employees.company_id` is **REQUIRED** - All employees must belong to a company
- SuperAdmin users do not have employee records (only users_roles records)
- One project can have multiple tasks (project_id is optional - tasks can be created individually or inside projects)
- Tasks are directly assigned to multiple employees (via task_assignments)
- **Leave Approval:** 2-level workflow - Manager approves first, then HR/CEO approves (final)
- **Task Permissions:** When assigning tasks, permission_type (Viewer/Editor) must be specified
- **Notifications:** In-app notifications for leave approval/rejection and task assignment

