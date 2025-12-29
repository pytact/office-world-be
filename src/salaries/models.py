from uuid import uuid4, UUID
from datetime import datetime, date
from typing import TYPE_CHECKING, Optional
from decimal import Decimal
from sqlalchemy import (
    String,
    Numeric,
    Integer,
    Date,
    DateTime,
    func,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base

if TYPE_CHECKING:
    from src.employees.models import Employee


class BankInfo(Base):
    """Bank information model for employee bank account details.
    
    Based on F6_db_spec.md Section 7.1 - Bank Information Management (F-006).
    
    Represents an employee's bank account used for salary payments. Only one active
    bank account exists per employee at any time. BankInfo is never hard-deleted
    (supports soft delete only).
    
    Field Categories:
    - Primary Key: id (UUID)
    - Foreign Keys: employee_id (references employees table)
    - Business Fields: bank_name, branch, account_number, ifsc_code
    - Audit Fields: created_at, updated_at, deleted_at, created_by, updated_by, deleted_by
    
    Business Rules:
    - Only one active bank_info per employee (enforced by unique constraint)
    - BankInfo is never hard-deleted (soft delete only)
    - Updates affect future payments only (application logic)
    """

    __tablename__ = "bank_info"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Foreign Keys
    employee_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    # Business Fields
    bank_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Bank identifier (ENUM: HDFC, ICICI, SBI, AXIS, KOTAK, PNB, BOB)",
    )
    branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bank branch name (min 1 character, max 255 characters)",
    )
    account_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Bank account number (min 8 characters, max 20 characters, alphanumeric only, sensitive data - encrypted at application level)",
    )
    ifsc_code: Mapped[str] = mapped_column(
        String(11),
        nullable=False,
        comment="Bank IFSC code (11 characters, format: 4 uppercase letters + 0 + 6 alphanumeric, sensitive data - encrypted at application level)",
    )

    # Audit Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when record was created (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when record was last updated (UTC)",
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Timestamp when record was soft-deleted (UTC), NULL if active",
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        default=None,
        comment="User ID who created the record (CEO/HR)",
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        default=None,
        comment="User ID who last updated the record (CEO/HR)",
    )
    deleted_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        default=None,
        comment="User ID who soft-deleted the record (CEO/HR)",
    )

    # Relationships
    employee: Mapped["Employee"] = relationship(
        "Employee",
        back_populates="bank_info",
        foreign_keys=[employee_id],
    )

    # Table Constraints
    __table_args__ = (
        CheckConstraint(
            "bank_name IN ('HDFC', 'ICICI', 'SBI', 'AXIS', 'KOTAK', 'PNB', 'BOB')",
            name="chk_bank_info_bank_name",
        ),
        CheckConstraint(
            "LENGTH(branch) >= 1",
            name="chk_bank_info_branch_length",
        ),
        CheckConstraint(
            "LENGTH(account_number) >= 8 AND LENGTH(account_number) <= 20 AND account_number ~ '^[A-Za-z0-9]+$'",
            name="chk_bank_info_account_number",
        ),
        CheckConstraint(
            "LENGTH(ifsc_code) = 11 AND ifsc_code ~ '^[A-Z]{4}0[A-Z0-9]{6}$'",
            name="chk_bank_info_ifsc_code",
        ),
    )

    def __repr__(self) -> str:
        return f"<BankInfo(id={self.id}, employee_id={self.employee_id}, bank_name={self.bank_name})>"


