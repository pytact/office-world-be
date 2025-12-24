from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Tuple
from calendar import monthrange

from src.leaves.schemas import DayType
from src.leaves.exceptions import InvalidWorkingDay


def calculate_days(start_date: date, end_date: date, day_type: DayType) -> Decimal:
    """Calculate number of leave days from date range and day type.

    Args:
        start_date: Leave start date (inclusive)
        end_date: Leave end date (inclusive)
        day_type: FULL_DAY, FIRST_HALF, or SECOND_HALF

    Returns:
        Decimal: Number of leave days
    """
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    # Calculate total calendar days
    total_days = (end_date - start_date).days + 1

    # Convert to leave days based on day type
    if day_type == DayType.FULL_DAY:
        return Decimal(str(total_days))
    elif day_type in [DayType.FIRST_HALF, DayType.SECOND_HALF]:
        return Decimal("0.5") * total_days
    else:
        raise ValueError(f"Invalid day_type: {day_type}")


def validate_working_days(start_date: date, end_date: date) -> List[str]:
    """Validate that all dates in range are working days (not weekends).

    Args:
        start_date: Start date of range
        end_date: End date of range

    Returns:
        List of invalid date strings (empty if all valid)

    Raises:
        InvalidWorkingDay: If any date is not a working day
    """
    invalid_dates = []
    current_date = start_date

    while current_date <= end_date:
        # Check if it's a weekend (Monday=0, Sunday=6)
        if current_date.weekday() >= 5:  # Saturday=5, Sunday=6
            invalid_dates.append(current_date.isoformat())
        current_date += timedelta(days=1)

    return invalid_dates


def generate_etag(updated_at: datetime) -> str:
    """Generate ETag from updated_at timestamp.

    Args:
        updated_at: Last updated timestamp

    Returns:
        str: ETag string in format "YYYYMMDDTHHMMSSZ"
    """
    return updated_at.strftime("%Y%m%dT%H%M%SZ")


def format_last_modified(updated_at: datetime) -> str:
    """Format datetime for Last-Modified header (RFC 7231 format).

    Args:
        updated_at: Timestamp to format

    Returns:
        str: RFC 7231 formatted date string
    """
    # Convert to GMT/UTC
    if updated_at.tzinfo is None:
        # Assume UTC if no timezone info
        updated_at = updated_at.replace(tzinfo=datetime.timezone.utc)

    # Format according to RFC 7231
    return updated_at.strftime("%a, %d %b %Y %H:%M:%S GMT")


def is_working_day(check_date: date) -> bool:
    """Check if a date is a working day (not weekend).

    Args:
        check_date: Date to check

    Returns:
        bool: True if working day, False if weekend
    """
    # Monday=0, Sunday=6
    return check_date.weekday() < 5  # Working days: Mon-Fri


def get_date_range(start_date: date, end_date: date) -> List[date]:
    """Get list of all dates in a range (inclusive).

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        List of dates from start_date to end_date inclusive
    """
    if start_date > end_date:
        return []

    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def format_date_for_display(dt: date) -> str:
    """Format date for display purposes.

    Args:
        dt: Date to format

    Returns:
        str: Formatted date string
    """
    return dt.strftime("%Y-%m-%d")


def validate_leave_overlap(
    existing_leaves: List[Tuple[date, date]],
    new_start: date,
    new_end: date
) -> bool:
    """Check if new leave request overlaps with existing leaves.

    Args:
        existing_leaves: List of (start_date, end_date) tuples for existing leaves
        new_start: New leave start date
        new_end: New leave end date

    Returns:
        bool: True if overlap exists, False otherwise
    """
    for existing_start, existing_end in existing_leaves:
        # Check for overlap: new leave starts before existing ends AND new leave ends after existing starts
        if new_start <= existing_end and new_end >= existing_start:
            return True
    return False


def get_leave_status_priority(status: str) -> int:
    """Get priority order for leave status sorting.

    Args:
        status: Leave status string

    Returns:
        int: Priority number (lower = higher priority)
    """
    priorities = {
        "PENDING_MANAGER": 1,
        "PENDING_HR": 2,
        "APPROVED_MANAGER": 3,
        "APPROVED_HR": 4,
        "REJECTED_MANAGER": 5,
        "REJECTED_HR": 6,
        "CANCELLED": 7
    }
    return priorities.get(status, 999)


def get_workflow_stage_from_status(manager_status: str, hr_status: str) -> str:
    """Determine current workflow stage from status combination.

    Args:
        manager_status: Manager approval status
        hr_status: HR approval status

    Returns:
        str: Current workflow stage ("manager", "hr", "ceo", "complete", "terminated")
    """
    if manager_status == "CANCELLED" or hr_status == "CANCELLED":
        return "terminated"
    elif manager_status == "REJECTED_MANAGER" or hr_status == "REJECTED_HR":
        return "terminated"
    elif hr_status == "APPROVED_HR":
        return "complete"
    elif manager_status == "APPROVED_MANAGER":
        return "hr"
    else:
        return "manager"


def can_user_approve_at_stage(
    user_role: str,
    current_stage: str,
    applicant_role: str = None
) -> bool:
    """Check if user can approve at current workflow stage.

    Args:
        user_role: User's role (employee, manager, hr, ceo)
        current_stage: Current workflow stage (manager, hr, ceo)
        applicant_role: Role of leave applicant (for CEO approval of HR leaves)

    Returns:
        bool: True if user can approve at this stage
    """
    if current_stage == "manager":
        return user_role == "manager"
    elif current_stage == "hr":
        return user_role == "hr"
    elif current_stage == "ceo":
        return user_role == "ceo" and applicant_role == "hr"
    return False

