"""API documentation for Salary Management endpoints.

Based on F6_api_spec.md - Salary Management (F-006).
Centralized Swagger/OpenAPI documentation class.
"""

from typing import ClassVar


class SalaryApiDocs:
    """API documentation for Salary Management endpoints."""
    
    get_active_salary: ClassVar[dict] = {
        "summary": "Get active salary for an employee",
        "description": "Retrieve active salary details for an employee. Used for payroll, employee view, and offer confirmation. Returns 404 if no active salary exists. Supports ETag-based caching with If-None-Match header. Only CEO and HR can access this endpoint."
    }
    
    create_salary: ClassVar[dict] = {
        "summary": "Create initial salary",
        "description": "Create initial SalaryDetails for an employee. Validates no active salary exists (returns 409 if active salary exists - use revise endpoint instead). effective_from must be >= today. Only CEO and HR can access this endpoint."
    }
    
    revise_salary: ClassVar[dict] = {
        "summary": "Revise salary (increment/change)",
        "description": "Revise existing salary by creating a new record and closing the active one. Fetches active salary, sets effective_to = yesterday, and inserts new salary record. Never updates in-place. If-Match header required. Only CEO and HR can access this endpoint."
    }
    
    get_salary_history: ClassVar[dict] = {
        "summary": "Get salary history",
        "description": "Retrieve salary history for an employee. Returns list of all salary changes over time. Supports ETag-based caching with If-None-Match header. HR / CEO only."
    }
    
    get_bank_info: ClassVar[dict] = {
        "summary": "Get bank information",
        "description": "Retrieve bank information for an employee. Returns masked account number and IFSC code for security. Supports ETag-based caching with If-None-Match header. Only CEO and HR can access this endpoint. Returns 404 if bank info not found."
    }
    
    create_bank_info: ClassVar[dict] = {
        "summary": "Create bank information",
        "description": "Create new BankInfo for an employee. Only one BankInfo per employee. Only CEO and HR can access this endpoint."
    }
    
    update_bank_info: ClassVar[dict] = {
        "summary": "Update bank information",
        "description": "Update existing BankInfo for an employee by ID. Updates affect future salary payments only. If-Match header required. Only CEO and HR can access this endpoint."
    }
    
    delete_bank_info: ClassVar[dict] = {
        "summary": "Delete bank information",
        "description": "Soft delete BankInfo for an employee by ID. The bank info record will be marked as deleted but preserved for audit purposes. Only CEO and HR can access this endpoint."
    }
    
    run_payment: ClassVar[dict] = {
        "summary": "Execute salary payment",
        "description": "Execute salary payment for an employee. Used by HR and automated payroll jobs. Checks payment not already done, fetches active salary_details and bank_info, inserts salary_payment, and triggers async slip generation."
    }
    
    list_payments_by_month_year: ClassVar[dict] = {
        "summary": "Get salary payments by month/year",
        "description": "Get salary payments by month and year across company. Used for payroll reports, compliance, and finance reconciliation. Supports ETag-based caching with If-None-Match header. Only CEO and HR can access this endpoint."
    }
    
    list_payments: ClassVar[dict] = {
        "summary": "List salary payments",
        "description": "List all salary payments for an employee with pagination, filtering, and sorting. Supports filtering by year, month, and payment method. Supports sorting by paid_on, month, year, amount, or created_at. Supports ETag-based caching with If-None-Match header. Only CEO and HR can access this endpoint."
    }
    
    get_salary_slip: ClassVar[dict] = {
        "summary": "Download salary slip PDF",
        "description": "Download salary slip PDF for a specific salary payment. Returns raw PDF file binary data. Only CEO and HR can access this endpoint. Returns 404 if slip not generated yet."
    }
