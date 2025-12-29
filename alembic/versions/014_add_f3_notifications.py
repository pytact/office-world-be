"""Add F3 Notifications

Revision ID: 014_f3_notifications
Revises: 013_fix_salary_constraint
Create Date: 2025-01-XX 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '014_f3_notifications'
down_revision: Union[str, None] = '013_fix_salary_constraint'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create notifications table for F3 Notifications.
    
    Based on F3_db_spec.md Section 7.2.1 - Notification entity with email-first 
    and in-app delivery channels, polymorphic relationships to leaves and tasks,
    read/unread state management, and complete audit trail.
    
    Business Rules:
    - Multi-tenant company scoping
    - User-scoped notification visibility
    - Polymorphic relationships to leaves and tasks
    - Read/unread state for in-app notifications
    - Soft-delete support
    """
    
    # Create notifications table
    op.create_table(
        'notifications',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Foreign Keys
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Business Fields
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('related_record_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('related_table', sa.String(length=50), nullable=True),
        sa.Column('data', postgresql.JSONB(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='sent'),
        
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
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_notifications_user_id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_notifications_company_id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_notifications_created_by'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_notifications_updated_by'),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_notifications_deleted_by'),
        
        # Check Constraints
        sa.CheckConstraint(
            "type IN ('leave_request', 'leave_approval', 'leave_rejection', 'leave_manager_approval', "
            "'task_assignment', 'task_permission_change', 'task_status_change', "
            "'user_activation', 'user_deactivation')",
            name='chk_notifications_type'
        ),
        sa.CheckConstraint(
            "channel IN ('email', 'in_app')",
            name='chk_notifications_channel'
        ),
        sa.CheckConstraint(
            "status IN ('sent', 'failed')",
            name='chk_notifications_status'
        ),
        sa.CheckConstraint(
            "(related_table IS NULL) OR (related_table IN ('leaves', 'tasks'))",
            name='chk_notifications_related_table'
        ),
        sa.CheckConstraint(
            "(related_record_id IS NULL AND related_table IS NULL) OR "
            "(related_record_id IS NOT NULL AND related_table IS NOT NULL)",
            name='chk_notifications_related_fields'
        ),
        sa.CheckConstraint(
            "(read_at IS NULL) OR (channel = 'in_app' AND is_read = true)",
            name='chk_notifications_read_at'
        ),
    )
    
    # ============================================================================
    # FOREIGN KEY INDEXES (MANDATORY)
    # ============================================================================
    op.create_index('idx_notifications_user_id', 'notifications', ['user_id'], unique=False)
    op.create_index('idx_notifications_company_id', 'notifications', ['company_id'], unique=False)
    op.create_index('idx_notifications_created_by', 'notifications', ['created_by'], unique=False)
    op.create_index('idx_notifications_updated_by', 'notifications', ['updated_by'], unique=False)
    op.create_index('idx_notifications_deleted_by', 'notifications', ['deleted_by'], unique=False)
    
    # ============================================================================
    # AUDIT FIELD INDEXES (MANDATORY)
    # ============================================================================
    op.create_index('idx_notifications_updated_at', 'notifications', ['updated_at'], unique=False)
    op.create_index('idx_notifications_created_at', 'notifications', ['created_at'], unique=False)
    op.create_index('idx_notifications_deleted_at', 'notifications', ['deleted_at'], unique=False)
    
    # ============================================================================
    # PRIMARY KEY INDEX (already created by primary key, but explicit for clarity)
    # ============================================================================
    op.create_index('idx_notifications_id', 'notifications', ['id'], unique=False)
    
    # ============================================================================
    # COMPOSITE INDEXES
    # ============================================================================
    # Index 1: User channel active (partial index for in-app notifications)
    op.create_index(
        'idx_notifications_user_channel_active',
        'notifications',
        ['user_id', 'channel', 'created_at'],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL AND channel = 'in_app'")
    )
    
    # Index 2: Company user active (partial index for list queries)
    op.create_index(
        'idx_notifications_company_user_active',
        'notifications',
        ['company_id', 'user_id', 'created_at'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL')
    )
    
    # Index 3: User unread (partial index for unread count queries)
    op.create_index(
        'idx_notifications_user_unread',
        'notifications',
        ['user_id', 'is_read', 'created_at'],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL AND channel = 'in_app' AND is_read = false")
    )
    
    # Index 4: Related record lookup (for polymorphic relationships)
    op.create_index(
        'idx_notifications_related_record',
        'notifications',
        ['related_table', 'related_record_id'],
        unique=False,
        postgresql_where=sa.text('related_record_id IS NOT NULL AND deleted_at IS NULL')
    )
    
    # ============================================================================
    # SOFT DELETE PARTIAL INDEXES
    # ============================================================================
    op.create_index(
        'idx_notifications_active',
        'notifications',
        ['id'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL')
    )
    
    # ============================================================================
    # DATABASE TRIGGER FOR updated_at
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
    
    # Create trigger for notifications table
    op.execute("""
        CREATE TRIGGER update_notifications_updated_at
        BEFORE UPDATE ON notifications
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Drop notifications table and all related indexes, constraints, and trigger."""
    
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS update_notifications_updated_at ON notifications")
    # Note: Function update_updated_at_column() may be used by other tables, so we don't drop it
    
    # Drop partial indexes
    op.drop_index('idx_notifications_active', table_name='notifications')
    op.drop_index('idx_notifications_related_record', table_name='notifications')
    op.drop_index('idx_notifications_user_unread', table_name='notifications')
    op.drop_index('idx_notifications_company_user_active', table_name='notifications')
    op.drop_index('idx_notifications_user_channel_active', table_name='notifications')
    
    # Drop primary key index
    op.drop_index('idx_notifications_id', table_name='notifications')
    
    # Drop audit field indexes
    op.drop_index('idx_notifications_deleted_at', table_name='notifications')
    op.drop_index('idx_notifications_created_at', table_name='notifications')
    op.drop_index('idx_notifications_updated_at', table_name='notifications')
    
    # Drop foreign key indexes
    op.drop_index('idx_notifications_deleted_by', table_name='notifications')
    op.drop_index('idx_notifications_updated_by', table_name='notifications')
    op.drop_index('idx_notifications_created_by', table_name='notifications')
    op.drop_index('idx_notifications_company_id', table_name='notifications')
    op.drop_index('idx_notifications_user_id', table_name='notifications')
    
    # Drop table (this will also drop all constraints)
    op.drop_table('notifications')

