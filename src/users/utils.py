"""Utility functions for User & Role Management module."""

from uuid import uuid4
from datetime import datetime
from typing import Optional


def generate_request_id(existing_id: Optional[str] = None) -> str:
    """Generate or return X-Request-ID header value.
    
    If client provides X-Request-ID, echo it back. Otherwise, generate new one.
    Format: req_<12-char-hex> (e.g., req_abc123xyz789)
    
    Handles empty strings by treating them as None (will generate new ID).
    """
    if existing_id and existing_id.strip():  # Handle empty strings
        return existing_id
    return f"req_{uuid4().hex[:12]}"


def generate_etag(updated_at: datetime) -> str:
    """Generate ETag from updated_at timestamp.
    
    Format: YYYYMMDDTHHMMSSZ (e.g., "20240120T103000Z")
    Based on F1A_api_spec.md Section 5.3 - ETag format.
    """
    # Ensure UTC timezone
    if updated_at.tzinfo:
        dt = updated_at.astimezone(datetime.now().astimezone().tzinfo).replace(tzinfo=None)
    else:
        dt = updated_at
    
    return dt.strftime("%Y%m%dT%H%M%SZ")


def format_last_modified(updated_at: datetime) -> str:
    """Format datetime for Last-Modified header (RFC 7231 format).
    
    Format: Wed, 20 Jan 2024 10:30:00 GMT
    Based on F1A_api_spec.md Section 5.3 - Last-Modified format.
    """
    # Ensure UTC timezone
    if updated_at.tzinfo:
        dt = updated_at.astimezone(datetime.now().astimezone().tzinfo).replace(tzinfo=None)
    else:
        dt = updated_at
    
    # Format as RFC 7231 Last-Modified header
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