class SalaryDetails(Base):
    """Salary details model for time-based salary configurations.
    
    Based on F6_db_spec.md Section 7.2 - Salary Configuration (F-006).
    
    Defines the monthly gross salary configuration for an employee over a specific
    effective period. Only one active configuration is allowed per employee at any time.
    
    Field Categories:
    - Primary Key: id (UUID)
    - Foreign Keys: employee_id (references employees table)
    - Business Fields: amount, currency, payment_frequency, effective_from, effective_to
    - Audit Fields: created_at, updated_at, deleted_at, created_by, updated_by, deleted_by
    
    Business Rules:
    - Only one active SalaryDetails per employee (effective_to IS NULL, enforced by application logic)
    - No overlapping effective periods for same employee (enforced by unique constraint + application logic)
    - Updating salary auto-closes previous record (application logic sets effective_to)
    """

    __tablename__ = "salary_details"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Foreign Keys
    employee_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    # Business Fields
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Monthly gross salary amount (must be greater than 0 and less than or equal to 999999999.99)",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Salary currency (ENUM: INR, USD, EUR, GBP, AUD, CAD)",
    )
    payment_frequency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Payment cadence (ENUM: MONTHLY, BI_WEEKLY, WEEKLY)",
    )
    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Start date of salary configuration (inclusive), must be today or future date",
    )
    effective_to: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        default=None,
        comment="End date of salary configuration (inclusive), NULL for active records, required for historical records",
    )

    # Audit Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when record was created (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when record was last updated (UTC)",
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Timestamp when record was soft-deleted (UTC), NULL if active",
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        default=None,
        comment="User ID who created the record (CEO/HR)",
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        default=None,
        comment="User ID who last updated the record (CEO/HR)",
    )
    deleted_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        default=None,
        comment="User ID who soft-deleted the record (CEO/HR)",
    )

    # Relationships
    employee: Mapped["Employee"] = relationship(
        "Employee",
        back_populates="salary_details",
        foreign_keys=[employee_id],
    )
    salary_history: Mapped[list["SalaryHistory"]] = relationship(
        "SalaryHistory",
        back_populates="salary_details",
    )

    # Table Constraints
    __table_args__ = (
        CheckConstraint(
            "amount > 0 AND amount <= 999999999.99",
            name="chk_salary_details_amount",
        ),
        CheckConstraint(
            "currency IN ('INR', 'USD', 'EUR', 'GBP', 'AUD', 'CAD')",
            name="chk_salary_details_currency",
        ),
        CheckConstraint(
            "payment_frequency IN ('MONTHLY', 'BI_WEEKLY', 'WEEKLY')",
            name="chk_salary_details_payment_frequency",
        ),
        CheckConstraint(
            "(effective_to IS NULL AND effective_from >= CURRENT_DATE) OR (effective_to IS NOT NULL)",
            name="chk_salary_details_effective_from",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="chk_salary_details_effective_to",
        ),
    )

    def __repr__(self) -> str:
        return f"<SalaryDetails(id={self.id}, employee_id={self.employee_id}, amount={self.amount}, currency={self.currency})>"


