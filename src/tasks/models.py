from uuid import uuid4, UUID
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, func, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base

if TYPE_CHECKING:
    from src.companies.models import Company
    from src.employees.models import Employee
    from src.projects.models import Project
    from src.users.models import User
else:
    # Import at runtime for foreign_keys reference
    from src.companies.models import Company
    from src.employees.models import Employee
    from src.projects.models import Project
    from src.users.models import User


class Task(Base):
    """Task model for atomic units of work within a company.
    
    Based on F8_db_spec.md Section 7.1 - Task Management (F-008).
    
    Represents a single unit of work. Tasks are company-scoped, have one immutable
    owner, may have multiple assignees, and optionally belong to a project. All
    permissions and visibility are task-based.
    
    Field Categories:
    - Primary Key: id (UUID)
    - Foreign Keys: company_id (required tenant boundary), owner_id (immutable), 
      project_id (optional project linkage)
    - Business Fields: name (required), description (optional), status (TODO, 
      IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED)
    - Hard Delete: is_deleted (BOOLEAN marker, true = deleted, false = active)
    - Audit Fields: created_at, updated_at, created_by, updated_by
    """

    __tablename__ = "tasks"

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
        ForeignKey("companies.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    # Business Fields
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(5000),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="TODO",
    )

    # Hard Delete Field
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

    # Relationships
    company: Mapped["Company"] = relationship(
        "Company",
        foreign_keys=[company_id],
    )
    owner: Mapped["Employee"] = relationship(
        "Employee",
        foreign_keys=[owner_id],
    )
    project: Mapped["Project | None"] = relationship(
        "Project",
        foreign_keys=[project_id],
    )
    assignments: Mapped[list["TaskAssignment"]] = relationship(
        "TaskAssignment",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    # Table Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('TODO', 'IN_PROGRESS', 'HALT', 'REVIEW', 'DONE', 'CANCELLED')",
            name="chk_tasks_status",
        ),
    )


class TaskAssignment(Base):
    """TaskAssignment model for task-employee assignments with permissions.
    
    Based on F8_db_spec.md Section 7.2 - Task Assignment (F-008).
    
    Represents assignment of an employee to a task with a specific permission level.
    This junction table enables many-to-many relationship between employees and tasks,
    with granular permission control (VIEWER, EDITOR).
    
    Field Categories:
    - Primary Key: id (UUID)
    - Foreign Keys: task_id (required), employee_id (required)
    - Business Fields: permission (VIEWER, EDITOR)
    - Audit Fields: created_at, updated_at, created_by, updated_by
    - Unique Constraint: (task_id, employee_id) prevents duplicate assignments
    """

    __tablename__ = "task_assignments"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Foreign Keys
    task_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    # Business Fields
    permission: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
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

    # Relationships
    task: Mapped["Task"] = relationship(
        "Task",
        foreign_keys=[task_id],
        back_populates="assignments",
    )
    employee: Mapped["Employee"] = relationship(
        "Employee",
        foreign_keys=[employee_id],
    )

    # Table Constraints
    __table_args__ = (
        CheckConstraint(
            "permission IN ('VIEWER', 'EDITOR')",
            name="chk_task_assignments_permission",
        ),
        UniqueConstraint(
            "task_id",
            "employee_id",
            name="uq_task_assignments_task_employee",
        ),
    )
