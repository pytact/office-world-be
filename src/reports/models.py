"""SQLAlchemy models for Reports & Analytics module.

Based on F12B_api_spec.md - Export functionality for Reports & Analytics (F-012 Part B).
"""

from uuid import uuid4, UUID
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Integer, DateTime, func, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base

if TYPE_CHECKING:
    from src.users.models import User
    from src.companies.models import Company
else:
    # Import at runtime for foreign_keys reference
    from src.users.models import User
    from src.companies.models import Company


class Export(Base):
    """Export model for PDF export requests and artifacts.
    
    Based on F12B_api_spec.md Section 4.1 - Export resource.
    
    Represents an asynchronous PDF export request with a 24-hour TTL. Exports are
    generated asynchronously and stored as immutable snapshots of filtered report views.
    
    Field Categories:
    - Primary Key: id (UUID)
    - Foreign Keys: user_id (export owner), company_id (tenant boundary)
    - Business Fields: report_type, status, filters (JSON snapshot)
    - File Fields: file_path, file_size (for completed exports)
    - Error Fields: error_message (for failed exports)
    - Timestamp Fields: created_at, expires_at, completed_at, failed_at
    - Status Values: PENDING, PROCESSING, COMPLETED, FAILED, EXPIRED
    """
    
    __tablename__ = "exports"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )
    
    # Foreign Keys
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Business Fields
    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="PENDING",
        index=True,
    )
    filters: Mapped[dict] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # File Fields (for completed exports)
    file_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    file_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    
    # Error Fields (for failed exports)
    error_message: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    
    # Timestamp Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="selectin",
    )
    company: Mapped["Company"] = relationship(
        "Company",
        foreign_keys=[company_id],
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Export(id={self.id}, report_type={self.report_type}, status={self.status})>"

