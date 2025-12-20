# Project Overview: SaaS Company Management Platform

**Project Name:** officeWorld

## 1. Project Goal & Context

### 1.1 Background
Mid-market companies (including agencies and software companies) require a unified platform to manage employees, projects, tasks, attendance, leave workflows, salaries, and internal governance. Existing tools are often fragmented across HR systems, project management tools, and manual processes, leading to operational inefficiencies and weak access control.

This platform is a controlled, multi-tenant SaaS where all companies and users are provisioned centrally by a SuperAdmin, ensuring strong governance, data isolation, and standardized onboarding.

### 1.2 Problem Statement
Organizations lack a single, secure system that combines employee lifecycle management with day-to-day execution (projects and tasks), while enforcing strict role-based access, approval workflows, auditability, and reliable invitation-based onboarding.

### 1.3 High-Level Goals
- Provide a centralized platform for managing companies, users, and roles.
- Ensure user invitation and onboarding flows work reliably from day one.
- Enforce strict RBAC with permission inheritance and task-level permissions.
- Enable operational transparency with notifications and auditability.

### 1.4 Global/Non-Functional Requirements
- Multi-tenant data isolation by company
- Role-based access control enforced on every request
- High performance via permission caching
- Reliable email delivery for invitations and workflows
- Secure, invitation-only onboarding

---

## 2. Feature Breakdown

### 2.1 Feature List Summary
| Feature ID | Name | Summary | Priority | Size | Depends On |
|------------|------|---------|----------|------|------------|
| F-000 | Core Platform Foundation | Modules, models, auth, predefined roles | High | Large | None |
| F-001 | User & Role Management | User invitation and role assignment | High | Large | F-000 |
| F-002 | RBAC & Permission Engine | Permission enforcement and inheritance | High | Large | F-000 |
| F-003 | Notifications System | Email & in-app notifications (invite-first) | High | Medium | F-000 |
| F-004 | Platform Company Management | SuperAdmin manages companies | High | Medium | F-001 |
| F-005 | Employee Management | Employee lifecycle and profiles | High | Large | F-001 |
| F-006 | Salary & History Management | Salary records and change tracking | High | Medium | F-005 |
| F-007 | Project Management | Company-level projects | Medium | Medium | F-002 |
| F-008 | Task Management & Assignment | Tasks with Viewer/Editor permissions | High | Large | F-002 |
| F-009 | Leave Management Workflow | Two-level leave approvals | High | Medium | F-005 |
| F-010 | Attendance Management | Check-in/check-out and logs | Medium | Medium | F-005 |
| F-011 | Audit Logging | Track platform and company actions | Medium | Small | F-002 |
| F-012 | KPI Dashboards | Platform and company KPIs | Low | Small | F-002 |

---

### 2.2 Feature Details

#### F-000 — Core Platform Foundation
- **Short Summary:**  
  Establishes the foundational system capabilities required before any business features can operate.
- **Business Value:**  
  Provides a secure, consistent base for authentication, data models, and system initialization.
- **Key Capabilities:**
  - Module scaffolding
  - Core models (users, companies, roles, permissions)
  - Authentication (login, logout, password reset)
  - Token-based invitation activation
  - Predefined roles and permissions seeding
- **Actors:**
  - System
  - SuperAdmin
- **Dependencies:**
  - None
- **Notes / Risks / Open Questions:**
  - Must fully support multi-company users

---

#### F-001 — User & Role Management
- **Short Summary:**  
  Manages user invitations, role assignments, and company membership.
- **Business Value:**  
  Enables controlled onboarding and enforces one-role-per-company rules.
- **Key Capabilities:**
  - User invitations (platform & company level)
  - Role assignment per company
  - User activation/deactivation
- **Actors:**
  - SuperAdmin
  - CEO
  - HR
- **Dependencies:**
  - F-000
- **Notes / Risks / Open Questions:**
  - No role switching within the same company

---

#### F-002 — RBAC & Permission Engine
- **Short Summary:**  
  Centralized permission validation system.
- **Business Value:**  
  Prevents unauthorized access and enforces security boundaries.
- **Key Capabilities:**
  - Permission checks on every API request
  - Permission inheritance (CEO → Manager → Employee, HR → Employee)
  - Redis-based permission caching
- **Actors:**
  - All roles (system-level)
- **Dependencies:**
  - F-000
- **Notes / Risks / Open Questions:**
  - Cache invalidation correctness is critical

---

#### F-003 — Notifications System
- **Short Summary:**  
  Email-first notification system with minimal in-app alerts, designed to support user invitation and onboarding flows.
- **Business Value:**  
  Ensures invitations, approvals, and task assignments reliably reach users.
- **Key Capabilities:**
  - Invitation emails with activation links
  - Leave approval/rejection emails
  - Task assignment and permission-change emails
  - Minimal in-app notifications (leave + task)
- **Actors:**
  - All roles
- **Dependencies:**
  - F-000
- **Notes / Risks / Open Questions:**
  - Email delivery is a critical-path dependency
  - Notification preferences are out of scope for V1

---

#### F-004 — Platform Company Management
- **Short Summary:**  
  Enables SuperAdmin to manage tenant companies.
- **Business Value:**  
  Centralized governance and controlled company onboarding.
- **Key Capabilities:**
  - Company CRUD
  - Activation/deactivation
  - View company metadata
- **Actors:**
  - SuperAdmin
- **Dependencies:**
  - F-001
- **Notes / Risks / Open Questions:**
  - No self-serve company creation

---

