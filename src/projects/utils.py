"""Utility functions for Project Management module.

Based on F7_api_spec.md Section 2.3 - Conditional Requests (ETags).
Pure helper functions - no business logic, no database access.
"""

from datetime import datetime


def generate_etag(updated_at: datetime) -> str:
    """Generate ETag from updated_at timestamp.
    
    Format: Convert datetime to ETag format (e.g., "20240120T103000Z")
    Based on F7_api_spec.md Section 2.3 - ETag Generation.
    """
    # Ensure UTC timezone
    if updated_at.tzinfo:
        dt = updated_at.astimezone(datetime.now().astimezone().tzinfo).replace(tzinfo=None)
    else:
        dt = updated_at
    
    return dt.strftime("%Y%m%dT%H%M%SZ")


def format_last_modified(updated_at: datetime) -> str:
    """Format datetime for Last-Modified header (RFC 7231 format).
    
    Format: "Wed, 20 Jan 2024 10:30:00 GMT"
    Based on F7_api_spec.md Section 2.3 - Conditional Requests (ETags).
    """
    # Ensure UTC timezone
    if updated_at.tzinfo:
        dt = updated_at.astimezone(datetime.now().astimezone().tzinfo).replace(tzinfo=None)
    else:
        dt = updated_at
    
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
