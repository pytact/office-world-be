"""Add F9 Leave Management

Revision ID: 012_f9_leave_management
Revises: 011_f8_task_management
Create Date: 2025-01-XX 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '012_f9_leave_management'
down_revision: Union[str, None] = '011_f8_task_management'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create leave_requests table for F9 Leave Management.
    
    Based on F9_db_spec.md Section 7.1 - Leave Management (F-009).
    Creates company-scoped leave requests with dual status tracking (manager_status and hr_status)
    for role-based approval workflows. Supports soft delete for auditability.
    
    Business Rules:
    - Overlapping leave requests for the same employee are not allowed (application-level validation)
    - Leave on weekends or holidays is not allowed (application-level validation)
    - Rejection reasons are mandatory when status is REJECTED_MANAGER or REJECTED_HR (application-level)
    - Both manager_status and hr_status can be CANCELLED (by applicant)
    - Number of days is calculated from date range and day_type
    """
    
    # Create leave_requests table
    op.create_table(
        'leave_requests',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Foreign Keys
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('manager_approver_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hr_approver_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Business Fields
        sa.Column('leave_type', sa.String(length=20), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('day_type', sa.String(length=20), nullable=False),
        sa.Column('number_of_days', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        
        # Manager Workflow Fields
        sa.Column('manager_status', sa.String(length=20), nullable=False, server_default='PENDING_MANAGER'),
        sa.Column('manager_approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('manager_rejection_reason', sa.Text(), nullable=True),
        
        # HR Workflow Fields
        sa.Column('hr_status', sa.String(length=20), nullable=False, server_default='PENDING_HR'),
        sa.Column('hr_approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('hr_rejection_reason', sa.Text(), nullable=True),
        
        # Audit Fields
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Primary Key Constraint
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_leave_requests_company_id'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_leave_requests_employee_id'),
        sa.ForeignKeyConstraint(['manager_approver_id'], ['employees.id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_leave_requests_manager_approver_id'),
        sa.ForeignKeyConstraint(['hr_approver_id'], ['employees.id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_leave_requests_hr_approver_id'),
        sa.ForeignKeyConstraint(['created_by'], ['employees.id'], ondelete='SET NULL', onupdate='CASCADE', name='fk_leave_requests_created_by'),
        sa.ForeignKeyConstraint(['updated_by'], ['employees.id'], ondelete='SET NULL', onupdate='CASCADE', name='fk_leave_requests_updated_by'),
        sa.ForeignKeyConstraint(['deleted_by'], ['employees.id'], ondelete='SET NULL', onupdate='CASCADE', name='fk_leave_requests_deleted_by'),
        
        # Check Constraints
        sa.CheckConstraint(
            "leave_type IN ('CASUAL', 'SICK', 'PAID', 'UNPAID')",
            name='chk_leave_requests_leave_type'
        ),
        sa.CheckConstraint(
            "day_type IN ('FULL_DAY', 'FIRST_HALF', 'SECOND_HALF')",
            name='chk_leave_requests_day_type'
        ),
        sa.CheckConstraint(
            "end_date >= start_date",
            name='chk_leave_requests_date_range'
        ),
        sa.CheckConstraint(
            "number_of_days >= 0",
            name='chk_leave_requests_number_of_days'
        ),
        sa.CheckConstraint(
            "LENGTH(reason) >= 10 AND LENGTH(reason) <= 500",
            name='chk_leave_requests_reason_length'
        ),
        sa.CheckConstraint(
            "manager_status IN ('PENDING_MANAGER', 'APPROVED_MANAGER', 'REJECTED_MANAGER', 'CANCELLED')",
            name='chk_leave_requests_manager_status'
        ),
        sa.CheckConstraint(
            "hr_status IN ('PENDING_HR', 'APPROVED_HR', 'REJECTED_HR', 'CANCELLED')",
            name='chk_leave_requests_hr_status'
        ),
        sa.CheckConstraint(
            "manager_rejection_reason IS NULL OR (LENGTH(manager_rejection_reason) >= 10 AND LENGTH(manager_rejection_reason) <= 500)",
            name='chk_leave_requests_manager_rejection_reason_length'
        ),
        sa.CheckConstraint(
            "hr_rejection_reason IS NULL OR (LENGTH(hr_rejection_reason) >= 10 AND LENGTH(hr_rejection_reason) <= 500)",
            name='chk_leave_requests_hr_rejection_reason_length'
        ),
    )
    
    # ============================================================================
    # FOREIGN KEY INDEXES (MANDATORY - Section 9.2)
    # ============================================================================
    op.create_index('idx_leave_requests_company_id', 'leave_requests', ['company_id'], unique=False)
    op.create_index('idx_leave_requests_employee_id', 'leave_requests', ['employee_id'], unique=False)
    op.create_index('idx_leave_requests_manager_approver_id', 'leave_requests', ['manager_approver_id'], unique=False)
    op.create_index('idx_leave_requests_hr_approver_id', 'leave_requests', ['hr_approver_id'], unique=False)
    op.create_index('idx_leave_requests_created_by', 'leave_requests', ['created_by'], unique=False)
    op.create_index('idx_leave_requests_updated_by', 'leave_requests', ['updated_by'], unique=False)
    op.create_index('idx_leave_requests_deleted_by', 'leave_requests', ['deleted_by'], unique=False)
    
    # ============================================================================
    # AUDIT FIELD INDEXES (MANDATORY - Section 9.3)
    # ============================================================================
    op.create_index('idx_leave_requests_updated_at', 'leave_requests', ['updated_at'], unique=False)
    op.create_index('idx_leave_requests_created_at', 'leave_requests', ['created_at'], unique=False)
    op.create_index('idx_leave_requests_deleted_at', 'leave_requests', ['deleted_at'], unique=False)
    
    # ============================================================================
    # COMPOSITE INDEXES (Section 9.4)
    # ============================================================================
    # Index 1: Company status active (partial index)
    op.create_index(
        'idx_leave_requests_company_status_active',
        'leave_requests',
        ['company_id', 'manager_status', 'hr_status'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL')
    )
    
    # Index 2: Employee date range (partial index for overlap detection)
    op.create_index(
        'idx_leave_requests_employee_date_range',
        'leave_requests',
        ['employee_id', 'start_date', 'end_date'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL')
    )
    
    # Index 3: Manager approver pending (partial index)
    op.create_index(
        'idx_leave_requests_approver_pending',
        'leave_requests',
        ['manager_approver_id', 'manager_status'],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL AND manager_status = 'PENDING_MANAGER'")
    )
    
    # Index 4: HR approver pending (partial index)
    op.create_index(
        'idx_leave_requests_hr_approver_pending',
        'leave_requests',
        ['hr_approver_id', 'hr_status'],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL AND hr_status = 'PENDING_HR' AND manager_status = 'APPROVED_MANAGER'")
    )
    
    # Index 5: Company created_at DESC (partial index for list queries with sort)
    op.execute("""
        CREATE INDEX idx_leave_requests_company_created_at 
        ON leave_requests (company_id, created_at DESC) 
        WHERE deleted_at IS NULL
    """)
    
    # ============================================================================
    # SOFT DELETE PARTIAL INDEXES (Section 9.5)
    # ============================================================================
    op.create_index(
        'idx_leave_requests_active',
        'leave_requests',
        ['id'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL')
    )
    
    # ============================================================================
    # DATABASE TRIGGER FOR updated_at (Section 7.1, lines 285-299)
    # ============================================================================
    # Create trigger function (if not exists - may be shared across tables)
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Create trigger for leave_requests table
    op.execute("""
        CREATE TRIGGER update_leave_requests_updated_at
        BEFORE UPDATE ON leave_requests
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Drop leave_requests table and all related indexes, constraints, and trigger."""
    
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS update_leave_requests_updated_at ON leave_requests")
    # Note: Function update_updated_at_column() may be used by other tables, so we don't drop it
    
    # Drop partial indexes
    op.drop_index('idx_leave_requests_active', table_name='leave_requests')
    op.execute("DROP INDEX IF EXISTS idx_leave_requests_company_created_at")
    
    # Drop composite indexes
    op.drop_index('idx_leave_requests_hr_approver_pending', table_name='leave_requests')
    op.drop_index('idx_leave_requests_approver_pending', table_name='leave_requests')
    op.drop_index('idx_leave_requests_employee_date_range', table_name='leave_requests')
    op.drop_index('idx_leave_requests_company_status_active', table_name='leave_requests')
    
    # Drop audit field indexes
    op.drop_index('idx_leave_requests_deleted_at', table_name='leave_requests')
    op.drop_index('idx_leave_requests_created_at', table_name='leave_requests')
    op.drop_index('idx_leave_requests_updated_at', table_name='leave_requests')
    
    # Drop foreign key indexes
    op.drop_index('idx_leave_requests_deleted_by', table_name='leave_requests')
    op.drop_index('idx_leave_requests_updated_by', table_name='leave_requests')
    op.drop_index('idx_leave_requests_created_by', table_name='leave_requests')
    op.drop_index('idx_leave_requests_hr_approver_id', table_name='leave_requests')
    op.drop_index('idx_leave_requests_manager_approver_id', table_name='leave_requests')
    op.drop_index('idx_leave_requests_employee_id', table_name='leave_requests')
    op.drop_index('idx_leave_requests_company_id', table_name='leave_requests')
    
    # Drop table (this will also drop all constraints)
    op.drop_table('leave_requests')

