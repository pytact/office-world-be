# SaaS Company Management Platform - Requirements Document

## 1. Roles and Permissions

### 1.1 SuperAdmin (Platform Level)

**Access Scope:**
- Operates across all companies
- Cannot access company data ( projects, tasks, attendance, leaves, salaries)
- Can view company information (from companies table: name, desc, slug, address, city, state, country, postalcode, website, logo_url, etc.)

**Permissions:**
- ✅ Manage companies (CRUD operations on companies table)
- ✅ Manage users (change company, change roles)
- ✅ View KPIs (total companies count, total employees count - active/inactive)
- ✅ View company information (all fields in companies table)
- ✅ Invite users: SuperAdmin, CEO, HR, Manager, Employee
- ❌ Cannot access company data ( projects, tasks, attendance, leaves, salaries)

---

### 1.2 CEO (Company Admin - Tenant Level)

**Access Scope:**
- Operates only within own company
- Has overall control of company operations

**Permissions:**
- ✅ View KPIs (own company only):
  - Total employees (active/inactive)
  - Total projects (active/inactive/completed)
  - Total tasks (active/inactive/completed/canceled)

**Employee Management:**
- ✅ List employees of own company
- ✅ CRUD employee (all details):
  - User Account Details
  - Employment Details
  - Personal Details
  - Emergency Contacts
  - ID Documents
  - Salary Information
- ✅ View/edit salary information of all employees
- ✅ View salary history of employees
- ✅ Delete employees (soft delete using `is_del`)
- ✅ Deactivate employees (using `is_active`)

**Project & Task Management:**
- ✅ Create/edit/delete projects and tasks
- ✅ View all projects and tasks in company

**Attendance:**
- ✅ View attendance list of all employees

**Leave Management:**
- ✅ Approve/Reject leave requests

**Holiday Management:**
- ✅ Company-wide holiday CRUD

**Invitations:**
- ✅ Invite users only within own company
- ✅ Roles allowed: CEO, HR, Manager, Employee

**Permission Inheritance:**
- ✅ Automatically has Manager permissions
- ✅ Automatically has Employee permissions

---

### 1.3 HR (Company Level)

**Access Scope:**
- Operates only within own company

**Permissions:**
- ✅ Invite HR, Manager, Employee

**Employee Management:**
- ✅ CRUD employee details:
  - User Account
  - Employment
  - Personal
  - Emergency
  - Documents
  - Salary
- ✅ View/edit salary information of all employees
- ✅ View salary history

**Attendance & Leave:**
- ✅ View attendance of all employees
- ✅ Approve/Reject leave requests
- ❌ Cannot mark attendance for employees (only view)

**Holiday Management:**
- ✅ Manage holidays (CRUD)

**Projects & Tasks:**
- ❌ Cannot create/edit projects and tasks

**Permission Inheritance:**
- ✅ Automatically has Employee permissions

---

### 1.4 Manager (Company Level)

**Access Scope:**
- Operates only within own company
- Can see all company data

**KPIs:**
- ✅ Project count (active/inactive/completed)
- ✅ Task count (active/inactive/completed/canceled)

**Employee Access:**
- ✅ View employee details (only project/task info, no personal info)
- ✅ View attendance of employees
- ✅ View leave information of employees
- ❌ Cannot view salary information of employees

**Project Management:**
- ✅ Create projects
- ✅ Edit/delete projects they created (CRUD)
- ✅ View all projects in company

**Task Management:**
- ✅ Create tasks individually (without project) or inside projects
- ✅ Assign tasks to employees
- ✅ View all tasks in company
- ✅ Assign task roles: Viewer / Editor
- ✅ Change task permissions after assignment (assign and revoke)

**Permission Inheritance:**
- ✅ Automatically has Employee permissions

---

### 1.5 Employee (Company Level)

**Access Scope:**
- Operates only within own company
- Can see only own data (no company-wide statistics)

**Profile Management:**
- ✅ Edit own profile:
  - Personal details
  - Emergency contacts
  - Address
  - Other personal information
- ✅ Change password
- ❌ Cannot view other employees' profiles (own only)

**Tasks:**
- ✅ Create tasks individually (without project) or inside projects
- ✅ Access tasks created by self
- ✅ View only own assigned tasks
- ✅ View/Edit tasks only if permission is assigned (Viewer/Editor)
  - Can view own assigned tasks (read-only by default)
  - Can edit own assigned tasks only if Manager/Employee assigns Editor permission
- ✅ Assign tasks to other employees
  - When assigning, must specify permission: Viewer or Editor
  - Assigner chooses the permission level during assignment

**Leaves:**
- ✅ Apply for leave
- ✅ View leave status

**Attendance:**
- ✅ Mark/view own attendance

**Data Visibility:**
- ✅ View company holidays
- ✅ View own salary information

---

## 2. Task Permissions (Viewer/Editor)

### 2.1 Viewer Role
- ✅ Read-only access to tasks
- ✅ Can view task details, comments, status

### 2.2 Editor Role
- ✅ Can update task status
- ✅ Can add comments
- ✅ Can mark task as complete
- ✅ Can edit task details (if assigned as Editor)

### 2.3 Permission Management
- ✅ Manager can assign task permissions (Viewer/Editor)
- ✅ Manager can change task permissions after assignment (assign and revoke)
- ✅ Employees can assign tasks to other employees
  - When assigning a task, the assigner must specify permission: Viewer or Editor
  - Assigner can choose which permission level to grant
- ✅ Manager can see all tasks in company

---

## 3. Permission Inheritance

### 3.1 Hierarchy
- **CEO** automatically has:
  - Manager permissions
  - Employee permissions

- **Manager** automatically has:
  - Employee permissions

- **HR** automatically has:
  - Employee permissions

