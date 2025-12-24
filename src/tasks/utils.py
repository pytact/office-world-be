"""Utility functions for Task Management module.

Based on F8_api_spec.md Section 2.3 - Conditional Requests (ETags).
Pure helper functions - no business logic, no database access.
"""

from datetime import datetime, timezone


def generate_etag(updated_at: datetime) -> str:
    """Generate ETag from updated_at timestamp.
    
    Format: Convert datetime to ETag format (e.g., "20240120T103000Z")
    Based on F8_api_spec.md Section 2.3 - ETag Generation.
    """
    # Ensure UTC timezone
    if updated_at.tzinfo:
        # Convert to UTC
        dt_utc = updated_at.astimezone(timezone.utc)
        dt = dt_utc.replace(tzinfo=None)
    else:
        # Assume naive datetime is already UTC
        dt = updated_at
    
    return dt.strftime("%Y%m%dT%H%M%SZ")


def format_last_modified(updated_at: datetime) -> str:
    """Format datetime for Last-Modified header (RFC 7231 format).
    
    Based on F8_api_spec.md Section 2.3 - Last-Modified header.
    Format: "Wed, 20 Jan 2024 10:30:00 GMT"
    """
    # Ensure UTC timezone
    if updated_at.tzinfo:
        # Convert to UTC
        dt_utc = updated_at.astimezone(timezone.utc)
        dt = dt_utc.replace(tzinfo=None)
    else:
        # Assume naive datetime is already UTC
        dt = updated_at
    
    # Format: "Wed, 20 Jan 2024 10:30:00 GMT"
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
