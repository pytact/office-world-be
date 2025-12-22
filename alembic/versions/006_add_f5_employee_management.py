"""Add F5 Employee Management

Revision ID: 006_f5_employee_management
Revises: 005_f4_company_fields
Create Date: 2025-01-20 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006_f5_employee_management'
down_revision: Union[str, None] = '005_f4_company_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create employees table for F5 Employee Management.
    
    Based on F5_db_spec.md Section 7.1 - Employee Management (F-005).
    Creates company-bound personnel records linked one-to-one with User.
    """
    # Create employees table
    op.create_table(
        'employees',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Foreign Keys (Immutable)
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Professional Fields
        sa.Column('joining_date', sa.Date(), nullable=False),
        sa.Column('employment_status', sa.String(length=20), nullable=False),
        sa.Column('job_title', sa.String(length=255), nullable=True),
        sa.Column('department', sa.String(length=20), nullable=True),
        sa.Column('employment_type', sa.String(length=20), nullable=True),
        sa.Column('employment_level', sa.String(length=20), nullable=True),
        sa.Column('work_email', sa.String(length=254), nullable=True),
        
        # Personal Fields
        sa.Column('gender', sa.String(length=10), nullable=True),
        sa.Column('marital_status', sa.String(length=20), nullable=True),
        sa.Column('blood_group', sa.String(length=5), nullable=True),
        sa.Column('nationality', sa.String(length=100), nullable=True),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('document_type', sa.String(length=20), nullable=True),
        sa.Column('document_number', sa.String(length=50), nullable=True),
        
        # Separation Fields
        sa.Column('separation_initiated_date', sa.Date(), nullable=True),
        sa.Column('separation_reason', sa.String(length=500), nullable=True),
        sa.Column('last_working_day', sa.Date(), nullable=True),
        sa.Column('notice_period_days', sa.Integer(), nullable=True),
        
        # Lifecycle Fields
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        
        # Audit Fields
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Primary Key Constraint
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='RESTRICT', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        
        # CHECK Constraints for ENUMs
        sa.CheckConstraint(
            "employment_status IN ('TRAINEE', 'PROBATION', 'CONFIRMED', 'NOTICE_PERIOD', 'ACTIVE', 'ON_HOLD', 'TERMINATED', 'RESIGNED')",
            name='chk_employees_employment_status'
        ),
        sa.CheckConstraint(
            "department IN ('FRONTEND', 'BACKEND', 'FULLSTACK', 'QA', 'HR', 'DEVOPS', 'UIUX', 'PRODUCT', 'MARKETING', 'DATA', 'SUPPORT')",
            name='chk_employees_department'
        ),
        sa.CheckConstraint(
            "employment_type IN ('FULL_TIME', 'PART_TIME', 'CONTRACT', 'FREELANCE', 'TEMPORARY')",
            name='chk_employees_employment_type'
        ),
        sa.CheckConstraint(
            "employment_level IN ('INTERN', 'JUNIOR', 'MID', 'SENIOR', 'LEAD', 'MANAGER')",
            name='chk_employees_employment_level'
        ),
        sa.CheckConstraint(
            "gender IN ('MALE', 'FEMALE', 'OTHER')",
            name='chk_employees_gender'
        ),
        sa.CheckConstraint(
            "marital_status IN ('SINGLE', 'MARRIED', 'DIVORCED', 'WIDOWED', 'SEPARATED')",
            name='chk_employees_marital_status'
        ),
        sa.CheckConstraint(
            "blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')",
            name='chk_employees_blood_group'
        ),
        sa.CheckConstraint(
            "document_type IN ('AADHAAR', 'PAN', 'DL', 'VOTER_ID', 'PASSPORT')",
            name='chk_employees_document_type'
        ),
        sa.CheckConstraint(
            "notice_period_days >= 0 AND notice_period_days <= 365",
            name='chk_employees_notice_period_days'
        ),
        sa.CheckConstraint(
            "is_active IN (true, false)",
            name='chk_employees_is_active'
        ),
        sa.CheckConstraint(
            "is_deleted IN (true, false)",
            name='chk_employees_is_deleted'
        ),
    )
    
    # Primary Key Index (automatically created, but explicit for clarity)
    op.create_index(op.f('ix_employees_id'), 'employees', ['id'], unique=False)
    
    # Foreign Key Indexes (CRITICAL for JOIN performance)
    op.create_index(op.f('ix_employees_user_id'), 'employees', ['user_id'], unique=False)
    op.create_index(op.f('ix_employees_company_id'), 'employees', ['company_id'], unique=False)
    op.create_index(op.f('ix_employees_created_by'), 'employees', ['created_by'], unique=False)
    op.create_index(op.f('ix_employees_updated_by'), 'employees', ['updated_by'], unique=False)
    op.create_index(op.f('ix_employees_deleted_by'), 'employees', ['deleted_by'], unique=False)
    
    # Unique Constraint Indexes
    op.create_unique_constraint('uq_employees_user_id', 'employees', ['user_id'])
    # Note: UNIQUE constraint on (company_id, LOWER(work_email)) will be created separately
    # as it requires a functional index with WHERE clause
    
    # Audit Field Indexes
    op.create_index(op.f('ix_employees_updated_at'), 'employees', ['updated_at'], unique=False)
    
    # Query Optimization Indexes
    op.create_index(op.f('ix_employees_is_deleted'), 'employees', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_employees_is_active'), 'employees', ['is_active'], unique=False)
    op.create_index(op.f('ix_employees_employment_status'), 'employees', ['employment_status'], unique=False)
    op.create_index(op.f('ix_employees_department'), 'employees', ['department'], unique=False)
    # Created_at index with DESC ordering for "newest first" queries (per spec Section 9.5)
    op.execute("""
        CREATE INDEX idx_employees_created_at 
        ON employees (created_at DESC)
    """)
    
    # Composite Indexes (Partial indexes for better performance)
    op.create_index(
        'idx_employees_company_active',
        'employees',
        ['company_id', 'is_deleted'],
        unique=False,
        postgresql_where=sa.text("is_deleted = false")
    )
    op.create_index(
        'idx_employees_company_status',
        'employees',
        ['company_id', 'employment_status'],
        unique=False,
        postgresql_where=sa.text("is_deleted = false")
    )
    op.create_index(
        'idx_employees_company_department',
        'employees',
        ['company_id', 'department'],
        unique=False,
        postgresql_where=sa.text("is_deleted = false")
    )
    op.create_index(
        'idx_employees_status_active',
        'employees',
        ['employment_status', 'is_active'],
        unique=False,
        postgresql_where=sa.text("is_deleted = false")
    )
    
    # Soft Delete Indexes (Partial indexes)
    op.create_index(
        'idx_employees_active',
        'employees',
        ['id'],
        unique=False,
        postgresql_where=sa.text("is_deleted = false")
    )
    # Company active list index with DESC ordering for created_at (per spec Section 9.7)
    op.execute("""
        CREATE INDEX idx_employees_company_active_list 
        ON employees (company_id, created_at DESC) 
        WHERE is_deleted = false
    """)
    
    # Unique constraint on (company_id, LOWER(work_email)) WHERE work_email IS NOT NULL
    # This requires a functional unique index
    op.execute("""
        CREATE UNIQUE INDEX uq_employees_company_work_email 
        ON employees (company_id, LOWER(work_email)) 
        WHERE work_email IS NOT NULL
    """)
    
    # Text Search Indexes (per spec Section 9.8)
    # Create pg_trgm extension for trigram text search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    
    # Create GIN trigram index for work_email text search
    op.execute("""
        CREATE INDEX idx_employees_work_email_trgm 
        ON employees USING gin(work_email gin_trgm_ops) 
        WHERE work_email IS NOT NULL
    """)


def downgrade() -> None:
    """Drop employees table and all related indexes/constraints."""
    # Drop text search index (GIN trigram)
    op.execute("DROP INDEX IF EXISTS idx_employees_work_email_trgm")
    
    # Drop unique index for work_email (functional index)
    op.execute("DROP INDEX IF EXISTS uq_employees_company_work_email")
    
    # Drop all indexes (including functional indexes)
    op.execute("DROP INDEX IF EXISTS idx_employees_company_active_list")
    op.drop_index('idx_employees_active', table_name='employees')
    op.drop_index('idx_employees_status_active', table_name='employees')
    op.drop_index('idx_employees_company_department', table_name='employees')
    op.drop_index('idx_employees_company_status', table_name='employees')
    op.drop_index('idx_employees_company_active', table_name='employees')
    op.execute("DROP INDEX IF EXISTS idx_employees_created_at")
    op.drop_index(op.f('ix_employees_department'), table_name='employees')
    op.drop_index(op.f('ix_employees_employment_status'), table_name='employees')
    op.drop_index(op.f('ix_employees_is_active'), table_name='employees')
    op.drop_index(op.f('ix_employees_is_deleted'), table_name='employees')
    op.drop_index(op.f('ix_employees_updated_at'), table_name='employees')
    op.drop_constraint('uq_employees_user_id', 'employees', type_='unique')
    op.drop_index(op.f('ix_employees_deleted_by'), table_name='employees')
    op.drop_index(op.f('ix_employees_updated_by'), table_name='employees')
    op.drop_index(op.f('ix_employees_created_by'), table_name='employees')
    op.drop_index(op.f('ix_employees_company_id'), table_name='employees')
    op.drop_index(op.f('ix_employees_user_id'), table_name='employees')
    op.drop_index(op.f('ix_employees_id'), table_name='employees')
    
    # Drop table (this will also drop all constraints)
    op.drop_table('employees')

