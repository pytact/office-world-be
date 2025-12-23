"""Add F7 Project Management

Revision ID: 009_f7_project_management
Revises: 008_f6_salary_management
Create Date: 2025-01-XX 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '009_f7_project_management'
down_revision: Union[str, None] = '008_f6_salary_management'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create projects table for F7 Project Management.
    
    Based on F7_db_spec.md Section 7.1 - Project Management (F-007).
    Creates company-scoped project containers for organizing tasks.
    """
    
    # Create projects table
    op.create_table(
        'projects',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Foreign Keys
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Business Fields
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        
        # Soft Delete Field
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        
        # Audit Fields
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Primary Key Constraint
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='RESTRICT', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        
        # Check Constraints
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'COMPLETED')",
            name='chk_projects_status'
        ),
    )
    
    # Indexes for projects
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    op.create_index(op.f('ix_projects_company_id'), 'projects', ['company_id'], unique=False)
    op.create_index(op.f('ix_projects_updated_at'), 'projects', ['updated_at'], unique=False)
    
    # Unique constraint: Project name must be unique per company (case-insensitive)
    # This requires a functional unique index
    op.execute("""
        CREATE UNIQUE INDEX uq_projects_company_name 
        ON projects (company_id, LOWER(name)) 
        WHERE deleted_at IS NULL
    """)


def downgrade() -> None:
    """Drop projects table."""
    # Drop unique index (functional index)
    op.execute("DROP INDEX IF EXISTS uq_projects_company_name")
    
    # Drop indexes
    op.drop_index(op.f('ix_projects_updated_at'), table_name='projects')
    op.drop_index(op.f('ix_projects_company_id'), table_name='projects')
    op.drop_index(op.f('ix_projects_id'), table_name='projects')
    
    # Drop table
    op.drop_table('projects')

