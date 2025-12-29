ui_data_contract.md
1. Feature Summary

The Attendance Management feature provides a server-time–driven, immutable system to track daily employee presence via check-in and check-out events. It ensures accurate worked-time calculation across refreshes and sessions through client-side live counters (calculated using check-in time from API and current time), enforces strict role-based visibility (excluding SuperAdmin), automatically handles missed check-outs at midnight, and avoids approvals, edits, or payroll coupling.

2. Screens Covered
- SCR_ATTENDANCE_TODAY
- SCR_ATTENDANCE_LOGS
- SCR_ATTENDANCE_DETAIL

3. Data Requirements Per Screen
3.1 Screen ID
SCR_ATTENDANCE_TODAY
Route: /attendance/today

3.2 Reads (Server Data Required)
Reads:
- Attendance:
    fields:
      - attendance_date
      - check_in_time
      - check_out_time
      - status
      - worked_time
      - is_auto_check_out
- Context:
    fields:
      - server_time
      - employee_timezone


Returned only for the authenticated employee and only for today's local date.
Deactivated employees cannot access this screen.

3.3 Writes (Actions / Mutations)
Writes:
- check_in_attendance
- check_out_attendance

3.4 Query Parameters
Query Parameters:
- none

3.5 Derived or Aggregated Fields
Derived Fields:
- live_worked_time        // Calculated by UI: current_time - check_in_time (while checked in)
- can_check_in  (boolean)
- can_check_out (boolean)


Derived from status and existence of check-in/check-out timestamps.
Live worked time is calculated by UI comparing check-in time (from API) with current client time, updating in real-time (typically every second).

3.6 UI Data Constraints

Exactly one check-in and one check-out per day

Check-out is mandatory to finalize attendance (auto check-out at local midnight if missed)

Attendance becomes immutable after CHECKED_OUT

Live counter must resume correctly after refresh or re-login (UI fetches check-in time from API and recalculates)

Live counter is calculated by UI using check-in time from API and current client time, updating in real-time

Deactivated employees cannot access this screen (no attendance history viewing, no check-in/out)

3.1 Screen ID
SCR_ATTENDANCE_LOGS
Route: /company/attendance

3.2 Reads (Server Data Required)
Reads:
- Attendance:
    fields:
      - attendance_date
      - status
      - worked_time
      - is_auto_check_out
- Employee:
    fields:
      - id
      - user.first_name
      - user.last_name


Visibility rules:

Manager: all employees' attendance

HR / CEO: full company attendance

Employee: no access to this screen

SuperAdmin: no access to this screen (explicitly excluded)

3.3 Writes (Actions / Mutations)
Writes:
- none

3.4 Query Parameters
Query Parameters:
- employee_id        // HR / CEO only
- start_date
- end_date
- status
- page
- page_size
- sort_by
- sort_order

## 3.5 Derived or Aggregated Fields
Derived Fields:
- attendance_status_label
- is_auto_check_out_indicator (boolean/string)  // Visual indicator for auto check-out records

3.6 UI Data Constraints

Server-side pagination and filtering required

Data must be strictly company-scoped

Attendance records remain visible even after employee deactivation (but deactivated employees cannot access)

SuperAdmin must never receive attendance data (explicitly excluded from all attendance endpoints)

Auto check-out records must be visually distinguishable from manual check-outs

3.1 Screen ID
SCR_ATTENDANCE_DETAIL
Route: /company/attendance/:employeeId/:date

3.2 Reads (Server Data Required)
Reads:
- Attendance:
    fields:
      - attendance_date
      - check_in_time
      - check_out_time
      - status
      - worked_time
      - is_auto_check_out
- AttendanceLog:
    fields:
      - action_type (CHECK_IN, CHECK_OUT, AUTO_CHECK_OUT)
      - action_time
      - location
      - ip_address
      - device_info
      - notes
      - is_auto_action
- Employee:
    fields:
      - user.first_name
      - user.last_name


Visibility rules:

Manager: attendance of employees in their scope

HR / CEO: full company attendance

Employee: no access to this screen

SuperAdmin: no access to this screen (explicitly excluded)

3.3 Writes (Actions / Mutations)
Writes:
- none

3.4 Query Parameters
Query Parameters:
- employeeId (path parameter)
- date       (path parameter)

3.5 Derived or Aggregated Fields
Derived Fields:
- is_auto_check_out_indicator (boolean/string)  // Visual indicator if check-out was automatic
- action_type_label  // Human-readable action type label

3.6 UI Data Constraints

Read-only for all roles

Immutable event log must be returned in chronological order

Only one Attendance record may exist per employee per day

Date resolution must respect employee local timezone

AUTO_CHECK_OUT action type must be included in AttendanceLog when check-out was automatic

Auto check-out information must be clearly displayed in UI

SuperAdmin cannot access this screen (explicitly excluded)

4. Proposed API Hints (Not Final API Spec)
Proposed API Hints:
- GET  /api/v1/attendance/today                    // Get today's attendance data for authenticated employee
- POST /api/v1/attendance/check-in                 // Record employee check-in for current day
- POST /api/v1/attendance/check-out                // Record employee check-out for current day
- GET  /api/v1/company/attendance                 // Get paginated attendance records list with filters
- GET  /api/v1/company/attendance/{employeeId}/{date}  // Get detailed attendance for specific employee and date

API Response for /api/v1/attendance/today:
- Returns check-in time (if checked in) which UI uses to calculate live counter
- UI calculates live counter by comparing check-in time with current client time
- Counter updates in real-time as UI recalculates (typically every second)

5. Cross-Screen Data Dependencies
SCR_ATTENDANCE_TODAY and SCR_ATTENDANCE_DETAIL both depend on:
- Attendance (including is_auto_check_out field)
- AttendanceLog (detail only, including AUTO_CHECK_OUT action type)

F-005 (Employee Management) provides:
- Employee identity and timezone
- Employee activation status (for access control)

F-002 (RBAC) enforces:
- Role-based visibility and access
- SuperAdmin exclusion from all attendance endpoints
- Deactivated employee restrictions

6. Data Edge Cases

Second check-in attempt on the same day

Check-out attempt without prior check-in

Page refresh or logout during active check-in (UI fetches check-in time from API and recalculates counter)

Day boundary crossing at employee local midnight (triggers auto check-out if missed)

Deactivated employee attempting to access attendance screens (access completely blocked)

Missing check-out (system automatically performs check-out at local midnight)

Direct URL access to unauthorized attendance detail (SuperAdmin blocked, deactivated employees blocked)

Concurrent check-in/check-out requests

API failures (UI handles gracefully by showing last known state or error message)

Multiple browser tabs with same attendance session (each tab independently fetches check-in time from API and calculates counter)

Auto check-out at midnight while employee is still viewing screen (counter stops, final time displayed)

Timezone changes affecting auto check-out timing (uses employee's configured timezone)

Server time synchronization issues (all calculations use server UTC time)