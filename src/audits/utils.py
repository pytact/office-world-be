"""Utility functions for Audit Logging & Activity History module.

Based on F11_api_spec.md Section 8 - ETags & Conditional Requests.
Pure helper functions - no business logic, no database access.
"""

from datetime import datetime, timezone


def generate_etag(created_at: datetime) -> str:
    """Generate ETag from created_at timestamp.
    
    Based on F11_api_spec.md Section 8.1 - ETag Generation.
    Format: Convert created_at timestamp to ETag format (e.g., "20240120T103000Z")
    
    Note: Audit logs are immutable, so ETag is based on created_at (not updated_at).
    """
    # Ensure UTC timezone
    if created_at.tzinfo is None:
        dt = created_at.replace(tzinfo=timezone.utc)
    else:
        dt = created_at.astimezone(timezone.utc)
    
    # Format: YYYYMMDDTHHMMSSZ (UTC)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def format_last_modified(created_at: datetime) -> str:
    """Format datetime for Last-Modified header (RFC 7231 format).
    
    Based on F11_api_spec.md Section 8.3 - ETag Requirements.
    Format: RFC 7231 format (e.g., "Wed, 20 Jan 2024 10:30:00 GMT")
    """
    # Ensure UTC timezone
    if created_at.tzinfo is None:
        dt = created_at.replace(tzinfo=timezone.utc)
    else:
        dt = created_at.astimezone(timezone.utc)
    
    # Format: RFC 7231 format
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
