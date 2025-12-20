"""Base exception classes and global exception handlers."""

import re
from uuid import uuid4
from typing import Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from asyncpg.exceptions import (
    UniqueViolationError,
    ForeignKeyViolationError,
    NotNullViolationError,
    CheckViolationError,
)


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[list[dict]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or []


class BadRequestError(AppException):
    """400 Bad Request - Invalid input or format."""

    def __init__(self, message: str, error_code: str = "INVALID_REQUEST", details: Optional[list[dict]] = None):
        super().__init__(message, error_code, status.HTTP_400_BAD_REQUEST, details)


class UnauthenticatedError(AppException):
    """401 Unauthenticated - Missing or invalid token."""

    def __init__(self, message: str, error_code: str = "UNAUTHENTICATED", details: Optional[list[dict]] = None):
        super().__init__(message, error_code, status.HTTP_401_UNAUTHORIZED, details)


class ForbiddenError(AppException):
    """403 Forbidden - Insufficient permissions."""

    def __init__(self, message: str, error_code: str = "INSUFFICIENT_PERMISSIONS", details: Optional[list[dict]] = None):
        super().__init__(message, error_code, status.HTTP_403_FORBIDDEN, details)


class NotFoundError(AppException):
    """404 Not Found - Resource not found."""

    def __init__(self, resource: str, resource_id: Optional[str] = None):
        resource_id_str = f" with ID {resource_id}" if resource_id else ""
        message = f"{resource} not found{resource_id_str}"
        error_code = f"{resource.upper().replace(' ', '_')}_NOT_FOUND"
        super().__init__(message, error_code, status.HTTP_404_NOT_FOUND)


class ConflictError(AppException):
    """409 Conflict - Resource conflict or duplicate."""

    def __init__(self, message: str, error_code: str = "RESOURCE_CONFLICT", details: Optional[list[dict]] = None):
        super().__init__(message, error_code, status.HTTP_409_CONFLICT, details)


class ValidationError(AppException):
    """422 Unprocessable Entity - Validation or business rule violation."""

    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR", details: Optional[list[dict]] = None):
        super().__init__(message, error_code, status.HTTP_422_UNPROCESSABLE_ENTITY, details)


class GoneError(AppException):
    """410 Gone - Resource is no longer available (expired, deleted permanently)."""

    def __init__(self, message: str, error_code: str = "RESOURCE_GONE", details: Optional[list[dict]] = None):
        super().__init__(message, error_code, status.HTTP_410_GONE, details)


class PreconditionRequiredError(AppException):
    """428 Precondition Required - If-Match header missing."""

    def __init__(self, message: str, error_code: str = "PRECONDITION_REQUIRED", details: Optional[list[dict]] = None):
        super().__init__(message, error_code, status.HTTP_428_PRECONDITION_REQUIRED, details)


class PreconditionFailedError(AppException):
    """412 Precondition Failed - ETag mismatch."""

    def __init__(self, message: str, error_code: str = "PRECONDITION_FAILED", details: Optional[list[dict]] = None):
        super().__init__(message, error_code, status.HTTP_412_PRECONDITION_FAILED, details)


class InternalServerError(AppException):
    """500 Internal Server Error - Server error."""

    def __init__(self, message: str = "Internal server error", error_code: str = "INTERNAL_ERROR", details: Optional[list[dict]] = None):
        super().__init__(message, error_code, status.HTTP_500_INTERNAL_SERVER_ERROR, details)


# Exception Handlers


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application exceptions."""
    # Get or generate X-Request-ID (middleware should have set it, but ensure it's present)
    x_request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex[:12]}"
    
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "details": exc.details,
            },
            "message": exc.message,
        },
    )
    response.headers["X-Request-ID"] = x_request_id
    return response


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    # Get or generate X-Request-ID
    x_request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex[:12]}"
    
    details = [{"field": str(err["loc"][-1]), "issue": err["msg"]} for err in exc.errors()]
    response = JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "details": details,
            },
            "message": "Validation error",
        },
    )
    response.headers["X-Request-ID"] = x_request_id
    return response


async def catch_all_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all exception handler for unexpected errors."""
    # Get or generate X-Request-ID
    x_request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex[:12]}"
    
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "details": [],
            },
            "message": "An unexpected error occurred",
        },
    )
    response.headers["X-Request-ID"] = x_request_id
    return response


# Database Constraint Exception Handler


def extract_field_name(error_msg: str, constraint_name: Optional[str] = None) -> str:
    """Extract field name from constraint name or error message."""
    if constraint_name:
        field = constraint_name
        # Remove prefixes: ix_, fk_, pk_, uq_, ck_
        for prefix in ["ix_", "fk_", "pk_", "uq_", "ck_"]:
            if field.startswith(prefix):
                field = field[len(prefix) :]
        # Remove table prefix (e.g., "users_" from "users_email")
        if "_" in field:
            parts = field.split("_", 1)
            if len(parts) > 1:
                field = parts[1]
        # Remove suffixes: _key, _idx, _constraint
        for suffix in ["_key", "_idx", "_constraint"]:
            if field.endswith(suffix):
                field = field[: -len(suffix)]
        return field

    # Extract from error message: "Key (field_name)=(value)"
    match = re.search(r"Key \(([^)]+)\)", error_msg)
    if match:
        return match.group(1)

    # Extract constraint name and recurse
    match = re.search(r'constraint "([^"]+)"', error_msg)
    if match:
        return extract_field_name(error_msg, match.group(1))

    return "field"


def extract_constraint_info(error_msg: str) -> tuple[Optional[str], str]:
    """Extract constraint name and field from error message."""
    constraint_name = None
    match = re.search(r'constraint "([^"]+)"', error_msg)
    if match:
        constraint_name = match.group(1)
    field_name = extract_field_name(error_msg, constraint_name)
    return constraint_name, field_name


