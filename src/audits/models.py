from uuid import uuid4, UUID
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base

if TYPE_CHECKING:
    from src.companies.models import Company
    from src.users.models import User
else:
    # Import at runtime for foreign_keys reference
    from src.companies.models import Company
    from src.users.models import User


class AuditLog(Base):
    """AuditLog model for immutable audit logging and activity history.
    
    Based on F11_db_spec.md Section 7.1 - Audit Logging & Activity History (F-011).
    
    AuditLog is an immutable, append-only record capturing meaningful actions 
    performed within the system. All audit logs are company-scoped for 
    multi-tenant isolation.
    
    Key Characteristics:
    - Immutable: Once created, cannot be updated or deleted
    - Append-only: New records only, no modifications
    - Company-scoped: All records belong to a company
    - Asynchronous: Written asynchronously without blocking business operations
    
    Field Categories:
    - Identity Fields: id (primary key)
    - Relationship Fields: company_id (required), actor_id (optional for SYSTEM actions)
    - Action Fields: action_code, table_name, record_id
    - Change Tracking: old_values, new_values (JSONB partial snapshots)
    - Metadata Fields: ip_address, user_agent, description
    - Timestamp Fields: created_at (action timestamp, immutable)
    """

    __tablename__ = "audit_logs"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Relationship Fields
    company_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    # Action Fields
    action_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    table_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    record_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
    )

    # Change Tracking Fields (JSONB partial snapshots)
    old_values: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    new_values: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Metadata Fields
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    # Timestamp Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    # Relationships
    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="audit_logs",
    )
    actor: Mapped["User | None"] = relationship(
        "User",
        back_populates="audit_logs",
    )
