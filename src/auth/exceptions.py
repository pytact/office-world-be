"""Domain-specific exceptions for authentication."""

from src.exceptions import (
    UnauthenticatedError,
    ForbiddenError,
    NotFoundError,
    BadRequestError,
    ConflictError,
    ValidationError,
    GoneError,
)
from src.auth.constants import (
    ERROR_INVALID_CREDENTIALS,
    ERROR_ACCOUNT_INACTIVE,
    ERROR_ACCOUNT_DELETED,
    ERROR_COMPANY_INACTIVE,
    ERROR_INVALID_TOKEN,
    ERROR_INVITATION_NOT_FOUND,
    ERROR_INVITATION_EXPIRED,
    ERROR_ACCOUNT_ALREADY_ACTIVATED,
    ERROR_PASSWORD_MISMATCH,
    ERROR_PASSWORD_WEAK,
    ERROR_RESET_TOKEN_NOT_FOUND,
    ERROR_RESET_TOKEN_EXPIRED,
    ERROR_RESET_TOKEN_USED,
    ERROR_CODE_INVALID_CREDENTIALS,
    ERROR_CODE_ACCOUNT_INACTIVE,
    ERROR_CODE_ACCOUNT_DELETED,
    ERROR_CODE_COMPANY_INACTIVE,
    ERROR_CODE_INVALID_TOKEN,
    ERROR_CODE_INVITATION_NOT_FOUND,
    ERROR_CODE_INVITATION_EXPIRED,
    ERROR_CODE_ACCOUNT_ALREADY_ACTIVATED,
    ERROR_CODE_PASSWORD_MISMATCH,
    ERROR_CODE_PASSWORD_WEAK,
    ERROR_CODE_RESET_TOKEN_NOT_FOUND,
    ERROR_CODE_RESET_TOKEN_EXPIRED,
    ERROR_CODE_RESET_TOKEN_USED,
)


class InvalidCredentials(UnauthenticatedError):
    """401 - Invalid email or password."""

    def __init__(self):
        super().__init__(
            message=ERROR_INVALID_CREDENTIALS,
            error_code=ERROR_CODE_INVALID_CREDENTIALS,
            details=[{"field": "email", "issue": ERROR_INVALID_CREDENTIALS}],
        )


class AccountInactive(ForbiddenError):
    """403 - User account is deactivated."""

    def __init__(self):
        super().__init__(
            message=ERROR_ACCOUNT_INACTIVE,
            error_code=ERROR_CODE_ACCOUNT_INACTIVE,
            details=[{"field": "is_active", "issue": ERROR_ACCOUNT_INACTIVE}],
        )


class AccountDeleted(ForbiddenError):
    """403 - User account is soft-deleted."""

    def __init__(self):
        super().__init__(
            message=ERROR_ACCOUNT_DELETED,
            error_code=ERROR_CODE_ACCOUNT_DELETED,
            details=[{"field": "is_deleted", "issue": ERROR_ACCOUNT_DELETED}],
        )


class CompanyInactive(ForbiddenError):
    """403 - User's company is inactive."""

    def __init__(self):
        super().__init__(
            message=ERROR_COMPANY_INACTIVE,
            error_code=ERROR_CODE_COMPANY_INACTIVE,
            details=[{"field": "company", "issue": ERROR_COMPANY_INACTIVE}],
        )


class InvalidToken(BadRequestError):
    """400 - Invalid or malformed token."""

    def __init__(self):
        super().__init__(
            message=ERROR_INVALID_TOKEN,
            error_code=ERROR_CODE_INVALID_TOKEN,
            details=[{"field": "token", "issue": ERROR_INVALID_TOKEN}],
        )


class InvitationNotFound(NotFoundError):
    """404 - Invitation token not found."""

    def __init__(self, token: str):
        super().__init__(resource="Invitation", resource_id=token)


class InvitationExpired(GoneError):
    """410 - Invitation token expired."""

    def __init__(self):
        super().__init__(
            message=ERROR_INVITATION_EXPIRED,
            error_code=ERROR_CODE_INVITATION_EXPIRED,
            details=[{"field": "token", "issue": ERROR_INVITATION_EXPIRED}],
        )


class AccountAlreadyActivated(ConflictError):
    """409 - User account is already activated."""

    def __init__(self):
        super().__init__(
            message=ERROR_ACCOUNT_ALREADY_ACTIVATED,
            error_code=ERROR_CODE_ACCOUNT_ALREADY_ACTIVATED,
            details=[{"field": "activate_at", "issue": ERROR_ACCOUNT_ALREADY_ACTIVATED}],
        )


class PasswordMismatch(BadRequestError):
    """400 - Password confirmation does not match."""

    def __init__(self):
        super().__init__(
            message=ERROR_PASSWORD_MISMATCH,
            error_code=ERROR_CODE_PASSWORD_MISMATCH,
            details=[{"field": "password_confirm", "issue": ERROR_PASSWORD_MISMATCH}],
        )


class PasswordWeak(ValidationError):
    """422 - Password does not meet complexity requirements."""

    def __init__(self, issue: str):
        super().__init__(
            message=ERROR_PASSWORD_WEAK,
            error_code=ERROR_CODE_PASSWORD_WEAK,
            details=[{"field": "password", "issue": issue}],
        )


class ResetTokenNotFound(NotFoundError):
    """404 - Password reset token not found."""

    def __init__(self, token: str):
        super().__init__(resource="ResetToken", resource_id=token)


class ResetTokenExpired(GoneError):
    """410 - Password reset token expired."""

    def __init__(self):
        super().__init__(
            message=ERROR_RESET_TOKEN_EXPIRED,
            error_code=ERROR_CODE_RESET_TOKEN_EXPIRED,
            details=[{"field": "token", "issue": ERROR_RESET_TOKEN_EXPIRED}],
        )


class ResetTokenUsed(ConflictError):
    """409 - Password reset token already used."""

    def __init__(self):
        super().__init__(
            message=ERROR_RESET_TOKEN_USED,
            error_code=ERROR_CODE_RESET_TOKEN_USED,
            details=[{"field": "token", "issue": ERROR_RESET_TOKEN_USED}],
        )
