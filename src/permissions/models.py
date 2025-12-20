from uuid import uuid4, UUID
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, func, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base

if TYPE_CHECKING:
    from src.users.models import User
    from src.companies.models import Company


class Role(Base):
    """Role model for permission containers.
    
    Based on F2_db_spec.md Section 7.1 - Role entity with fixed, predefined role 
    with immutable code and JSONB permissions for RBAC & Permission Engine (F-002).
    
    Stores predefined roles with permission definitions as JSONB.
    Permissions follow resource-action structure: {"resource": ["action1", "action2"]}
    """

    __tablename__ = "roles"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Role Identity Fields
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    permissions: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
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

    # Relationships
    role_assignments: Mapped[list["UserRoleAssignment"]] = relationship(
        "UserRoleAssignment",
        back_populates="role",
        cascade="all, delete-orphan",
    )

    # Table Constraints
    __table_args__ = (
        CheckConstraint(
            "code IN ('superadmin', 'ceo', 'hr', 'manager', 'employee')",
            name="chk_roles_code"
        ),
    )


class UserRoleAssignment(Base):
    """User Role Assignment model linking users to roles within company contexts.
    
    Based on F1_db_spec.md Section 7.4 - Active association linking user, role, 
    and company. Enforces one active assignment per user.
    
    Also used by F2_db_spec.md Section 7.3 - Links users to roles within company 
    contexts, providing permission evaluation context for RBAC & Permission Engine (F-002).
    """

    __tablename__ = "user_role_assignments"

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
    role_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    # Status Fields
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
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

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="role_assignments",
        foreign_keys=[user_id],
    )
    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="role_assignments",
    )
    company: Mapped["Company | None"] = relationship(
        "Company",
        back_populates="role_assignments",
    )

    # Note: Unique constraint on user_id WHERE is_active = true AND deleted_at IS NULL
    # should be created via migration as partial unique index (not in __table_args__)
