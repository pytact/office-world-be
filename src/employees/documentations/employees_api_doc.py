"""API documentation for Employee endpoints.

Based on F5_api_spec.md Section 4.3 - API Documentation Class (Rule 10).
All endpoint documentation MUST use this centralized class structure.
"""

from typing import ClassVar


class EmployeeApiDocs:
    """API documentation for Employee endpoints.
    
    Based on F5_api_spec.md Section 4.3 - API Documentation Class (Rule 10).
    Router endpoints MUST reference summary and description from this class,
    NOT hardcoded strings.
    """
    
    list: ClassVar[dict] = {
        "summary": "Purpose of this API is to list employees with pagination, search, filtering, and sorting",
        "description": "Retrieves a paginated list of employees in the authenticated user's company. Supports filtering by department and employment_status, search by name/email, and sorting. Soft-deleted employees are excluded. CEO and HR see all employees with full fields. Manager and Employee see all fields but cannot see CEO or HR employee records. Requires JWT authentication."
    }
    
    create: ClassVar[dict] = {
        "summary": "Purpose of this API is to create a new employee from existing User",
        "description": "Creates a new employee record linked to an existing User. Enforces one-to-one User ↔ Employee constraint. User must not already have an employee record. JoiningDate is mandatory and immutable after creation. ENUM fields must be validated. WorkEmail must be unique within company (case-insensitive). Separation fields are required when employment_status is RESIGNED or TERMINATED. Only CEO and HR can create employees."
    }
    
    get: ClassVar[dict] = {
        "summary": "Purpose of this API is to get employee details with role-based field visibility",
        "description": "Retrieves detailed employee information. CEO, HR, Manager, and Employee roles can view employee details from their company. All roles see all fields. Includes derived fields (can_edit_employee, can_deactivate, can_soft_delete) based on role and employee state. Soft-deleted employees are not accessible. Requires If-None-Match header for cache validation (optional)."
    }
    
    update: ClassVar[dict] = {
        "summary": "Purpose of this API is to update employee fields including activation/deactivation",
        "description": "Updates employee fields. JoiningDate, user_id, and company_id are immutable. Setting is_active=false deactivates employee (blocks login). Setting is_active=true reactivates employee (restores login). Separation fields are required when employment_status changes to RESIGNED or TERMINATED. WorkEmail must be unique within company (case-insensitive). Only CEO and HR can update employees. Requires If-Match header for concurrency control."
    }
    
    delete: ClassVar[dict] = {
        "summary": "Purpose of this API is to soft delete an employee",
        "description": "Soft deletes an employee by setting is_deleted=true. After soft delete, employee is not visible to anyone (including CEO). Historical data is preserved. Only CEO and HR can soft delete employees. Requires If-Match header for concurrency control."
    }
