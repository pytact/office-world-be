"""Add F10 Attendance Management

Revision ID: 015_f10_attendance
Revises: 014_f3_notifications
Create Date: 2025-01-XX 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '015_f10_attendance'
down_revision: Union[str, None] = '014_f3_notifications'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create attendance and attendance_logs tables for F10 Attendance Management.
    
    Based on F10_db_spec.md Section 7.1 - Attendance Management (F-010).
    Creates company-scoped attendance tracking with check-in/check-out times,
    status lifecycle, and immutable event logs for audit purposes.
    
    Business Rules:
    - Exactly one attendance record per employee per day
    - Status transitions: NOT_STARTED → CHECKED_IN → CHECKED_OUT (linear, irreversible)
    - Attendance records are immutable after CHECKED_OUT status
    - Check-out is mandatory (auto check-out at employee's local midnight if missed)
    - Attendance is calculated using employee's local timezone
    """
    
    # Create attendance table
    op.create_table(
        'attendance',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Foreign Keys (Immutable after creation)
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Business Fields
        sa.Column('attendance_date', sa.Date(), nullable=False),
        sa.Column('check_in_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('check_out_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='NOT_STARTED'),
        sa.Column('worked_time', sa.String(length=20), nullable=True),
        sa.Column('is_auto_check_out', sa.Boolean(), nullable=False, server_default='false'),
        
        # Soft Delete
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        
        # Audit Fields - Created
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Audit Fields - Updated
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Audit Fields - Deleted
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Primary Key Constraint
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_attendance_employee_id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_attendance_company_id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE', name='fk_attendance_created_by'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE', name='fk_attendance_updated_by'),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE', name='fk_attendance_deleted_by'),
        
        # Check Constraints
        sa.CheckConstraint(
            "status IN ('NOT_STARTED', 'CHECKED_IN', 'CHECKED_OUT')",
            name='chk_attendance_status'
        ),
    )
    
    # Create indexes for attendance table
    op.create_index('ix_attendance_id', 'attendance', ['id'], unique=False)
    op.create_index('ix_attendance_employee_id', 'attendance', ['employee_id'], unique=False)
    op.create_index('ix_attendance_company_id', 'attendance', ['company_id'], unique=False)
    op.create_index('ix_attendance_attendance_date', 'attendance', ['attendance_date'], unique=False)
    op.create_index('ix_attendance_check_in_time', 'attendance', ['check_in_time'], unique=False)
    op.create_index('ix_attendance_check_out_time', 'attendance', ['check_out_time'], unique=False)
    op.create_index('ix_attendance_status', 'attendance', ['status'], unique=False)
    op.create_index('ix_attendance_is_auto_check_out', 'attendance', ['is_auto_check_out'], unique=False)
    op.create_index('ix_attendance_is_deleted', 'attendance', ['is_deleted'], unique=False)
    op.create_index('ix_attendance_created_at', 'attendance', ['created_at'], unique=False)
    op.create_index('ix_attendance_created_by', 'attendance', ['created_by'], unique=False)
    op.create_index('ix_attendance_updated_by', 'attendance', ['updated_by'], unique=False)
    op.create_index('ix_attendance_deleted_by', 'attendance', ['deleted_by'], unique=False)
    
    # Create unique constraint: one attendance record per employee per day (only for non-deleted records)
    op.create_index(
        'uq_attendance_employee_date',
        'attendance',
        ['employee_id', 'attendance_date'],
        unique=True,
        postgresql_where=sa.text('is_deleted = false')
    )
    
    # Create attendance_logs table
    op.create_table(
        'attendance_logs',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Foreign Keys
        sa.Column('attendance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Business Fields
        sa.Column('action_type', sa.String(length=20), nullable=False),
        sa.Column('action_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('location', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('device_info', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.String(length=1000), nullable=True),
        sa.Column('is_auto_action', sa.Boolean(), nullable=False, server_default='false'),
        
        # Soft Delete
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        
        # Audit Fields - Created
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Audit Fields - Updated
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Audit Fields - Deleted
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Primary Key Constraint
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['attendance_id'], ['attendance.id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_attendance_logs_attendance_id'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_attendance_logs_employee_id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE', name='fk_attendance_logs_created_by'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE', name='fk_attendance_logs_updated_by'),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE', name='fk_attendance_logs_deleted_by'),
        
        # Check Constraints
        sa.CheckConstraint(
            "action_type IN ('CHECK_IN', 'CHECK_OUT', 'AUTO_CHECK_OUT')",
            name='chk_attendance_logs_action_type'
        ),
    )
    
    # Create indexes for attendance_logs table
    op.create_index('ix_attendance_logs_id', 'attendance_logs', ['id'], unique=False)
    op.create_index('ix_attendance_logs_attendance_id', 'attendance_logs', ['attendance_id'], unique=False)
    op.create_index('ix_attendance_logs_employee_id', 'attendance_logs', ['employee_id'], unique=False)
    op.create_index('ix_attendance_logs_action_type', 'attendance_logs', ['action_type'], unique=False)
    op.create_index('ix_attendance_logs_action_time', 'attendance_logs', ['action_time'], unique=False)
    op.create_index('ix_attendance_logs_is_auto_action', 'attendance_logs', ['is_auto_action'], unique=False)
    op.create_index('ix_attendance_logs_is_deleted', 'attendance_logs', ['is_deleted'], unique=False)
    op.create_index('ix_attendance_logs_created_at', 'attendance_logs', ['created_at'], unique=False)
    op.create_index('ix_attendance_logs_created_by', 'attendance_logs', ['created_by'], unique=False)
    op.create_index('ix_attendance_logs_updated_by', 'attendance_logs', ['updated_by'], unique=False)
    op.create_index('ix_attendance_logs_deleted_by', 'attendance_logs', ['deleted_by'], unique=False)


def downgrade() -> None:
    """Drop attendance and attendance_logs tables."""
    op.drop_table('attendance_logs')
    op.drop_table('attendance')

