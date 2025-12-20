"""Utility functions for Companies System module.

Based on F4_api_spec.md - ETag generation and Last-Modified formatting.
"""

from datetime import datetime


def generate_etag(updated_at: datetime) -> str:
    """Generate ETag from updated_at timestamp.
    
    Based on F4_api_spec.md Section 6.1 - ETag Generation.
    Format: Convert datetime to ETag format (e.g., "20240120T103000Z")
    """
    # Ensure UTC timezone
    if updated_at.tzinfo:
        dt = updated_at.astimezone(datetime.now().astimezone().tzinfo).replace(tzinfo=None)
    else:
        dt = updated_at
    
    # Format: YYYYMMDDTHHMMSSZ (UTC)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def format_last_modified(updated_at: datetime) -> str:
    """Format datetime for Last-Modified header (RFC 7231 format).
    
    Based on F4_api_spec.md Section 6.4 - ETag Headers in Responses.
    """
    # Ensure UTC timezone
    if updated_at.tzinfo:
        dt = updated_at.astimezone(datetime.now().astimezone().tzinfo).replace(tzinfo=None)
    else:
        dt = updated_at
    
    # Format: RFC 7231 format (e.g., "Wed, 20 Jan 2024 10:30:00 GMT")
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
