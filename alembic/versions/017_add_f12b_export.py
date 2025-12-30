"""Add F12B Export Functionality for Reports & Analytics

Revision ID: 017_f12b_export
Revises: 016_f11_audit_logging
Create Date: 2025-01-20 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '017_f12b_export'
down_revision: Union[str, None] = '016_f11_audit_logging'  # Must match revision in 016_add_f11_audit_logging.py
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create exports table for F12B Export Functionality (F-012 Part B).
    
    Based on F12B_api_spec.md Section 4.1 - Export resource.
    Creates table for asynchronous PDF export requests with 24-hour TTL.
    Exports are generated asynchronously and stored as immutable snapshots of filtered report views.
    
    Business Rules:
    - Asynchronous: PDF generation happens asynchronously (non-blocking)
    - TTL: Exports expire 24 hours after creation (expires_at field)
    - Immutable: Once created, export filters are immutable (snapshot)
    - Status Flow: PENDING → PROCESSING → COMPLETED/FAILED
    - Company-scoped: All exports belong to a company (company_id NOT NULL)
    - User-owned: All exports belong to a user (user_id NOT NULL)
    - Status Values: PENDING, PROCESSING, COMPLETED, FAILED, EXPIRED
    """
    
    # Create exports table
    op.create_table(
        'exports',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Foreign Keys
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Business Fields
        sa.Column('report_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('filters', postgresql.JSON, nullable=True),
        
        # File Fields (for completed exports)
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        
        # Error Fields (for failed exports)
        sa.Column('error_message', sa.String(length=1000), nullable=True),
        
        # Timestamp Fields
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        
        # Primary Key Constraint
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(
            ['user_id'], 
            ['users.id'], 
            ondelete='RESTRICT', 
            onupdate='CASCADE', 
            name='fk_exports_user_id'
        ),
        sa.ForeignKeyConstraint(
            ['company_id'], 
            ['companies.id'], 
            ondelete='RESTRICT', 
            onupdate='CASCADE', 
            name='fk_exports_company_id'
        ),
    )
    
    # Create indexes for exports table
    # Note: Primary key index (pk_exports) is automatically created by PostgreSQL
    
    # Foreign Key Indexes (MANDATORY)
    op.create_index('idx_exports_user_id', 'exports', ['user_id'], unique=False)
    op.create_index('idx_exports_company_id', 'exports', ['company_id'], unique=False)
    
    # Business Field Indexes (MANDATORY)
    op.create_index('idx_exports_report_type', 'exports', ['report_type'], unique=False)
    op.create_index('idx_exports_status', 'exports', ['status'], unique=False)
    
    # Composite Indexes for Common Query Patterns
    # Index 1: User + status (user's export list filtering by status)
    op.create_index(
        'idx_exports_user_status', 
        'exports', 
        ['user_id', 'status'], 
        unique=False
    )
    
    # Index 2: Company + status (company's export list filtering by status)
    op.create_index(
        'idx_exports_company_status', 
        'exports', 
        ['company_id', 'status'], 
        unique=False
    )
    
    # Index 3: User + created_at DESC (user's export list sorted by creation date)
    op.execute("""
        CREATE INDEX idx_exports_user_created 
        ON exports (user_id, created_at DESC)
    """)
    
    # Index 4: Company + created_at DESC (company's export list sorted by creation date)
    op.execute("""
        CREATE INDEX idx_exports_company_created 
        ON exports (company_id, created_at DESC)
    """)
    
    # Index 5: Status + expires_at (for cleanup job to find expired exports)
    op.create_index(
        'idx_exports_status_expires', 
        'exports', 
        ['status', 'expires_at'], 
        unique=False
    )
    
    # Index 6: Report type + status (for filtering exports by report type and status)
    op.create_index(
        'idx_exports_report_status', 
        'exports', 
        ['report_type', 'status'], 
        unique=False
    )


def downgrade() -> None:
    """Drop exports table."""
    op.drop_table('exports')

