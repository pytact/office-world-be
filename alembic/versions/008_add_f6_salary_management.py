"""Add F6 Salary Management

Revision ID: 008_f6_salary_management
Revises: 007_make_user_names_nullable
Create Date: 2025-01-XX 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008_f6_salary_management'
down_revision: Union[str, None] = '007_make_user_names_nullable'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create salary management tables for F6 Salary Management.
    
    Based on F6_db_spec.md Section 7 - Salary Management (F-006).
    Creates: bank_info, salary_details, salary_payments, salary_history tables.
    """
    
    # ============================================================================
    # Table: bank_info
    # ============================================================================
    op.create_table(
        'bank_info',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Foreign Keys
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Business Fields
        sa.Column('bank_name', sa.String(length=50), nullable=False),
        sa.Column('branch', sa.String(length=255), nullable=False),
        sa.Column('account_number', sa.String(length=20), nullable=False),
        sa.Column('ifsc_code', sa.String(length=11), nullable=False),
        
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
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='RESTRICT', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        
        # Check Constraints
        sa.CheckConstraint(
            "bank_name IN ('HDFC', 'ICICI', 'SBI', 'AXIS', 'KOTAK', 'PNB', 'BOB')",
            name='chk_bank_info_bank_name'
        ),
        sa.CheckConstraint(
            "LENGTH(branch) >= 1",
            name='chk_bank_info_branch_length'
        ),
        sa.CheckConstraint(
            "LENGTH(account_number) >= 8 AND LENGTH(account_number) <= 20 AND account_number ~ '^[A-Za-z0-9]+$'",
            name='chk_bank_info_account_number'
        ),
        sa.CheckConstraint(
            "LENGTH(ifsc_code) = 11 AND ifsc_code ~ '^[A-Z]{4}0[A-Z0-9]{6}$'",
            name='chk_bank_info_ifsc_code'
        ),
    )
    
    # Indexes for bank_info
    op.create_index(op.f('ix_bank_info_id'), 'bank_info', ['id'], unique=False)
    op.create_index(op.f('ix_bank_info_employee_id'), 'bank_info', ['employee_id'], unique=False)
    
    # Unique constraint: Only one active bank_info per employee (partial unique index)
    op.execute("""
        CREATE UNIQUE INDEX uq_bank_info_employee_active 
        ON bank_info (employee_id) 
        WHERE deleted_at IS NULL
    """)
    
    # ============================================================================
    # Table: salary_details
    # ============================================================================
    op.create_table(
        'salary_details',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Foreign Keys
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Business Fields
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('payment_frequency', sa.String(length=20), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        
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
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='RESTRICT', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        
        # Check Constraints
        sa.CheckConstraint(
            "amount > 0 AND amount <= 999999999.99",
            name='chk_salary_details_amount'
        ),
        sa.CheckConstraint(
            "currency IN ('INR', 'USD', 'EUR', 'GBP', 'AUD', 'CAD')",
            name='chk_salary_details_currency'
        ),
        sa.CheckConstraint(
            "payment_frequency IN ('MONTHLY', 'BI_WEEKLY', 'WEEKLY')",
            name='chk_salary_details_payment_frequency'
        ),
        sa.CheckConstraint(
            "effective_from >= CURRENT_DATE",
            name='chk_salary_details_effective_from'
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name='chk_salary_details_effective_to'
        ),
    )
    
    # Indexes for salary_details
    op.create_index(op.f('ix_salary_details_id'), 'salary_details', ['id'], unique=False)
    op.create_index(op.f('ix_salary_details_employee_id'), 'salary_details', ['employee_id'], unique=False)
    
    # ============================================================================
    # Table: salary_payments
    # ============================================================================
    op.create_table(
        'salary_payments',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Foreign Keys
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Business Fields
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('paid_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('payment_method', sa.String(length=20), nullable=False),
        sa.Column('slip_url', sa.String(length=500), nullable=True),
        
        # Audit Fields (Immutable records - no updated_at/updated_by)
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Primary Key Constraint
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='RESTRICT', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        
        # Check Constraints
        sa.CheckConstraint(
            "amount > 0",
            name='chk_salary_payments_amount'
        ),
        sa.CheckConstraint(
            "currency IN ('INR', 'USD', 'EUR', 'GBP', 'AUD', 'CAD')",
            name='chk_salary_payments_currency'
        ),
        sa.CheckConstraint(
            "month >= 1 AND month <= 12",
            name='chk_salary_payments_month'
        ),
        sa.CheckConstraint(
            "year >= 2000 AND year <= 9999",
            name='chk_salary_payments_year'
        ),
        sa.CheckConstraint(
            "payment_method IN ('BANK_TRANSFER', 'UPI', 'CHEQUE', 'CASH')",
            name='chk_salary_payments_payment_method'
        ),
    )
    
    # Indexes for salary_payments
    op.create_index(op.f('ix_salary_payments_id'), 'salary_payments', ['id'], unique=False)
    op.create_index(op.f('ix_salary_payments_employee_id'), 'salary_payments', ['employee_id'], unique=False)
    
    # Unique constraint: Only one payment per employee per month/year
    op.create_unique_constraint('uq_salary_payments_employee_month_year', 'salary_payments', 
                                ['employee_id', 'month', 'year'])
    
    # ============================================================================
    # Table: salary_history
    # ============================================================================
    op.create_table(
        'salary_history',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Foreign Keys
        sa.Column('salary_details_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Business Fields
        sa.Column('previous_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('new_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('changed_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Audit Fields (Immutable audit log - only created_at)
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        # Primary Key Constraint
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['salary_details_id'], ['salary_details.id'], ondelete='RESTRICT', onupdate='RESTRICT'),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='SET NULL', onupdate='CASCADE'),
        
        # Check Constraints
        sa.CheckConstraint(
            "new_amount > 0",
            name='chk_salary_history_new_amount'
        ),
    )
    
    # Indexes for salary_history
    op.create_index(op.f('ix_salary_history_id'), 'salary_history', ['id'], unique=False)
    op.create_index(op.f('ix_salary_history_salary_details_id'), 'salary_history', ['salary_details_id'], unique=False)


def downgrade() -> None:
    """Drop salary management tables."""
    # Drop tables in reverse order (respecting foreign key dependencies)
    op.drop_table('salary_history')
    op.drop_table('salary_payments')
    op.drop_table('salary_details')
    
    # Drop unique index (functional index)
    op.execute("DROP INDEX IF EXISTS uq_bank_info_employee_active")
    
    op.drop_table('bank_info')

