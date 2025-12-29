"""Domain-specific constants for Attendance Management module.

Based on F10_domain_model.md and F10_api_spec.md.
Static values only - no functions, no computed values, no logic.
"""

# ============================================================================
# Status Values
# ============================================================================

STATUS_NOT_STARTED = "NOT_STARTED"
STATUS_CHECKED_IN = "CHECKED_IN"
STATUS_CHECKED_OUT = "CHECKED_OUT"

# ============================================================================
# Action Type Values
# ============================================================================

ACTION_TYPE_CHECK_IN = "CHECK_IN"
ACTION_TYPE_CHECK_OUT = "CHECK_OUT"
ACTION_TYPE_AUTO_CHECK_OUT = "AUTO_CHECK_OUT"

# ============================================================================
# Error Messages
# ============================================================================

ERROR_ATTENDANCE_NOT_FOUND = "Attendance record not found"
ERROR_ATTENDANCE_NOT_FOUND_TODAY = "No attendance record found for today. Please check in to start tracking."
ERROR_EMPLOYEE_NOT_FOUND = "Employee not found or not in your scope"
ERROR_ALREADY_CHECKED_OUT = "You have already checked out for today. Check-in is only allowed once per day."
ERROR_SUPERADMIN_NO_ACCESS = "SuperAdmin cannot access attendance data. Attendance endpoints are restricted to company-scoped users."
ERROR_DEACTIVATED_EMPLOYEE_NO_ACCESS = "Deactivated employees cannot access attendance features. Please contact your administrator."
ERROR_EMPLOYEE_NO_ACCESS = "Employees cannot access company attendance endpoints. This endpoint is restricted to Managers, HR, and CEO."
ERROR_MANAGER_SCOPE_VIOLATION = "Manager cannot access attendance for this employee. Access is restricted to employees in your scope."
ERROR_CHECK_OUT_WITHOUT_CHECK_IN = "No attendance record found for today. Please check in first."
ERROR_FUTURE_DATE_CHECK_IN = "Check-in is not allowed on future dates"
ERROR_FUTURE_DATE_CHECK_OUT = "Check-out is not allowed on future dates"

# ============================================================================
# Success Messages
# ============================================================================

SUCCESS_ATTENDANCE_TODAY_RETRIEVED = "Today's attendance retrieved successfully"
SUCCESS_ATTENDANCE_HISTORY_RETRIEVED = "Attendance history retrieved successfully"
SUCCESS_CHECK_IN_RECORDED = "Check-in recorded successfully"
SUCCESS_CHECK_OUT_RECORDED = "Check-out recorded successfully"
SUCCESS_COMPANY_ATTENDANCE_RETRIEVED = "Attendance records retrieved successfully"
SUCCESS_ATTENDANCE_DETAIL_RETRIEVED = "Attendance detail retrieved successfully"

# ============================================================================
# Error Codes
# ============================================================================

ERROR_CODE_ATTENDANCE_NOT_FOUND = "ATTENDANCE_NOT_FOUND"
ERROR_CODE_EMPLOYEE_NOT_FOUND = "EMPLOYEE_NOT_FOUND"
ERROR_CODE_ALREADY_CHECKED_OUT = "ALREADY_CHECKED_OUT"
ERROR_CODE_INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
ERROR_CODE_BUSINESS_RULE_FAILED = "BUSINESS_RULE_FAILED"
ERROR_CODE_VALIDATION_FAILED = "VALIDATION_FAILED"
