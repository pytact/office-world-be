from uuid import uuid4, UUID
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, func, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base

if TYPE_CHECKING:
    from src.companies.models import Company
    from src.users.models import User
    from src.tasks.models import Task
else:
    # Import at runtime for foreign_keys reference
    from src.companies.models import Company
    from src.users.models import User


class Project(Base):
    """Project model for company-scoped project containers.
    
    Based on F7_db_spec.md Section 7.1 - Project Management (F-007).
    
    Represents a company-scoped container used to organize tasks. Projects do not 
    manage membership, permissions, or ownership. Access and visibility are derived 
    entirely from task associations.
    
    Field Categories:
    - Primary Key: id (UUID)
    - Foreign Keys: company_id (required tenant boundary)
    - Business Fields: name (company-unique, case-insensitive), status (ACTIVE, INACTIVE, COMPLETED)
    - Soft Delete: deleted_at (timestamp-based soft delete)
    - Audit Fields: created_at, updated_at, created_by, updated_by, deleted_by
    """

    __tablename__ = "projects"

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

    # Business Fields
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="ACTIVE",
    )

    # Soft Delete Field
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    deleted_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )

    # Relationships
    company: Mapped["Company"] = relationship(
        "Company",
        foreign_keys=[company_id],
    )

    # Table Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'COMPLETED')",
            name="chk_projects_status",
        ),
    )