#### F-005 — Employee Management
- **Short Summary:**  
  Manages employee records tied to companies.
- **Business Value:**  
  System of record for workforce data.
- **Key Capabilities:**
  - Employee CRUD
  - Activation/deactivation
  - Soft deletion
- **Actors:**
  - CEO
  - HR
- **Dependencies:**
  - F-001
- **Notes / Risks / Open Questions:**
  - SuperAdmin excluded from employee data

---

#### F-006 — Salary & History Management
- **Short Summary:**  
  Tracks employee compensation and salary changes.
- **Business Value:**  
  Transparent and auditable salary management.
- **Key Capabilities:**
  - Salary CRUD
  - Salary history tracking
- **Actors:**
  - CEO
  - HR
- **Dependencies:**
  - F-005
- **Notes / Risks / Open Questions:**
  - Strict role-based visibility

---

#### F-007 — Project Management
- **Short Summary:**  
  Company-level project tracking.
- **Business Value:**  
  Organizes work into structured initiatives.
- **Key Capabilities:**
  - Project CRUD
  - Status tracking
- **Actors:**
  - CEO
  - Manager
- **Dependencies:**
  - F-002
- **Notes / Risks / Open Questions:**
  - Projects are optional containers

---

#### F-008 — Task Management & Assignment
- **Short Summary:**  
  Task execution with granular Viewer/Editor permissions.
- **Business Value:**  
  Supports day-to-day work with controlled collaboration.
- **Key Capabilities:**
  - Standalone and project-linked tasks
  - Task assignment
  - Viewer/Editor permissions
- **Actors:**
  - CEO
  - Manager
  - Employee
- **Dependencies:**
  - F-002
- **Notes / Risks / Open Questions:**
  - Permission conflict resolution

---

#### F-009 — Leave Management Workflow
- **Short Summary:**  
  Two-level leave approval workflow.
- **Business Value:**  
  Structured and auditable leave handling.
- **Key Capabilities:**
  - Leave application
  - Manager approval
  - HR/CEO final approval
- **Actors:**
  - Employee
  - Manager
  - HR
  - CEO
- **Dependencies:**
  - F-005
- **Notes / Risks / Open Questions:**
  - Approver unavailability handling

---

#### F-010 — Attendance Management
- **Short Summary:**  
  Tracks daily attendance with logs and provides real-time visibility of active working time.
- **Business Value:**  
  Attendance visibility, compliance, and transparency for employees and managers.
- **Key Capabilities:**
  - Check-in/check-out
  - Attendance logs
  - Live working-time counter visible on user dashboard (HH:MM:SS since check-in)
  - Available to: CEO, HR, Manager, Employee
  - Not available to: SuperAdmin
- **Actors:**
  - CEO
  - HR
  - Manager
  - Employee
- **Dependencies:**
  - F-005
- **Notes / Risks / Open Questions:**
  - Metadata privacy considerations

---

#### F-011 — Audit Logging
- **Short Summary:**  
  Captures audit logs for critical actions.
- **Business Value:**  
  Compliance and traceability.
- **Key Capabilities:**
  - Action logging
  - Old/new value tracking
- **Actors:**
  - System
- **Dependencies:**
  - F-002
- **Notes / Risks / Open Questions:**
  - Log retention policy

---

#### F-012 — KPI Dashboards
- **Short Summary:**  
  High-level operational metrics.
- **Business Value:**  
  Visibility for platform and company admins.
- **Key Capabilities:**
  - Platform KPIs
  - Company KPIs
- **Actors:**
  - SuperAdmin
  - CEO
  - Manager
- **Dependencies:**
  - F-002
- **Notes / Risks / Open Questions:**
  - Exporting not in scope for V1

---

## 3. Shared Domain Concepts

### 3.1 Shared Entities
| Entity | Description | Used In |
|--------|--------------|----------|
| User | Authenticated platform user | F-000, F-001 |
| Company | Tenant organization | F-004 |
| Role | Permission container | F-000, F-002 |
| Employee | Company-bound profile | F-005 |
| Project | Work container | F-007 |
| Task | Unit of work | F-008 |
| Leave | Time-off request | F-009 |
| Attendance | Presence record | F-010 |
| Notification | User alert | F-003 |
| AuditLog | Action record | F-011 |

### 3.2 Cross-Cutting Concerns
- Authentication & authorization
- Multi-tenancy isolation
- Notifications
- Auditing
- Data privacy

---

## 4. Recommended Implementation Sequence

### 4.1 Sequential Order
1. `F-000` – Core platform foundation  
2. `F-001` – User & role management (users must exist before invites are consumed)  
3. `F-002` – RBAC & permission engine 
4. `F-003` – Notifications system (invite flow is critical)  
5. `F-004` – Company onboarding  
6. `F-005` – Employee management  
7. `F-008` – Task execution core  
8. `F-007` – Project management  
9. `F-009` – Leave workflows  
10. `F-010` – Attendance  
11. `F-011` – Auditing  
12. `F-012` – KPIs  

### 4.2 Parallelizable Features
- F-006 (Salary Management)
- F-011 (Audit Logging)

---

## 5. Cross-Feature Integration Notes
- Notifications are critical for invitation and approval flows
- RBAC wraps all APIs
- Audit logs generated for platform and tenant actions

---

## 6. Open Questions
- Future reporting/export needs
- Notification preference customization
- SLA expectations for email delivery

## 7. Assumptions
- No self-service onboarding
- No role switching within the same company
- Roles and permissions are predefined and fixed in V1
