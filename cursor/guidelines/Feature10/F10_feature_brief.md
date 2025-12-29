# Feature Brief: F-010 — Attendance Management

## 1. Context & Problem

**Background:** officeWorld needs a reliable way to track employee presence and working hours on a daily basis. Attendance data must be accurate, tamper-resistant, and consistent across refreshes, logins, and devices.

**Current Pain / Problem:** Client-side timers and editable attendance records lead to incorrect data, manipulation risks, and lack of trust in attendance reports.

**Why Now:** Attendance is a foundational operational feature required before analytics, compliance reporting, and future payroll integrations.

## 2. Goal / Outcome

**Primary Goal:** Implement a server-time–based attendance system with mandatory check-in and check-out.

**Secondary Goals:**
- Display a live working-time counter for the current day (UI calculates countdown using check-in time from API and current time)
- Enforce immutable attendance records

**Success Criteria (Business View):**
- Attendance remains accurate across refresh, logout, and re-login
- Daily worked time is calculated correctly per employee timezone
- Attendance data cannot be edited or manipulated

## 3. In Scope

- Daily check-in and check-out
- Mandatory check-out
- Live working-time counter (UI calculates using check-in time from API and current client time)
- Single API endpoint that returns user's check-in time
- Total worked time calculation per day
- Employee-local timezone handling
- Role-based attendance visibility
- Immutable attendance records

## 4. Out of Scope

- Break tracking
- Manual attendance edits or corrections
- Attendance approval workflows
- Payroll or salary calculations
- SuperAdmin access to attendance data (SuperAdmin must never receive or access attendance data)

## 5. Primary Actors

| Actor | Description |
|-------|-------------|
| Employee | Checks in/out and views own attendance |
| Manager | Views attendance of all employees |
| HR | Full attendance visibility |
| CEO | Full attendance visibility |
| System | Calculates time using server timestamps |

## 6. User Stories

- As an employee, I want to check in and out so that my working time is recorded.
- As an employee, I want to see a live timer so that I know how long I've worked today.
- As a manager, I want to view employee attendance so that I can monitor presence.
- As HR or CEO, I want full access to attendance data so that oversight is maintained.

## 7. Constraints & Assumptions

### Constraints

- Only one check-in and one check-out per day
- Check-out is mandatory (auto check-out occurs at local midnight if employee misses manual check-out)
- Attendance records cannot be edited
- Attendance is calculated using the employee's local timezone
- Day resets at local midnight

### Assumptions

- Server stores timestamps in UTC and converts using employee timezone
- Single API endpoint provides check-in time; UI calculates live counter by comparing check-in time with current time
- Live counter is calculated client-side and resumes correctly after refresh or logout
- Attendance data remains stored even if an employee is deactivated
- Deactivated employees cannot view attendance history or check in/out

## 8. Dependencies

- F-005 — Employee Management
- F-002 — RBAC & Permission Engine

## 9. Open Questions

None identified at this stage

## 10. Acceptance Criteria

- Employees can check in once per day
- Employees must check out to complete attendance (auto check-out at local midnight if missed)
- Live working-time counter shows total worked time for the current day (calculated by UI using check-in time from API and current time)
- Counter resumes correctly after page refresh or re-login
- Attendance resets daily at employee local midnight
- Employees can view only their own attendance
- Managers can view attendance for all employees
- HR and CEO have full attendance visibility
- SuperAdmin cannot access or view attendance data
- Attendance records are immutable and cannot be edited
- Deactivated employees cannot view attendance history or perform check-in/check-out actions
