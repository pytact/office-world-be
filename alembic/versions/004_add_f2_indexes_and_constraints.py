"""Add F2 indexes and constraints

Revision ID: 004_add_f2_indexes
Revises: 003_add_password
Create Date: 2025-01-19 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_add_f2_indexes'
down_revision: Union[str, None] = '003_add_password'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================================
    # 1. CHECK CONSTRAINT: roles.code enum (F2_db_spec.md Section 7.1)
    # ============================================================================
    op.create_check_constraint(
        'chk_roles_code',
        'roles',
        "code IN ('superadmin', 'ceo', 'hr', 'manager', 'employee')"
    )

    # ============================================================================
    # 2. PARTIAL UNIQUE INDEX: user_role_assignments.user_id (F2_db_spec.md Section 7.3)
    # ============================================================================
    # One active role assignment per user
    op.create_index(
        'uq_user_role_assignments_user_active',
        'user_role_assignments',
        ['user_id'],
        unique=True,
        postgresql_where=sa.text('is_active = true AND deleted_at IS NULL')
    )

    # ============================================================================
    # 3. MANDATORY AUDIT FIELD INDEXES (F2_db_spec.md Section 9.3)
    # ============================================================================
    # Essential for incremental sync, change tracking, and audit queries
    op.create_index('idx_roles_updated_at', 'roles', ['updated_at'])
    op.create_index('idx_users_updated_at', 'users', ['updated_at'])
    op.create_index('idx_user_role_assignments_updated_at', 'user_role_assignments', ['updated_at'])
    op.create_index('idx_companies_updated_at', 'companies', ['updated_at'])

    # ============================================================================
    # 4. JSONB GIN INDEX: roles.permissions (F2_db_spec.md Section 9.5)
    # ============================================================================
    # GIN index on permissions JSONB column for efficient permission queries
    op.create_index(
        'idx_roles_permissions_gin',
        'roles',
        ['permissions'],
        postgresql_using='gin'
    )

    # ============================================================================
    # 5. PERMISSION EVALUATION INDEXES (F2_db_spec.md Section 9.4)
    # ============================================================================
    # Note: Active user role assignment lookup (idx_user_role_assignments_active_user) 
    # is already created above as uq_user_role_assignments_user_active (same index)

    # Role permissions lookup
    op.create_index(
        'idx_roles_code',
        'roles',
        ['code'],
        postgresql_where=sa.text('deleted_at IS NULL')
    )

    # Company-scoped permission queries
    op.create_index(
        'idx_user_role_assignments_company_active',
        'user_role_assignments',
        ['company_id', 'is_active'],
        postgresql_where=sa.text('deleted_at IS NULL AND company_id IS NOT NULL')
    )

    # User activation status lookup
    op.create_index(
        'idx_users_active',
        'users',
        ['id', 'is_active'],
        postgresql_where=sa.text('deleted_at IS NULL')
    )

    # Company activation status lookup
    op.create_index(
        'idx_companies_active',
        'companies',
        ['id', 'is_active'],
        postgresql_where=sa.text('deleted_at IS NULL')
    )

    # ============================================================================
    # 6. SOFT DELETE INDEXES (F2_db_spec.md Section 9.6)
    # ============================================================================
    # Partial indexes excluding soft-deleted records
    op.create_index(
        'idx_roles_active',
        'roles',
        ['id'],
        postgresql_where=sa.text('deleted_at IS NULL')
    )
    op.create_index(
        'idx_users_active_only',
        'users',
        ['id'],
        postgresql_where=sa.text('deleted_at IS NULL')
    )
    op.create_index(
        'idx_user_role_assignments_active',
        'user_role_assignments',
        ['id'],
        postgresql_where=sa.text('deleted_at IS NULL')
    )
    op.create_index(
        'idx_companies_active_only',
        'companies',
        ['id'],
        postgresql_where=sa.text('deleted_at IS NULL')
    )

    # ============================================================================
    # 7. COMPOSITE INDEXES (F2_db_spec.md Section 9.7)
    # ============================================================================
    # Permission evaluation query: Get user's role and company context
    op.create_index(
        'idx_user_role_assignments_evaluation',
        'user_role_assignments',
        ['user_id', 'role_id', 'company_id', 'is_active'],
        postgresql_where=sa.text('deleted_at IS NULL AND is_active = true')
    )

    # Cache invalidation query: Find all users for a company
    op.create_index(
        'idx_user_role_assignments_company_users',
        'user_role_assignments',
        ['company_id', 'user_id'],
        postgresql_where=sa.text('deleted_at IS NULL AND is_active = true AND company_id IS NOT NULL')
    )

    # Cache invalidation query: Find all users with a specific role
    op.create_index(
        'idx_user_role_assignments_role_users',
        'user_role_assignments',
        ['role_id', 'user_id'],
        postgresql_where=sa.text('deleted_at IS NULL AND is_active = true')
    )

    # ============================================================================
    # 8. CASE-INSENSITIVE UNIQUE INDEXES (F2_db_spec.md Section 9.8)
    # ============================================================================
    # Unique company name (case-insensitive)
    op.create_index(
        'uq_companies_name_ci',
        'companies',
        [sa.text('LOWER(name)')],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL')
    )

    # Unique company slug (case-insensitive)
    op.create_index(
        'uq_companies_slug_ci',
        'companies',
        [sa.text('LOWER(slug)')],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL')
    )


def downgrade() -> None:
    # Drop case-insensitive unique indexes
    op.drop_index('uq_companies_slug_ci', table_name='companies')
    op.drop_index('uq_companies_name_ci', table_name='companies')

    # Drop composite indexes
    op.drop_index('idx_user_role_assignments_role_users', table_name='user_role_assignments')
    op.drop_index('idx_user_role_assignments_company_users', table_name='user_role_assignments')
    op.drop_index('idx_user_role_assignments_evaluation', table_name='user_role_assignments')

    # Drop soft delete indexes
    op.drop_index('idx_companies_active_only', table_name='companies')
    op.drop_index('idx_user_role_assignments_active', table_name='user_role_assignments')
    op.drop_index('idx_users_active_only', table_name='users')
    op.drop_index('idx_roles_active', table_name='roles')

    # Drop permission evaluation indexes
    op.drop_index('idx_companies_active', table_name='companies')
    op.drop_index('idx_users_active', table_name='users')
    op.drop_index('idx_user_role_assignments_company_active', table_name='user_role_assignments')
    op.drop_index('idx_roles_code', table_name='roles')
    # Note: idx_user_role_assignments_active_user (Section 9.4) is the same index as 
    # uq_user_role_assignments_user_active (Section 7.3) - already dropped above

    # Drop JSONB GIN index
    op.drop_index('idx_roles_permissions_gin', table_name='roles')

    # Drop mandatory audit field indexes
    op.drop_index('idx_companies_updated_at', table_name='companies')
    op.drop_index('idx_user_role_assignments_updated_at', table_name='user_role_assignments')
    op.drop_index('idx_users_updated_at', table_name='users')
    op.drop_index('idx_roles_updated_at', table_name='roles')

    # Drop partial unique index
    op.drop_index('uq_user_role_assignments_user_active', table_name='user_role_assignments')

    # Drop CHECK constraint
    op.drop_constraint('chk_roles_code', 'roles', type_='check')

