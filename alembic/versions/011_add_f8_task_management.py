"""Add F8 Task Management

Revision ID: 011_f8_task_management
Revises: 010_remove_active_status
Create Date: 2025-01-XX 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '011_f8_task_management'
down_revision: Union[str, None] = '010_remove_active_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tasks and task_assignments tables for F8 Task Management.
    
    Based on F8_db_spec.md Section 7 - Task Management (F-008).
    Creates company-scoped tasks with owner (always the creator) and optional project linkage,
    plus task assignments for employee-task relationships with permissions (VIEWER/EDITOR).
    
    Business Rules:
    - owner_id is always the creator of the task (immutable, set at creation)
    - Tasks can be assigned to employees via task_assignments table with VIEWER or EDITOR permissions
    - Owner should not be in task_assignments (they already have full access as owner)
    """
    
    # Create tasks table
    op.create_table(
        'tasks',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Foreign Keys
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),  # Always the creator (immutable)
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Business Fields
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=5000), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='TODO'),
        
        # Hard Delete Field
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        
        # Audit Fields
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Primary Key Constraint
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['employees.id'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='RESTRICT', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        
        # Check Constraints
        sa.CheckConstraint(
            "status IN ('TODO', 'IN_PROGRESS', 'HALT', 'REVIEW', 'DONE', 'CANCELLED')",
            name='chk_tasks_status'
        ),
    )
    
    # Indexes for tasks
    op.create_index(op.f('ix_tasks_id'), 'tasks', ['id'], unique=False)
    op.create_index(op.f('ix_tasks_company_id'), 'tasks', ['company_id'], unique=False)
    op.create_index(op.f('ix_tasks_owner_id'), 'tasks', ['owner_id'], unique=False)
    op.create_index(op.f('ix_tasks_project_id'), 'tasks', ['project_id'], unique=False)
    op.create_index(op.f('ix_tasks_updated_at'), 'tasks', ['updated_at'], unique=False)
    
    # Create task_assignments table
    # Used to assign tasks to employees with VIEWER or EDITOR permissions.
    # Note: Owner should not be assigned here (they already have full access as owner).
    op.create_table(
        'task_assignments',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Foreign Keys
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),  # Employee assigned to task (not owner)
        
        # Business Fields
        sa.Column('permission', sa.String(length=20), nullable=False),  # VIEWER or EDITOR
        
        # Audit Fields
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Primary Key Constraint
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        
        # Check Constraints
        sa.CheckConstraint(
            "permission IN ('VIEWER', 'EDITOR')",
            name='chk_task_assignments_permission'
        ),
        
        # Unique Constraint
        sa.UniqueConstraint('task_id', 'employee_id', name='uq_task_assignments_task_employee'),
    )
    
    # Indexes for task_assignments
    op.create_index(op.f('ix_task_assignments_id'), 'task_assignments', ['id'], unique=False)
    op.create_index(op.f('ix_task_assignments_task_id'), 'task_assignments', ['task_id'], unique=False)
    op.create_index(op.f('ix_task_assignments_employee_id'), 'task_assignments', ['employee_id'], unique=False)
    op.create_index(op.f('ix_task_assignments_updated_at'), 'task_assignments', ['updated_at'], unique=False)


def downgrade() -> None:
    """Drop tasks and task_assignments tables."""
    # Drop task_assignments indexes
    op.drop_index(op.f('ix_task_assignments_updated_at'), table_name='task_assignments')
    op.drop_index(op.f('ix_task_assignments_employee_id'), table_name='task_assignments')
    op.drop_index(op.f('ix_task_assignments_task_id'), table_name='task_assignments')
    op.drop_index(op.f('ix_task_assignments_id'), table_name='task_assignments')
    
    # Drop task_assignments table
    op.drop_table('task_assignments')
    
    # Drop tasks indexes
    op.drop_index(op.f('ix_tasks_updated_at'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_project_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_owner_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_company_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_id'), table_name='tasks')
    
    # Drop tasks table
    op.drop_table('tasks')

