"""Utility functions for Attendance Management module.

Based on F10_api_spec.md Section 2.4 - Response Headers (ETags).
Pure helper functions - no business logic, no database access.
"""

from datetime import datetime, timezone


def generate_etag(updated_at: datetime) -> str:
    """Generate ETag from updated_at timestamp.
    
    Based on F10_api_spec.md Section 2.4 - ETag format.
    Format: Convert datetime to ETag format (e.g., "20240120T103000Z")
    """
    # Ensure UTC timezone
    if updated_at.tzinfo is None:
        dt = updated_at.replace(tzinfo=timezone.utc)
    else:
        dt = updated_at.astimezone(timezone.utc)
    
    # Format: YYYYMMDDTHHMMSSZ (UTC)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def format_last_modified(updated_at: datetime) -> str:
    """Format datetime for Last-Modified header (RFC 7231 format).
    
    Based on F10_api_spec.md Section 2.4 - Last-Modified header.
    Format: "Wed, 20 Jan 2024 10:30:00 GMT"
    """
    # Ensure UTC timezone
    if updated_at.tzinfo is None:
        dt = updated_at.replace(tzinfo=timezone.utc)
    else:
        dt = updated_at.astimezone(timezone.utc)
    
    # Format: RFC 1123 format (e.g., "Wed, 20 Jan 2024 10:30:00 GMT")
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