### 3.2 Multiple Roles
- ❌ Users cannot have multiple roles in the same company
- ❌ One role at a time (no combined permissions)
- If a user has multiple roles, only one role is active at a time

---

## 4. Data Access Scope

### 4.1 Company Isolation
- ✅ All roles see data only from their own company (except SuperAdmin)
- ✅ Strong data isolation per company
- ✅ Multi-tenant architecture with company_id filtering

### 4.2 Role-Specific Data Access
- **Employees:** See only own data (no company-wide statistics)
- **Manager:** Can see all company data (no salary info)
- **CEO/HR:** Can see all company data
- **SuperAdmin:** Cannot access company data (only company management)

---

## 5. Leave Approval Workflow

### 5.1 Approval Flow
1. **Employee** applies for leave
2. **Manager** approves/rejects (first level)
3. **HR or CEO** approves/rejects (second level - final approval)

### 5.2 Approvers
- ✅ Manager can approve/reject (first level)
- ✅ HR can approve/reject (final level)
- ✅ CEO can approve/reject (final level)

---

## 6. Permission Validation

### 6.1 Validation Strategy
- ✅ Permissions checked on every API request
- ✅ Cached using Redis for performance
- ✅ Stored in database (roles table with JSON permissions)

### 6.2 Implementation
- Permissions stored in `roles` table as JSON
- Format: `{"resource": ["action1", "action2", ...]}`
- Example: `{"employees": ["create", "read", "update", "delete"]}`
- Redis cache for fast permission lookups
- Cache invalidation on role/permission updates

---

## 7. Data Management Rules

### 7.1 Employee Management
- Employees must belong to a company (`company_id` is REQUIRED)
- SuperAdmin users do not have employee records
- Employee deletion uses soft delete (`is_del = true`)
- Employee deactivation uses `is_active = false`

### 7.2 User Management
- SuperAdmin can change users' company
- SuperAdmin can change roles of users across companies
- Users can have only one role per company
- Users can belong to multiple companies with different roles

---

## 8. Summary of Key Rules

### 8.1 Access Control
- ✅ Strict role-based access control (RBAC)
- ✅ Company-level data isolation
- ✅ Permission inheritance (CEO → Manager → Employee, HR → Employee)
- ✅ One role per user per company

### 8.2 Data Visibility
- **SuperAdmin:** Company management only (no data access)
- **CEO:** All company data
- **HR:** All company data (except projects/tasks)
- **Manager:** All company data (no salary info)
- **Employee:** Own data only

### 8.3 Permission Storage
- Stored in `roles` table as JSON
- Cached in Redis for performance
- Validated on every API request

---

## 9. Notifications System

### 9.1 Email Notifications

**User Invitations:**
- ✅ Send invitation email when user is invited
- ✅ Email contains: invitation link, role, company name, inviter name
- ✅ Email includes token for account activation
- ✅ Reminder email if invitation not accepted (optional)

**Leave Requests:**
- ✅ Send email to Manager when employee applies for leave
  - Email contains: employee name, leave type, dates, number of days, reason
- ✅ Send email to HR/CEO when Manager approves leave (for final approval)
  - Email contains: employee name, leave details, manager approval status
- ✅ Send email to employee when leave is approved/rejected
  - Email contains: leave status, approver name, approval/rejection reason (if rejected)

**Task Assignments:**
- ✅ Send email to employee when task is assigned
  - Email contains: task name, project name, assigner name, permission level (Viewer/Editor), due date (if any)
- ✅ Send email when task permission is changed (Viewer ↔ Editor)
- ✅ Send email when task status changes (if employee is assigned)

**Other Email Notifications:**
- ✅ Welcome email when user activates account
- ✅ Password reset email
- ✅ Salary change notification (to employee)
- ✅ Employee creation notification (to new employee)
- ✅ Project assignment notification (if applicable)

### 9.2 In-App Notifications (Minimal)

**Notification Types:**
- ✅ Leave approved/rejected
- ✅ Task assigned

**Basic Features:**
- ✅ Notification list in app
- ✅ Mark as read/unread
- ✅ Show notification count badge
- ✅ Click notification to navigate to related page

### 9.3 Notification Preferences (Minimal)

**Default Settings:**
- ✅ All notifications enabled by default
- ✅ Email notifications for all important actions
- ✅ In-app notifications for leave approval/rejection and task assignment

### 9.4 Notification Storage

**Database:**
- ✅ Store notifications in `notifications` table (needs to be added to schema)
- ✅ Track notification status (read/unread)
- ✅ Store notification type, message, related record ID
- ✅ Link notifications to users
- ✅ Store notification timestamp

**Notification Table Fields:**
- `id` - Primary key
- `user_id` - Foreign key to users (recipient)
- `company_id` - Foreign key to companies (nullable for platform-level notifications)
- `type` - Notification type (invitation, leave_request, leave_approval, task_assignment, etc.)
- `title` - Notification title
- `message` - Notification message/content
- `related_record_id` - ID of related record (task_id, leave_id, etc.)
- `related_table` - Name of related table (tasks, leaves, etc.)
- `link` - Action URL/link
- `is_read` - Boolean (read/unread status)
- `read_at` - Timestamp when read
- `created_at` - Timestamp when created
- `data` - JSON field for additional data (optional)

---

## 10. Next Steps

This requirements document covers:
- ✅ All role permissions
- ✅ Task permissions (Viewer/Editor)
- ✅ Permission inheritance
- ✅ Data access scope
- ✅ Leave approval workflow
- ✅ Permission validation strategy
- ✅ Notifications system (email + in-app)

**Ready for:**
- Database schema finalization (including notifications table)
- API endpoint design
- Permission middleware implementation
- Frontend role-based UI components
- Email service integration
- Basic in-app notification list

