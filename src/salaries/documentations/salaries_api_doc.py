"""API documentation for Salary Management endpoints.

Based on F6_api_spec.md - Salary Management (F-006).
Centralized Swagger/OpenAPI documentation class.
"""

from typing import ClassVar


class SalaryApiDocs:
    """API documentation for Salary Management endpoints."""
    
    get_overview: ClassVar[dict] = {
        "summary": "Get salary overview for an employee",
        "description": "Retrieve complete salary overview for an employee, including current salary details, salary history, bank information, and payment summary. Only CEO and HR can access this endpoint. Supports ETag-based caching with If-None-Match header."
    }
    
    create_or_update_salary: ClassVar[dict] = {
        "summary": "Create or update salary details",
        "description": "Create new SalaryDetails or update existing salary (creates new record and auto-closes previous active record). Only one active SalaryDetails per employee. System validates no overlapping effective periods. If-Match header required when updating existing salary. Only CEO and HR can access this endpoint."
    }
    
    upsert_bank_info: ClassVar[dict] = {
        "summary": "Create or update bank information",
        "description": "Create or update BankInfo for an employee (upsert pattern - creates if not exists, updates if exists). Only one BankInfo per employee. BankInfo is never deleted (soft delete or updates only). Updates affect future salary payments only. If-Match header required when updating existing BankInfo. Only CEO and HR can access this endpoint."
    }
    
    create_payment: ClassVar[dict] = {
        "summary": "Create salary payment",
        "description": "Create a monthly salary payment record for an employee. Only one payment per employee per month/year. Amount is automatically derived from active SalaryDetails for the payment month. System automatically generates salary slip (async operation) and emails it to employee. Only CEO and HR can access this endpoint."
    }
    
    list_payments: ClassVar[dict] = {
        "summary": "List salary payments",
        "description": "List all salary payments for an employee with pagination, filtering, and sorting. Supports filtering by year, month, and payment method. Supports sorting by paid_on, month, year, amount, or created_at. Only CEO and HR can access this endpoint."
    }
    
    get_salary_slip: ClassVar[dict] = {
        "summary": "Download salary slip PDF",
        "description": "Download salary slip PDF for a specific salary payment. Returns raw PDF file binary data. Only CEO and HR can access this endpoint. Returns 404 if slip not generated yet."
    }
