"""Utility functions for Salary Management module.

Based on F6_api_spec.md - Salary Management (F-006).
Pure helper functions - no business logic, no database access.
"""

from datetime import datetime
from typing import Optional


def generate_etag(updated_at: datetime) -> str:
    """Generate ETag from updated_at timestamp.
    
    Format: Convert datetime to ETag format (e.g., "20240120T103000Z")
    Based on F6_api_spec.md Section 2.4 - Response Headers.
    """
    return updated_at.strftime("%Y%m%dT%H%M%SZ")


def format_last_modified(updated_at: datetime) -> str:
    """Format datetime for Last-Modified header (RFC 7231 format).
    
    Format: "Wed, 20 Jan 2024 10:30:00 GMT"
    Based on F6_api_spec.md Section 2.4 - Response Headers.
    """
    return updated_at.strftime("%a, %d %b %Y %H:%M:%S GMT")


def mask_account_number(account_number: str) -> str:
    """Mask bank account number - show last 4 characters, mask rest with *.
    
    Based on F6_api_spec.md Section 10.1 - Bank Account Number Masking.
    Example: "1234567890123456" → "****3456"
    """
    if not account_number or len(account_number) < 4:
        return account_number
    
    return "*" * (len(account_number) - 4) + account_number[-4:]


def mask_ifsc_code(ifsc_code: str) -> str:
    """Mask IFSC code - show first 4 characters, mask rest with *.
    
    Based on F6_api_spec.md Section 10.2 - IFSC Code Masking.
    Example: "HDFC0001234" → "HDFC****234"
    """
    if not ifsc_code or len(ifsc_code) < 4:
        return ifsc_code
    
    return ifsc_code[:4] + "*" * (len(ifsc_code) - 4)


def generate_payment_period_label(month: int, year: int) -> str:
    """Generate human-readable payment period label.
    
    Based on F6_api_spec.md Section 4.3.4 - Salary Payment Response.
    Example: month=3, year=2024 → "March 2024"
    """
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    if 1 <= month <= 12:
        return f"{month_names[month - 1]} {year}"
    return f"Month {month}, {year}"


def get_latest_updated_at(*timestamps: Optional[datetime]) -> Optional[datetime]:
    """Get the latest (most recent) timestamp from multiple timestamps.
    
    Used for generating ETag from multiple resources (e.g., salary overview).
    Returns None if all timestamps are None.
    """
    valid_timestamps = [ts for ts in timestamps if ts is not None]
    if not valid_timestamps:
        return None
    return max(valid_timestamps)