async def database_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for database constraint violations."""
    # Get or generate X-Request-ID
    x_request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex[:12]}"
    
    # Handle IntegrityError (wraps asyncpg exceptions)
    if isinstance(exc, IntegrityError):
        orig_exc = exc.orig if hasattr(exc, "orig") else exc

        # Handle Unique Violation
        if isinstance(orig_exc, UniqueViolationError):
            _, field_name = extract_constraint_info(str(orig_exc))
            response = JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error": {
                        "code": f"DUPLICATE_{field_name.upper()}",
                        "details": [{"field": field_name, "issue": f"{field_name} must be unique"}],
                    },
                    "message": f"A record with this {field_name} already exists. Please use a different value.",
                },
            )
            response.headers["X-Request-ID"] = x_request_id
            return response

        # Handle Foreign Key Violation
        elif isinstance(orig_exc, ForeignKeyViolationError):
            error_msg = str(orig_exc)
            match = re.search(
                r'Key \(([^)]+)\)=\(([^)]+)\) is not present in table "([^"]+)"',
                error_msg,
            )
            if match:
                field_name, key_value, table_name = match.group(1), match.group(2), match.group(3)
                resource_name = table_name.replace("_", " ").title().replace(" ", "")
                response = JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "error": {
                            "code": f"{resource_name.upper()}_NOT_FOUND",
                            "details": [
                                {
                                    "field": field_name,
                                    "issue": f"Referenced {resource_name} with ID '{key_value}' not found",
                                }
                            ],
                        },
                        "message": f"The referenced {resource_name} does not exist.",
                    },
                )
                response.headers["X-Request-ID"] = x_request_id
                return response
            response = JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": {
                        "code": "FOREIGN_KEY_VIOLATION",
                        "details": [{"field": "reference", "issue": "Referenced record not found"}],
                    },
                    "message": "The referenced record does not exist.",
                },
            )
            response.headers["X-Request-ID"] = x_request_id
            return response

        # Handle Not Null Violation
        elif isinstance(orig_exc, NotNullViolationError):
            error_msg = str(orig_exc)
            match = re.search(r'column "([^"]+)"', error_msg)
            field_name = match.group(1) if match else "field"
            response = JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": {
                        "code": "REQUIRED_FIELD_MISSING",
                        "details": [{"field": field_name, "issue": f"{field_name} is required"}],
                    },
                    "message": f"The field '{field_name}' is required and cannot be null.",
                },
            )
            response.headers["X-Request-ID"] = x_request_id
            return response

        # Handle Check Violation
        elif isinstance(orig_exc, CheckViolationError):
            _, field_name = extract_constraint_info(str(orig_exc))
            response = JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": {
                        "code": "CHECK_CONSTRAINT_VIOLATION",
                        "details": [{"field": field_name, "issue": "Value violates check constraint"}],
                    },
                    "message": f"The value provided for '{field_name}' violates a validation rule.",
                },
            )
            response.headers["X-Request-ID"] = x_request_id
            return response

    # Handle direct asyncpg exceptions (fallback)
    if isinstance(exc, UniqueViolationError):
        _, field_name = extract_constraint_info(str(exc))
        response = JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": f"DUPLICATE_{field_name.upper()}",
                    "details": [{"field": field_name, "issue": f"{field_name} must be unique"}],
                },
                "message": f"A record with this {field_name} already exists. Please use a different value.",
            },
        )
        response.headers["X-Request-ID"] = x_request_id
        return response

    elif isinstance(exc, ForeignKeyViolationError):
        error_msg = str(exc)
        match = re.search(
            r'Key \(([^)]+)\)=\(([^)]+)\) is not present in table "([^"]+)"',
            error_msg,
        )
        if match:
            field_name, key_value, table_name = match.group(1), match.group(2), match.group(3)
            resource_name = table_name.replace("_", " ").title().replace(" ", "")
            response = JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": {
                        "code": f"{resource_name.upper()}_NOT_FOUND",
                        "details": [
                            {
                                "field": field_name,
                                "issue": f"Referenced {resource_name} with ID '{key_value}' not found",
                            }
                        ],
                    },
                    "message": f"The referenced {resource_name} does not exist.",
                },
            )
            response.headers["X-Request-ID"] = x_request_id
            return response
        response = JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "FOREIGN_KEY_VIOLATION",
                    "details": [{"field": "reference", "issue": "Referenced record not found"}],
                },
                "message": "The referenced record does not exist.",
            },
        )
        response.headers["X-Request-ID"] = x_request_id
        return response

    elif isinstance(exc, NotNullViolationError):
        error_msg = str(exc)
        match = re.search(r'column "([^"]+)"', error_msg)
        field_name = match.group(1) if match else "field"
        response = JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "REQUIRED_FIELD_MISSING",
                    "details": [{"field": field_name, "issue": f"{field_name} is required"}],
                },
                "message": f"The field '{field_name}' is required and cannot be null.",
            },
        )
        response.headers["X-Request-ID"] = x_request_id
        return response

    elif isinstance(exc, CheckViolationError):
        _, field_name = extract_constraint_info(str(exc))
        response = JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "CHECK_CONSTRAINT_VIOLATION",
                    "details": [{"field": field_name, "issue": "Value violates check constraint"}],
                },
                "message": f"The value provided for '{field_name}' violates a validation rule.",
            },
        )
        response.headers["X-Request-ID"] = x_request_id
        return response

    # If we get here, it's an unhandled database exception
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "DATABASE_ERROR",
                "details": [],
            },
            "message": "A database error occurred",
        },
    )
    response.headers["X-Request-ID"] = x_request_id
    return response
