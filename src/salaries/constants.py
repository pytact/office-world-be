"""Domain-specific constants for Salary Management module.

Based on F6_api_spec.md - Salary Management (F-006).
Contains error messages, success messages, error codes, and enum values.
"""

# Error Messages
ERROR_EMPLOYEE_NOT_FOUND = "Employee not found."
ERROR_SALARY_DETAILS_NOT_FOUND = "Salary details not found."
ERROR_BANK_INFO_NOT_FOUND = "Bank information not found."
ERROR_SALARY_PAYMENT_NOT_FOUND = "Salary payment not found."
ERROR_SALARY_SLIP_NOT_FOUND = "Salary slip not found."
ERROR_INVALID_REQUEST = "Invalid request format or parameters."
ERROR_VALIDATION_FAILED = "Request validation failed."
ERROR_OVERLAPPING_SALARY_PERIOD = "Salary period overlaps with existing SalaryDetails. Please adjust the effective dates."
ERROR_DUPLICATE_SALARY_PAYMENT = "Salary payment already exists for this employee, month, and year."
ERROR_BUSINESS_RULE_FAILED = "Business rule violation."
ERROR_NO_ACTIVE_SALARY = "No active salary configuration found for the payment month. Please configure salary details first."
ERROR_INSUFFICIENT_PERMISSIONS = "Access denied. Only CEO and HR can view salary information."
ERROR_PRECONDITION_REQUIRED = "If-Match header required but missing (when updating existing resource)."
ERROR_PRECONDITION_FAILED = "Resource has been modified since retrieval. Please fetch the latest version and retry."
ERROR_ASYNC_OPERATION_FAILED = "Salary slip generation or email delivery failed. Payment record was created, but slip generation needs to be retried."

# Success Messages
SUCCESS_SALARY_OVERVIEW_RETRIEVED = "Salary overview retrieved successfully"
SUCCESS_SALARY_DETAILS_CREATED = "Salary details created successfully"
SUCCESS_BANK_INFO_UPDATED = "Bank information updated successfully"
SUCCESS_SALARY_PAYMENT_CREATED = "Salary payment created successfully. Salary slip will be emailed to the employee."
SUCCESS_SALARY_PAYMENTS_RETRIEVED = "Salary payments retrieved successfully"

# Error Codes
ERROR_CODE_EMPLOYEE_NOT_FOUND = "EMPLOYEE_NOT_FOUND"
ERROR_CODE_SALARY_DETAILS_NOT_FOUND = "SALARY_DETAILS_NOT_FOUND"
ERROR_CODE_BANK_INFO_NOT_FOUND = "BANK_INFO_NOT_FOUND"
ERROR_CODE_SALARY_PAYMENT_NOT_FOUND = "SALARY_PAYMENT_NOT_FOUND"
ERROR_CODE_SALARY_SLIP_NOT_FOUND = "SALARY_SLIP_NOT_FOUND"
ERROR_CODE_INVALID_REQUEST = "INVALID_REQUEST"
ERROR_CODE_VALIDATION_FAILED = "VALIDATION_FAILED"
ERROR_CODE_OVERLAPPING_SALARY_PERIOD = "OVERLAPPING_SALARY_PERIOD"
ERROR_CODE_DUPLICATE_SALARY_PAYMENT = "DUPLICATE_SALARY_PAYMENT"
ERROR_CODE_BUSINESS_RULE_FAILED = "BUSINESS_RULE_FAILED"
ERROR_CODE_INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
ERROR_CODE_PRECONDITION_REQUIRED = "PRECONDITION_REQUIRED"
ERROR_CODE_PRECONDITION_FAILED = "PRECONDITION_FAILED"
ERROR_CODE_ASYNC_OPERATION_FAILED = "ASYNC_OPERATION_FAILED"

# Enum Values
# Bank Names
BANK_HDFC = "HDFC"
BANK_ICICI = "ICICI"
BANK_SBI = "SBI"
BANK_AXIS = "AXIS"
BANK_KOTAK = "KOTAK"
BANK_PNB = "PNB"
BANK_BOB = "BOB"

# Currencies
CURRENCY_INR = "INR"
CURRENCY_USD = "USD"
CURRENCY_EUR = "EUR"
CURRENCY_GBP = "GBP"
CURRENCY_AUD = "AUD"
CURRENCY_CAD = "CAD"

# Payment Frequencies
FREQUENCY_MONTHLY = "MONTHLY"
FREQUENCY_BI_WEEKLY = "BI_WEEKLY"
FREQUENCY_WEEKLY = "WEEKLY"

# Payment Methods
PAYMENT_METHOD_BANK_TRANSFER = "BANK_TRANSFER"
PAYMENT_METHOD_UPI = "UPI"
PAYMENT_METHOD_CHEQUE = "CHEQUE"
PAYMENT_METHOD_CASH = "CASH"
