"""FastAPI application entry point."""

import logging
import sys
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from src.config import settings
from src.api.router import api_router
from src.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    database_exception_handler,
    catch_all_exception_handler,
)
from src.infra.cache_redis import close_redis
from sqlalchemy.exc import IntegrityError
from asyncpg.exceptions import (
    UniqueViolationError,
    ForeignKeyViolationError,
    NotNullViolationError,
    CheckViolationError,
)

# Setup logger with proper configuration - output to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Explicitly use stdout
    ],
    force=True  # Override any existing configuration
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Also configure the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
if not root_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    root_logger.addHandler(handler)

# Import all models to ensure relationships are registered with SQLAlchemy
# This must happen before any queries that use relationships
import src.users.models  # noqa: F401
import src.employees.models  # noqa: F401 - Required for User.employee relationship
import src.permissions.models  # noqa: F401
import src.companies.models  # noqa: F401
import src.salaries.models  # noqa: F401 - Required for Employee salary relationships
import src.projects.models  # noqa: F401 - Required for Project relationships
import src.tasks.models  # noqa: F401 - Required for Task relationships
import src.leaves.models  # noqa: F401 - Required for LeaveRequest relationships
import src.attendance.models  # noqa: F401 - Required for Attendance relationships
import src.audits.models  # noqa: F401 - Required for AuditLog relationships


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add X-Request-ID header to all responses.
    
    Based on F1A_api_spec.md Section 2.2 - All responses MUST include X-Request-ID header.
    """
    
    async def dispatch(self, request: StarletteRequest, call_next):
        # Get X-Request-ID from request header or generate new one
        x_request_id = request.headers.get("X-Request-ID")
        if not x_request_id:
            x_request_id = f"req_{uuid4().hex[:12]}"
        
        # Log incoming request (both logger and print for visibility)
        log_message = (
            f"{request.method} {request.url.path} - "
            f"X-Request-ID: {x_request_id} - "
            f"If-None-Match: {request.headers.get('If-None-Match', 'None')}"
        )
        logger.info(log_message)
        print(f"[REQUEST] {log_message}", flush=True)  # Print to stdout for visibility
        
        # Process request
        response = await call_next(request)
        
        # Log response (both logger and print for visibility)
        response_message = (
            f"Response {response.status_code} for {request.method} {request.url.path} - "
            f"X-Request-ID: {x_request_id}"
        )
        logger.info(response_message)
        print(f"[RESPONSE] {response_message}", flush=True)  # Print to stdout for visibility
        
        # Set X-Request-ID header in response
        response.headers["X-Request-ID"] = x_request_id
        
        return response


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException."""
    # Get or generate X-Request-ID
    x_request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex[:12]}"
    
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "details": [{"field": "general", "issue": exc.detail}],
            },
            "message": exc.detail or "An error occurred",
        },
    )
    response.headers["X-Request-ID"] = x_request_id
    return response


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    debug=settings.debug,
    swagger_ui_parameters={
        "persistAuthorization": True,  # Persist authorization token on page refresh (auth_setup.md RULE 13.1.1)
        "tryItOutEnabled": True,  # Enable "Try it out" by default
    },
)

# Register CORS middleware (must be before other middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Register middleware for X-Request-ID header (must be before exception handlers)
app.add_middleware(RequestIDMiddleware)

# Register exception handlers (order matters - most specific first)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
# Database handlers (BEFORE catch-all)
app.add_exception_handler(IntegrityError, database_exception_handler)
app.add_exception_handler(UniqueViolationError, database_exception_handler)
app.add_exception_handler(ForeignKeyViolationError, database_exception_handler)
app.add_exception_handler(NotNullViolationError, database_exception_handler)
app.add_exception_handler(CheckViolationError, database_exception_handler)
app.add_exception_handler(Exception, catch_all_exception_handler)  # Last - catch-all

# Register API router
app.include_router(api_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler - cleanup resources"""
    await close_redis()
