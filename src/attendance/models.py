"""
Attendance Management Models

This module contains SQLAlchemy models for the Attendance Management feature (F-010).
Models follow the database design specification from F10_db_spec.md.
"""

from datetime import datetime, date
from uuid import UUID, uuid4
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, Date, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base

if TYPE_CHECKING:
    from src.employees.models import Employee
    from src.companies.models import Company
else:
    # Import at runtime for foreign_keys reference
    from src.employees.models import Employee
    from src.companies.models import Company


class Attendance(Base):
    """
    Attendance model - One-per-day attendance record for an employee.
    
    Tracks employee daily attendance with check-in/check-out times, status lifecycle,
    and automatic check-out handling. Exactly one attendance record exists per employee
    per day.
    
    Status Transitions (Linear, Irreversible):
        NOT_STARTED → CHECKED_IN → CHECKED_OUT
    
    Business Rules:
        - Exactly one attendance record per employee per day
        - Only one check-in and one check-out per day per employee
        - Check-out is mandatory (auto check-out at employee's local midnight if missed)
        - Attendance records are immutable after CHECKED_OUT status
        - Attendance is calculated using employee's local timezone
        - Day resets at employee's local midnight
    
    Table: attendance
    """

    __tablename__ = "attendance"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
        comment="Primary key, unique attendance identifier"
    )

    # Foreign Keys (Immutable after creation)
    employee_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="Attending employee ID (required, immutable)"
    )

    company_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="Owning company ID (required, immutable)"
    )

    # Business Fields
    attendance_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Local calendar date (derived from employee timezone, required)"
    )

    check_in_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Server timestamp of check-in (UTC, nullable if not checked in)"
    )

    check_out_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Server timestamp of check-out (UTC, auto-set at midnight if missed, nullable if not checked out)"
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="NOT_STARTED",
        index=True,
        comment="Attendance lifecycle state (NOT_STARTED, CHECKED_IN, CHECKED_OUT)"
    )

    worked_time: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Derived duration between check-in and check-out (e.g., '9h 29m'), read-only, nullable if not checked out"
    )

    is_auto_check_out: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Flag indicating if check-out was automatic (defaults to false)"
    )

    # Soft Delete
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Soft delete flag, defaults to false"
    )

    # Audit Fields - Created
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="Timestamp when record was created"
    )

    created_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="User ID who created the record"
    )

    # Audit Fields - Updated
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
        comment="Timestamp when record was last updated"
    )

    updated_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="User ID who last updated the record"
    )

    # Audit Fields - Deleted
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when record was soft-deleted (NULL if active)"
    )

    deleted_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="User ID who soft-deleted the record"
    )

    # Relationships
    # Relationship to Employee (many-to-one)
    employee: Mapped["Employee"] = relationship(
        "Employee",
        foreign_keys=[employee_id],
        backref="attendances",
        lazy="select"
    )
    
    # Relationship to Company (many-to-one)
    company: Mapped["Company"] = relationship(
        "Company",
        foreign_keys=[company_id],
        backref="attendances",
        lazy="select"
    )
    
    # Relationship to AttendanceLog (one-to-many)
    attendance_logs: Mapped[list["AttendanceLog"]] = relationship(
        "AttendanceLog",
        back_populates="attendance",
        cascade="all, delete-orphan",
        lazy="select"
    )

    def __repr__(self) -> str:
        """String representation of Attendance model"""
        return f"<Attendance(id={self.id}, employee_id={self.employee_id}, date={self.attendance_date}, status={self.status})>"


class AttendanceLog(Base):
    """
    AttendanceLog model - Immutable, append-only event log for attendance actions.
    
    Records every attendance action (check-in, check-out, auto check-out) with
    contextual metadata for audit and traceability. Includes both manual and automatic actions.
    
    Action Types:
        - CHECK_IN: Manual check-in by employee
        - CHECK_OUT: Manual check-out by employee
        - AUTO_CHECK_OUT: System-generated check-out at local midnight
    
    Business Rules:
        - Immutable, append-only log that records every attendance action
        - All actions are immutable once logged
        - AUTO_CHECK_OUT is system-generated at local midnight
        - Includes contextual metadata: location, IP address, device info, notes
    
    Table: attendance_logs
    """

    __tablename__ = "attendance_logs"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
        comment="Primary key, unique attendance log identifier"
    )

    # Foreign Keys
    attendance_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("attendance.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="Related attendance record ID (required)"
    )

    employee_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="Acting employee ID (required)"
    )

    # Business Fields
    action_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Attendance action type (CHECK_IN, CHECK_OUT, AUTO_CHECK_OUT)"
    )

    action_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="Server timestamp of action (UTC, required)"
    )

    location: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional location information (free text, max 500 characters, nullable)"
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP address (IPv4 or IPv6 format, max 45 characters, nullable)"
    )

    device_info: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Client device details (free text, max 255 characters, nullable)"
    )

    notes: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="System notes (free text, max 1000 characters, nullable)"
    )

    is_auto_action: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Flag indicating if action was automatic (defaults to false)"
    )

    # Soft Delete
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Soft delete flag, defaults to false"
    )

    # Audit Fields - Created
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="Timestamp when record was created"
    )

    created_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="User ID who created the record (system-generated actions may have NULL)"
    )

    # Audit Fields - Updated
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
        comment="Timestamp when record was last updated (may remain unchanged for immutable records)"
    )

    updated_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="User ID who last updated the record (may remain NULL for immutable records)"
    )

    # Audit Fields - Deleted
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when record was soft-deleted (NULL if active)"
    )

    deleted_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="User ID who soft-deleted the record"
    )

    # Relationships
    # Relationship to Attendance (many-to-one)
    attendance: Mapped["Attendance"] = relationship(
        "Attendance",
        back_populates="attendance_logs",
        lazy="select"
    )
    
    # Relationship to Employee (many-to-one)
    employee: Mapped["Employee"] = relationship(
        "Employee",
        foreign_keys=[employee_id],
        backref="attendance_logs",
        lazy="select"
    )

    def __repr__(self) -> str:
        """String representation of AttendanceLog model"""
        return f"<AttendanceLog(id={self.id}, attendance_id={self.attendance_id}, action_type={self.action_type}, action_time={self.action_time})>"
