from uuid import uuid4, UUID
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, Text, func, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base

if TYPE_CHECKING:
    from src.users.models import User
    from src.companies.models import Company


class Notification(Base):
    """Notification model for user notifications.
    
    Based on F3_db_spec.md Section 7.2.1 - Notification entity with email-first 
    and in-app delivery channels, polymorphic relationships to leaves and tasks,
    read/unread state management, and complete audit trail.
    
    Supports:
    - Multi-tenant company scoping
    - User-scoped notification visibility
    - Polymorphic relationships to leaves and tasks
    - Read/unread state for in-app notifications
    - Soft-delete support
    """

    __tablename__ = "notifications"

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
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    related_record_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
    )
    related_table: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="sent",
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
    deleted_by: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    # Table Constraints
    __table_args__ = (
        # Column-level CHECK constraints (defined inline in mapped_column)
        # Note: SQLAlchemy doesn't support inline CHECK constraints in mapped_column,
        # so we define them as table-level constraints
        
        # CHECK constraint for type field
        CheckConstraint(
            "type IN ('leave_request', 'leave_approval', 'leave_rejection', 'leave_manager_approval', "
            "'task_assignment', 'task_permission_change', 'task_status_change', "
            "'user_activation', 'user_deactivation')",
            name="chk_notifications_type"
        ),
        # CHECK constraint for channel field
        CheckConstraint(
            "channel IN ('email', 'in_app')",
            name="chk_notifications_channel"
        ),
        # CHECK constraint for status field
        CheckConstraint(
            "status IN ('sent', 'failed')",
            name="chk_notifications_status"
        ),
        # CHECK constraint for related_table field
        CheckConstraint(
            "(related_table IS NULL) OR (related_table IN ('leaves', 'tasks'))",
            name="chk_notifications_related_table"
        ),
        # Table-level CHECK constraint: related_record_id and related_table must both be NULL or both be NOT NULL
        CheckConstraint(
            "(related_record_id IS NULL AND related_table IS NULL) OR "
            "(related_record_id IS NOT NULL AND related_table IS NOT NULL)",
            name="chk_notifications_related_fields"
        ),
        # Table-level CHECK constraint: read_at is only applicable when channel = 'in_app' and is_read = true
        CheckConstraint(
            "(read_at IS NULL) OR (channel = 'in_app' AND is_read = true)",
            name="chk_notifications_read_at"
        ),
    )

