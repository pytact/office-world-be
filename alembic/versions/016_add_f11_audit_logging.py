"""Add F11 Audit Logging & Activity History

Revision ID: 016_f11_audit_logging
Revises: 015_f10_attendance
Create Date: 2025-01-XX 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '016_f11_audit_logging'
down_revision: Union[str, None] = '015_f10_attendance'  # Must match revision in 015_add_f10_attendance_management.py
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create audit_logs table for F11 Audit Logging & Activity History.
    
    Based on F11_db_spec.md Section 7.1 - Audit Logging & Activity History (F-011).
    Creates immutable, append-only records of system and user actions for audit,
    compliance, and traceability.
    
    Business Rules:
    - Immutable: Once created, cannot be updated or deleted
    - Append-only: New records only, no modifications
    - Company-scoped: All records belong to a company (company_id NOT NULL)
    - Asynchronous: Written asynchronously without blocking business operations
    - SYSTEM actions: actor_id is NULL for system-generated actions
    """
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Relationship Fields
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Action Fields
        sa.Column('action_code', sa.String(length=100), nullable=False),
        sa.Column('table_name', sa.String(length=100), nullable=False),
        sa.Column('record_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Change Tracking Fields (JSONB partial snapshots)
        sa.Column('old_values', postgresql.JSONB, nullable=True),
        sa.Column('new_values', postgresql.JSONB, nullable=True),
        
        # Metadata Fields
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('description', sa.String(length=1000), nullable=True),
        
        # Timestamp Fields
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        # Primary Key Constraint
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(
            ['company_id'], 
            ['companies.id'], 
            ondelete='RESTRICT', 
            onupdate='CASCADE', 
            name='fk_audit_logs_company_id'
        ),
        sa.ForeignKeyConstraint(
            ['actor_id'], 
            ['users.id'], 
            ondelete='SET NULL', 
            onupdate='CASCADE', 
            name='fk_audit_logs_actor_id'
        ),
    )
    
    # Create indexes for audit_logs table
    # Note: Primary key index (pk_audit_logs) is automatically created by PostgreSQL
    
    # Foreign Key Indexes (MANDATORY)
    op.create_index('idx_audit_logs_company_id', 'audit_logs', ['company_id'], unique=False)
    op.create_index('idx_audit_logs_actor_id', 'audit_logs', ['actor_id'], unique=False)
    
    # Audit Field Index (MANDATORY)
    op.create_index('idx_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)
    
    # Composite Indexes for Common Query Patterns
    # Index 1: Company + created_at DESC (most common query pattern)
    op.execute("""
        CREATE INDEX idx_audit_logs_company_created 
        ON audit_logs (company_id, created_at DESC)
    """)
    
    # Index 2: Company + action_code
    op.create_index(
        'idx_audit_logs_company_action', 
        'audit_logs', 
        ['company_id', 'action_code'], 
        unique=False
    )
    
    # Index 3: Company + table_name (Manager role filtering)
    op.create_index(
        'idx_audit_logs_company_table', 
        'audit_logs', 
        ['company_id', 'table_name'], 
        unique=False
    )
    
    # Index 4: Company + created_at DESC + action_code
    op.execute("""
        CREATE INDEX idx_audit_logs_company_created_action 
        ON audit_logs (company_id, created_at DESC, action_code)
    """)
    
    # Index 5: Company + created_at DESC + table_name (Manager role queries with date)
    op.execute("""
        CREATE INDEX idx_audit_logs_company_created_table 
        ON audit_logs (company_id, created_at DESC, table_name)
    """)


def downgrade() -> None:
    """Drop audit_logs table."""
    op.drop_table('audit_logs')

