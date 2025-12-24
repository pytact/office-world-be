from uuid import uuid4, UUID
from datetime import datetime, date
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import (
    String,
    Date,
    DateTime,
    Numeric,
    Text,
    func,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base

if TYPE_CHECKING:
    from src.companies.models import Company
    from src.employees.models import Employee
else:
    # Import at runtime for foreign_keys reference
    from src.companies.models import Company
    from src.employees.models import Employee


class LeaveRequest(Base):
    """Leave Request model for employee time-off requests.
    
    Based on F9_db_spec.md Section 7.1 - Leave Management (F-009).
    
    Represents a request for leave submitted by an employee. The request follows 
    a role-based approval workflow with dual status tracking (manager_status and 
    hr_status) and ends in a terminal state.
    
    Field Categories:
    - Primary Key: id (UUID)
    - Foreign Keys: company_id (required tenant boundary), employee_id (applicant),
      manager_approver_id, hr_approver_id, created_by, updated_by, deleted_by
    - Business Fields: leave_type, start_date, end_date, day_type, number_of_days,
      reason, manager_status, manager_approved_at, manager_rejection_reason,
      hr_status, hr_approved_at, hr_rejection_reason
    - Soft Delete: deleted_at (timestamp-based soft delete)
    - Audit Fields: created_at, updated_at, created_by, updated_by, deleted_at, deleted_by
    """

    __tablename__ = "leave_requests"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Foreign Keys
    company_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    manager_approver_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    hr_approver_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    # Business Fields
    leave_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    day_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    number_of_days: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Manager Workflow Fields
    manager_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="PENDING_MANAGER",
    )
    manager_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    manager_rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # HR Workflow Fields
    hr_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="PENDING_HR",
    )
    hr_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    hr_rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Audit Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    deleted_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationships
    # Note: Multiple FKs to employees table require foreign_keys parameter to avoid ambiguity
    # One-way relationships (back_populates not defined in Employee model)
    company: Mapped["Company"] = relationship(
        "Company",
        foreign_keys=[company_id],
    )
    employee: Mapped["Employee"] = relationship(
        "Employee",
        foreign_keys=[employee_id],
    )
    manager_approver: Mapped["Employee"] = relationship(
        "Employee",
        foreign_keys=[manager_approver_id],
    )
    hr_approver: Mapped["Employee"] = relationship(
        "Employee",
        foreign_keys=[hr_approver_id],
    )

    # Table Constraints
    __table_args__ = (
        CheckConstraint(
            "leave_type IN ('CASUAL', 'SICK', 'PAID', 'UNPAID')",
            name="chk_leave_requests_leave_type",
        ),
        CheckConstraint(
            "day_type IN ('FULL_DAY', 'FIRST_HALF', 'SECOND_HALF')",
            name="chk_leave_requests_day_type",
        ),
        CheckConstraint(
            "end_date >= start_date",
            name="chk_leave_requests_date_range",
        ),
        CheckConstraint(
            "number_of_days >= 0",
            name="chk_leave_requests_number_of_days",
        ),
        CheckConstraint(
            "LENGTH(reason) >= 10 AND LENGTH(reason) <= 500",
            name="chk_leave_requests_reason_length",
        ),
        CheckConstraint(
            "manager_status IN ('PENDING_MANAGER', 'APPROVED_MANAGER', 'REJECTED_MANAGER', 'CANCELLED')",
            name="chk_leave_requests_manager_status",
        ),
        CheckConstraint(
            "hr_status IN ('PENDING_HR', 'APPROVED_HR', 'REJECTED_HR', 'CANCELLED')",
            name="chk_leave_requests_hr_status",
        ),
        CheckConstraint(
            "manager_rejection_reason IS NULL OR (LENGTH(manager_rejection_reason) >= 10 AND LENGTH(manager_rejection_reason) <= 500)",
            name="chk_leave_requests_manager_rejection_reason_length",
        ),
        CheckConstraint(
            "hr_rejection_reason IS NULL OR (LENGTH(hr_rejection_reason) >= 10 AND LENGTH(hr_rejection_reason) <= 500)",
            name="chk_leave_requests_hr_rejection_reason_length",
        ),
    )

    def __repr__(self) -> str:
        return f"<LeaveRequest(id={self.id}, employee_id={self.employee_id}, company_id={self.company_id}, manager_status={self.manager_status}, hr_status={self.hr_status})>"
