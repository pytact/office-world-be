"""Utility functions for Permissions System module.

Based on F2_db_spec.md - ETag generation and Last-Modified formatting.
"""

from datetime import datetime


def generate_etag(updated_at: datetime) -> str:
    """Generate ETag from updated_at timestamp.
    
    Based on standard ETag generation pattern.
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
    
    Based on standard Last-Modified header format.
    Format: RFC 7231 format (e.g., "Wed, 20 Jan 2024 10:30:00 GMT")
    """
    # Ensure UTC timezone
    if updated_at.tzinfo:
        dt = updated_at.astimezone(datetime.now().astimezone().tzinfo).replace(tzinfo=None)
    else:
        dt = updated_at
    
    # Format: RFC 7231 format (e.g., "Wed, 20 Jan 2024 10:30:00 GMT")
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
