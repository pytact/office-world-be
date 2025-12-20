"""Domain-specific exceptions for Companies System module.

Based on F1A_api_spec.md - All error responses and exception types.
"""

from src.exceptions import (
    NotFoundError,
    BadRequestError,
    ConflictError,
    ValidationError,
    PreconditionRequiredError,
    PreconditionFailedError,
)
from src.companies.constants import (
    ERROR_COMPANY_NOT_FOUND,
    ERROR_INVALID_REQUEST,
    ERROR_VALIDATION_FAILED,
    ERROR_DUPLICATE_COMPANY_NAME,
    ERROR_DUPLICATE_COMPANY_SLUG,
    ERROR_INVALID_SORT_FIELD,
    ERROR_INVALID_SORT_ORDER,
    ERROR_PRECONDITION_REQUIRED,
    ERROR_PRECONDITION_FAILED,
    ERROR_CANNOT_DELETE_COMPANY_IN_USE,
    ERROR_CODE_COMPANY_NOT_FOUND,
    ERROR_CODE_INVALID_REQUEST,
    ERROR_CODE_VALIDATION_FAILED,
    ERROR_CODE_DUPLICATE_COMPANY_NAME,
    ERROR_CODE_DUPLICATE_COMPANY_SLUG,
    ERROR_CODE_INVALID_SORT_FIELD,
    ERROR_CODE_PRECONDITION_REQUIRED,
    ERROR_CODE_PRECONDITION_FAILED,
    ERROR_CODE_CANNOT_DELETE_COMPANY_IN_USE,
)


class CompanyNotFound(NotFoundError):
    """Company not found exception."""

    def __init__(self, company_id: str):
        super().__init__(resource="Company", resource_id=company_id)


class InvalidRequest(BadRequestError):
    """Invalid request format exception."""

    def __init__(self, message: str = ERROR_INVALID_REQUEST, details: list[dict] | None = None):
        super().__init__(
            message=message,
            error_code=ERROR_CODE_INVALID_REQUEST,
            details=details or [],
        )


class ValidationFailed(BadRequestError):
    """Request validation failed exception."""

    def __init__(self, message: str = ERROR_VALIDATION_FAILED, details: list[dict] | None = None):
        super().__init__(
            message=message,
            error_code=ERROR_CODE_VALIDATION_FAILED,
            details=details or [],
        )


class DuplicateCompanyName(ConflictError):
    """Duplicate company name exception.
    
    Based on F4_api_spec.md - 409 Conflict for duplicate resources.
    """

    def __init__(self, company_name: str):
        super().__init__(
            message="Company name must be unique.",
            error_code=ERROR_CODE_DUPLICATE_COMPANY_NAME,
            details=[
                {
                    "field": "name",
                    "issue": "A company with this name already exists.",
                }
            ],
        )


class DuplicateCompanySlug(ConflictError):
    """Duplicate company slug exception.
    
    Based on F4_api_spec.md - 409 Conflict for duplicate resources.
    """

    def __init__(self, company_slug: str):
        super().__init__(
            message="Company slug must be unique.",
            error_code=ERROR_CODE_DUPLICATE_COMPANY_SLUG,
            details=[
                {
                    "field": "slug",
                    "issue": "A company with this slug already exists.",
                }
            ],
        )


class InvalidSortField(ValidationError):
    """Invalid sort field exception."""

    def __init__(self, sort_field: str, valid_fields: list[str]):
        valid_fields_str = ", ".join(valid_fields)
        super().__init__(
            message=f"Invalid sort field. Allowed values: {valid_fields_str}",
            error_code=ERROR_CODE_INVALID_SORT_FIELD,
            details=[
                {
                    "field": "sort_by",
                    "issue": f"Invalid sort field '{sort_field}'. Allowed values: {valid_fields_str}",
                }
            ],
        )


class InvalidSortOrder(ValidationError):
    """Invalid sort order exception."""

    def __init__(self, sort_order: str):
        super().__init__(
            message="Invalid sort order. Must be 'asc' or 'desc'",
            error_code=ERROR_CODE_VALIDATION_FAILED,
            details=[
                {
                    "field": "sort_order",
                    "issue": f"Invalid sort order '{sort_order}'. Must be 'asc' or 'desc'",
                }
            ],
        )


class PreconditionRequired(PreconditionRequiredError):
    """If-Match header required exception."""

    def __init__(self):
        super().__init__(
            message=ERROR_PRECONDITION_REQUIRED,
            error_code=ERROR_CODE_PRECONDITION_REQUIRED,
            details=[{"field": "If-Match", "issue": "If-Match header is required for update operations"}],
        )


class PreconditionFailed(PreconditionFailedError):
    """ETag mismatch exception."""

    def __init__(self):
        super().__init__(
            message=ERROR_PRECONDITION_FAILED,
            error_code=ERROR_CODE_PRECONDITION_FAILED,
            details=[
                {
                    "field": "etag",
                    "issue": "Resource has been modified since retrieval. Please fetch the latest version and retry.",
                }
            ],
        )


class BusinessRuleFailed(ValidationError):
    """Business rule violation exception.
    
    Based on F4_api_spec.md - 422 Unprocessable Entity for business rule violations.
    Used when company profile updates are blocked (e.g., company inactive).
    """

    def __init__(self, message: str):
        from src.companies.constants import ERROR_CODE_BUSINESS_RULE_FAILED
        super().__init__(
            message=message,
            error_code=ERROR_CODE_BUSINESS_RULE_FAILED,
            details=[
                {
                    "field": "company",
                    "issue": message,
                }
            ],
        )
