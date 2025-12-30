from uuid import uuid4, UUID
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base

if TYPE_CHECKING:
    from src.permissions.models import UserRoleAssignment
    from src.employees.models import Employee
    from src.audits.models import AuditLog
else:
    # Import at runtime for foreign_keys reference
    from src.employees.models import Employee


class Company(Base):
    """Company model for tenant organizations.
    
    Based on F4_db_spec.md Section 7.1 - Platform Company Management (F-004).
    
    Company is a first-class aggregate that defines tenant boundaries, access 
    control scope, and ownership of all company-scoped data. Supports hard 
    deletion (no soft delete fields).
    
    Field Categories:
    - Immutable Fields: name, slug (cannot be changed after creation)
    - Governance Fields: is_active (SuperAdmin-only)
    - Profile Fields: description, address, city, state, country, postal_code, 
      website, logo_url (editable by CEO/HR when company is active)
    """

    __tablename__ = "companies"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Company Identity Fields (Immutable)
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # Profile Fields (Editable by CEO/HR when company is active)
    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    address: Mapped[str | None] = mapped_column(
        String(255),
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
    postal_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    website: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    logo_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    # Governance Fields (SuperAdmin-only)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
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
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationships
    role_assignments: Mapped[list["UserRoleAssignment"]] = relationship(
        "UserRoleAssignment",
        back_populates="company",
        cascade="all, delete-orphan",
    )
    employees: Mapped[list["Employee"]] = relationship(
        "Employee",
        foreign_keys="Employee.company_id",
        back_populates="company",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="company",
        passive_deletes=True,  # Let database handle RESTRICT constraint, don't modify audit_logs
    )
