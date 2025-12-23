from uuid import uuid4, UUID
from datetime import datetime, date
from typing import TYPE_CHECKING
from sqlalchemy import (
    String,
    Boolean,
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
    from src.users.models import User
    from src.companies.models import Company
    from src.salaries.models import BankInfo, SalaryDetails, SalaryPayment
    from src.salaries.models import BankInfo


class Employee(Base):
    """Employee model for company-bound personnel records.
    
    Based on F5_db_spec.md Section 7.1 - Employee Management (F-005).
    
    Employee is a company-bound personnel record linked one-to-one with a User.
    Employee is the authoritative source of personal and professional data and
    drives access to HR-related workflows.
    
    Field Categories:
    - Immutable Fields: user_id, company_id, joining_date (cannot be changed after creation)
    - Professional Fields: job_title, department, employment_type, employment_level, 
      work_email, employment_status
    - Personal Fields: gender, marital_status, blood_group, nationality, address, 
      city, state, country, document_type, document_number
    - Separation Fields: separation_initiated_date, separation_reason, last_working_day, 
      notice_period_days (required when status is RESIGNED or TERMINATED)
    - Lifecycle Fields: is_active, is_deleted (CEO/HR only)
    - Audit Fields: created_at, updated_at, deleted_at, created_by, updated_by, deleted_by
    """

    __tablename__ = "employees"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Foreign Keys (Immutable)
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    company_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    # Professional Fields
    joining_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    employment_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    job_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    department: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    employment_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    employment_level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    work_email: Mapped[str | None] = mapped_column(
        String(254),
        nullable=True,
    )

    # Personal Fields
    gender: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    marital_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    blood_group: Mapped[str | None] = mapped_column(
        String(5),
        nullable=True,
    )
    nationality: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    address: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    document_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    document_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Separation Fields
    separation_initiated_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    separation_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    last_working_day: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    notice_period_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Lifecycle Fields
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        index=True,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        index=True,
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    deleted_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="employee",
        foreign_keys=[user_id],
    )
    company: Mapped["Company"] = relationship(
        "Company",
        foreign_keys=[company_id],
        back_populates="employees",
    )
    bank_info: Mapped["BankInfo | None"] = relationship(
        "BankInfo",
        back_populates="employee",
        uselist=False,  # One-to-one relationship
    )
    salary_details: Mapped[list["SalaryDetails"]] = relationship(
        "SalaryDetails",
        back_populates="employee",
    )
    salary_payments: Mapped[list["SalaryPayment"]] = relationship(
        "SalaryPayment",
        back_populates="employee",
    )

    # Table Constraints
    __table_args__ = (
        CheckConstraint(
            "employment_status IN ('TRAINEE', 'PROBATION', 'CONFIRMED', 'NOTICE_PERIOD', 'ON_HOLD', 'TERMINATED', 'RESIGNED')",
            name="chk_employees_employment_status",
        ),
        CheckConstraint(
            "department IN ('FRONTEND', 'BACKEND', 'FULLSTACK', 'QA', 'HR', 'DEVOPS', 'UIUX', 'PRODUCT', 'MARKETING', 'DATA', 'SUPPORT')",
            name="chk_employees_department",
        ),
        CheckConstraint(
            "employment_type IN ('FULL_TIME', 'PART_TIME', 'CONTRACT', 'FREELANCE', 'TEMPORARY')",
            name="chk_employees_employment_type",
        ),
        CheckConstraint(
            "employment_level IN ('INTERN', 'JUNIOR', 'MID', 'SENIOR', 'LEAD', 'MANAGER')",
            name="chk_employees_employment_level",
        ),
        CheckConstraint(
            "gender IN ('MALE', 'FEMALE', 'OTHER')",
            name="chk_employees_gender",
        ),
        CheckConstraint(
            "marital_status IN ('SINGLE', 'MARRIED', 'DIVORCED', 'WIDOWED', 'SEPARATED')",
            name="chk_employees_marital_status",
        ),
        CheckConstraint(
            "blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')",
            name="chk_employees_blood_group",
        ),
        CheckConstraint(
            "document_type IN ('AADHAAR', 'PAN', 'DL', 'VOTER_ID', 'PASSPORT')",
            name="chk_employees_document_type",
        ),
        CheckConstraint(
            "notice_period_days >= 0 AND notice_period_days <= 365",
            name="chk_employees_notice_period_days",
        ),
    )

    def __repr__(self) -> str:
        return f"<Employee(id={self.id}, user_id={self.user_id}, company_id={self.company_id}, work_email={self.work_email})>"
