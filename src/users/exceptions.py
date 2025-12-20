"""Domain-specific exceptions for User & Role Management module."""

from src.exceptions import (
    NotFoundError,
    ConflictError,
    ForbiddenError,
    ValidationError,
    PreconditionRequiredError,
    PreconditionFailedError,
)
from src.users.constants import (
    ERROR_CODE_DUPLICATE_EMAIL,
    ERROR_CODE_COMPANY_NOT_FOUND,
    ERROR_CODE_ROLE_NOT_FOUND,
    ERROR_CODE_COMPANY_HAS_CEO,
    ERROR_CODE_BUSINESS_RULE_FAILED,
    ERROR_CODE_CANNOT_CHANGE_OWN_ROLE,
    ERROR_CODE_CANNOT_DEACTIVATE_OWN_ACCOUNT,
    ERROR_CODE_CANNOT_REASSIGN_SUPERADMIN,
    ERROR_CODE_PRECONDITION_REQUIRED,
    ERROR_CODE_PRECONDITION_FAILED,
    ERROR_CODE_TARGET_COMPANY_HAS_CEO,
    ERROR_DUPLICATE_EMAIL,
    ERROR_COMPANY_NOT_FOUND,
    ERROR_ROLE_NOT_FOUND,
    ERROR_COMPANY_ALREADY_HAS_CEO,
    ERROR_CANNOT_CHANGE_OWN_ROLE,
    ERROR_CANNOT_DEACTIVATE_OWN_ACCOUNT,
    ERROR_CANNOT_REASSIGN_SUPERADMIN,
    ERROR_PRECONDITION_REQUIRED,
    ERROR_PRECONDITION_FAILED,
    ERROR_TARGET_COMPANY_HAS_CEO,
)


class UserNotFound(NotFoundError):
    """User not found exception."""

    def __init__(self, user_id: str):
        super().__init__(resource="User", resource_id=user_id)


class DuplicateEmail(ConflictError):
    """Duplicate email exception."""

    def __init__(self, email: str):
        super().__init__(
            message=ERROR_DUPLICATE_EMAIL,
            error_code=ERROR_CODE_DUPLICATE_EMAIL,
            details=[{"field": "email", "issue": f"A user with email '{email}' already exists and is active."}],
        )


class CompanyNotFound(NotFoundError):
    """Company not found exception."""

    def __init__(self, company_slug: str):
        super().__init__(
            resource="Company",
            resource_id=company_slug,
        )


class RoleNotFound(NotFoundError):
    """Role not found exception."""

    def __init__(self, role_code: str):
        super().__init__(
            resource="Role",
            resource_id=role_code,
        )


class CompanyHasCEO(ValidationError):
    """Company already has an active CEO exception."""

    def __init__(self, company_name: str):
        super().__init__(
            message=ERROR_COMPANY_ALREADY_HAS_CEO,
            error_code=ERROR_CODE_BUSINESS_RULE_FAILED,
            details=[
                {
                    "field": "role_code",
                    "issue": f"Company '{company_name}' already has an active CEO. Only one CEO is allowed per company.",
                }
            ],
        )


class InsufficientPermissions(ForbiddenError):
    """Insufficient permissions exception."""

    def __init__(self, action: str):
        super().__init__(
            message=f"You do not have permission to {action}",
            error_code="INSUFFICIENT_PERMISSIONS",
            details=[{"field": "role", "issue": f"Only authorized roles can {action}"}],
        )


class CannotChangeOwnRole(ForbiddenError):
    """Cannot change own role exception."""

    def __init__(self):
        super().__init__(
            message=ERROR_CANNOT_CHANGE_OWN_ROLE,
            error_code=ERROR_CODE_CANNOT_CHANGE_OWN_ROLE,
            details=[{"field": "user_id", "issue": "You cannot change your own role."}],
        )


class CannotDeactivateOwnAccount(ValidationError):
    """Cannot deactivate own account exception."""

    def __init__(self):
        super().__init__(
            message=ERROR_CANNOT_DEACTIVATE_OWN_ACCOUNT,
            error_code=ERROR_CODE_BUSINESS_RULE_FAILED,
            details=[{"field": "user_id", "issue": "You cannot deactivate your own account."}],
        )


class CannotReassignSuperAdmin(ValidationError):
    """Cannot reassign SuperAdmin exception."""

    def __init__(self):
        super().__init__(
            message=ERROR_CANNOT_REASSIGN_SUPERADMIN,
            error_code=ERROR_CODE_BUSINESS_RULE_FAILED,
            details=[
                {
                    "field": "user_id",
                    "issue": "Cannot reassign SuperAdmin users. SuperAdmin users are not tied to any company.",
                }
            ],
        )


class PreconditionRequired(PreconditionRequiredError):
    """If-Match header required exception."""

    def __init__(self):
        super().__init__(
            message=ERROR_PRECONDITION_REQUIRED,
            error_code=ERROR_CODE_PRECONDITION_REQUIRED,
            details=[{"field": "If-Match", "issue": "If-Match header is required for concurrency control"}],
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


class TargetCompanyHasCEO(ValidationError):
    """Target company already has an active CEO exception."""

    def __init__(self, company_name: str):
        super().__init__(
            message=ERROR_TARGET_COMPANY_HAS_CEO,
            error_code=ERROR_CODE_BUSINESS_RULE_FAILED,
            details=[
                {
                    "field": "role_code",
                    "issue": f"Target company '{company_name}' already has an active CEO. Only one CEO is allowed per company. Please deactivate the current CEO or choose a different role.",
                }
            ],
        )


class InvalidCurrentPassword(ValidationError):
    """Invalid current password exception."""

    def __init__(self):
        super().__init__(
            message="Current password is incorrect",
            error_code="INVALID_CURRENT_PASSWORD",
            details=[{"field": "current_password", "issue": "The current password you provided is incorrect"}],
        )
