# Project: officeWorld
# Feature: F-010 — Attendance Management

## Purpose
Provide a reliable, server-time–driven attendance tracking system that records
employee presence per day using immutable check-in and check-out events, derives
worked time accurately, and enforces strict visibility and integrity rules—
without approvals, edits, or payroll impact.

---

# Domain Model: F-010 — Attendance Management

## 1. Domain Glossary
| Term | Definition | Examples |
|------|------------|----------|
| Attendance | Daily presence record for an employee | 2025-03-10 attendance |
| Check-In | First recorded work start for the day | 09:12 AM |
| Check-Out | Recorded work end for the day | 06:41 PM |
| Auto Check-Out | System-initiated check-out at local midnight if employee misses manual check-out | Automatic at 12:00 AM local time |
| Attendance Log | Immutable event log of actions | CHECK_IN event |
| Worked Time | Derived duration between check-in and check-out | 9h 29m |
| Server Time | Authoritative timestamp source | UTC time |
| Live Counter | Real-time working-time display calculated by UI using check-in time from API and current time | Updates every second |

---

## 2. Entities and Relationships

### 2.1 Entity List
| Entity | Description |
|--------|-------------|
| Attendance | One-per-day attendance record for an employee |
| AttendanceLog | Append-only event log for attendance actions |

---

### 2.2 Entity Details

#### Attendance
- **Description**:  
  Represents a single employee's attendance for one calendar day, driven entirely
  by server timestamps. Exactly one attendance record exists per employee per day.
  Check-out is mandatory and will be automatically performed at local midnight if
  the employee misses manual check-out.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | Employee | Attending employee | Required |
  | Company | Owning company | Required |
  | AttendanceDate | Local calendar date | Derived from timezone |
  | CheckInTime | Server timestamp of check-in | UTC |
  | CheckOutTime | Server timestamp of check-out | UTC (auto-set at midnight if missed) |
  | Status | Attendance lifecycle state | ENUM-controlled |
  | WorkedTime | Derived duration | Read-only |
  | IsAutoCheckOut | Flag indicating if check-out was automatic | Boolean |

- **Status ENUM**:
```text
NOT_STARTED
CHECKED_IN
CHECKED_OUT
Rules:

Exactly one Attendance per employee per day

Status transitions are linear and irreversible

Attendance is immutable after CHECKED_OUT

Auto check-out occurs at employee's local midnight if manual check-out is missed
```

#### AttendanceLog
- **Description**:  
  Immutable, append-only log that records every attendance action with contextual
  metadata for audit and traceability. Includes both manual and automatic actions.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | Attendance | Related attendance record | Required |
  | Employee | Acting employee | Required |
  | ActionType | Attendance action | ENUM-controlled |
  | ActionTime | Server timestamp | UTC |
  | Location | Optional location info | Free text |
  | IPAddress | Client IP | Optional |
  | DeviceInfo | Client device details | Optional |
  | Notes | System notes | Optional |
  | IsAutoAction | Flag indicating if action was automatic | Boolean |

- **ActionType ENUM**:
```text
CHECK_IN
CHECK_OUT
AUTO_CHECK_OUT
Rules:

All actions are immutable once logged

AUTO_CHECK_OUT is system-generated at local midnight
```

### 2.3 Relationship Overview (Text Diagram)
```text
Company 1..* Attendance
Employee 1..* Attendance
Attendance 1..* AttendanceLog
```

---

## 3. Business Rules and Constraints

### 3.1 Attendance Rules
- Only one check-in and one check-out per day per employee
- Check-out is mandatory (auto check-out at local midnight if missed)
- Attendance records are immutable after CHECKED_OUT status
- Attendance is calculated using employee's local timezone
- Day resets at employee's local midnight

### 3.2 Access Control Rules
- **Employees**: Can view only their own attendance
- **Managers**: Can view attendance for all employees in their scope
- **HR**: Full attendance visibility across the company
- **CEO**: Full attendance visibility across the company
- **SuperAdmin**: Cannot access or view attendance data (explicitly excluded)
- **Deactivated Employees**: Cannot view attendance history or perform check-in/check-out actions

### 3.3 Live Counter Rules
- Single API endpoint provides check-in time to the UI
- UI calculates live working-time counter by comparing check-in time (from API) with current client time
- Counter derives from server-stored check-in time retrieved via API
- Counter resumes correctly after page refresh or re-login (UI recalculates using API-provided check-in time)
- Counter stops permanently after check-out

### 3.4 Employee Status Rules
- Deactivated employees cannot access attendance features
- Historical attendance data remains stored even after employee deactivation
- Deactivated employees cannot view their own attendance history