class SalaryPayment(Base):
    """Salary payment model for monthly payment execution records.
    
    Based on F6_db_spec.md Section 7.3 - Salary Payment Records (F-006).
    
    Represents a completed salary payment for a specific employee, month, and year.
    Records are immutable and append-only (cannot be updated or deleted).
    
    Field Categories:
    - Primary Key: id (UUID)
    - Foreign Keys: employee_id (references employees table)
    - Business Fields: amount, currency, month, year, paid_on, payment_method, slip_url
    - Audit Fields: created_at, deleted_at, created_by, deleted_by
    
    Business Rules:
    - Only one payment per employee per month/year (enforced by unique constraint)
    - Records are immutable (no UPDATE operations, application-level enforcement)
    - Records should not be soft-deleted (application-level enforcement, deleted_at should remain NULL)
    - Amount and currency derived from active SalaryDetails at payment time
    
    Note: This model does not include `updated_at` and `updated_by` fields because
    records are immutable (append-only).
    """

    __tablename__ = "salary_payments"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Foreign Keys
    employee_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    # Business Fields
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Paid amount, derived from active SalaryDetails at payment time (must be greater than 0)",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Payment currency, derived from active SalaryDetails (ENUM: INR, USD, EUR, GBP, AUD, CAD)",
    )
    month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Salary month (1-12)",
    )
    year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Salary year (YYYY, 2000-9999)",
    )
    paid_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Payment execution date (UTC)",
    )
    payment_method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Mode of payment (ENUM: BANK_TRANSFER, UPI, CHEQUE, CASH)",
    )
    slip_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        default=None,
        comment="Salary slip file location/URL, optional (generated async)",
    )

    # Audit Fields (Immutable records - no updated_at/updated_by)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when record was created (UTC)",
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Timestamp when record was soft-deleted (UTC), NULL if active (immutable records should not be soft-deleted, but field exists for consistency)",
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        default=None,
        comment="User ID who created the record (CEO/HR)",
    )
    deleted_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        default=None,
        comment="User ID who soft-deleted the record (should remain NULL for immutable records)",
    )

    # Relationships
    employee: Mapped["Employee"] = relationship(
        "Employee",
        back_populates="salary_payments",
        foreign_keys=[employee_id],
    )

    # Table Constraints
    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="chk_salary_payments_amount",
        ),
        CheckConstraint(
            "currency IN ('INR', 'USD', 'EUR', 'GBP', 'AUD', 'CAD')",
            name="chk_salary_payments_currency",
        ),
        CheckConstraint(
            "month >= 1 AND month <= 12",
            name="chk_salary_payments_month",
        ),
        CheckConstraint(
            "year >= 2000 AND year <= 9999",
            name="chk_salary_payments_year",
        ),
        CheckConstraint(
            "payment_method IN ('BANK_TRANSFER', 'UPI', 'CHEQUE', 'CASH')",
            name="chk_salary_payments_payment_method",
        ),
    )

    def __repr__(self) -> str:
        return f"<SalaryPayment(id={self.id}, employee_id={self.employee_id}, month={self.month}, year={self.year}, amount={self.amount})>"


class SalaryHistory(Base):
    """Salary history model for immutable audit log of salary configuration changes.
    
    Based on F6_db_spec.md Section 7.4 - Salary History (F-006).
    
    Immutable audit record capturing changes to SalaryDetails over time. Created
    automatically when SalaryDetails is updated.
    
    Field Categories:
    - Primary Key: id (UUID)
    - Foreign Keys: salary_details_id (references salary_details table)
    - Business Fields: previous_amount, new_amount, effective_from, changed_by
    - Audit Fields: created_at
    
    Business Rules:
    - Records are immutable (no UPDATE/DELETE operations, application-level enforcement)
    - Created automatically when SalaryDetails is updated (application logic)
    - Not created for first salary configuration (previous_amount will be NULL)
    - Records should never be soft-deleted (preserve audit trail)
    
    Note: This model does not include `updated_at`, `updated_by`, `deleted_at`, or
    `deleted_by` fields because records are immutable (append-only audit log).
    """

    __tablename__ = "salary_history"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Foreign Keys
    salary_details_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("salary_details.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Business Fields
    previous_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        default=None,
        comment="Previous salary amount (before change), NULL for first salary configuration",
    )
    new_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="New salary amount (after change), must be greater than 0",
    )
    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Effective date of new salary configuration (inclusive)",
    )
    changed_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        default=None,
        comment="User ID who made the salary change (CEO/HR)",
    )

    # Audit Fields (Immutable audit log - only created_at)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when salary change was recorded (UTC)",
    )

    # Relationships
    salary_details: Mapped["SalaryDetails"] = relationship(
        "SalaryDetails",
        back_populates="salary_history",
        foreign_keys=[salary_details_id],
    )

    # Table Constraints
    __table_args__ = (
        CheckConstraint(
            "new_amount > 0",
            name="chk_salary_history_new_amount",
        ),
    )

    def __repr__(self) -> str:
        return f"<SalaryHistory(id={self.id}, salary_details_id={self.salary_details_id}, previous_amount={self.previous_amount}, new_amount={self.new_amount})>"
